# ASRock Rack D1541D4U-2T8R mit NVIDIA Tesla T4: Unterlagen zum Verkauf

Ein Speicher- und Inferenzserver auf Basis eines Xeon-D-Boards, eingerichtet
unter TrueNAS SCALE. Alle Angaben hier wurden am 03. und 04.10.2026 auf dem
laufenden Gerät ausgelesen oder gemessen, nicht aus Datenblättern übernommen.

| Datei | Inhalt |
|---|---|
| [README.md](README.md) | Diese Übersicht: Ausstattung, Zustand, Kühlung, was man wissen sollte |
| [EINRICHTUNG.md](EINRICHTUNG.md) | Was für die T4 eingerichtet ist, Wiederherstellung nach einer Neuinstallation, Fehlersuche |
| [MESSUNGEN.md](MESSUNGEN.md) | Rohwerte der Lüfter- und Lastmessungen |
| [skripte/](skripte/) | Lüfterregelung und Wächter, genau so, wie sie auf dem System laufen |
| [bmc-konsole/](bmc-konsole/) | Weboberfläche mit HTML5-Fernkonsole für den BMC, als Docker-Container |
| [smart/](smart/) | Ungekürzte SMART-Ausgaben aller zwölf Datenträger |

## Ausstattung

| | |
|---|---|
| Board | ASRock Rack D1541D4U-2T8R, BIOS P1.30 (17.04.2018) |
| CPU | Intel Xeon D-1541, 8 Kerne, 16 Threads, 2,1 GHz, fest verlötet |
| Arbeitsspeicher | 128 GB DDR4-2400 ECC registered, 4× 32 GB Samsung M393A4K40BB1-CRC |
| Fernwartung | BMC (AMI MegaRAC, ASPEED) mit eigenem Netzanschluss, IPMI 2.0 |
| Grafik | NVIDIA Tesla T4, 16 GB, passiv, mit Radiallüfter (Blower) gekühlt |
| Netzwerk onboard | 2× 10GBase-T (Intel X540) |
| Netzwerk Steckkarte | HPE 563SFP+ (869583-001), 4× 10G SFP+ (Intel X710) |
| Speichercontroller | Broadcom/LSI SAS3008, meldet sich als SAS9300-8i, **IT-Mode**, Firmware 16.00.12.00 |
| Betriebssystem | TrueNAS SCALE 26.0.0-BETA.3 |

Die T4 läuft mit acht statt sechzehn PCIe-3.0-Bahnen (`LnkSta: Width x8
(downgraded)`). Ihr Port an der CPU ist geteilt, die andere Hälfte gehört dem
Speichercontroller. Für Inferenz reicht das, weil das Modell im Grafikspeicher
liegt und der Bus nur beim Laden belastet wird.

Der Speichercontroller läuft nachweislich im IT-Mode: Der Treiber meldet
`Protocol=(Initiator,Target)` und keine RAID-Fähigkeit. Für ZFS ist das die
richtige Betriebsart.

## Datenträger

| Menge | Typ | Modell | Anbindung |
|---|---|---|---|
| 8 | SAS-SSD 3,2 TB | HPE MO003200JWUGA | SAS3008 |
| 2 | HDD 4 TB | WD Green WD40EZRX | SATA am Board |
| 2 | SATA-SSD 120 GB | HPE VK0120GEYJP | SATA, gespiegelter boot-pool |

### Zustand

**Die acht SAS-SSDs** wurden am 03.10.2026 mit *SCSI Cryptographic Erase
(Sanitize)* gelöscht. Im Ordner `smart/` liegt für jede SSD der Stand vor und
nach dem Löschen.

| Seriennummer | Betriebsstunden | Abnutzung | Defektliste | Unkorrigierte Fehler |
|---|---|---|---|---|
| WZV1BL6A | 44.575 | 2 % | 0 | 0 |
| WZV1KBBA | 44.564 | 2 % | 0 | 0 |
| WZX0234A | 43.991 | 2 % | 0 | 0 |
| WZX038XA | 43.991 | 2 % | 0 | 0 |
| WZX00G5A | 43.990 | 2 % | 0 | 0 |
| WZX01YYA | 43.989 | 2 % | 0 | 0 |
| WZV1WUVA | 22.779 | 1 % | 0 | 0 |
| WZV1URWA | 22.704 | 1 % | 0 | 0 |

