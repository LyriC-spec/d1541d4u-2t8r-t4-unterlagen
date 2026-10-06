# Tesla T4 und Lüfterregelung: Einrichtung, Wiederherstellung, Fehlersuche

Diese Anleitung beschreibt, was auf dem System eingerichtet ist, damit die
Tesla T4 zuverlässig und leise läuft, und wie man es nach einer Neuinstallation
von TrueNAS wiederherstellt. Stand 04.10.2026, ausgelesen am laufenden System.

## Warum überhaupt etwas eingerichtet werden muss

Die T4 ist eine passive Serverkarte. Ab Werk fehlen ihr drei Dinge:

1. **Persistence Mode.** Ohne ihn bleibt die Karte im Leerlauf im
   Leistungszustand P0 und zieht rund 28 W. Mit ihm fällt sie auf P8 mit etwa
   10 bis 14 W.
2. **Gesperrter Tiefschlaf (D3cold).** Darf der Kernel die Karte in D3cold
   schicken, kann sie vom PCIe-Bus verschwinden und kommt erst nach einem
   Neustart wieder.
3. **Kühlung.** Die Karte hat keinen eigenen Lüfter. Sie wird von einem
   Radiallüfter (Blower) am Anschluss FRNT_FAN2 angeblasen, und den regelt ein
   eigenes Skript nach der GPU-Temperatur. Der BMC kennt die GPU-Temperatur
   nicht und kann das nicht selbst.

Der NVIDIA-Treiber selbst ist in TrueNAS eingeschaltet (System → Erweitert →
NVIDIA-Treiber, intern `system.advanced.update {"nvidia": true}`) und wird bei
jedem Start als Systemerweiterung geladen. Dafür ist kein eigener Eintrag nötig.

## Die Lüfteranschlüsse

Der BMC dieses Boards (ASRock Rack, AMI MegaRAC) stellt alle Lüfter mit einem
einzigen Befehl, ein Byte je Anschluss:

```
ipmitool raw 0x3a 0x01 <B1> <B2> <B3> <B4> <B5> <B6> <B7> <B8>
```

`0x01` bis `0x64` ist der Stellwert in Prozent, `0x00` überlässt den Anschluss
der Automatik des BMC. Auslesen mit `ipmitool raw 0x3a 0x02`.

| Byte | Anschluss | Was dranhängt | Wer regelt |
|---|---|---|---|
| 1 | CPU_FAN1 | CPU-Kühler | lässt sich nicht stellen, läuft fest auf ~4400 U/min |
| 2 | CPU_FAN2 | – | auf dem Board nicht vorhanden |
| 3 | REAR_FAN1 | 2× Noctua 60 mm am Y-Kabel | Regelung, Zone „Gehäuse“ |
| 4 | REAR_FAN2 | – | auf dem Board nicht vorhanden |
| 5 | FRNT_FAN1 | nicht belegt | – |
| 6 | FRNT_FAN2 | **Blower der T4** | Regelung, Zone „Blower“ |
| 7 | FRNT_FAN3 | Lüfter auf Chipsatz und 10G-Baustein X540 | Regelung, Zone „Netz“ |
| 8 | FRNT_FAN4 | nicht belegt | – |

Am Y-Kabel von REAR_FAN1 meldet nur einer der beiden Noctua seine Drehzahl.
Fällt der andere aus, zeigt das kein Sensor an. Bei der Wartung also beide
ansehen.

Gemessene Drehzahlen (04.10.2026, Leerlauf):

| Stellwert | Blower (FRNT_FAN2) | Noctua (REAR_FAN1) | Netz (FRNT_FAN3) |
|---|---|---|---|
| 100 % | 6800 | 3100 | 4900 |
| 80 % | 6100 | 2600 | 4200 |
| 60 % | 5200 | 1900 | 3300 |
| 50 % | 4600 | 1600 | 2800 |
| 40 % | 4000 | 1300 | 2300 |
| 30 % | 3200 | 900 | 1700 |
| 25 % | 2800 | 700 | 1400 |
| 20 % | 2300 | 500 | 1100 |
| 15 % | 1700 | 300 | 700 |

