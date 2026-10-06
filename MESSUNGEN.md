# Messungen

Abschnitte 1 bis 3 vom 04.10.2026, gemessen am laufenden System im **offenen Aufbau**,
also ohne geschlossenes Gehäuse. Raumtemperatur nicht erfasst.

## 1. Drehzahl je Stellwert

Leerlauf, jeweils 15 s nach dem Setzen gelesen. Gesetzt wurden REAR_FAN1,
FRNT_FAN2 und FRNT_FAN3 gemeinsam mit `ipmitool raw 0x3a 0x01`.

| Stellwert | Blower (FRNT_FAN2) | Noctua (REAR_FAN1) | Netz (FRNT_FAN3) | CPU_FAN1 |
|---|---|---|---|---|
| 100 % | 6800 | 3100 | 4900 | 4400 |
| 80 % | 6100 | 2600 | 4200 | 4400 |
| 60 % | 5200 | 1900 | 3300 | 4400 |
| 50 % | 4600 | 1600 | 2800 | 4400 |
| 40 % | 4000 | 1300 | 2300 | 4400 |
| 30 % | 3200 | 900 | 1700 | 4400 |
| 25 % | 2800 | 700 | 1400 | 4400 |
| 20 % | 2300 | 500 | 1100 | 4400 |
| 15 % | 1700 | 300 | 700 | 4400 |

Im BMC-Ereignisprotokoll ist dabei kein Lüfterereignis entstanden.

## 2. Blower fest, Dauerlast

Last: CUDA-Beispiel `nbody -benchmark -numbodies=131072` in einer Schleife,
Container `nvcr.io/nvidia/k8s/cuda-sample:nbody`. Gehäuse- und Netzlüfter fest
auf 40 %. Je Stufe acht Minuten, ein Messpunkt alle zehn Sekunden.

Spalten: Uhrzeit, Stellwert, Blowerdrehzahl, dann GPU-Temperatur (°C),
Leistung (W), SM-Takt (MHz), Auslastung (%), aktive Drosselgründe
(`0x4` = Leistungsgrenze 70 W, bei der T4 unter Volllast normal), zuletzt
CPU-Temperatur. Einzelne niedrige Leistungs- und Auslastungswerte fallen auf
den Neustart von `nbody` zwischen zwei Läufen.

