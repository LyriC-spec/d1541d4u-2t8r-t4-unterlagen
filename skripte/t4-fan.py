#!/usr/bin/env python3
"""
t4-fan.py - Luefterregelung fuer das ASRock Rack D1541D4U-2T8R mit Tesla T4

Der BMC (AMI MegaRAC, ASRock-Firmware 0.16/0.22) stellt alle Luefter mit
einem einzigen Befehl:

    ipmitool raw 0x3a 0x01 <8 Bytes>

Ein Byte je Anschluss, Wert 0x01-0x64 = Duty in Prozent, 0x00 = Automatik
des BMC. Reihenfolge, am 04.10.2026 einzeln ausgemessen:

    1 CPU_FAN1   reagiert nicht, laeuft fest auf ~4400 U/min -> 0x00
    2 CPU_FAN2   auf diesem Board nicht vorhanden            -> 0x00
    3 REAR_FAN1  2x Noctua 60 mm am Y-Kabel, Gehaeuse hinten -> Zone "gehaeuse"
                 (nur einer der beiden meldet seine Drehzahl)
    4 REAR_FAN2  nicht vorhanden                             -> 0x00
    5 FRNT_FAN1  nicht belegt                                -> 0x00
    6 FRNT_FAN2  Radiallüfter (Blower) der T4                -> Zone "blower"
    7 FRNT_FAN3  kuehlt Chipsatz und den 10G-Baustein X540   -> Zone "netz"
    8 FRNT_FAN4  nicht belegt                                -> 0x00

Ein Lueftermodus wie bei Supermicro ("Full") existiert nicht, der BMC
uebernimmt geschriebene Werte direkt. Die einzige Drehzahlschwelle ist
Lower Non-Critical 100 U/min; selbst bei 15 % Duty (Rear 300 U/min) hat der
BMC keinen Luefterfehler gemeldet. Die Untergrenze von 30 % ist deshalb keine
BMC-Grenze, sondern entspricht dem, was die BMC-Automatik im Leerlauf selbst
faehrt.

Zonen:
  blower   = GPU-Kurve. Bei unbekanntem GPU-Zustand Vollast.
  gehaeuse = Maximum aus Platten- und CPU-Kurve.
  netz     = Maximum aus X540- und Chipsatzkurve. Die X540-Temperatur gibt es
             nur ueber IPMI, alle anderen Werte kommen aus sysfs und
             nvidia-smi.

Messgrundlage: siehe Kopf von CURVE_GPU und die Dokumentation im Repository.
"""
import os
import subprocess
import sys
import signal
import time
import logging
from collections import deque
from logging.handlers import RotatingFileHandler

INTERVAL = 10          # Sekunden je Regelschritt
SMOOTH_N = 6           # gleitender Mittelwert ueber 6 Messungen = 60 s
HYST = 4               # erst ab 4 Punkten Differenz herunterschalten
DOWN_STEP = 5          # und dann hoechstens 5 Punkte je Schritt
REASSERT_S = 30        # Stellwerte spaetestens alle 30 s erneut schreiben
X540_EVERY = 3         # X540 nur jeden dritten Takt per IPMI lesen (KCS schonen)
HEARTBEAT = "/tmp/t4-fan.heartbeat"
LOGFILE = "/mnt/scripts/t4-fan.log"

DUTY_MIN, DUTY_MAX = 30, 100

# (Temperatur C, Duty Prozent) - dazwischen wird linear interpoliert
CURVE_GPU = [(45, 30), (55, 50), (62, 70), (68, 90), (72, 100)]
CURVE_CPU = [(55, 30), (70, 45), (80, 65), (88, 85), (95, 100)]
CURVE_DISK = [(40, 30), (45, 50), (50, 70), (55, 90), (58, 100)]
CURVE_X540 = [(55, 30), (65, 50), (75, 75), (85, 100)]
CURVE_PCH = [(55, 30), (65, 50), (75, 75), (85, 100)]

EMERG = {"gpu": 80, "cpu": 92, "disk": 58, "x540": 95, "pch": 90}

log = logging.getLogger("t4-fan")
log.setLevel(logging.INFO)
_h = RotatingFileHandler(LOGFILE, maxBytes=512 * 1024, backupCount=2)
_h.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S"))
log.addHandler(_h)


def ipmi(args, timeout=15):
    try:
        r = subprocess.run(["ipmitool"] + args, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode == 0, r.stdout
    except Exception:
        return False, ""


def set_fans(blower, gehaeuse, netz):
    """Alle acht Bytes in einem Befehl, bis zu drei Versuche."""
    werte = [0, 0, gehaeuse, 0, 0, blower, netz, 0]
    args = ["raw", "0x3a", "0x01"] + ["0x%02x" % w for w in werte]
    for _ in range(3):
        ok, _out = ipmi(args)
        if ok:
            return True
        time.sleep(2)
    log.warning("Stellwerte %s konnten nicht gesetzt werden", werte)
    return False


def _hwmon(name, alle=True):
    """Hoechster Temperaturwert aller hwmon-Geraete dieses Namens."""
    best = -1
    base = "/sys/class/hwmon"
    try:
        geraete = os.listdir(base)
    except OSError:
        return best
    for d in geraete:
        pfad = os.path.join(base, d)
        try:
            with open(os.path.join(pfad, "name")) as fh:
                if fh.read().strip() != name:
                    continue
            for f in os.listdir(pfad):
                if f.startswith("temp") and f.endswith("_input"):
                    with open(os.path.join(pfad, f)) as fh:
                        v = int(fh.read().strip()) // 1000
                    if 0 < v < 150:
                        best = max(best, v)
        except (OSError, ValueError):
            continue
    return best


def gpu_temp():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10)
        werte = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
        return max(werte) if werte else -1
    except Exception:
        return -1


