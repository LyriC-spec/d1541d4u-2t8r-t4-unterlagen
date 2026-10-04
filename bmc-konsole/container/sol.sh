#!/bin/sh
# Textkonsole ueber IPMI Serial-over-LAN. ttyd startet das Skript je Verbindung.
export IPMI_PASSWORD="$BMC_PASSWORD"
I="ipmitool -I lanplus -H $BMC_HOST -U ${BMC_USER:-admin} -E -C 3"
# eine haengengebliebene alte Sitzung blockiert sonst die neue
$I sol deactivate >/dev/null 2>&1
echo "SOL-Verbindung zu $BMC_HOST. Ins BIOS: beim Start Entf oder F2. Beenden: ~."
exec $I sol activate
