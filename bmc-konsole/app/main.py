"""BMC-Konsole: Weboberflaeche fuer einen alten AMI-MegaRAC-BMC.

Laeuft hinter nginx im selben Container. nginx fragt fuer noVNC und den
WebSocket per auth_request /api/auth/check nach, ob die Sitzung gueltig ist.
"""
import atexit
import hashlib
import hmac
import json
import logging
import os
import secrets
import signal
import sys
import threading
import time
from functools import wraps

from flask import Flask, abort, jsonify, request, send_from_directory, session

from ipmi import Ipmi, IpmiError, Poller
from kvm import Kvm, KvmError

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("app")

DATA = os.environ.get("DATA_DIR", "/data")
WEB = os.environ.get("WEB_DIR", "/opt/bmc-konsole/web")
BMC_HOST = os.environ["BMC_HOST"]
BMC_USER = os.environ.get("BMC_USER", "admin")
BMC_PASS = os.environ["BMC_PASSWORD"]
# optional eigener, schwaecher berechtigter Benutzer fuer die Konsole (Web-Login im Klartext)
BMC_WEB_USER = os.environ.get("BMC_WEB_USER") or BMC_USER
BMC_WEB_PASS = os.environ.get("BMC_WEB_PASSWORD") or BMC_PASS
TITEL = os.environ.get("UI_TITLE", "BMC-Konsole")
FAN_HINWEIS = os.environ.get("FAN_NOTICE", "")


def _geheimnis(datei, laenge=32):
    """Liest ein Geheimnis aus /data oder erzeugt es (atomar, 0600).
    Eine leere Datei gilt als fehlend - sonst waere ein leeres Kennwort gueltig."""
    pfad = os.path.join(DATA, datei)
    if os.path.exists(pfad):
        with open(pfad) as fh:
            wert = fh.read().strip()
        if wert:
            return wert
        log.warning("%s ist leer - erzeuge neu", pfad)
    wert = secrets.token_urlsafe(laenge)
    tmp = pfad + ".neu"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, wert.encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, pfad)
    return wert


UI_PASSWORD = os.environ.get("UI_PASSWORD") or _geheimnis("ui_password", 12)
if not UI_PASSWORD:
    raise SystemExit("UI_PASSWORD ist leer")
if not os.environ.get("UI_PASSWORD"):
    log.warning("UI_PASSWORD nicht gesetzt - erzeugtes Kennwort liegt in %s/ui_password", DATA)
# aendert sich das Kennwort, werden alle bestehenden Sitzungen ungueltig
_KENNWORT_GEN = hashlib.sha256(UI_PASSWORD.encode()).hexdigest()[:16]
SITZUNG_MAX = 12 * 3600

with open(os.environ.get("FAN_CONFIG", "/opt/bmc-konsole/fans.json")) as fh:
    LUEFTER = json.load(fh)

app = Flask(__name__, static_folder=None)
app.secret_key = _geheimnis("session_secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                  SESSION_COOKIE_NAME="bmckonsole", SESSION_COOKIE_SECURE=True,
                  PERMANENT_SESSION_LIFETIME=SITZUNG_MAX, SESSION_REFRESH_EACH_REQUEST=False)

ipmi = Ipmi(BMC_HOST, BMC_USER, BMC_PASS, cache_dir=DATA)
poller = Poller(ipmi)
kvm = Kvm(BMC_HOST, BMC_WEB_USER, BMC_WEB_PASS, data_dir=DATA)

_fehlversuche = {}
_sitzungen = set()            # serverseitig gueltige Sitzungs-IDs; Neustart meldet alle ab
_sitzungen_lock = threading.Lock()


def client_ip():
    return request.headers.get("X-Real-IP", request.remote_addr)


def angemeldet():
    if session.get("ok") is not True or session.get("gen") != _KENNWORT_GEN:
        return False
    if time.time() - float(session.get("seit", 0)) > SITZUNG_MAX:
        return False
    with _sitzungen_lock:
        return session.get("sid") in _sitzungen


def api(f):
    """Nur fuer angemeldete Nutzer; schreibende Aufrufe brauchen das CSRF-Token."""
    @wraps(f)
    def w(*a, **kw):
        if not angemeldet():
            return jsonify(fehler="Nicht angemeldet"), 401
        if request.method != "GET":
            token = request.headers.get("X-CSRF-Token", "")
            if not hmac.compare_digest(token, session.get("csrf", "")):
                return jsonify(fehler="CSRF-Token ungueltig"), 403
        try:
            return f(*a, **kw)
        except (IpmiError, KvmError) as e:
            log.warning("%s: %s", f.__name__, e)
            return jsonify(fehler=str(e)), 502
    return w