Die BMC-Automatik (`0x00`) fährt im Leerlauf dieselben Drehzahlen wie 30 %.
Die einzige Drehzahlschwelle des BMC liegt bei 100 U/min (Lower Non-Critical).
Selbst bei 15 % hat er keinen Lüfterfehler gemeldet. Anders als bei manchen
Supermicro-Boards zwingt dieser BMC also nicht von sich aus alle Lüfter auf
Vollast.

## Was auf dem System liegt

| Ort | Inhalt |
|---|---|
| `/mnt/scripts/t4-fan.py` | Die Regelung, Takt 10 s, drei Zonen (Gehäusezone folgt seit 06.10.2026 auch der GPU) |
| `/mnt/scripts/t4-fan-waechter.sh` | Wächter, prüft minütlich Prozess und Lebenszeichen |
| `/mnt/scripts/t4-fan.log` | Protokoll der Regelung, rotiert bei 512 KB |
| `/mnt/scripts/t4-fan-waechter.log` | Protokoll des Wächters, schreibt nur bei Eingriffen |
| `/tmp/t4-fan.heartbeat` | Lebenszeichen: Zeitstempel und die drei Stellwerte |

`/mnt/scripts` ist ein eigenes ZFS-Dataset (`boot-pool/scripts`). Es übersteht
TrueNAS-Updates, weil es nicht zur Boot-Umgebung gehört. **Eine Neuinstallation
löscht den boot-pool aber vollständig**, und damit auch die Skripte. Deshalb
liegen sie in diesem Repository im Ordner `skripte/`.

## Die fünf Startbefehle

In der Weboberfläche unter **System → Erweitert → Init/Shutdown Scripts**, alle
vom Typ `Command`, Zeitpunkt `POSTINIT`, alle aktiv:

| Nr | Befehl | Zweck | Timeout |
|---|---|---|---|
| 1 | `bash -c "echo 0 > /sys/bus/pci/devices/0000:04:00.0/d3cold_allowed; echo on > /sys/bus/pci/devices/0000:04:00.0/power/control"` | D3cold sperren | 30 |
| 2 | `ipmitool raw 0x3a 0x01 0x00 0x00 0x3c 0x00 0x00 0x64 0x3c 0x00` | Startsicherung: Blower 100 %, Gehäuse und Netz 60 %, bis die Regelung übernimmt | 30 |
| 3 | `zfs mount boot-pool/scripts` | Skript-Dataset einhängen | 30 |
| 4 | `bash -c "for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do nvidia-smi -pm 1 >/dev/null 2>&1 && exit 0; sleep 2; done; exit 1"` | Persistence Mode, wartet bis zu 60 s auf den Treiber | 120 |
| 5 | `setsid nohup /mnt/scripts/t4-fan.py >/dev/null 2>&1 </dev/null &` | Regelung starten | 30 |

Dazu ein Cron-Auftrag (System → Erweitert → Cron Jobs), minütlich
(`* * * * *`), als `root`, Standardausgabe und Fehlerausgabe ausgeblendet:

```
/mnt/scripts/t4-fan-waechter.sh
```

Die PCI-Adresse `0000:04:00.0` gilt für den jetzigen Steckplatz. Wer die Karte
umsteckt, prüft sie mit `lspci | grep -i nvidia` und passt Eintrag 1 an.

### Kein Dollarzeichen in den Startbefehlen

TrueNAS reicht den hinterlegten Befehl durch eine zusätzliche
Kommandozeilen-Ebene. Alles mit `$` wird dabei aufgelöst, **bevor** der Befehl
läuft. Schleifen über Variablen und Befehlsersetzungen wie `$(seq 1 30)`
scheitern lautlos. Weder das Startprotokoll noch die Weboberfläche zeigen
etwas, nur `/var/log/middlewared.log` (`grep InitShutdownScriptService`).
Deshalb ist die Schleife in Eintrag 4 mit ausgeschriebenen Zahlen geschrieben.
**Wer einen Eintrag umschreibt, verwendet kein `$`.**

## Wiederherstellen nach einer Neuinstallation von TrueNAS

1. NVIDIA-Treiber einschalten: System → Erweitert → „Install NVIDIA Drivers“
   (oder `midclt call system.advanced.update '{"nvidia": true}'`). Danach muss
   `nvidia-smi` die Karte zeigen.
