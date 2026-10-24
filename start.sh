#!/bin/bash
set -e

# Als root gestartet: Config-/Data-Verzeichnisse (auch bestehende Volumes aus
# Versionen, die noch als root liefen) dem App-Benutzer übergeben und das
# Skript ohne root-Rechte neu starten.
if [ "$(id -u)" = "0" ]; then
    chown -R sgrm:sgrm "${SGRM_CONFIG_DIR:-/app/config}" "${SGRM_DATA_DIR:-/app/data}"
    exec setpriv --reuid=sgrm --regid=sgrm --init-groups "$0" "$@"
fi

echo "Starte Web-Interface..."
python web_interface.py &

echo "Starte Monitoring-Service..."
python monitoring.py &

# docker stop: SIGTERM an beide Prozesse weiterreichen statt nach 10 s
# per SIGKILL beendet zu werden (bash als PID 1 ignoriert SIGTERM sonst).
trap 'kill $(jobs -p) 2>/dev/null' TERM INT

# Beendet den Container, sobald einer der beiden Prozesse stirbt,
# damit Dockers Restart-Policy greifen kann.
wait -n
exit $?
