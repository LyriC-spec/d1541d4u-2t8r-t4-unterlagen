"""IPMI-Zugriff auf den BMC ueber das Netz (ipmitool lanplus).

Alle Aufrufe laufen ueber eine Sperre nacheinander: Der alte MegaRAC-BMC
verkraftet parallele RMCP+-Sitzungen schlecht. Das Passwort geht per
Umgebungsvariable an ipmitool (-E), damit es nicht in der Prozessliste steht.

Gemessen an diesem BMC (ASRock D1541D4U-2T8R, Firmware 0.16):
  sdr elist mit SDR-Cache  ~0,3 s   -> Messwerte alle 10 s
  sensor (mit Schwellen)   ~3,8 s   -> Schwellwerte alle 5 min
  raw/chassis/sel          ~0,1 s
"""
import logging
import os
import re
import subprocess
import threading
import time
from collections import deque

log = logging.getLogger("ipmi")


class IpmiError(Exception):
    pass


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


class Ipmi:
    def __init__(self, host, user, password, cipher="3", cache_dir="/data"):
        self.host = host
        self.user = user
        self.password = password
        self.cipher = cipher
        self.sdr_cache = os.path.join(cache_dir, "sdr.cache")
        self.lock = threading.Lock()

    def _base(self):
        return ["ipmitool", "-I", "lanplus", "-H", self.host, "-U", self.user,
                "-E", "-C", self.cipher, "-N", "3", "-R", "2"]

    def run(self, args, timeout=30, use_cache=False):
        cmd = self._base()
        if use_cache and os.path.exists(self.sdr_cache):
            cmd += ["-S", self.sdr_cache]
        cmd += list(args)
        env = dict(os.environ, IPMI_PASSWORD=self.password)
        with self.lock:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=timeout, env=env)
            except subprocess.TimeoutExpired:
                raise IpmiError("Zeitueberschreitung bei: %s" % " ".join(args))
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()
            raise IpmiError(msg[-1] if msg else "ipmitool-Fehler %d" % r.returncode)
        return r.stdout

    # --- SDR / Sensoren -------------------------------------------------

    def refresh_sdr_cache(self):
        tmp = self.sdr_cache + ".neu"
        self.run(["sdr", "dump", tmp], timeout=60)
        os.replace(tmp, self.sdr_cache)

    def sensor_values(self):
        """Schnelle Messwerte: Name, Wert, Einheit, Status."""
        out = self.run(["sdr", "elist", "full"], use_cache=True)
        werte = {}
        for zeile in out.splitlines():
            teile = [t.strip() for t in zeile.split("|")]
            if len(teile) < 5:
                continue
            name, _id, status, _entity, lesung = teile[:5]
            m = re.match(r"^(-?[0-9.]+)\s*(.*)$", lesung)
            if m:
                wert, einheit = float(m.group(1)), m.group(2)
            else:
                wert, einheit = None, lesung
            werte[name] = {"name": name, "wert": wert, "einheit": einheit,
                           "status": status}
        return werte

    def sensor_thresholds(self):
        """Langsame Vollabfrage mit Schwellwerten."""
        out = self.run(["sensor"], timeout=60)
        schwellen = {}
        for zeile in out.splitlines():
            t = [x.strip() for x in zeile.split("|")]
            if len(t) < 10:
                continue
            schwellen[t[0]] = {
                "einheit": t[2], "status": t[3],
                "lnr": _num(t[4]), "lcr": _num(t[5]), "lnc": _num(t[6]),
                "unc": _num(t[7]), "ucr": _num(t[8]), "unr": _num(t[9]),
            }
        return schwellen

    # --- Lueftersteuerung (ASRock Rack, netfn 0x3a) ----------------------

    def fan_duties(self):
        out = self.run(["raw", "0x3a", "0x02"])
        werte = [int(x, 16) for x in out.split()]
        if len(werte) != 8:
            raise IpmiError("Unerwartete Antwort auf 0x3a 0x02: %r" % out.strip())
        return werte

    def set_fan_duties(self, werte):
        if len(werte) != 8 or any(not (0 <= w <= 100) for w in werte):
            raise IpmiError("Ungueltige Stellwerte: %r" % (werte,))
        self.run(["raw", "0x3a", "0x01"] + ["0x%02x" % w for w in werte])

    # --- Stromversorgung --------------------------------------------------

    def power_status(self):
        out = self.run(["chassis", "power", "status"]).strip().lower()
        if out.endswith(" on"):
            return "an"
        if out.endswith(" off"):
            return "aus"
        return "unbekannt"

    def power(self, aktion):
        erlaubt = {"on": "on", "soft": "soft", "off": "off",
                   "reset": "reset", "cycle": "cycle"}
        if aktion not in erlaubt:
            raise IpmiError("Unbekannte Aktion")
        return self.run(["chassis", "power", erlaubt[aktion]]).strip()

    def boot_into_bios(self):
        """Naechster Start ins BIOS-Setup, danach bootet der Host normal.

        no-timeout ist noetig: Dieser BMC verwirft die Vorgabe sonst nach
        60 s (gemessen 04.10.2026), wenn bis dahin kein Neustart kam."""
        return self.run(["chassis", "bootparam", "set", "bootflag", "force_bios",
                         "options=no-timeout"]).strip()

    def boot_flag_clear(self):
        # options=timeout stellt Parameter 3 wieder auf den Werkszustand (00)
        return self.run(["chassis", "bootparam", "set", "bootflag", "none",
                         "options=timeout"]).strip()

    def boot_flag(self):
        """Startvorgabe aus Bootparameter 5. Ist das Valid-Bit geloescht,
        gilt der Selektor nicht mehr (der BMC verwirft die Vorgabe laut
        IPMI-Spezifikation, wenn nicht innerhalb von 60 s neu gestartet wird)."""
        out = self.run(["chassis", "bootparam", "get", "5"])
        if "Boot Flag Invalid" in out:
            return "keine Vorgabe"
        for zeile in out.splitlines():
            if "Boot Device Selector" in zeile:
                return zeile.split(":", 1)[1].strip()
        return "unbekannt"

    def chassis_status(self):
        out = self.run(["chassis", "status"])
        d = {}
        for zeile in out.splitlines():
            if ":" in zeile:
                k, v = zeile.split(":", 1)
                d[k.strip()] = v.strip()
        return d

    # --- Ereignisprotokoll -----------------------------------------------

    def sel_list(self):
        out = self.run(["sel", "elist"], use_cache=True, timeout=60)
        eintraege = []
        for zeile in out.splitlines():
            t = [x.strip() for x in zeile.split("|")]
            if len(t) < 5:
                continue
            eintraege.append({"id": t[0], "datum": t[1], "zeit": t[2],
                              "sensor": t[3], "ereignis": t[4],
                              "richtung": t[5] if len(t) > 5 else ""})
        eintraege.reverse()   # neueste zuerst
        return eintraege

    def sel_info(self):
        return self._kv(self.run(["sel", "info"]))

    def sel_clear(self):
        return self.run(["sel", "clear"]).strip()

    def bmc_time(self):
        return self.run(["sel", "time", "get"]).strip()

    def set_bmc_time(self, zeitpunkt):
        # ipmitool erwartet "MM/DD/YYYY HH:MM:SS"
        return self.run(["sel", "time", "set", zeitpunkt]).strip()

    # --- Informationen ----------------------------------------------------

    def mc_info(self):
        return self._kv(self.run(["mc", "info"]))

    def lan_info(self):
        return self._kv(self.run(["lan", "print", "1"]))

    def fru(self):
        return self._kv(self.run(["fru", "print", "0"]))

    def mc_reset(self):
        return self.run(["mc", "reset", "cold"]).strip()

    @staticmethod
    def _kv(text):
        d = {}
        letzter = None
        for zeile in text.splitlines():
            if ":" in zeile and not zeile.startswith(" " * 20):
                k, v = zeile.split(":", 1)
                k = k.strip()
                if k:
                    d[k] = v.strip()
                    letzter = k
            elif letzter and zeile.strip():
                d[letzter] += " " + zeile.strip()
        return d


