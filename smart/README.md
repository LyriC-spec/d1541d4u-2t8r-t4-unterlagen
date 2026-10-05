# SMART-Reports

Ungekürzte Ausgaben aller zwölf Datenträger, auf dem Gerät erzeugt und nicht
nachbearbeitet. Die Dateinamen enthalten Modell und Seriennummer, nicht den
Gerätenamen (`/dev/sdX`), weil der sich nach einem Kaltstart ändern kann.

| Ordner | Inhalt |
|---|---|
| [aktuell/](aktuell/) | Stand 05.10.2026, nach den Firmware-Updates und einem erweiterten Selbsttest auf jedem Laufwerk. `smartctl -x`, bei den SAS-SSDs zusätzlich `sg_logs -a` mit allen SCSI-Logseiten (Selbsttest, Hintergrundscan, Solid-State-Media, Fehlerzähler, Phy-Ereignisse) |
| [2026-10-03_erstpruefung/](2026-10-03_erstpruefung/) | Erste Prüfung bei der Übernahme. Für die SAS-SSDs je ein Stand vor und nach dem Löschen (*SCSI Cryptographic Erase*, Dateien `_post-erase`). Die Boot-SSDs stehen hier noch auf der alten Firmware HPG1 |

## Erweiterter Selbsttest

Alle zwölf Laufwerke haben den erweiterten Selbsttest (*Extended*, liest das
ganze Medium) ohne Fehler abgeschlossen. Die SAS-SSDs führen ihn gedrosselt im
Hintergrund aus und brauchten dafür knapp zehn Stunden (04.10.2026 22:20 bis
05.10.2026 etwa 8:10).

## Übersicht, Stand 05.10.2026

### SAS-SSDs HPE MO003200JWUGA, 3,2 TB, Firmware HPD4

| Seriennummer | Betriebsstunden | Abnutzung | Defektliste | Fehler Lesen / Schreiben (unkorrigiert) | Gelesen / geschrieben | Non-medium errors | Selbsttest |
|---|---|---|---|---|---|---|---|
| WZV1BL6A | 44.622 | 2 % | 0 | 0 / 0 | 352 / 231 TB | 105.432 | ohne Fehler |
| WZV1KBBA | 44.611 | 2 % | 0 | 0 / 0 | 286 / 186 TB | 105.313 | ohne Fehler |
| WZX0234A | 44.038 | 2 % | 0 | 0 / 0 | 282 / 198 TB | 82.105 | ohne Fehler |
| WZX038XA | 44.038 | 2 % | 0 | 0 / 0 | 273 / 201 TB | 82.121 | ohne Fehler |
| WZX00G5A | 44.037 | 2 % | 0 | 0 / 0 | 281 / 199 TB | 82.117 | ohne Fehler |
| WZX01YYA | 44.036 | 2 % | 0 | 0 / 0 | 281 / 198 TB | 82.117 | ohne Fehler |
| WZV1WUVA | 22.826 | 1 % | 0 | 0 / 0 | 88 / 187 TB | 969 | ohne Fehler |
| WZV1URWA | 22.752 | 1 % | 0 | 0 / 0 | 66 / 134 TB | 761 | ohne Fehler |

Alle melden `SMART Health Status: OK`, Temperatur 33–34 °C. Auch die Zähler
für *korrigierte* Lese- und Schreibfehler stehen bei allen auf null.

*Non-medium errors* zählt Meldungen im Befehlsablauf, etwa „nicht bereit“ beim
Anlaufen nach einem Neustart, und nichts, was den Flash-Speicher betrifft.
Zwischen dem 03. und dem 05.10. ist der Zähler bei allen acht gleichmäßig um
100 bis 160 gestiegen. In diesen Tagen wurde der Server für BIOS-Einstellung
und Firmware-Updates oft neu gestartet und kalt gestartet. Über die zehn
Stunden des Selbsttests ohne Neustart kamen nur 0 bis 3 hinzu.
*Invalid DWORD* (Ereignisse auf dem SAS-Link) steht bei 5 bis 14 und hat sich
nicht verändert.

### Boot-SSDs HPE VK0120GEYJP, 120 GB, Firmware HPG6

| Seriennummer | Betriebsstunden | Verschleiß (Attr. 173, normiert) | Umgelagerte Sektoren | Fehlerprotokoll | Selbsttest |
|---|---|---|---|---|---|
| BTWA545404R6120CGN | 53.242 | 93 von 100 | 0 | leer | ohne Fehler |
| BTWA545404RR120CGN | 51.402 | 98 von 100 | 0 | leer | ohne Fehler |

### Festplatten WD Green WD40EZRX, 4 TB, Firmware 80.00A80

| Seriennummer | Betriebsstunden | Einschaltvorgänge | Umgelagert / wartend / unlesbar | CRC-Fehler | Fehlerprotokoll | Selbsttest |
|---|---|---|---|---|---|---|
| WD-WCC4EKKH4HY9 | 2.845 | 1.324 | 0 / 0 / 0 | 0 | leer | ohne Fehler |
| WD-WCC4EKKH4ULK | 5.244 | 535 | 0 / 0 / 0 | 0 | leer | ohne Fehler |

## Selbst nachprüfen

```bash
sudo smartctl -x /dev/sdX            # alle Laufwerke
sudo sg_logs -a /dev/sdX             # SAS: alle Logseiten
sudo smartctl -t long /dev/sdX       # erweiterter Selbsttest starten
sudo sg_requests -p /dev/sdX         # SAS: Fortschritt eines laufenden Tests
```