```
00:24:48 duty=100 blower=6800 gpu=[45, 65.85, 1215, 100, 0x0000000000000004] cpu=42
00:24:58 duty=100 blower=6800 gpu=[47, 64.42, 1200, 100, 0x0000000000000004] cpu=43
00:25:09 duty=100 blower=6800 gpu=[49, 69.06, 1200, 100, 0x0000000000000004] cpu=46
00:25:19 duty=100 blower=6800 gpu=[51, 69.06, 1200, 100, 0x0000000000000004] cpu=44
00:25:30 duty=100 blower=6700 gpu=[52, 69.67, 1200, 66, 0x0000000000000004] cpu=48
00:25:40 duty=100 blower=6800 gpu=[53, 68.39, 1170, 23, 0x0000000000000004] cpu=44
00:25:51 duty=100 blower=6800 gpu=[54, 68.77, 1200, 100, 0x0000000000000004] cpu=45
00:26:01 duty=100 blower=6800 gpu=[55, 36.43, 1110, 16, 0x0000000000000004] cpu=45
00:26:12 duty=100 blower=6800 gpu=[54, 37.78, 1590, 1, 0x0000000000000000] cpu=45
00:26:22 duty=100 blower=6800 gpu=[55, 36.55, 1575, 79, 0x0000000000000004] cpu=46
00:26:33 duty=100 blower=6800 gpu=[57, 66.58, 1155, 100, 0x0000000000000004] cpu=46
00:26:43 duty=100 blower=6800 gpu=[57, 68.53, 1170, 100, 0x0000000000000004] cpu=49
00:26:54 duty=100 blower=6800 gpu=[57, 69.34, 1155, 100, 0x0000000000000004] cpu=46
00:27:05 duty=100 blower=6800 gpu=[57, 68.30, 1155, 100, 0x0000000000000004] cpu=49
00:27:15 duty=100 blower=6800 gpu=[57, 63.48, 1125, 2, 0x0000000000000004] cpu=49
00:27:26 duty=100 blower=6700 gpu=[57, 38.79, 1590, 12, 0x0000000000000000] cpu=48
00:27:36 duty=100 blower=6800 gpu=[58, 67.01, 1155, 100, 0x0000000000000004] cpu=49
00:27:47 duty=100 blower=6800 gpu=[59, 68.11, 1155, 100, 0x0000000000000004] cpu=47
00:27:57 duty=100 blower=6800 gpu=[59, 70.49, 1125, 100, 0x0000000000000004] cpu=50
00:28:08 duty=100 blower=6800 gpu=[59, 67.20, 1155, 39, 0x0000000000000004] cpu=49
00:28:18 duty=100 blower=6800 gpu=[58, 38.91, 1590, 1, 0x0000000000000000] cpu=47
00:28:29 duty=100 blower=6800 gpu=[58, 40.22, 1575, 100, 0x0000000000000004] cpu=47
00:28:39 duty=100 blower=6800 gpu=[59, 66.63, 1155, 100, 0x0000000000000004] cpu=46
00:28:50 duty=100 blower=6800 gpu=[59, 65.67, 1140, 68, 0x0000000000000004] cpu=46
00:29:00 duty=100 blower=6800 gpu=[58, 40.26, 1590, 1, 0x0000000000000000] cpu=46
00:29:11 duty=100 blower=6800 gpu=[59, 36.45, 1575, 69, 0x0000000000000004] cpu=47
00:29:22 duty=100 blower=6800 gpu=[60, 65.82, 1155, 100, 0x0000000000000004] cpu=46
00:29:32 duty=100 blower=6800 gpu=[60, 68.29, 1140, 100, 0x0000000000000004] cpu=47
00:29:43 duty=100 blower=6700 gpu=[60, 67.49, 1140, 51, 0x0000000000000004] cpu=47
00:29:53 duty=100 blower=6800 gpu=[60, 78.21, 1125, 2, 0x0000000000000004] cpu=47
00:30:04 duty=100 blower=6800 gpu=[59, 39.64, 1590, 69, 0x0000000000000000] cpu=47
00:30:15 duty=100 blower=6700 gpu=[59, 39.30, 1575, 31, 0x0000000000000004] cpu=47
00:30:25 duty=100 blower=6800 gpu=[60, 65.57, 1140, 100, 0x0000000000000004] cpu=47
00:30:36 duty=100 blower=6800 gpu=[60, 68.39, 1125, 100, 0x0000000000000004] cpu=51
00:30:46 duty=100 blower=6800 gpu=[60, 68.20, 1140, 100, 0x0000000000000004] cpu=47
00:30:57 duty=100 blower=6800 gpu=[60, 69.73, 1125, 100, 0x0000000000000004] cpu=47
00:31:08 duty=100 blower=6800 gpu=[60, 64.61, 1125, 6, 0x0000000000000004] cpu=47
00:31:18 duty=100 blower=6700 gpu=[59, 38.05, 1590, 1, 0x0000000000000000] cpu=47
00:31:29 duty=100 blower=6800 gpu=[60, 46.61, 1515, 100, 0x0000000000000004] cpu=47
00:31:39 duty=100 blower=6800 gpu=[60, 67.63, 1155, 100, 0x0000000000000004] cpu=48
00:31:50 duty=100 blower=6800 gpu=[61, 67.68, 1125, 100, 0x0000000000000004] cpu=47
00:32:00 duty=100 blower=6800 gpu=[59, 42.21, 1590, 2, 0x0000000000000000] cpu=50
00:32:11 duty=100 blower=6800 gpu=[59, 41.08, 1575, 37, 0x0000000000000004] cpu=50
00:32:21 duty=100 blower=6700 gpu=[61, 65.97, 1140, 100, 0x0000000000000004] cpu=48
00:32:32 duty=100 blower=6800 gpu=[61, 68.49, 1125, 100, 0x0000000000000004] cpu=50
00:32:43 duty=100 blower=6800 gpu=[59, 38.89, 1590, 6, 0x0000000000000000] cpu=49
00:32:53 duty=100 blower=6800 gpu=[60, 39.08, 1590, 83, 0x0000000000000000] cpu=47
00:33:04 duty=100 blower=6800 gpu=[61, 68.54, 1140, 100, 0x0000000000000004] cpu=47
00:33:14 duty=70 blower=5600 gpu=[62, 68.25, 1140, 100, 0x0000000000000004] cpu=47
00:33:25 duty=70 blower=5600 gpu=[62, 60.68, 1110, 41, 0x0000000000000004] cpu=47
00:33:36 duty=70 blower=5600 gpu=[62, 43.22, 1590, 1, 0x0000000000000000] cpu=48
00:33:46 duty=70 blower=5600 gpu=[64, 68.82, 1125, 100, 0x0000000000000004] cpu=51
00:33:57 duty=70 blower=5600 gpu=[64, 67.05, 1125, 100, 0x0000000000000004] cpu=47
00:34:07 duty=70 blower=5600 gpu=[63, 42.53, 1590, 14, 0x0000000000000000] cpu=50
00:34:18 duty=70 blower=5600 gpu=[65, 67.63, 1125, 100, 0x0000000000000004] cpu=50
00:34:28 duty=70 blower=5600 gpu=[65, 107.99, 1020, 2, 0x0000000000000004] cpu=47
00:34:39 duty=70 blower=5600 gpu=[65, 66.91, 1470, 71, 0x0000000000000004] cpu=47
00:34:49 duty=70 blower=5600 gpu=[66, 68.34, 1110, 100, 0x0000000000000004] cpu=47
00:35:00 duty=70 blower=5600 gpu=[66, 82.03, 1080, 61, 0x0000000000000004] cpu=47
00:35:10 duty=70 blower=5600 gpu=[65, 41.61, 1590, 1, 0x0000000000000000] cpu=47
00:35:21 duty=70 blower=5600 gpu=[67, 68.06, 1110, 100, 0x0000000000000004] cpu=47
00:35:32 duty=70 blower=5600 gpu=[66, 64.28, 1110, 37, 0x0000000000000004] cpu=47
00:35:42 duty=70 blower=5600 gpu=[67, 63.90, 1095, 100, 0x0000000000000004] cpu=47
00:35:53 duty=70 blower=5600 gpu=[67, 66.44, 1095, 80, 0x0000000000000004] cpu=50
00:36:03 duty=70 blower=5600 gpu=[66, 43.53, 1575, 100, 0x0000000000000004] cpu=50
00:36:14 duty=70 blower=5600 gpu=[67, 67.82, 1095, 100, 0x0000000000000004] cpu=51
00:36:24 duty=70 blower=5600 gpu=[66, 40.41, 1575, 1, 0x0000000000000000] cpu=51
00:36:35 duty=70 blower=5600 gpu=[67, 63.33, 1110, 100, 0x0000000000000004] cpu=51
00:36:45 duty=70 blower=5600 gpu=[67, 68.39, 1095, 100, 0x0000000000000004] cpu=48
00:36:56 duty=70 blower=5600 gpu=[66, 43.18, 1590, 1, 0x0000000000000000] cpu=51
00:37:07 duty=70 blower=5600 gpu=[68, 66.92, 1110, 100, 0x0000000000000004] cpu=47
00:37:17 duty=70 blower=5600 gpu=[68, 68.20, 1095, 100, 0x0000000000000004] cpu=51
00:37:28 duty=70 blower=5600 gpu=[66, 40.58, 1590, 1, 0x0000000000000000] cpu=49
00:37:39 duty=70 blower=5600 gpu=[68, 68.06, 1095, 100, 0x0000000000000004] cpu=51
00:37:49 duty=70 blower=5600 gpu=[68, 67.58, 1095, 38, 0x0000000000000004] cpu=48
00:38:00 duty=70 blower=5600 gpu=[67, 41.92, 1575, 100, 0x0000000000000004] cpu=48
00:38:10 duty=70 blower=5600 gpu=[68, 65.34, 1095, 100, 0x0000000000000004] cpu=51
00:38:21 duty=70 blower=5600 gpu=[67, 43.95, 1590, 1, 0x0000000000000000] cpu=47
00:38:31 duty=70 blower=5600 gpu=[68, 66.92, 1095, 100, 0x0000000000000004] cpu=50
00:38:42 duty=70 blower=5600 gpu=[67, 44.57, 1590, 1, 0x0000000000000000] cpu=48
00:38:52 duty=70 blower=5600 gpu=[68, 67.15, 1095, 100, 0x0000000000000004] cpu=52
00:39:03 duty=70 blower=5600 gpu=[68, 40.63, 1005, 2, 0x0000000000000004] cpu=48
00:39:14 duty=70 blower=5600 gpu=[68, 67.62, 1095, 100, 0x0000000000000004] cpu=47
00:39:24 duty=70 blower=5600 gpu=[68, 67.92, 1095, 97, 0x0000000000000004] cpu=49
00:39:35 duty=70 blower=5600 gpu=[67, 43.51, 1590, 1, 0x0000000000000000] cpu=48
00:39:45 duty=70 blower=5600 gpu=[69, 67.87, 1095, 100, 0x0000000000000004] cpu=47
00:39:56 duty=70 blower=5600 gpu=[68, 62.42, 1095, 71, 0x0000000000000004] cpu=47
00:40:06 duty=70 blower=5600 gpu=[67, 43.41, 1575, 84, 0x0000000000000004] cpu=50
00:40:17 duty=70 blower=5600 gpu=[68, 68.92, 1080, 100, 0x0000000000000004] cpu=48
00:40:28 duty=70 blower=5600 gpu=[67, 45.07, 1590, 1, 0x0000000000000000] cpu=47
00:40:38 duty=70 blower=5600 gpu=[68, 67.58, 1095, 100, 0x0000000000000004] cpu=50
00:40:49 duty=70 blower=5600 gpu=[68, 64.96, 1095, 42, 0x0000000000000004] cpu=48
00:41:00 duty=70 blower=5600 gpu=[68, 52.80, 1470, 87, 0x0000000000000004] cpu=48
00:41:10 duty=70 blower=5600 gpu=[69, 64.05, 1080, 100, 0x0000000000000004] cpu=51
00:41:21 duty=70 blower=5600 gpu=[67, 39.20, 1395, 1, 0x0000000000000000] cpu=49
00:41:31 duty=70 blower=5600 gpu=[69, 65.34, 1095, 100, 0x0000000000000004] cpu=48
00:41:42 duty=50 blower=4600 gpu=[69, 71.58, 1065, 2, 0x0000000000000004] cpu=48
00:41:52 duty=50 blower=4600 gpu=[71, 67.11, 1080, 100, 0x0000000000000004] cpu=48
00:42:03 duty=50 blower=4600 gpu=[71, 68.15, 1080, 100, 0x0000000000000004] cpu=48
00:42:13 duty=50 blower=4600 gpu=[72, 66.63, 1080, 100, 0x0000000000000004] cpu=48
00:42:24 duty=50 blower=4600 gpu=[73, 66.35, 1065, 100, 0x0000000000000004] cpu=48
00:42:35 duty=50 blower=4600 gpu=[73, 67.39, 1065, 100, 0x0000000000000004] cpu=49
00:42:45 duty=50 blower=4600 gpu=[74, 63.08, 1065, 59, 0x0000000000000004] cpu=48
00:42:56 duty=50 blower=4600 gpu=[74, 66.82, 1050, 100, 0x0000000000000004] cpu=51
00:43:06 duty=50 blower=4600 gpu=[73, 45.33, 1590, 60, 0x0000000000000000] cpu=51
00:43:17 duty=50 blower=4600 gpu=[75, 65.63, 1050, 97, 0x0000000000000004] cpu=48
00:43:27 duty=50 blower=4600 gpu=[76, 65.67, 1065, 100, 0x0000000000000004] cpu=47
00:43:38 duty=50 blower=4600 gpu=[74, 42.62, 1440, 48, 0x0000000000000000] cpu=48
00:43:49 duty=50 blower=4600 gpu=[76, 66.10, 1050, 100, 0x0000000000000004] cpu=51
00:43:59 duty=50 blower=4600 gpu=[76, 66.06, 1050, 100, 0x0000000000000004] cpu=51
00:44:10 duty=50 blower=4600 gpu=[75, 47.26, 1575, 32, 0x0000000000000004] cpu=48
00:44:20 duty=50 blower=4600 gpu=[75, 44.52, 1590, 2, 0x0000000000000000] cpu=48
00:44:31 duty=50 blower=4600 gpu=[77, 66.44, 1035, 100, 0x0000000000000004] cpu=51
00:44:41 duty=50 blower=4600 gpu=[77, 65.25, 1035, 100, 0x0000000000000004] cpu=48
00:44:52 duty=50 blower=4600 gpu=[76, 39.69, 1470, 86, 0x0000000000000004] cpu=48
00:45:02 duty=50 blower=4600 gpu=[76, 49.28, 1590, 2, 0x0000000000000000] cpu=48
00:45:13 duty=50 blower=4600 gpu=[77, 64.87, 1020, 71, 0x0000000000000004] cpu=48
00:45:24 duty=50 blower=4600 gpu=[78, 65.34, 1035, 100, 0x0000000000000004] cpu=52
00:45:34 duty=50 blower=4600 gpu=[78, 66.62, 1035, 100, 0x0000000000000004] cpu=48
00:45:45 duty=50 blower=4600 gpu=[77, 48.09, 1590, 17, 0x0000000000000000] cpu=48
00:45:55 duty=50 blower=4600 gpu=[79, 74.33, 885, 2, 0x0000000000000004] cpu=48
00:46:06 duty=50 blower=4600 gpu=[78, 65.15, 1005, 23, 0x0000000000000004] cpu=48
00:46:16 duty=50 blower=4600 gpu=[79, 65.67, 1005, 100, 0x0000000000000004] cpu=49
00:46:27 duty=50 blower=4600 gpu=[79, 65.57, 1035, 100, 0x0000000000000004] cpu=51
00:46:37 duty=50 blower=4600 gpu=[79, 65.59, 1020, 100, 0x0000000000000004] cpu=48
00:46:48 duty=50 blower=4600 gpu=[78, 48.35, 1590, 26, 0x0000000000000000] cpu=48
00:46:59 duty=50 blower=4600 gpu=[78, 60.51, 1020, 29, 0x0000000000000004] cpu=51
00:47:09 duty=50 blower=4600 gpu=[79, 65.81, 1020, 100, 0x0000000000000004] cpu=48
00:47:20 duty=50 blower=4600 gpu=[79, 60.93, 1005, 100, 0x0000000000000004] cpu=48
00:47:30 duty=50 blower=4600 gpu=[79, 65.49, 1020, 100, 0x0000000000000004] cpu=48
00:47:41 duty=50 blower=4600 gpu=[78, 43.53, 1575, 36, 0x0000000000000004] cpu=48
00:47:52 duty=50 blower=4600 gpu=[78, 49.76, 1590, 2, 0x0000000000000000] cpu=48
00:48:02 duty=50 blower=4600 gpu=[79, 58.27, 990, 69, 0x0000000000000004] cpu=51
00:48:13 duty=50 blower=4600 gpu=[79, 65.97, 1020, 100, 0x0000000000000004] cpu=48
00:48:23 duty=50 blower=4600 gpu=[79, 65.53, 1005, 100, 0x0000000000000004] cpu=48
00:48:34 duty=50 blower=4600 gpu=[79, 65.25, 1005, 100, 0x0000000000000004] cpu=52
00:48:44 duty=50 blower=4600 gpu=[80, 65.76, 1005, 100, 0x0000000000000004] cpu=48
00:48:55 duty=50 blower=4600 gpu=[80, 63.48, 1005, 100, 0x0000000000000004] cpu=52
00:49:05 duty=50 blower=4600 gpu=[78, 45.27, 1575, 15, 0x0000000000000004] cpu=52
00:49:16 duty=50 blower=4600 gpu=[79, 84.71, 915, 44, 0x0000000000000004] cpu=51
00:49:27 duty=50 blower=4600 gpu=[79, 61.98, 1020, 82, 0x0000000000000004] cpu=51
00:49:37 duty=50 blower=4600 gpu=[80, 65.40, 1020, 100, 0x0000000000000004] cpu=52
00:49:48 duty=50 blower=4600 gpu=[80, 65.06, 1005, 100, 0x0000000000000004] cpu=51
00:49:58 duty=50 blower=4600 gpu=[79, 41.20, 1560, 100, 0x0000000000000004] cpu=52
```