def protokoll(aktion, **details):
    log.info("AKTION %s von %s %s", aktion, client_ip(), details or "")


# --- Anmeldung -----------------------------------------------------------

@app.post("/api/auth/login")
def login():
    ip = client_ip()
    versuche = [t for t in _fehlversuche.get(ip, []) if t > time.time() - 300]
    if len(versuche) >= 8:
        return jsonify(fehler="Zu viele Fehlversuche, bitte 5 Minuten warten"), 429
    kennwort = (request.get_json(silent=True) or {}).get("kennwort", "")
    if not isinstance(kennwort, str) or not kennwort or \
            not hmac.compare_digest(kennwort.encode(), UI_PASSWORD.encode()):
        versuche.append(time.time())
        _fehlversuche[ip] = versuche
        time.sleep(1)
        return jsonify(fehler="Kennwort falsch"), 403
    _fehlversuche.pop(ip, None)
    session.clear()
    session.permanent = True
    sid = secrets.token_urlsafe(16)
    with _sitzungen_lock:
        _sitzungen.add(sid)
    session["ok"] = True
    session["sid"] = sid
    session["gen"] = _KENNWORT_GEN
    session["seit"] = time.time()
    session["csrf"] = secrets.token_urlsafe(24)
    log.info("Anmeldung von %s", ip)
    return jsonify(csrf=session["csrf"])


@app.post("/api/auth/logout")
def logout():
    with _sitzungen_lock:
        _sitzungen.discard(session.get("sid"))
    session.clear()
    return jsonify(ok=True)


@app.get("/api/auth/check")
def check():
    # fuer nginx auth_request (noVNC, WebSocket)
    return ("", 204) if angemeldet() else ("", 401)


@app.get("/api/auth/state")
def state():
    return jsonify(angemeldet=angemeldet(), csrf=session.get("csrf") if angemeldet() else None,
                   titel=TITEL, bmc=BMC_HOST)


# --- Lesende Endpunkte ---------------------------------------------------

@app.get("/api/overview")
@api
def overview():
    d = poller.snapshot()
    return jsonify(sensoren=_sensoren_mit_schwellen(d), luefter=_luefter(d),
                   strom=d["strom"], fehler=d["fehler"], stand=d["stand"],
                   kvm=kvm.status()["laeuft"])


def _sensoren_mit_schwellen(d):
    liste = []
    for name, s in d["sensoren"].items():
        e = dict(s)
        e.update({k: v for k, v in d["schwellen"].get(name, {}).items()
                  if k in ("lnr", "lcr", "lnc", "unc", "ucr", "unr")})
        # ohne Messwert steht in "einheit" nur "No Reading" - Einheit aus der Schwellwertabfrage nehmen
        einheit = s["einheit"] if s["wert"] is not None else \
            d["schwellen"].get(name, {}).get("einheit") or s["einheit"]
        e["art"] = _art(einheit)
        liste.append(e)
    return liste


def _art(einheit):
    e = (einheit or "").lower()
    if "degrees" in e:
        return "temperatur"
    if "rpm" in e:
        return "luefter"
    if "volts" in e:
        return "spannung"
    if "watts" in e:
        return "leistung"
    return "sonstige"


def _luefter(d):
    stellwerte = d["luefter"]
    out = []
    for f in LUEFTER:
        s = d["sensoren"].get(f["sensor"], {})
        out.append({"byte": f["byte"], "sensor": f["sensor"], "name": f["name"],
                    "hinweis": f.get("hinweis", ""), "regelbar": f.get("regelbar", True),
                    "duty": stellwerte[f["byte"] - 1] if stellwerte else None,
                    "rpm": s.get("wert"), "status": s.get("status")})
    return out


@app.get("/api/history")
@api
def history():
    n = max(1, min(360, request.args.get("n", 90, type=int)))
    return jsonify(verlauf=poller.history_all(n))


@app.get("/api/fans")
@api
def fans():
    return jsonify(luefter=_luefter(poller.snapshot()), hinweis=FAN_HINWEIS)


@app.get("/api/power")
@api
def power_get():
    return jsonify(strom=ipmi.power_status(), chassis=ipmi.chassis_status(),
                   bootflag=ipmi.boot_flag())


