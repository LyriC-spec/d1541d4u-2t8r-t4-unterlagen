/* BMC-Konsole – Oberflaeche. Alle Daten werden als Text gesetzt, nie als HTML. */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  function h(tag, attrs, ...kinder) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kind of kinder.flat()) {
      if (kind === null || kind === undefined || kind === false) continue;
      el.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
    }
    return el;
  }

  const zustand = { csrf: null, tab: "uebersicht", uebersicht: null, verlauf: {}, verlaufStand: 0 };

  /* ---------- API ---------- */
  async function api(pfad, { method = "GET", body } = {}) {
    const opt = { method, headers: {}, credentials: "same-origin" };
    if (method !== "GET") opt.headers["X-CSRF-Token"] = zustand.csrf || "";
    if (body !== undefined) {
      opt.headers["Content-Type"] = "application/json";
      opt.body = JSON.stringify(body);
    }
    const r = await fetch(pfad, opt);
    if (r.status === 401) { zeigeLogin(); throw new Error("Nicht angemeldet"); }
    let daten = {};
    try { daten = await r.json(); } catch (_) { /* leer */ }
    if (!r.ok) throw new Error(daten.fehler || `Fehler ${r.status}`);
    return daten;
  }

  /* ---------- Meldungen und Dialog ---------- */
  function toast(text, art = "") {
    const t = h("div", { class: `toast ${art}`, text });
    $("#toasts").append(t);
    setTimeout(() => t.remove(), art === "bad" ? 9000 : 4500);
  }

  function bestaetigen({ titel, text, wort = null, knopf = "Ausführen" }) {
    const dlg = $("#confirm");
    $("#confirm-title").textContent = titel;
    $("#confirm-text").textContent = text;
    $("#confirm-ok").textContent = knopf;
    const typed = $("#confirm-typed"), input = $("#confirm-input"), ok = $("#confirm-ok");
    typed.hidden = !wort;
    input.value = "";
    $("#confirm-word").textContent = wort || "";
    ok.disabled = !!wort;
    input.oninput = () => { ok.disabled = input.value.trim().toUpperCase() !== wort; };
    // returnValue bleibt sonst vom letzten Dialog stehen: Esc nach einem
    // frueheren "ok" wuerde als Bestaetigung gelten
    dlg.returnValue = "";
    return new Promise(res => {
      dlg.onclose = () => res(dlg.returnValue === "ok" &&
                              (!wort || input.value.trim().toUpperCase() === wort));
      dlg.showModal();
      if (wort) input.focus();
    });
  }

  $("#confirm-cancel").addEventListener("click", () => $("#confirm").close("cancel"));
  $("#confirm").addEventListener("cancel", () => { $("#confirm").returnValue = "cancel"; });

  window.BMC = { api, toast, bestaetigen, h };

  /* ---------- Formatierung ---------- */
  const EINHEIT = { "degrees C": "°C", "RPM": "U/min", "Volts": "V", "Watts": "W", "Amps": "A" };
  const einheit = e => EINHEIT[e] || e || "";
  function wertText(s) {
    if (s.wert === null || s.wert === undefined) return "–";
    const n = s.art === "spannung" ? s.wert.toFixed(2) : Math.round(s.wert).toLocaleString("de-DE");
    return `${s.art === "spannung" ? n.replace(".", ",") : n} ${einheit(s.einheit)}`;
  }
  function statusPill(st) {
    const s = (st || "").toLowerCase();
    if (s === "ok") return h("span", { class: "pill ok", text: "OK" });
    if (s === "ns" || s === "") return h("span", { class: "pill", text: "kein Wert" });
    if (/^[lu]?nc/.test(s)) return h("span", { class: "pill warn", text: "Warnung" });
    if (/^[lu]?(cr|nr)/.test(s)) return h("span", { class: "pill bad", text: "Kritisch" });
    return h("span", { class: "pill", text: st });
  }
  const upm = f => (f.rpm === null || f.rpm === undefined ? "–" : `${Math.round(f.rpm).toLocaleString("de-DE")} U/min`);
  const dutyText = f => (f.duty === null || f.duty === undefined ? "Stellwert unbekannt" : f.duty === 0 ? "BMC-Automatik" : `Stellwert ${f.duty} %`);
  function alter(ts) {
    if (!ts) return "–";
    const s = Math.round(Date.now() / 1000 - ts);
    return s < 60 ? `vor ${s} s` : `vor ${Math.round(s / 60)} min`;
  }

  function spark(punkte) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "spark");
    svg.setAttribute("viewBox", "0 0 96 26");
    svg.setAttribute("preserveAspectRatio", "none");
    if (!punkte || punkte.length < 2) return svg;
    const v = punkte.map(p => p[1]);
    let min = Math.min(...v), max = Math.max(...v);
    // Mindestspanne 10 % des Mittelwerts: sonst fuellt ein Schwanken um 1 °C die ganze Hoehe
    const mitte = (min + max) / 2, spanne = Math.max(max - min, Math.abs(mitte) * 0.1, 0.5);
    min = mitte - spanne / 2; max = mitte + spanne / 2;
    const x = i => (i / (punkte.length - 1)) * 96;
    const y = w => 24 - ((w - min) / (max - min)) * 22;
    const d = v.map((w, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(w).toFixed(1)}`).join("");
    const area = document.createElementNS(ns, "path");
    area.setAttribute("class", "area");
    area.setAttribute("d", `${d}L96,26L0,26Z`);
    const linie = document.createElementNS(ns, "path");
    linie.setAttribute("d", d);
    svg.append(area, linie);
    const t = document.createElementNS(ns, "title");
    t.textContent = `min ${min.toFixed(1)} · max ${max.toFixed(1)}`;
    svg.append(t);
    return svg;
  }

  /* ---------- Anmeldung ---------- */
  function zeigeLogin() {
    window.dispatchEvent(new Event("bmc-abmelden"));
    $("#app").hidden = true;
    $("#login").hidden = false;
    $("#pw").focus();
  }

  async function start() {
    const st = await fetch("/api/auth/state", { credentials: "same-origin" }).then(r => r.json());
    document.title = st.titel;
    $("#app-title").textContent = st.titel;
    $("#login-title").textContent = st.titel;
    $("#login-sub").textContent = `BMC ${st.bmc}`;
    if (st.angemeldet) { zustand.csrf = st.csrf; zeigeApp(); } else zeigeLogin();
  }

  $("#login-form").addEventListener("submit", async ev => {
    ev.preventDefault();
    $("#login-error").textContent = "";
    try {
      const r = await fetch("/api/auth/login", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kennwort: $("#pw").value }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.fehler || "Anmeldung fehlgeschlagen");
      zustand.csrf = d.csrf;
      $("#pw").value = "";
      zeigeApp();
    } catch (e) { $("#login-error").textContent = e.message; }
  });

  $("#logout").addEventListener("click", async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } catch (_) { /* egal */ }
    zeigeLogin();
  });

  /* ---------- Navigation ---------- */
  const TITEL = { uebersicht: "Übersicht", sensoren: "Sensoren", luefter: "Lüfter", strom: "Stromversorgung",
                  konsole: "Konsole", ereignisse: "Ereignisprotokoll", bmc: "BMC" };
  function zeigeApp() {
    $("#login").hidden = true;
    $("#app").hidden = false;
    wechsleTab();
    aktualisiere();
  }
  function wechsleTab() {
    if ($("#app").hidden) return;
    const tab = (location.hash || "#uebersicht").slice(1);
    zustand.tab = TITEL[tab] ? tab : "uebersicht";
    $$(".tab").forEach(t => { t.hidden = t.id !== `tab-${zustand.tab}`; });
    $$(".sidebar nav a").forEach(a => a.classList.toggle("active", a.dataset.tab === zustand.tab));
    $("#page-title").textContent = TITEL[zustand.tab];
    $("#sidebar").classList.remove("open");
    window.dispatchEvent(new CustomEvent("bmc-tab", { detail: zustand.tab }));
    ladeTab();
  }
  window.addEventListener("hashchange", wechsleTab);
  $("#menu-btn").addEventListener("click", ev => { ev.stopPropagation(); $("#sidebar").classList.toggle("open"); });
  $$(".sidebar nav a").forEach(a => a.addEventListener("click", () => $("#sidebar").classList.remove("open")));
  $(".main").addEventListener("click", () => $("#sidebar").classList.remove("open"));

  $("#theme-toggle").addEventListener("click", () => {
    const dunkel = matchMedia("(prefers-color-scheme: dark)").matches;
    const jetzt = document.documentElement.dataset.theme || (dunkel ? "dark" : "light");
    const neu = jetzt === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = neu;
    try { localStorage.setItem("bmc-theme", neu); } catch (_) { /* egal */ }
  });
  try { const t = localStorage.getItem("bmc-theme"); if (t) document.documentElement.dataset.theme = t; } catch (_) { /* egal */ }

  /* ---------- Regelmäßige Aktualisierung ---------- */
  async function aktualisiere() {
    if ($("#app").hidden) return;
    try {
      const d = await api("/api/overview");
      zustand.uebersicht = d;
      if (Date.now() - zustand.verlaufStand > 30000) {
        zustand.verlauf = (await api("/api/history?n=90")).verlauf;
        zustand.verlaufStand = Date.now();
      }
      kopfzeile(d);
      if (zustand.tab === "uebersicht") zeichneUebersicht(d);
      if (zustand.tab === "sensoren") zeichneSensoren(d);
      if (zustand.tab === "luefter") zeichneLuefter(d.luefter, null, false);
    } catch (e) {
      if (e.message !== "Nicht angemeldet") banner(`Verbindung zur Konsole gestört: ${e.message}`);
    }
  }
  setInterval(() => { if (!document.hidden) aktualisiere(); }, 10000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) aktualisiere(); });

  function banner(text) {
    const b = $("#banner");
    b.hidden = !text;
    b.textContent = text || "";
  }

  function kopfzeile(d) {
    const p = $("#power-pill");
    p.className = `pill ${d.strom === "an" ? "ok" : d.strom === "aus" ? "bad" : ""}`;
    p.textContent = `Server ${d.strom || "?"}`;
    const q = $("#poll-pill");
    q.className = `pill ${d.fehler ? "bad" : d.stand ? "ok" : ""}`;
    q.textContent = d.fehler ? "BMC antwortet nicht" : d.stand ? `BMC ${alter(d.stand)}` : "warte auf BMC";
    q.title = d.fehler || "Letzte erfolgreiche Abfrage beim BMC";
    banner(d.fehler ? `Letzte Abfrage beim BMC fehlgeschlagen: ${d.fehler}` : "");
  }

  async function ladeTab() {
    try {
      if (zustand.tab === "uebersicht" && zustand.uebersicht) zeichneUebersicht(zustand.uebersicht);
      if (zustand.tab === "sensoren" && zustand.uebersicht) zeichneSensoren(zustand.uebersicht);
      if (zustand.tab === "luefter") { const f = await api("/api/fans"); zeichneLuefter(f.luefter, f.hinweis, true); }
      if (zustand.tab === "strom") await ladeStrom();
      if (zustand.tab === "ereignisse") await ladeSel();
      if (zustand.tab === "bmc") await ladeBmc();
    } catch (e) { if (e.message !== "Nicht angemeldet") toast(e.message, "bad"); }
  }

  /* ---------- Übersicht ---------- */
  function kpi(label, wert, sub, art) {
    return h("div", { class: "card kpi" },
      h("div", { class: "label", text: label }),
      h("div", { class: `value ${art || ""}`, text: wert }),
      sub ? h("div", { class: "sub", text: sub }) : null);
  }

  function zeichneUebersicht(d) {
    const s = d.sensoren || [];
    const temps = s.filter(x => x.art === "temperatur" && x.wert !== null);
    const spannungen = s.filter(x => x.art === "spannung");
    const auffaellig = s.filter(x => x.status && !["ok", "ns"].includes(x.status.toLowerCase()));
    const cpu = s.find(x => /cpu temp/i.test(x.name));
    const heiss = temps.reduce((a, b) => (a && a.wert > b.wert ? a : b), null);
    const lf = (d.luefter || []).filter(f => f.rpm !== null && f.rpm !== undefined);
    $("#kpis").replaceChildren(
      kpi("Server", d.strom === "an" ? "Eingeschaltet" : d.strom === "aus" ? "Ausgeschaltet" : "–",
          d.kvm ? "Konsole aktiv" : "Konsole aus"),
      kpi("CPU", cpu ? wertText(cpu) : "–", "Temperatur"),
      kpi("Wärmster Sensor", heiss ? wertText(heiss) : "–", heiss ? heiss.name : ""),
      kpi("Lüfter", `${lf.length} aktiv`, lf.map(f => `${f.name} ${Math.round(f.rpm)}`).slice(0, 2).join(" · ")),
      kpi("Meldungen", auffaellig.length ? `${auffaellig.length} auffällig` : "Alles OK",
          `${spannungen.length} Spannungen überwacht`));
    $("#ov-temps").replaceChildren(...temps.map(t =>
      h("div", { class: "row" }, h("span", { text: t.name }), h("span", { class: "val", text: wertText(t) }),
        spark(zustand.verlauf[t.name]))));
    $("#ov-fans").replaceChildren(...(d.luefter || []).filter(f => f.rpm !== null && f.rpm !== undefined).map(f =>
      h("div", { class: "row" },
        h("span", {}, f.name, h("br"), h("span", { class: "muted small", text: dutyText(f) })),
        h("span", { class: "val", text: upm(f) }),
        spark(zustand.verlauf[f.sensor]))));
  }

  /* ---------- Sensoren ---------- */
  const GRUPPEN = [["temperatur", "Temperaturen"], ["luefter", "Lüfter"], ["spannung", "Spannungen"],
                   ["leistung", "Leistung"], ["sonstige", "Sonstige"]];
  function schwellenText(s) {
    const f = v => (v === null || v === undefined ? null : (s.art === "spannung" ? v.toFixed(2).replace(".", ",") : Math.round(v)));
    const unten = f(s.lcr) ?? f(s.lnc), oben = f(s.ucr) ?? f(s.unc);
    const teile = [];
    if (unten !== null) teile.push(`unten ${unten}`);
    if (oben !== null) teile.push(`oben ${oben}`);
    return teile.join(" · ") || "–";
  }
  function zeichneSensoren(d) {
    const s = d.sensoren || [];
    const ziel = $("#sensor-groups");
    ziel.replaceChildren(...GRUPPEN.map(([art, titel]) => {
      const liste = s.filter(x => x.art === art);
      if (!liste.length) return null;
      return h("div", { class: "card" },
        h("div", { class: "card-head" }, h("h2", { text: titel }), h("span", { class: "muted small", text: `${liste.length} Sensoren` })),
        h("div", { class: "table-wrap" }, h("table", { class: "table" },
          h("thead", {}, h("tr", {}, h("th", { text: "Sensor" }), h("th", { class: "num", text: "Wert" }),
            h("th", { text: "Status" }), h("th", { text: "Schwellen" }), h("th", { text: "Verlauf" }))),
          h("tbody", {}, liste.map(x => h("tr", {},
            h("td", { text: x.name }), h("td", { class: "num", text: wertText(x) }),
            h("td", {}, statusPill(x.status)), h("td", { class: "muted", text: schwellenText(x) }),
            h("td", {}, spark(zustand.verlauf[x.name]))))))));
    }).filter(Boolean));
  }

  /* ---------- Lüfter ---------- */
  function zeichneLuefter(liste, hinweis, neuAufbauen) {
    if (hinweis !== null && hinweis !== undefined) {
      $("#fan-notice").hidden = !hinweis;
      $("#fan-notice").textContent = hinweis;
    }
    const ziel = $("#fan-cards");
    if (!neuAufbauen && ziel.children.length === liste.length) {
      // nur Messwerte nachziehen, Schieberegler nicht anfassen
      liste.forEach(f => {
        const c = ziel.querySelector(`[data-byte="${f.byte}"]`);
        if (!c) return;
        c.querySelector(".fan-rpm").textContent = upm(f);
        c.querySelector(".bar > span").style.width = `${f.duty || 0}%`;
        c.querySelector(".fan-duty").textContent = dutyText(f);
      });
      return;
    }
    ziel.replaceChildren(...liste.map(f => {
      const unbekannt = f.duty === null || f.duty === undefined;
      const slider = h("input", { type: "range", min: "0", max: "100", step: "1", value: String(f.duty ?? 0),
                                  disabled: !f.regelbar, "aria-label": `Stellwert ${f.name}` });
      const out = h("output", { text: unbekannt ? "–" : slider.value === "0" ? "Auto" : `${slider.value} %` });
      const setzen = h("button", { class: "btn btn-sm", type: "button", disabled: !f.regelbar || unbekannt, text: "Setzen",
        onclick: async () => {
          const duty = Number(slider.value);
          if (duty > 0 && duty < 20 && !(await bestaetigen({ titel: "Sehr niedriger Stellwert",
              text: `${duty} % ist sehr wenig. Unter Last kann das Bauteil zu warm werden.`, knopf: "Trotzdem setzen" }))) return;
          try {
            await api("/api/fans", { method: "POST", body: { byte: f.byte, duty } });
            toast(`${f.name}: ${duty === 0 ? "BMC-Automatik" : duty + " %"}`, "ok");
            setTimeout(aktualisiere, 1500);
          } catch (e) { toast(e.message, "bad"); }
        } });
      slider.addEventListener("input", () => {
        out.textContent = slider.value === "0" ? "Auto" : `${slider.value} %`;
        if (f.regelbar) setzen.disabled = false;
      });
      return h("div", { class: "card fan", "data-byte": String(f.byte) },
        h("div", { class: "fan-top" }, h("h2", { text: f.name }), h("span", { class: "muted small", text: f.sensor })),
        h("div", { class: "fan-rpm", text: upm(f) }),
        h("div", { class: "bar" }, h("span", { style: `width:${f.duty || 0}%` })),
        h("div", { class: "muted small fan-duty", text: dutyText(f) }),
        f.hinweis ? h("div", { class: "small", text: f.hinweis }) : null,
        h("div", { class: "fan-ctl" }, slider, out, setzen));
    }));
  }
  async function alleLuefter(art) {
    // die Antwort enthaelt die gesetzten Werte; der Zwischenspeicher des Pollers ist noch alt
    const r = await api("/api/fans", { method: "POST", body: { alle: art } });
    const f = await api("/api/fans");
    f.luefter.forEach(x => { x.duty = r.werte[x.byte - 1]; });
    zeichneLuefter(f.luefter, f.hinweis, true);
  }
  $("#fans-auto").addEventListener("click", async () => {
    if (!(await bestaetigen({ titel: "Alle Lüfter auf BMC-Automatik", text: "Der BMC regelt dann selbst. Er kennt die GPU-Temperatur nicht." }))) return;
    try { await alleLuefter("auto"); toast("Alle Lüfter auf Automatik", "ok"); }
    catch (e) { toast(e.message, "bad"); }
  });
  $("#fans-full").addEventListener("click", async () => {
    try { await alleLuefter("voll"); toast("Alle regelbaren Lüfter auf 100 %", "ok"); }
    catch (e) { toast(e.message, "bad"); }
  });

  /* ---------- Strom ---------- */
  async function ladeStrom() {
    const d = await api("/api/power");
    const big = $("#power-big");
    big.textContent = d.strom === "an" ? "Eingeschaltet" : d.strom === "aus" ? "Ausgeschaltet" : "Unbekannt";
    big.className = `power-big ${d.strom === "an" ? "ok" : "bad"}`;
    const wichtig = ["System Power", "Power Overload", "Main Power Fault", "Power Restore Policy",
                     "Last Power Event", "Chassis Intrusion", "Drive Fault", "Cooling/Fan Fault"];
    $("#chassis-kv").replaceChildren(...wichtig.filter(k => d.chassis[k] !== undefined)
      .flatMap(k => [h("dt", { text: k }), h("dd", { text: d.chassis[k] })]));
    $("#bootflag").textContent = d.bootflag;
  }
  const STROM = {
    on: { titel: "Server einschalten", text: "Schaltet den Server ein.", knopf: "Einschalten" },
    soft: { titel: "Herunterfahren", text: "Sendet ein ACPI-Signal. Das Betriebssystem fährt geordnet herunter.", knopf: "Herunterfahren" },
    off: { titel: "Hart ausschalten", text: "Trennt den Server sofort vom Strom, wie Ziehen des Steckers. Ungespeicherte Daten gehen verloren.", wort: "AUS", knopf: "Ausschalten" },
    reset: { titel: "Reset", text: "Startet den Server sofort neu, ohne Herunterfahren.", wort: "RESET", knopf: "Reset" },
    cycle: { titel: "Aus- und wieder einschalten", text: "Schaltet hart aus und nach kurzer Pause wieder ein.", wort: "NEUSTART", knopf: "Ausführen" },
    bios: { titel: "Nächster Start ins BIOS", text: "Der nächste Start des Servers geht direkt ins BIOS-Setup, auch wenn er erst später kommt. Am laufenden System ändert sich nichts, bis du neu startest. Die Konsole muss dafür auf einem anderen Rechner laufen als auf diesem Server.", knopf: "Setzen" },
    "bios-zuruecknehmen": { titel: "Startvorgabe zurücknehmen", text: "Der nächste Start läuft wieder normal.", knopf: "Zurücknehmen" },
  };
  document.addEventListener("click", async ev => {
    const b = ev.target.closest("[data-power]");
    if (!b) return;
    const aktion = b.dataset.power, def = STROM[aktion];
    if (!(await bestaetigen(def))) return;
    try {
      await api(`/api/power/${aktion}`, { method: "POST" });
      toast(`${def.titel}: ausgeführt`, "ok");
      if (zustand.tab === "strom") setTimeout(() => ladeStrom().catch(() => {}), 2000);
      setTimeout(aktualisiere, 3000);
    } catch (e) { toast(e.message, "bad"); }
  });

  /* ---------- Ereignisprotokoll ---------- */
  async function ladeSel() {
    const d = await api("/api/sel");
    const i = d.info || {};
    $("#sel-info").textContent = `${i["Entries"] ?? "?"} Einträge · ${i["Percent Used"] ?? "?"} belegt · letzte Änderung ${i["Last Add Time"] ?? "–"}`;
    const tb = $("#sel-table tbody");
    if (!d.eintraege.length) {
      tb.replaceChildren(h("tr", {}, h("td", { colspan: "6", class: "muted", text: "Keine Einträge" })));
      return;
    }
    tb.replaceChildren(...d.eintraege.map(e => h("tr", {},
      h("td", { text: parseInt(e.id, 16) || e.id }), h("td", { text: e.datum }), h("td", { text: e.zeit }),
      h("td", { text: e.sensor }), h("td", { text: e.ereignis }),
      h("td", {}, e.richtung ? h("span", { class: `pill ${/deasserted/i.test(e.richtung) ? "ok" : "warn"}`, text: e.richtung }) : null))));
  }
  $("#sel-reload").addEventListener("click", () => ladeSel().catch(e => toast(e.message, "bad")));
  $("#sel-clear").addEventListener("click", async () => {
    if (!(await bestaetigen({ titel: "Ereignisprotokoll löschen", text: "Alle Einträge werden im BMC gelöscht.", wort: "LÖSCHEN", knopf: "Löschen" }))) return;
    try { await api("/api/sel/clear", { method: "POST" }); toast("Ereignisprotokoll gelöscht", "ok"); await ladeSel(); }
    catch (e) { toast(e.message, "bad"); }
  });

  /* ---------- BMC ---------- */
  function kv(ziel, obj, schluessel) {
    const k = schluessel || Object.keys(obj);
    $(ziel).replaceChildren(...k.filter(x => obj[x]).flatMap(x => [h("dt", { text: x }), h("dd", { text: obj[x] })]));
  }
  async function ladeBmc() {
    const d = await api("/api/bmc");
    kv("#mc-kv", d.mc, ["Firmware Revision", "IPMI Version", "Manufacturer Name", "Product ID", "Device Available"]);
    kv("#lan-kv", d.lan);
    kv("#fru-kv", d.fru);
    kv("#time-kv", { "BMC": d.zeit, "Container": d.container_zeit });
  }
  $("#bmc-time").addEventListener("click", async () => {
    try { await api("/api/bmc/zeit", { method: "POST" }); toast("BMC-Uhr gestellt", "ok"); await ladeBmc(); }
    catch (e) { toast(e.message, "bad"); }
  });
  $("#bmc-reset").addEventListener("click", async () => {
    if (!(await bestaetigen({ titel: "BMC neu starten", text: "Nur der BMC startet neu, der Server läuft weiter. Konsole und IPMI sind etwa zwei Minuten weg.", wort: "BMC", knopf: "Neu starten" }))) return;
    try { await api("/api/bmc/reset", { method: "POST" }); toast("BMC startet neu", "ok"); }
    catch (e) { toast(e.message, "bad"); }
  });

  start().catch(e => { zeigeLogin(); $("#login-error").textContent = e.message; });
})();