2. Dataset anlegen und Skripte zurückspielen, als root:

   ```bash
   zfs create -o mountpoint=/mnt/scripts boot-pool/scripts
   cp skripte/t4-fan.py skripte/t4-fan-waechter.sh /mnt/scripts/
   chmod +x /mnt/scripts/t4-fan.py /mnt/scripts/t4-fan-waechter.sh
   ```

3. Die fünf Startbefehle und den Cron-Auftrag von oben anlegen.
4. Neu starten und mit dem nächsten Abschnitt prüfen.

## Prüfen, ob nach einem Neustart alles greift

```bash
nvidia-smi --query-gpu=persistence_mode,pstate,clocks.mem,power.draw,temperature.gpu --format=csv,noheader
# gesund im Leerlauf: Enabled, P8, 405 MHz, 10-14 W, unter 45 C

cat /sys/bus/pci/devices/0000:04:00.0/d3cold_allowed   # muss 0 sein
ps -eo cmd | grep "[t]4-fan.py"                        # laeuft die Regelung?
cat /tmp/t4-fan.heartbeat                               # Zeitstempel frisch, dann Blower/Gehaeuse/Netz in %
ipmitool raw 0x3a 0x02                                  # Byte 3, 6 und 7 = aktuelle Stellwerte (hex)
tail -5 /mnt/scripts/t4-fan.log
grep InitShutdownScriptService /var/log/middlewared.log | tail   # Fehler der Startbefehle
```

## Fehlersuche

### Die Lüfter laufen dauerhaft laut

Zuerst ins Protokoll des Wächters schauen:

```bash
tail -20 /mnt/scripts/t4-fan-waechter.log
tail -20 /mnt/scripts/t4-fan.log
```

Der Wächter stellt alle Zonen bewusst auf 100 %, bevor er die Regelung neu
startet. Im Zweifel laut statt heiß.

| Zeile im Wächterprotokoll | Bedeutung |
|---|---|
| `Regelung laeuft nicht` … `Regelung neu gestartet` | Hat sich selbst geheilt. Danach regelt sie wieder herunter. |
| `Prozess laeuft, Herzschlag aber aelter als 90s - beende ihn` | Die Regelung hing und wurde neu gestartet. |
| `Dataset war nicht eingehaengt, nachgeholt` | Startbefehl 3 hat nicht gegriffen. Prüfen, ob er noch existiert und aktiv ist. |
| `FEHLER: /mnt/scripts/t4-fan.py nicht gefunden` | Das Skript fehlt, etwa nach einer Neuinstallation. Siehe Wiederherstellen. |
| `NEUSTART FEHLGESCHLAGEN - Luefter bleiben auf 100 Prozent` | Von Hand starten und die Fehlermeldung lesen: `/mnt/scripts/t4-fan.py` |

Steht im Regelprotokoll `NOTFALL`, war eine Temperatur über der Notfallgrenze.
Das ist kein Fehler der Regelung.

Unter anhaltender Last auf der Grafikkarte dreht der Blower hoch, und das ist
so gewollt. Leise wird das System erst wieder, wenn die Last endet.

### Die Karte ist verschwunden

`nvidia-smi` meldet „No devices were found“, oder `lspci` zeigt die Karte nicht
mehr. Dann war sie meist in D3cold. Neu starten und prüfen, ob Startbefehl 1
gegriffen hat (`d3cold_allowed` muss `0` sein).

### Die Karte zieht im Leerlauf 28 W

Persistence Mode ist aus. `nvidia-smi -pm 1` setzt ihn sofort. Dauerhaft sorgt
Startbefehl 4 dafür. Hat er nicht gegriffen, steht der Grund in
`/var/log/middlewared.log`.

### Die Regelung von Hand anhalten

```bash
pkill -TERM -f "[t]4-fan.py"
```

Die Regelung stellt beim Beenden alle Zonen auf 100 %. Spätestens nach einer
Minute startet der Wächter sie wieder. Wer sie länger anhalten will, schaltet
vorher den Cron-Auftrag ab.

Die BMC-Automatik von Hand zurückholen:

```bash
ipmitool raw 0x3a 0x01 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
```

Danach kühlt **niemand** die T4 nach Bedarf. Die Automatik kennt die
GPU-Temperatur nicht und regelt nur nach den Sensoren des Boards. Für den
Dauerbetrieb mit Last auf der Karte ist das nicht geeignet.