Die Betriebsstunden sind hoch, rund fünf Jahre Dauerbetrieb bei den meisten.
Die Abnutzung ist dagegen gering: Nach Angabe der Laufwerke selbst
(*Percentage used endurance indicator*) sind 1 bis 2 % der Schreiblebensdauer
verbraucht. Alle melden `SMART Health Status: OK`.

Ein Hinweis zur Einordnung: Sechs der acht SSDs zeigen einen hohen Zähler bei
*Non-medium errors* (rund 82.000 bis 105.000, die beiden jüngeren 624 und 821),
dazu einzelne *Invalid DWORD*-Ereignisse auf dem SAS-Link.
Diese Zähler betreffen Übertragung und Befehlsablauf, nicht den Speicher
selbst. Die Zähler für Medienschäden (Defektliste, unkorrigierte Lese- und
Schreibfehler) stehen bei allen acht auf null.

**Die beiden Festplatten** (WD Green, 4 TB): 2.820 und 5.219 Betriebsstunden,
keine umgelagerten oder wartenden Sektoren, keine CRC-Fehler, Kurztest ohne
Fehler. Die WD Green ist eine Desktopplatte und nicht für Dauerbetrieb im
Verbund gebaut. Für Daten mit Wert gehören sie gespiegelt.

**Die beiden Boot-SSDs** (HPE VK0120GEYJP, 120 GB): 53.218 und 51.379
Betriebsstunden, also rund sechs Jahre am Netz. Keine umgelagerten Sektoren,
keine Einträge im Fehlerprotokoll, Kurztest am 04.10.2026 ohne Fehler. Der
Verschleißwert (Attribut 173, normiert) steht bei 93 und 98 von 100. SMART war
in beiden Laufwerken abgeschaltet und wurde für diese Prüfung eingeschaltet.

## Kühlung der Tesla T4

Die T4 ist eine passive Serverkarte und darauf ausgelegt, im Luftstrom eines
Rackservers zu stecken. Hier bläst ein eigener Radiallüfter am Anschluss
FRNT_FAN2 durch ihren Kühlkörper, und ein Skript regelt ihn nach der
GPU-Temperatur. Der BMC des Boards kennt die GPU-Temperatur nicht und kann das
nicht selbst übernehmen.

Die Regelung kennt drei Zonen:

| Zone | Lüfter | Richtet sich nach |
|---|---|---|
| Blower | FRNT_FAN2 | GPU |
| Gehäuse | REAR_FAN1, zwei Noctua 60 mm am Y-Kabel | Datenträger, CPU |
| Netz | FRNT_FAN3 auf Chipsatz und X540 | 10G-Baustein X540, Chipsatz |

Dazu ein Wächter, der jede Minute prüft, ob die Regelung lebt, und sie notfalls
neu startet. Im Zweifel stellt er alle Lüfter auf Vollast. Alles läuft aus
fünf Startbefehlen in TrueNAS, die Updates überstehen. Einzelheiten stehen in
[EINRICHTUNG.md](EINRICHTUNG.md).

Gemessen unter Dauerlast (CUDA-Beispiel `nbody`, 66–70 W):

| Blower fest auf | Drehzahl | GPU eingeschwungen |
|---|---|---|
| 100 % | 6800 U/min | 60–61 °C |
| 70 % | 5600 U/min | 68 °C |
| 50 % | 4600 U/min | 79–80 °C, Takt fällt |

Im Leerlauf: Persistence Mode an, Leistungszustand P8, 405 MHz Speichertakt,
rund 11 W, 40–50 °C, Blower auf 30 % (3200 U/min).

Mit der Regelung (dieselbe Last, Blower frei): Nach drei Minuten pendelt sie
sich bei **64–65 °C und 76–80 % Blower** (6100 U/min) ein. Gehäuse- und
Netzzone bleiben dabei auf 30 %, die Datenträger bei 37 °C, der X540 bei 50 °C.
Endet die Last, ist der Blower nach anderthalb Minuten wieder auf 30 %. Die
Rohwerte stehen in [MESSUNGEN.md](MESSUNGEN.md).

## Fernwartung (BMC)