@app.get("/api/sel")
@api
def sel():
    return jsonify(eintraege=ipmi.sel_list(), info=ipmi.sel_info())


@app.get("/api/bmc")
@api
def bmc():
    lan = ipmi.lan_info()
    lan_kurz = {k: lan.get(k, "") for k in ("IP Address Source", "IP Address", "Subnet Mask",
                                             "MAC Address", "Default Gateway IP",
                                             "RMCP+ Cipher Suites")}
    return jsonify(mc=ipmi.mc_info(), lan=lan_kurz, fru=ipmi.fru(), zeit=ipmi.bmc_time(),
                   container_zeit=time.strftime("%d.%m.%Y %H:%M:%S"))


def _vnc_kennwort():
    try:
        with open(os.path.join(DATA, "vnc", "klartext")) as fh:
            return fh.read().strip()
    except OSError:
        return ""


@app.get("/api/kvm")
@api
def kvm_status():
    return jsonify(dict(kvm.status(), vnc=_vnc_kennwort()))


# --- Schreibende Endpunkte -----------------------------------------------

@app.post("/api/fans")
@api
def fans_set():
    body = request.get_json(silent=True) or {}
    werte = ipmi.fan_duties()
    if body.get("alle") == "auto":
        werte = [0] * 8
    elif body.get("alle") == "voll":
        werte = _alle_voll(werte)
    else:
        try:
            byte = int(body.get("byte", 0))
            duty = int(body.get("duty", -1))
        except (TypeError, ValueError):
            abort(400)
        if not any(f["byte"] == byte and f.get("regelbar", True) for f in LUEFTER):
            abort(400)
        if not 0 <= duty <= 100:
            abort(400)
        werte[byte - 1] = duty
    ipmi.set_fan_duties(werte)
    protokoll("luefter", werte=werte)
    poller.jetzt_aktualisieren()
    return jsonify(ok=True, werte=werte)


def _alle_voll(werte):
    neu = list(werte)
    for f in LUEFTER:
        if f.get("regelbar", True):
            neu[f["byte"] - 1] = 100
    return neu


@app.post("/api/power/<aktion>")
@api
def power_set(aktion):
    if aktion == "bios":
        out = ipmi.boot_into_bios()
    elif aktion == "bios-zuruecknehmen":
        out = ipmi.boot_flag_clear()
    else:
        out = ipmi.power(aktion)
    protokoll("strom", aktion=aktion)
    poller.jetzt_aktualisieren()
    return jsonify(ok=True, meldung=out)


@app.post("/api/sel/clear")
@api
def sel_clear():
    protokoll("sel_loeschen")
    return jsonify(ok=True, meldung=ipmi.sel_clear())


@app.post("/api/bmc/zeit")
@api
def bmc_zeit():
    jetzt = time.strftime("%m/%d/%Y %H:%M:%S")
    protokoll("bmc_zeit", auf=jetzt)
    return jsonify(ok=True, meldung=ipmi.set_bmc_time(jetzt))


@app.post("/api/bmc/reset")
@api
def bmc_reset():
    kvm.stop("BMC wird neu gestartet")
    protokoll("bmc_reset")
    return jsonify(ok=True, meldung=ipmi.mc_reset())


@app.post("/api/kvm/start")
@api
def kvm_start():
    body = request.get_json(silent=True) or {}
    kvm.start(jars_erneuern=bool(body.get("jars_erneuern")))
    protokoll("kvm_start")
    return jsonify(dict(kvm.status(), vnc=_vnc_kennwort()))


@app.post("/api/kvm/stop")
@api
def kvm_stop():
    kvm.stop()
    protokoll("kvm_stop")
    return jsonify(kvm.status())


# --- Statische Oberflaeche ----------------------------------------------

@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/assets/<path:datei>")
def assets(datei):
    return send_from_directory(os.path.join(WEB, "assets"), datei)


@app.after_request
def kopfzeilen(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "same-origin"
    if request.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


def main():
    kvm.aufraeumen_beim_start()
    poller.start()
    # supervisord beendet mit SIGTERM; ohne Handler liefe atexit nicht,
    # und der JViewer (eigene Prozessgruppe) bliebe mit offener BMC-Sitzung stehen
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    atexit.register(lambda: kvm.stop("Container wird beendet", logout_timeout=4))
    from waitress import serve
    serve(app, host="127.0.0.1", port=5001, threads=8, ident=None)


if __name__ == "__main__":
    main()