def x540_temp():
    ok, out = ipmi(["sdr", "get", "X540 Temp"])
    if not ok:
        return -1
    for zeile in out.splitlines():
        if "Sensor Reading" in zeile:
            try:
                v = int(zeile.split(":", 1)[1].split()[0])
                return v if 0 < v < 150 else -1
            except (IndexError, ValueError):
                return -1
    return -1


def curve(punkte, temp):
    """Lineare Interpolation. None, wenn kein Messwert vorliegt."""
    if temp is None or temp < 0:
        return None
    if temp <= punkte[0][0]:
        return punkte[0][1]
    if temp >= punkte[-1][0]:
        return punkte[-1][1]
    for (t0, d0), (t1, d1) in zip(punkte, punkte[1:]):
        if t0 <= temp <= t1:
            spanne = t1 - t0
            return int(d0 + (d1 - d0) * (temp - t0) / spanne) if spanne else d1
    return punkte[-1][1]


class Glaetter:
    def __init__(self, n):
        self.buf = deque(maxlen=n)

    def add(self, v):
        if v is not None and v >= 0:
            self.buf.append(v)
        return self.mittel()

    def mittel(self):
        return sum(self.buf) / len(self.buf) if self.buf else None


def naechster_duty(aktuell, ziel):
    """Nach oben sofort, nach unten gebremst (Hysterese am Duty-Wert)."""
    if aktuell is None:
        return ziel
    if ziel > aktuell:
        return ziel
    if aktuell - ziel < HYST:
        return aktuell
    return max(ziel, aktuell - DOWN_STEP, DUTY_MIN)


def vollast(grund):
    log.warning("Vollast: %s", grund)
    set_fans(100, 100, 100)


def beenden(signum=None, frame=None):
    vollast("Dienst wird beendet")
    sys.exit(0)


signal.signal(signal.SIGTERM, beenden)
signal.signal(signal.SIGINT, beenden)


def main():
    log.info("gestartet (Takt %ss, Mittelwert ueber %s Messungen, Hysterese %s)",
             INTERVAL, SMOOTH_N, HYST)
    schluessel = ("gpu", "cpu", "disk", "x540", "pch")
    glatt = {k: Glaetter(SMOOTH_N) for k in schluessel}
    duty = {"blower": None, "gehaeuse": None, "netz": None}
    letzte_schreibung = 0.0
    x540 = -1
    takt = 0

    while True:
        if takt % X540_EVERY == 0:
            x540 = x540_temp()
        takt += 1
        roh = {"gpu": gpu_temp(), "cpu": _hwmon("coretemp"),
               "disk": _hwmon("drivetemp"), "x540": x540,
               "pch": _hwmon("pch_haswell")}
        mittel = {k: glatt[k].add(v) for k, v in roh.items()}

        def bedarf(punkte, k):
            """Nach oben auf den Rohwert, nach unten auf den Mittelwert."""
            werte = [x for x in (curve(punkte, mittel[k]), curve(punkte, roh[k]))
                     if x is not None]
            return max(werte) if werte else None

        def zone(*bedarfe):
            werte = [x for x in bedarfe if x is not None]
            return max(werte) if werte else DUTY_MAX

        if roh["gpu"] < 0:
            ziel_blower = DUTY_MAX   # Karte antwortet nicht - nie leise
        else:
            ziel_blower = zone(bedarf(CURVE_GPU, "gpu"))
        ziel_gehaeuse = zone(bedarf(CURVE_DISK, "disk"), bedarf(CURVE_CPU, "cpu"))
        ziel_netz = zone(bedarf(CURVE_X540, "x540"), bedarf(CURVE_PCH, "pch"))

        notfall = ["%s %d C" % (k, roh[k]) for k in schluessel
                   if roh[k] >= EMERG[k]]
        if notfall:
            neu = {"blower": 100, "gehaeuse": 100, "netz": 100}
            log.warning("NOTFALL (%s) -> alle Zonen Vollast", ", ".join(notfall))
        else:
            ziele = {"blower": ziel_blower, "gehaeuse": ziel_gehaeuse,
                     "netz": ziel_netz}
            neu = {z: naechster_duty(duty[z],
                                     max(DUTY_MIN, min(DUTY_MAX, ziele[z])))
                   for z in ziele}

        jetzt = time.time()
        faellig = (jetzt - letzte_schreibung) >= REASSERT_S
        if neu != duty or faellig:
            set_fans(neu["blower"], neu["gehaeuse"], neu["netz"])
            letzte_schreibung = jetzt

        if neu != duty:
            log.info("GPU %s C  CPU %s C  Platten %s C  X540 %s C  PCH %s C  ->  "
                     "Blower %s%%  Gehaeuse %s%%  Netz %s%%",
                     roh["gpu"], roh["cpu"], roh["disk"], roh["x540"], roh["pch"],
                     neu["blower"], neu["gehaeuse"], neu["netz"])
        duty = neu

        try:
            with open(HEARTBEAT, "w") as fh:
                fh.write("%d %d %d %d\n" % (int(jetzt), neu["blower"],
                                            neu["gehaeuse"], neu["netz"]))
        except OSError:
            pass

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        log.exception("Unerwarteter Fehler: %s", e)
        vollast("Dienst abgestuerzt")
        sys.exit(1)
