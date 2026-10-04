# BMC-Konsole: Weboberflaeche und HTML5-KVM fuer alte AMI-MegaRAC-BMCs
# Java 8, weil JViewer fuer Java 5 gebaut ist und neuere JREs die alten
# Swing-/AWT-Annahmen nicht mehr zuverlaessig erfuellen.
FROM eclipse-temurin:8-jre-jammy

ARG NOVNC_VERSION=1.5.0
ENV DEBIAN_FRONTEND=noninteractive \
    DATA_DIR=/data \
    WEB_DIR=/opt/bmc-konsole/web \
    FAN_CONFIG=/opt/bmc-konsole/fans.json

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      xvfb x11vnc x11-utils openbox xdotool fonts-dejavu-core \
      websockify nginx supervisor ipmitool openssl curl ca-certificates \
      python3 python3-flask python3-waitress python3-requests \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL https://github.com/novnc/noVNC/archive/refs/tags/v${NOVNC_VERSION}.tar.gz \
      | tar xz -C /opt \
 && mv /opt/noVNC-${NOVNC_VERSION} /opt/novnc \
 && useradd -r -m -d /home/konsole -s /usr/sbin/nologin konsole \
 && mkdir -p /data && chown konsole:konsole /data \
 && mkdir -p -m 1777 /tmp/.X11-unix

COPY app/ /opt/bmc-konsole/app/
COPY web/ /opt/bmc-konsole/web/
COPY fans.json /opt/bmc-konsole/fans.json
COPY container/supervisord.conf /etc/supervisor/bmc-konsole.conf
COPY container/nginx.conf /etc/nginx/nginx.conf
COPY container/openbox-rc.xml /home/konsole/.config/openbox/rc.xml
COPY container/entrypoint.sh /entrypoint.sh
RUN chown -R konsole:konsole /home/konsole && chmod 755 /entrypoint.sh

VOLUME /data
EXPOSE 8443
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD curl -fsk https://127.0.0.1:8443/api/auth/state >/dev/null || exit 1
ENTRYPOINT ["/entrypoint.sh"]