## 3. Regelung unter Dauerlast

Dieselbe Last, diesmal regelt `t4-fan.py` frei: acht Minuten Last, danach sechs
Minuten Ruhe. Spalten: Uhrzeit, Phase, Lebenszeichen der Regelung (Blower,
Gehäuse, Netz in %), GPU-Temperatur (°C), Leistung (W), SM-Takt (MHz),
gemessene Blowerdrehzahl.

```
00:52:52 last hb=[30 30 30] gpu=[50, 67.91, 1185] blower=3200
00:53:02 last hb=[36 30 30] gpu=[53, 73.76, 1155] blower=3700
00:53:13 last hb=[44 30 30] gpu=[57, 101.71, 1230] blower=4200
00:53:23 last hb=[52 30 30] gpu=[57, 39.59, 1590] blower=4700
00:53:34 last hb=[58 30 30] gpu=[58, 41.66, 1590] blower=5100
00:53:45 last hb=[61 30 30] gpu=[61, 68.29, 1155] blower=5200
00:53:55 last hb=[67 30 30] gpu=[61, 68.25, 1140] blower=5400
00:54:06 last hb=[70 30 30] gpu=[62, 67.58, 1155] blower=5600
00:54:16 last hb=[70 30 30] gpu=[62, 68.19, 1125] blower=5600
00:54:27 last hb=[70 30 30] gpu=[61, 40.53, 1590] blower=5600
00:54:37 last hb=[73 30 30] gpu=[63, 67.30, 1140] blower=5800
00:54:48 last hb=[73 30 30] gpu=[63, 66.25, 1125] blower=5800
00:54:58 last hb=[73 30 30] gpu=[62, 43.30, 1590] blower=5800
00:55:20 last hb=[76 30 30] gpu=[63, 39.30, 1590] blower=5900
00:55:31 last hb=[76 30 30] gpu=[64, 66.06, 1125] blower=5900
00:55:41 last hb=[76 30 30] gpu=[64, 65.97, 1155] blower=5900
00:55:52 last hb=[76 30 30] gpu=[63, 42.72, 1590] blower=5900
00:56:02 last hb=[76 30 30] gpu=[65, 67.15, 1110] blower=5900
00:56:13 last hb=[80 30 30] gpu=[65, 100.63, 930] blower=6100
00:56:23 last hb=[76 30 30] gpu=[65, 67.54, 1110] blower=5900
00:56:34 last hb=[80 30 30] gpu=[64, 68.63, 1125] blower=6100
00:56:44 last hb=[76 30 30] gpu=[63, 38.84, 1575] blower=5900
00:56:55 last hb=[80 30 30] gpu=[65, 67.63, 1110] blower=6100
00:57:05 last hb=[80 30 30] gpu=[65, 39.64, 990] blower=6100
00:57:16 last hb=[80 30 30] gpu=[64, 67.68, 1485] blower=6100
00:57:26 last hb=[76 30 30] gpu=[65, 67.44, 1125] blower=5900
00:57:37 last hb=[80 30 30] gpu=[64, 41.66, 1590] blower=6000
00:57:47 last hb=[80 30 30] gpu=[65, 67.73, 1125] blower=6100
00:57:58 last hb=[80 30 30] gpu=[65, 67.39, 1125] blower=6100
00:58:08 last hb=[80 30 30] gpu=[64, 43.89, 1590] blower=6100
00:58:19 last hb=[80 30 30] gpu=[65, 67.63, 1110] blower=6100
00:58:29 last hb=[80 30 30] gpu=[65, 65.40, 1110] blower=6100
00:58:40 last hb=[80 30 30] gpu=[64, 67.62, 1410] blower=6100
00:58:50 last hb=[80 30 30] gpu=[65, 66.73, 1110] blower=6100
00:59:00 last hb=[80 30 30] gpu=[64, 39.74, 1590] blower=6100
00:59:11 last hb=[80 30 30] gpu=[65, 66.96, 1110] blower=6100
00:59:22 last hb=[80 30 30] gpu=[65, 67.48, 1080] blower=6100
00:59:32 last hb=[80 30 30] gpu=[64, 37.76, 1530] blower=6100
00:59:43 last hb=[80 30 30] gpu=[65, 66.20, 1110] blower=6100
00:59:53 last hb=[80 30 30] gpu=[65, 63.62, 1125] blower=6000
01:00:04 last hb=[80 30 30] gpu=[64, 40.00, 1575] blower=6100
01:00:14 last hb=[80 30 30] gpu=[65, 65.97, 1140] blower=6100
01:00:25 last hb=[80 30 30] gpu=[65, 118.99, 1005] blower=6000
01:00:35 last hb=[80 30 30] gpu=[64, 39.20, 1575] blower=6100
01:00:46 last hb=[80 30 30] gpu=[65, 67.82, 1110] blower=6100
01:00:56 last hb=[80 30 30] gpu=[64, 42.98, 1590] blower=6100
01:01:09 last hb=[80 30 30] gpu=[65, 39.47, 1110] blower=6100
01:01:19 last hb=[80 30 30] gpu=[65, 67.25, 1125] blower=6100
01:01:30 ruhe hb=[75 30 30] gpu=[56, 10.94, 300] blower=6000
01:01:41 ruhe hb=[70 30 30] gpu=[53, 11.24, 300] blower=5700
01:01:51 ruhe hb=[65 30 30] gpu=[50, 10.46, 300] blower=5400
01:02:02 ruhe hb=[60 30 30] gpu=[48, 10.36, 300] blower=5200
01:02:12 ruhe hb=[55 30 30] gpu=[46, 10.46, 300] blower=4900
01:02:22 ruhe hb=[50 30 30] gpu=[45, 10.17, 300] blower=4600
01:02:33 ruhe hb=[45 30 30] gpu=[44, 10.27, 300] blower=4300
01:02:44 ruhe hb=[40 30 30] gpu=[44, 10.26, 300] blower=4000
01:02:54 ruhe hb=[35 30 30] gpu=[43, 10.46, 300] blower=3700
01:03:05 ruhe hb=[30 30 30] gpu=[43, 10.85, 300] blower=3200
01:03:15 ruhe hb=[30 30 30] gpu=[43, 10.17, 300] blower=3200
01:03:25 ruhe hb=[30 30 30] gpu=[42, 9.87, 300] blower=3200
01:03:36 ruhe hb=[30 30 30] gpu=[42, 10.26, 300] blower=3200
01:03:47 ruhe hb=[30 30 30] gpu=[42, 9.97, 300] blower=3200
01:03:57 ruhe hb=[30 30 30] gpu=[42, 9.97, 300] blower=3200
01:04:08 ruhe hb=[30 30 30] gpu=[42, 10.46, 300] blower=3100
01:04:18 ruhe hb=[30 30 30] gpu=[41, 10.07, 300] blower=3200
01:04:29 ruhe hb=[30 30 30] gpu=[41, 10.17, 300] blower=3200
01:04:39 ruhe hb=[30 30 30] gpu=[41, 10.07, 300] blower=3200
01:04:50 ruhe hb=[30 30 30] gpu=[41, 10.75, 300] blower=3100
01:05:00 ruhe hb=[30 30 30] gpu=[41, 10.26, 300] blower=3100
01:05:11 ruhe hb=[30 30 30] gpu=[40, 10.36, 300] blower=3100
01:05:21 ruhe hb=[30 30 30] gpu=[40, 11.14, 300] blower=3100
01:05:32 ruhe hb=[30 30 30] gpu=[40, 10.16, 300] blower=3100
01:05:42 ruhe hb=[30 30 30] gpu=[40, 10.26, 300] blower=3200
01:05:53 ruhe hb=[30 30 30] gpu=[40, 10.76, 300] blower=3100
01:06:03 ruhe hb=[30 30 30] gpu=[40, 9.97, 300] blower=3100
01:06:14 ruhe hb=[30 30 30] gpu=[39, 9.97, 300] blower=3100
01:06:24 ruhe hb=[30 30 30] gpu=[39, 10.85, 300] blower=3100
01:06:35 ruhe hb=[30 30 30] gpu=[39, 10.36, 300] blower=3100
01:06:45 ruhe hb=[30 30 30] gpu=[39, 11.33, 300] blower=3100
01:06:56 ruhe hb=[30 30 30] gpu=[39, 10.07, 300] blower=3100
01:07:06 ruhe hb=[30 30 30] gpu=[39, 10.16, 300] blower=3100
01:07:17 ruhe hb=[30 30 30] gpu=[39, 10.27, 300] blower=3100
01:07:27 ruhe hb=[30 30 30] gpu=[38, 9.78, 300] blower=3100
01:07:38 ruhe hb=[30 30 30] gpu=[38, 10.16, 300] blower=3100
```