Der BMC (AMI MegaRAC auf ASPEED) hat Firmware 00.16.00 von 2017. Das ist die
letzte Version, die ASRock für dieses Board veröffentlicht hat. Eine neuere
gibt es nicht, auch keine mit HTML5-Konsole oder Redfish. Seine Fernkonsole
braucht einen Java-Viewer, den aktuelle Browser nicht mehr starten.

Dafür liegt im Ordner [bmc-konsole/](bmc-konsole/) ein Docker-Container. Er
führt den Original-Viewer im Container aus und zeigt ihn als HTML5-Seite im
Browser, mit Sensoren, Lüftern, Stromversorgung, Ereignisprotokoll und einem
Knopf „Nächster Start ins BIOS“. Der Container läuft auf einem beliebigen
anderen Rechner im Netz. Auf dem Server selbst sollte er nicht laufen, sonst ist
er weg, sobald der Server neu startet.

![BMC-Konsole](bmc-konsole/bilder/konsole.png)

Was man zum BMC wissen sollte:

- **Er gehört in ein abgetrenntes Verwaltungsnetz.** Die Firmware verwendet
  OpenSSL 0.9.8 (nur TLS 1.0), OpenSSH 5.5 und IPMI 2.0. Für BMCs dieser
  AMI-Generation sind schwere Lücken bekannt, darunter fest eingebaute Konten
  (CVE-2022-40242). Updates gibt es keine mehr.
- **Nach einem Stromausfall bleibt der Server aus.** Die Power Restore Policy
  steht auf `always-off`. Ändern lässt sie sich mit
  `ipmitool chassis policy always-on` oder `previous`.
- Die BMC-Zugangsdaten bei der Übergabe ändern. Nach einem Zurücksetzen auf
  Werkseinstellungen gelten wieder die Standardwerte.

## Was man wissen sollte

**Alle Messungen stammen aus einem offenen Aufbau.** Das System lief während der
Prüfung ohne geschlossenes Gehäuse. Der Blower saugte also Raumluft an, und die
Gehäuselüfter bewegten keine geführte Luft. In einem geschlossenen Gehäuse
kann die Karte unter Last spürbar wärmer werden. Die Regelung ist dafür
ausgelegt: Sie fährt den Blower ab 72 °C auf 100 % und geht ab 80 °C in den
Notfallbetrieb. Nach dem Einbau lohnt eine Prüfung unter Last, siehe unten.

**Unter Dauerlast wird es laut.** Ein Radiallüfter mit 6800 U/min ist nicht
leise. Im Leerlauf ist das System ruhig.

**Ein Lüfter am Y-Kabel ist unbeobachtet.** An REAR_FAN1 hängen zwei Noctua,
gemeldet wird nur die Drehzahl des einen.

**CPU_FAN1 lässt sich nicht regeln.** Er läuft fest auf etwa 4400 U/min. Der
BMC nimmt Stellwerte für diesen Anschluss an, die Drehzahl ändert sich aber
nicht. Wahrscheinlich ist es ein 3-Pin-Lüfter ohne PWM-Eingang.

**Installiert ist eine Beta.** TrueNAS SCALE 26.0.0-BETA.3. Wer ein stabiles
System will, setzt neu auf. Die Hardware ist davon unberührt, und wie man die
T4 danach wieder einrichtet, steht in [EINRICHTUNG.md](EINRICHTUNG.md).

**Datenpools sind nicht angelegt.** Es existiert nur der gespiegelte boot-pool.
Die Aufteilung der Datenträger wählt der Käufer selbst.

**Die BMC-Firmware ist alt** (Stand 2017). Die Fernkonsole braucht einen
Java-Viewer, und eine Redfish-Schnittstelle gibt es nicht. IPMI über das Netz
und `ipmitool` funktionieren.

## Kühlung im eigenen Gehäuse prüfen

Nach dem Einbau einmal zehn Minuten Last auf die Karte geben, etwa ein
Inferenzlauf oder das CUDA-Beispiel `nbody`, und dabei beobachten:

```bash
watch -n 10 'nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.sm --format=csv,noheader; cat /tmp/t4-fan.heartbeat'
```

Bleibt die Karte unter 75 °C, passt der Luftweg. Steigt sie trotz 100 % Blower
darüber, sollte man die Luftführung verbessern: Der Blower muss kühle Luft
ansaugen können, und die warme Abluft der Karte darf nicht wieder angesaugt
werden.
