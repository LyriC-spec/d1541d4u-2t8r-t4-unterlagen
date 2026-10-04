/* Grafische Konsole: noVNC im Browser, dahinter der JViewer im Container.
 * noVNC wird erst nach der Anmeldung nachgeladen: /novnc/ liegt hinter der
 * Sitzungspruefung von nginx, ein statischer Import wuerde vor der Anmeldung
 * scheitern und das ganze Modul lahmlegen. */
const { api, toast } = window.BMC;
const $ = s => document.querySelector(s);

const KEYS = {
  F2: [0xffbf, "F2"], Delete: [0xffff, "Delete"], F11: [0xffc8, "F11"],
  F12: [0xffc9, "F12"], Escape: [0xff1b, "Escape"],
};

let RFB = null;
let rfb = null;
let sichtbar = false;
let laeuft = false;
let timer = null;
let neuTimer = null;
let vncKennwort = "";
let statusLaeuft = false;

function setzeZustand(text, art) {
  const p = $("#kvm-state");
  p.textContent = text;
  p.className = `pill ${art || ""}`;
}

function knoepfe(aktiv) {
  document.querySelectorAll("[data-key], #kvm-fullscreen").forEach(b => { b.disabled = !aktiv; });
}

function planeVerbindung(ms) {
  clearTimeout(neuTimer);
  neuTimer = setTimeout(verbinde, ms);
}

async function verbinde() {
  if (rfb || !laeuft || !sichtbar) return;
  if (!RFB) {
    try {
      RFB = (await import("/novnc/core/rfb.js")).default;
    } catch (e) {
      setzeZustand("noVNC nicht ladbar", "bad");
      toast(`noVNC konnte nicht geladen werden: ${e.message}`, "bad");
      return;
    }
    if (rfb || !laeuft || !sichtbar) return;
  }
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/websockify`;
  const r = new RFB($("#kvm-screen"), url, { shared: true, credentials: { password: vncKennwort } });
  rfb = r;
  r.scaleViewport = true;
  r.resizeSession = false;
  r.background = "#000";
  r.focusOnClick = true;
  r.addEventListener("connect", () => {
    if (rfb !== r) return;
    $("#kvm-placeholder").hidden = true;
    knoepfe(true);
    setzeZustand("verbunden", "ok");
  });
  r.addEventListener("credentialsrequired", () => {
    // Kennwort hat sich geaendert (Containerneustart) - frisch holen
    api("/api/kvm").then(s => { vncKennwort = s.vnc || ""; r.sendCredentials({ password: vncKennwort }); })
      .catch(() => r.disconnect());
  });
  r.addEventListener("disconnect", () => {
    if (rfb !== null && rfb !== r) return;   // altes Ereignis einer ersetzten Verbindung
    rfb = null;
    knoepfe(false);
    $("#kvm-placeholder").hidden = false;
    if (laeuft && sichtbar) {
      setzeZustand("verbinde neu …", "warn");
      planeVerbindung(2000);
    } else {
      setzeZustand(laeuft ? "läuft (nicht angezeigt)" : "gestoppt");
    }
  });
}

function trenne() {
  clearTimeout(neuTimer);
  if (rfb) { const r = rfb; rfb = null; r.disconnect(); }
}

function zeigeStatus(s) {
  laeuft = !!s.laeuft;
  vncKennwort = s.vnc || vncKennwort;
  $("#kvm-start").hidden = laeuft;
  $("#kvm-stop").hidden = !laeuft;
  $("#kvm-reload").hidden = laeuft || !s.fehler;
  $("#kvm-log").textContent = (s.log || []).join("\n");
  if (s.startet) setzeZustand("starte …", "warn");
  else if (s.fehler && !laeuft) {
    setzeZustand("Fehler", "bad");
    $("#kvm-error").textContent = s.fehler;
    $("#kvm-error").hidden = false;
  } else {
    $("#kvm-error").hidden = true;
    if (!laeuft) setzeZustand("gestoppt");
  }
}

async function status() {
  if (statusLaeuft) return;      // keine ueberlappenden Abfragen
  statusLaeuft = true;
  try {
    const s = await api("/api/kvm");
    zeigeStatus(s);
    if (laeuft && sichtbar && !rfb) verbinde();
    if (!laeuft) trenne();
  } catch (_) { /* Anzeige bleibt */ } finally { statusLaeuft = false; }
}

async function starte(jarsErneuern) {
  const b = $("#kvm-start");
  b.disabled = true;
  setzeZustand("starte …", "warn");
  try {
    const s = await api("/api/kvm/start", { method: "POST", body: { jars_erneuern: !!jarsErneuern } });
    zeigeStatus(s);
    laeuft = true;
    planeVerbindung(1500);
    toast("Viewer gestartet – das Bild erscheint nach wenigen Sekunden", "ok");
  } catch (e) {
    setzeZustand("Fehler", "bad");
    toast(`Konsole startet nicht: ${e.message}`, "bad");
  } finally {
    b.disabled = false;
    status();
  }
}

$("#kvm-start").addEventListener("click", () => starte(false));
$("#kvm-reload").addEventListener("click", () => starte(true));

$("#kvm-stop").addEventListener("click", async () => {
  laeuft = false;
  trenne();
  try { await api("/api/kvm/stop", { method: "POST" }); } catch (e) { toast(e.message, "bad"); }
  status();
});

document.querySelectorAll("[data-key]").forEach(b => b.addEventListener("click", () => {
  if (!rfb) return;
  if (b.dataset.key === "cad") rfb.sendCtrlAltDel();
  else { const [sym, code] = KEYS[b.dataset.key]; rfb.sendKey(sym, code); }
  rfb.focus();
}));

$("#kvm-fullscreen").addEventListener("click", () => {
  const el = $("#kvm-screen");
  if (document.fullscreenElement) document.exitFullscreen();
  else el.requestFullscreen().catch(() => {});
});

window.addEventListener("bmc-tab", ev => {
  sichtbar = ev.detail === "konsole";
  clearInterval(timer);
  if (sichtbar) {
    status();
    timer = setInterval(status, 4000);
  } else {
    // nur das Bild abbauen, der Viewer im Container laeuft weiter
    trenne();
  }
});

window.addEventListener("bmc-abmelden", () => {
  sichtbar = false;
  laeuft = false;
  clearInterval(timer);
  trenne();
});

// Seite wurde direkt mit #konsole und bestehender Sitzung geladen
if (!$("#app").hidden && (location.hash || "") === "#konsole") {
  window.dispatchEvent(new CustomEvent("bmc-tab", { detail: "konsole" }));
}