Protokoll der Regelung in derselben Zeit (`/mnt/scripts/t4-fan.log`):

```
2026-10-04 00:50:47  GPU 51 C  CPU 43 C  Platten 38 C  X540 46 C  PCH 39 C  ->  Blower 42%  Gehaeuse 30%  Netz 30%
2026-10-04 00:51:18  GPU 48 C  CPU 43 C  Platten 38 C  X540 46 C  PCH 38 C  ->  Blower 38%  Gehaeuse 30%  Netz 30%
2026-10-04 00:52:02  GPU 41 C  CPU 42 C  Platten 38 C  X540 44 C  PCH 38 C  ->  Blower 30%  Gehaeuse 30%  Netz 30%
2026-10-04 00:52:53  GPU 48 C  CPU 44 C  Platten 38 C  X540 46 C  PCH 39 C  ->  Blower 36%  Gehaeuse 30%  Netz 30%
2026-10-04 00:53:03  GPU 52 C  CPU 45 C  Platten 38 C  X540 46 C  PCH 40 C  ->  Blower 44%  Gehaeuse 30%  Netz 30%
2026-10-04 00:53:14  GPU 56 C  CPU 45 C  Platten 38 C  X540 46 C  PCH 40 C  ->  Blower 52%  Gehaeuse 30%  Netz 30%
2026-10-04 00:53:24  GPU 58 C  CPU 48 C  Platten 38 C  X540 46 C  PCH 41 C  ->  Blower 58%  Gehaeuse 30%  Netz 30%
2026-10-04 00:53:35  GPU 59 C  CPU 49 C  Platten 38 C  X540 47 C  PCH 41 C  ->  Blower 61%  Gehaeuse 30%  Netz 30%
2026-10-04 00:53:45  GPU 61 C  CPU 46 C  Platten 38 C  X540 47 C  PCH 41 C  ->  Blower 67%  Gehaeuse 30%  Netz 30%
2026-10-04 00:53:56  GPU 62 C  CPU 50 C  Platten 38 C  X540 47 C  PCH 42 C  ->  Blower 70%  Gehaeuse 30%  Netz 30%
2026-10-04 00:54:29  GPU 63 C  CPU 51 C  Platten 38 C  X540 48 C  PCH 42 C  ->  Blower 73%  Gehaeuse 30%  Netz 30%
2026-10-04 00:55:19  GPU 64 C  CPU 50 C  Platten 37 C  X540 48 C  PCH 43 C  ->  Blower 76%  Gehaeuse 30%  Netz 30%
2026-10-04 00:56:09  GPU 65 C  CPU 48 C  Platten 37 C  X540 49 C  PCH 43 C  ->  Blower 80%  Gehaeuse 30%  Netz 30%
2026-10-04 00:56:20  GPU 64 C  CPU 48 C  Platten 37 C  X540 49 C  PCH 43 C  ->  Blower 76%  Gehaeuse 30%  Netz 30%
2026-10-04 00:56:30  GPU 65 C  CPU 47 C  Platten 37 C  X540 49 C  PCH 43 C  ->  Blower 80%  Gehaeuse 30%  Netz 30%
2026-10-04 00:56:40  GPU 63 C  CPU 47 C  Platten 37 C  X540 49 C  PCH 43 C  ->  Blower 76%  Gehaeuse 30%  Netz 30%
2026-10-04 00:56:51  GPU 65 C  CPU 51 C  Platten 37 C  X540 49 C  PCH 43 C  ->  Blower 80%  Gehaeuse 30%  Netz 30%
2026-10-04 00:57:22  GPU 63 C  CPU 50 C  Platten 37 C  X540 50 C  PCH 43 C  ->  Blower 76%  Gehaeuse 30%  Netz 30%
2026-10-04 00:57:32  GPU 65 C  CPU 48 C  Platten 37 C  X540 50 C  PCH 43 C  ->  Blower 80%  Gehaeuse 30%  Netz 30%
2026-10-04 01:01:28  GPU 57 C  CPU 46 C  Platten 37 C  X540 50 C  PCH 42 C  ->  Blower 75%  Gehaeuse 30%  Netz 30%
2026-10-04 01:01:38  GPU 54 C  CPU 45 C  Platten 37 C  X540 50 C  PCH 41 C  ->  Blower 70%  Gehaeuse 30%  Netz 30%
2026-10-04 01:01:48  GPU 51 C  CPU 44 C  Platten 37 C  X540 50 C  PCH 40 C  ->  Blower 65%  Gehaeuse 30%  Netz 30%
2026-10-04 01:01:59  GPU 48 C  CPU 44 C  Platten 37 C  X540 50 C  PCH 39 C  ->  Blower 60%  Gehaeuse 30%  Netz 30%
2026-10-04 01:02:09  GPU 47 C  CPU 43 C  Platten 37 C  X540 50 C  PCH 39 C  ->  Blower 55%  Gehaeuse 30%  Netz 30%
2026-10-04 01:02:19  GPU 46 C  CPU 43 C  Platten 37 C  X540 50 C  PCH 39 C  ->  Blower 50%  Gehaeuse 30%  Netz 30%
2026-10-04 01:02:30  GPU 45 C  CPU 43 C  Platten 37 C  X540 50 C  PCH 38 C  ->  Blower 45%  Gehaeuse 30%  Netz 30%
2026-10-04 01:02:40  GPU 44 C  CPU 42 C  Platten 37 C  X540 50 C  PCH 38 C  ->  Blower 40%  Gehaeuse 30%  Netz 30%
2026-10-04 01:02:50  GPU 43 C  CPU 42 C  Platten 37 C  X540 50 C  PCH 38 C  ->  Blower 35%  Gehaeuse 30%  Netz 30%
2026-10-04 01:03:01  GPU 43 C  CPU 42 C  Platten 37 C  X540 50 C  PCH 38 C  ->  Blower 30%  Gehaeuse 30%  Netz 30%
```

