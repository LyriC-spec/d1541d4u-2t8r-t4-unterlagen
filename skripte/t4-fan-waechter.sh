#!/usr/bin/env bash
# t4-fan-waechter.sh - Waechter fuer t4-fan.py, laeuft minuetlich per Cron.
#
# Warum es ihn braucht: Der BMC uebernimmt geschriebene Stellwerte und haelt
# sie, bis jemand neue schreibt. Stirbt die Regelung, friert der letzte Wert
# ein - bei 30 % Blower und anschliessender Last auf der Karte bliebe nur deren
# eigene Drosselung.
#
# Geprueft wird zweierlei: laeuft der Prozess, und ist sein Herzschlag frisch.
# Ein haengender Prozess ist genauso schlimm wie ein toter.

SKRIPT=/mnt/scripts/t4-fan.py
HEARTBEAT=/tmp/t4-fan.heartbeat
MAX_ALTER=90          # Sekunden, Takt ist 10 s
LOG=/mnt/scripts/t4-fan-waechter.log

melde() { echo "$(date '+%F %T')  $*" >> "$LOG"; }

vollast() {
  # Byte 3 REAR_FAN1, 6 FRNT_FAN2 (Blower), 7 FRNT_FAN3 (Chipsatz/X540)
  ipmitool raw 0x3a 0x01 0x00 0x00 0x64 0x00 0x00 0x64 0x64 0x00 >/dev/null 2>&1
  melde "Sicherheitshalber alle Zonen auf 100 Prozent"
}

starte() {
  setsid nohup "$SKRIPT" >/dev/null 2>&1 </dev/null &
  sleep 5
  if ps -eo cmd | grep -q "[t]4-fan.py"; then
    melde "Regelung neu gestartet"
    midclt call mail.send "{\"subject\": \"[D1541D4U] Luefterregelung neu gestartet\", \"text\": \"Der Waechter hat t4-fan.py tot oder haengend vorgefunden und um $(date '+%F %T') neu gestartet. Die Luefter liefen zwischenzeitlich auf 100 Prozent.\"}" >/dev/null 2>&1 || true
  else
    melde "NEUSTART FEHLGESCHLAGEN - Luefter bleiben auf 100 Prozent"
    midclt call mail.send "{\"subject\": \"[D1541D4U] Luefterregelung laesst sich nicht starten\", \"text\": \"Der Waechter konnte t4-fan.py um $(date '+%F %T') nicht starten. Die Luefter laufen auf 100 Prozent. Bitte pruefen.\"}" >/dev/null 2>&1 || true
  fi
}

# Das Dataset wird beim Boot nicht automatisch eingehaengt.
if [ ! -x "$SKRIPT" ]; then
  zfs mount boot-pool/scripts >/dev/null 2>&1
  if [ ! -x "$SKRIPT" ]; then
    melde "FEHLER: $SKRIPT nicht gefunden, auch nach zfs mount nicht"
    vollast
    exit 1
  fi
  melde "Dataset war nicht eingehaengt, nachgeholt"
fi

laeuft=0
ps -eo cmd | grep -q "[t]4-fan.py" && laeuft=1

# Frisch gestartet (etwa durch PostInit beim Booten): Das erste Lebenszeichen
# kommt erst nach dem ersten Regelschritt, und eine alte Datei von vor dem
# Neustart liegt noch in /tmp. Ohne diese Pruefung wuerde der Waechter die
# neue Regelung sofort wieder beenden.
if [ "$laeuft" -eq 1 ]; then
  pid=$(pgrep -f "[t]4-fan.py" | head -1)
  laufzeit=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
  if [ -n "$laufzeit" ] && [ "$laufzeit" -lt "$MAX_ALTER" ]; then
    exit 0
  fi
fi

frisch=0
if [ -f "$HEARTBEAT" ]; then
  alter=$(( $(date +%s) - $(stat -c %Y "$HEARTBEAT") ))
  [ "$alter" -le "$MAX_ALTER" ] && frisch=1
fi

if [ "$laeuft" -eq 1 ] && [ "$frisch" -eq 1 ]; then
  exit 0
fi

if [ "$laeuft" -eq 1 ]; then
  melde "Prozess laeuft, Herzschlag aber aelter als ${MAX_ALTER}s - beende ihn"
  pkill -TERM -f "[t]4-fan.py" >/dev/null 2>&1
  sleep 5
  pkill -KILL -f "[t]4-fan.py" >/dev/null 2>&1
  sleep 1
else
  melde "Regelung laeuft nicht"
fi

vollast
starte
exit 0
