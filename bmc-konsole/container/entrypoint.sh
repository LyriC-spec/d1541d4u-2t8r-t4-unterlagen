#!/bin/sh
set -e
: "${BMC_HOST:?BMC_HOST fehlt}"
: "${BMC_PASSWORD:?BMC_PASSWORD fehlt}"

mkdir -p /data/tls /data/jviewer
if [ ! -s /data/tls/cert.pem ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -subj "/CN=bmc-konsole" -keyout /data/tls/key.pem -out /data/tls/cert.pem 2>/dev/null
  echo "Selbstsigniertes Zertifikat erzeugt (/data/tls)"
fi
# VNC-Kennwort: x11vnc lauscht nur auf localhost, im Host-Netz aber fuer alle
# lokalen Prozesse erreichbar. Neues Zufallskennwort bei jedem Containerstart.
mkdir -p /data/vnc
head -c 12 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 8 > /data/vnc/klartext
x11vnc -storepasswd "$(cat /data/vnc/klartext)" /data/vnc/passwd >/dev/null 2>&1
chmod 700 /data/vnc; chmod 600 /data/vnc/klartext /data/vnc/passwd

chown -R konsole:konsole /data
chmod 600 /data/tls/key.pem

# Reste eines unsauber beendeten Laufs: Xvfb haelt eine alte Sperrdatei mit
# einer im neuen PID-Namensraum wiederverwendeten PID fuer aktiv
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
mkdir -p -m 1777 /tmp/.X11-unix

exec /usr/bin/supervisord -c /etc/supervisor/bmc-konsole.conf