## 4. Geschlossenes Gehäuse, TrueNAS 27 (06.10.2026)

Nach dem Update auf TrueNAS 27.0.0-RC.1, Gehäusedeckel geschlossen. Dieselbe
Last wie oben (`nbody`, hier ohne Container direkt auf dem Host gestartet),
die Regelung arbeitet frei. Acht Minuten Last, danach sechs Minuten Ruhe.
Treiber unverändert 580.173.02. Kurzlauf vorab: 4.136 GFLOP/s.

Ergebnis: Die Karte wird im geschlossenen Gehäuse rund 10 K wärmer als im
offenen Aufbau. Der Blower steht nach gut zwei Minuten auf 100 %, die GPU
erreicht 74–75 °C und steigt am Ende nur noch um 1 K in drei Minuten. Grenzen
der T4 laut `nvidia-smi`: Max Operating 85 °C, Slowdown 93 °C, Shutdown 96 °C.
Eine thermische Drosselung trat nicht auf, aktiver Grund war nur die
Leistungsgrenze (`0x4`). Die Gehäusezone (Noctua hinten) blieb bei 30–33 %,
weil sie nach Platten- und CPU-Temperatur regelt, nicht nach der GPU.

Spalten: Uhrzeit, Phase, GPU-Temperatur, Leistung, SM-Takt, Auslastung,
Leistungszustand, gemessene Blowerdrehzahl (U/min).