class Poller:
    """Fragt den BMC im Hintergrund ab und haelt die Ergebnisse vor.

    Die Weboberflaeche liest nur aus diesem Zwischenspeicher, sie loest
    selbst keine BMC-Abfragen fuer Sensoren aus.
    """

    WERTE_ALLE = 10        # s
    SCHWELLEN_ALLE = 300   # s
    VERLAUF = 360          # Messpunkte = 1 h bei 10 s

    def __init__(self, ipmi):
        self.ipmi = ipmi
        self.daten = {"sensoren": {}, "schwellen": {}, "luefter": None,
                      "strom": None, "fehler": None, "stand": None}
        self.verlauf = {}
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self._wach = threading.Event()

    def start(self):
        threading.Thread(target=self._lauf, name="poller", daemon=True).start()

    def stop(self):
        self._stop.set()
        self._wach.set()

    def jetzt_aktualisieren(self):
        self._wach.set()

    def snapshot(self):
        with self.lock:
            return {k: v for k, v in self.daten.items()}

    def history_all(self, n):
        with self.lock:
            return {k: list(v)[-n:] for k, v in self.verlauf.items()}

    def _lauf(self):
        letzte_schwellen = 0
        cache_ok = False
        while not self._stop.is_set():
            t0 = time.time()
            fehler = []
            try:
                if not cache_ok:
                    self.ipmi.refresh_sdr_cache()
                    cache_ok = True
                werte = self.ipmi.sensor_values()
                # Messwerte sofort sichern - spaetere Teilabfragen duerfen sie nicht verwerfen
                with self.lock:
                    self.daten.update(sensoren=werte, stand=t0)
                    for name, s in werte.items():
                        if s["wert"] is not None:
                            v = self.verlauf.setdefault(name, deque(maxlen=self.VERLAUF))
                            v.append((int(t0), s["wert"]))
            except IpmiError as e:
                fehler.append(str(e))
                log.warning("Messwerte nicht lesbar: %s", e)
                cache_ok = False
            except Exception as e:  # noqa: BLE001
                fehler.append("Interner Fehler: %s" % e)
                log.exception("Poller")

            if t0 - letzte_schwellen > self.SCHWELLEN_ALLE:
                # auch bei Fehlschlag erst nach SCHWELLEN_ALLE wieder versuchen:
                # die Vollabfrage blockiert die IPMI-Sperre bis zu 60 s
                letzte_schwellen = t0
                try:
                    schwellen = self.ipmi.sensor_thresholds()
                    with self.lock:
                        self.daten["schwellen"] = schwellen
                except IpmiError as e:
                    log.warning("Schwellwerte nicht lesbar: %s", e)

            try:
                luefter = self.ipmi.fan_duties()
            except IpmiError as e:
                luefter = None
                log.warning("Luefterwerte nicht lesbar: %s", e)
            try:
                strom = self.ipmi.power_status()
            except IpmiError as e:
                strom = "unbekannt"
                fehler.append(str(e))
            with self.lock:
                self.daten.update(luefter=luefter, strom=strom,
                                  fehler="; ".join(fehler) or None)
            self._wach.wait(max(1.0, self.WERTE_ALLE - (time.time() - t0)))
            self._wach.clear()
