"""Grafische Konsole: originaler AMI-JViewer unter Xvfb.

Ablauf wie im Browser: Anmeldung an der BMC-Weboberflaeche, JNLP mit
KVM-Token holen, JViewer direkt mit java -cp starten. Ueber HTTP (nicht
HTTPS) angemeldet, liefert dieser BMC -kvmsecure 0 -kvmport 80; so braucht
Java kein TLS 1.0. Das Bild holt x11vnc vom Xvfb-Bildschirm, noVNC zeigt es
im Browser.
"""
import logging
import os
import re
import signal
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
import zipfile

import requests

log = logging.getLogger("kvm")

JARS = ["JViewer.jar", "JViewer-SOC.jar", "Linux_x86_64.jar"]


class KvmError(Exception):
    pass


class BmcWeb:
    """Minimaler Client fuer die alte MegaRAC-Weboberflaeche."""

    def __init__(self, host, user, password, timeout=15):
        self.base = "http://%s" % host
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.cookie = None
        self.csrf = None

    def login(self):
        r = requests.post(self.base + "/rpc/WEBSES/create.asp",
                          data={"WEBVAR_USERNAME": self.user,
                                "WEBVAR_PASSWORD": self.password},
                          timeout=self.timeout)
        r.raise_for_status()
        m = re.search(r"'SESSION_COOKIE'\s*:\s*'([^']*)'", r.text)
        t = re.search(r"'CSRFTOKEN'\s*:\s*'([^']*)'", r.text)
        wert = m.group(1) if m else ""
        if not wert or wert.startswith("Failure"):
            grund = "Benutzer oder Kennwort falsch" if "Login" in wert else (wert or "keine Antwort")
            raise KvmError("Anmeldung an der BMC-Weboberflaeche fehlgeschlagen (%s)" % grund)
        self.cookie = wert
        self.csrf = t.group(1) if t else ""

    def _get(self, pfad, **kw):
        return requests.get(self.base + pfad, timeout=kw.pop("timeout", self.timeout),
                            cookies={"SessionCookie": self.cookie,
                                     "Username": self.user, "lang": "EN"},
                            headers={"CSRFTOKEN": self.csrf}, **kw)

    def jnlp_arguments(self):
        r = self._get("/Java/jviewer.jnlp",
                      params={"EXTRNIP": self.host, "JNLPSTR": "JViewer"})
        r.raise_for_status()
        try:
            wurzel = ET.fromstring(r.text.strip())
        except ET.ParseError as e:
            raise KvmError("JNLP nicht lesbar (Sitzung abgelaufen?): %s" % e)
        args = [a.text or "" for a in wurzel.iter("argument")]
        if "-kvmtoken" not in args:
            raise KvmError("JNLP ohne KVM-Token - fehlt dem Benutzer das KVM-Recht?")
        return args

    def download(self, name, ziel):
        r = requests.get(self.base + "/Java/release/" + name, timeout=60, stream=True)
        r.raise_for_status()
        tmp = ziel + ".neu"
        with open(tmp, "wb") as fh:
            for block in r.iter_content(65536):
                fh.write(block)
        if not zipfile.is_zipfile(tmp):
            os.remove(tmp)
            raise KvmError("Download von %s ist keine gueltige JAR" % name)
        os.replace(tmp, ziel)

    def logout(self, timeout=None):
        if not self.cookie:
            return
        try:
            self._get("/rpc/WEBSES/logout.asp", timeout=timeout or self.timeout)
        except requests.RequestException:
            pass
        self.cookie = None