```
22:50:12  last   49 °C   32.64 W   1245 MHz   38 %  P0  Blower 3800
22:50:22  last   57 °C   67.88 W   1155 MHz  100 %  P0  Blower 4500
22:50:33  last   60 °C   67.74 W   1155 MHz  100 %  P0  Blower 5200
22:50:43  last   63 °C   67.74 W   1125 MHz  100 %  P0  Blower 5700
22:50:54  last   65 °C   67.20 W   1110 MHz  100 %  P0  Blower 6000
22:51:05  last   66 °C   67.83 W   1110 MHz  100 %  P0  Blower 6200
22:51:15  last   67 °C   67.74 W   1110 MHz  100 %  P0  Blower 6300
22:51:26  last   68 °C   64.88 W   1095 MHz  100 %  P0  Blower 6500
22:51:36  last   68 °C   68.06 W   1080 MHz  100 %  P0  Blower 6500
22:51:47  last   69 °C   67.88 W   1080 MHz  100 %  P0  Blower 6600
22:51:58  last   70 °C   67.45 W   1095 MHz  100 %  P0  Blower 6600
22:52:08  last   70 °C   68.26 W   1080 MHz  100 %  P0  Blower 6600
22:52:19  last   70 °C   65.82 W   1080 MHz  100 %  P0  Blower 6700
22:52:29  last   71 °C   68.26 W   1080 MHz  100 %  P0  Blower 6800
22:52:40  last   71 °C   66.17 W   1110 MHz  100 %  P0  Blower 6800
22:52:51  last   71 °C   65.69 W   1080 MHz  100 %  P0  Blower 6800
22:53:01  last   72 °C   68.17 W   1050 MHz  100 %  P0  Blower 6800
22:53:12  last   72 °C   65.78 W   1065 MHz  100 %  P0  Blower 6900
22:53:23  last   72 °C   66.41 W   1080 MHz  100 %  P0  Blower 6800
22:53:33  last   72 °C   66.60 W   1095 MHz  100 %  P0  Blower 6800
22:53:44  last   72 °C   64.74 W   1080 MHz  100 %  P0  Blower 6900
22:53:54  last   73 °C   63.82 W   1080 MHz  100 %  P0  Blower 6800
22:54:05  last   73 °C   67.07 W   1065 MHz  100 %  P0  Blower 6800
22:54:16  last   73 °C   66.22 W   1065 MHz  100 %  P0  Blower 6800
22:54:26  last   73 °C   65.56 W   1065 MHz  100 %  P0  Blower 6800
22:54:37  last   73 °C   66.25 W   1065 MHz  100 %  P0  Blower 6800
22:54:47  last   73 °C   66.03 W   1050 MHz  100 %  P0  Blower 6800
22:54:58  last   73 °C   65.79 W   1065 MHz  100 %  P0  Blower 6800
22:55:09  last   74 °C   66.88 W   1080 MHz  100 %  P0  Blower 6800
22:55:19  last   74 °C   61.58 W   1065 MHz  100 %  P0  Blower 6800
22:55:30  last   74 °C   64.80 W   1065 MHz  100 %  P0  Blower 6800
22:55:40  last   74 °C   67.22 W   1050 MHz  100 %  P0  Blower 6800
22:55:53  last   74 °C   66.94 W   1065 MHz  100 %  P0  Blower 6800
22:56:04  last   74 °C   67.03 W   1050 MHz  100 %  P0  Blower 6800
22:56:14  last   74 °C   65.80 W   1065 MHz  100 %  P0  Blower 6800
22:56:25  last   74 °C   65.49 W   1065 MHz  100 %  P0  Blower 6800
22:56:35  last   74 °C   65.75 W   1065 MHz  100 %  P0  Blower 6800
22:56:46  last   74 °C   65.75 W   1065 MHz  100 %  P0  Blower 6800
22:56:57  last   74 °C   66.27 W   1050 MHz  100 %  P0  Blower 6800
22:57:07  last   74 °C   66.25 W   1065 MHz  100 %  P0  Blower 6800
22:57:18  last   75 °C   61.59 W   1050 MHz  100 %  P0  Blower 6800
22:57:28  last   74 °C   66.84 W   1050 MHz  100 %  P0  Blower 6800
22:57:39  last   75 °C   65.27 W   1065 MHz  100 %  P0  Blower 6800
22:57:50  last   75 °C   66.26 W   1050 MHz  100 %  P0  Blower 6800
22:58:00  last   74 °C   68.55 W   1050 MHz  100 %  P0  Blower 6800
22:58:11  last   75 °C   66.37 W   1050 MHz  100 %  P0  Blower 6800
22:58:22  ruhe   67 °C   11.80 W    300 MHz    0 %  P8  Blower 6900
22:58:32  ruhe   62 °C   11.32 W    300 MHz    0 %  P8  Blower 6900
22:58:43  ruhe   58 °C   11.04 W    300 MHz    0 %  P8  Blower 6700
22:58:53  ruhe   55 °C   10.84 W    300 MHz    0 %  P8  Blower 6500
22:59:04  ruhe   53 °C   10.64 W    300 MHz    0 %  P8  Blower 6400
22:59:15  ruhe   51 °C   10.64 W    300 MHz    0 %  P8  Blower 6300
22:59:25  ruhe   50 °C   10.46 W    300 MHz    0 %  P8  Blower 6000
22:59:36  ruhe   49 °C   10.35 W    300 MHz    0 %  P8  Blower 5800
22:59:46  ruhe   48 °C   10.65 W    300 MHz    0 %  P8  Blower 5500
22:59:57  ruhe   47 °C   10.84 W    300 MHz    0 %  P8  Blower 5300
23:00:08  ruhe   47 °C   10.66 W    300 MHz    0 %  P8  Blower 5100
23:00:18  ruhe   46 °C   10.84 W    300 MHz    0 %  P8  Blower 4800
23:00:29  ruhe   46 °C   10.35 W    300 MHz    0 %  P8  Blower 4500
23:00:40  ruhe   46 °C   11.32 W    300 MHz    0 %  P8  Blower 4100
23:00:50  ruhe   46 °C   11.13 W    300 MHz    0 %  P8  Blower 3800
23:01:01  ruhe   46 °C   10.76 W    300 MHz    0 %  P8  Blower 3500
23:01:11  ruhe   45 °C   10.74 W    300 MHz    0 %  P8  Blower 3500
23:01:22  ruhe   45 °C   10.35 W    300 MHz    0 %  P8  Blower 3400
23:01:33  ruhe   45 °C   10.55 W    300 MHz    0 %  P8  Blower 3500
23:01:43  ruhe   45 °C   10.65 W    300 MHz    0 %  P8  Blower 3500
23:01:54  ruhe   45 °C   10.93 W    300 MHz    0 %  P8  Blower 3400
23:02:04  ruhe   45 °C   10.64 W    300 MHz    0 %  P8  Blower 3400
23:02:15  ruhe   45 °C   10.73 W    300 MHz    0 %  P8  Blower 3400
23:02:26  ruhe   44 °C   10.46 W    300 MHz    0 %  P8  Blower 3400
23:02:36  ruhe   44 °C   10.15 W    300 MHz    0 %  P8  Blower 3400
23:02:47  ruhe   44 °C   10.25 W    300 MHz    0 %  P8  Blower 3400
23:02:57  ruhe   44 °C   11.52 W    300 MHz    0 %  P8  Blower 3400
23:03:08  ruhe   44 °C   10.36 W    300 MHz    0 %  P8  Blower 3400
23:03:19  ruhe   44 °C   10.16 W    300 MHz    0 %  P8  Blower 3400
23:03:29  ruhe   44 °C   10.26 W    300 MHz    0 %  P8  Blower 3400
23:03:40  ruhe   44 °C   10.16 W    300 MHz    0 %  P8  Blower 3400
23:03:50  ruhe   44 °C   10.16 W    300 MHz    0 %  P8  Blower 3400
23:04:01  ruhe   44 °C   10.16 W    300 MHz    0 %  P8  Blower 3400
23:04:12  ruhe   44 °C   10.16 W    300 MHz    0 %  P8  Blower 3400
```