class Kvm:
    def __init__(self, host, user, password, data_dir="/data", display=":1"):
        self.host, self.user, self.password = host, user, password
        self.jar_dir = os.path.join(data_dir, "jviewer")
        self.native_dir = os.path.join(self.jar_dir, "native")
        self.logfile = os.path.join(data_dir, "jviewer.log")
        self.display = display
        self.proc = None
        self.web = None
        self.gestartet = None
        self.fehler = None
        self.gestoppt = False          # True, wenn wir selbst beendet haben
        self.lock = threading.Lock()   # schuetzt nur den Zustand, nie Netzarbeit
        self.start_lock = threading.Lock()

    # --- Hilfen ---------------------------------------------------------

    def _env(self):
        return dict(os.environ, DISPLAY=self.display)

    def _jars_bereit(self, erneuern=False):
        os.makedirs(self.native_dir, exist_ok=True)
        web = BmcWeb(self.host, self.user, self.password)
        for name in JARS:
            ziel = os.path.join(self.jar_dir, name)
            if erneuern or not os.path.exists(ziel):
                log.info("Lade %s vom BMC", name)
                web.download(name, ziel)
        for name in JARS:
            ziel = os.path.join(self.jar_dir, name)
            if not zipfile.is_zipfile(ziel):
                os.remove(ziel)
                raise KvmError("%s war beschaedigt und wurde geloescht - bitte erneut starten" % name)
        # native Bibliotheken auspacken (Laufwerksumleitung unter Linux)
        with zipfile.ZipFile(os.path.join(self.jar_dir, "Linux_x86_64.jar")) as z:
            for n in z.namelist():
                if n.endswith(".so"):
                    with open(os.path.join(self.native_dir, os.path.basename(n)), "wb") as fh:
                        fh.write(z.read(n))

    def _log_ende(self, n=12):
        try:
            with open(self.logfile, "rb") as fh:
                fh.seek(0, 2)
                fh.seek(max(0, fh.tell() - 4000))
                zeilen = fh.read().decode(errors="replace").splitlines()[-n:]
        except OSError:
            return []
        # Token und Cookies nie ausgeben
        return [re.sub(r"(-kvmtoken|-webcookie)\s+\S+", r"\1 ***", z) for z in zeilen]

    def aufraeumen_beim_start(self):
        """Verwaiste Viewer aus einem frueheren Lauf der App beenden."""
        subprocess.run(["pkill", "-f", "com.ami.kvm.jviewer.JViewer"], capture_output=True)

    # --- Zustand --------------------------------------------------------

    def status(self):
        web_alt = None
        if not self.lock.acquire(timeout=0.5):
            return {"laeuft": False, "startet": True, "seit": None, "fehler": None,
                    "log": self._log_ende()}
        try:
            laeuft = self.proc is not None and self.proc.poll() is None
            if self.proc is not None and not laeuft:
                code = self.proc.returncode
                if not self.gestoppt:
                    self.fehler = "Viewer hat sich beendet (Code %s)" % code
                log.info("Konsole: JViewer beendet (Code %s)", code)
                web_alt = self._zuruecksetzen()
            ergebnis = {"laeuft": laeuft, "startet": self.start_lock.locked() and not laeuft,
                        "seit": self.gestartet if laeuft else None,
                        "fehler": self.fehler, "log": self._log_ende()}
        finally:
            self.lock.release()
        if web_alt:
            web_alt.logout()
        return ergebnis

    def _zuruecksetzen(self):
        """Nur unter self.lock aufrufen. Gibt die alte BMC-Websitzung zurueck,
        damit der Logout ausserhalb der Sperre laufen kann."""
        web, self.web = self.web, None
        self.proc = None
        self.gestartet = None
        return web

    # --- Start und Stopp ------------------------------------------------

    def start(self, jars_erneuern=False):
        if not self.start_lock.acquire(blocking=False):
            raise KvmError("Die Konsole wird bereits gestartet")
        try:
            with self.lock:
                if self.proc is not None and self.proc.poll() is None:
                    return
                self.fehler = None
            web = None
            try:
                self._jars_bereit(jars_erneuern)
                web = BmcWeb(self.host, self.user, self.password)
                web.login()
                args = web.jnlp_arguments()
            except (requests.RequestException, KvmError, OSError, zipfile.BadZipFile) as e:
                if web:
                    web.logout()
                with self.lock:
                    self.fehler = str(e)
                raise KvmError(str(e))
            cp = ":".join(os.path.join(self.jar_dir, j) for j in JARS[:2])
            cmd = ["java", "-Xmx256m",
                   "-Djava.library.path=" + self.native_dir,
                   "-Dsun.java2d.xrender=false",
                   "-cp", cp, "com.ami.kvm.jviewer.JViewer"] + args
            with open(self.logfile, "ab") as fh:
                fh.write(("\n=== Start %s ===\n" % time.strftime("%F %T")).encode())
                fh.flush()
                proc = subprocess.Popen(cmd, env=self._env(), stdout=fh,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            with self.lock:
                self.proc, self.web = proc, web
                self.gestartet = time.time()
                self.gestoppt = False
            log.info("JViewer gestartet, PID %s", proc.pid)
            threading.Thread(target=self._ausschnitt_folgen, args=(proc,), daemon=True).start()
        finally:
            self.start_lock.release()

    def stop(self, grund="beendet", logout_timeout=None):
        with self.lock:
            proc = self.proc
            self.gestoppt = True
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=8)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        with self.lock:
            web = self._zuruecksetzen() if self.proc is proc else None
            self.fehler = None
        if web:
            web.logout(timeout=logout_timeout)
        if proc is not None:
            log.info("Konsole: %s", grund)

    # --- Bildausschnitt -------------------------------------------------

    def _ausschnitt_folgen(self, proc):
        """x11vnc auf das JViewer-Hauptfenster zuschneiden.

        Der Xvfb-Bildschirm ist groesser als jedes Fenster, das der JViewer
        oeffnet. Ohne Zuschnitt saehe man im Browser schwarze Raender. Aendert
        sich die Aufloesung des Servers (BIOS 800x600, Betriebssystem 1024x768),
        passt JViewer sein Fenster an, und der Zuschnitt zieht nach.
        """
        env = self._env()
        letzter = None
        while proc.poll() is None:
            try:
                r = subprocess.run(["xdotool", "search", "--name", r"^JViewer \["],
                                   capture_output=True, text=True, env=env, timeout=5)
                ids = r.stdout.split()
                if ids:
                    g = subprocess.run(["xdotool", "getwindowgeometry", "--shell", ids[0]],
                                       capture_output=True, text=True, env=env, timeout=5)
                    w = dict(z.split("=", 1) for z in g.stdout.split() if "=" in z)
                    clip = "%sx%s+%s+%s" % (w.get("WIDTH"), w.get("HEIGHT"), w.get("X"), w.get("Y"))
                    if clip != letzter and int(w.get("WIDTH", 0)) > 100:
                        self._x11vnc("clip:" + clip)
                        letzter = clip
            except (subprocess.SubprocessError, ValueError, OSError) as e:
                log.debug("Zuschnitt: %s", e)
            time.sleep(2)
        # ganzer Bildschirm wieder sichtbar
        try:
            g = subprocess.run(["xdotool", "getdisplaygeometry"], capture_output=True,
                               text=True, env=env, timeout=5).stdout.split()
            if len(g) == 2:
                self._x11vnc("clip:%sx%s+0+0" % (g[0], g[1]))
        except (subprocess.SubprocessError, OSError):
            pass

    def _x11vnc(self, befehl):
        subprocess.run(["x11vnc", "-display", self.display, "-R", befehl],
                       capture_output=True, env=self._env(), timeout=10)
        log.info("x11vnc %s", befehl)
