#!/bin/bash
set -e

# Volumes aus root-Versionen dem App-Benutzer übergeben, dann ohne root neu starten.
if [ "$(id -u)" = "0" ]; then
    chown -R sgrm:sgrm "${SGRM_CONFIG_DIR:-/app/config}" "${SGRM_DATA_DIR:-/app/data}"
    exec setpriv --reuid=sgrm --regid=sgrm --init-groups "$0" "$@"
fi

echo "Starte Web-Interface..."
python web_interface.py &

echo "Starte Monitoring-Service..."
python monitoring.py &

# bash als PID 1 ignoriert SIGTERM, sonst killt docker stop erst nach 10 s.
trap 'kill $(jobs -p) 2>/dev/null' TERM INT

# Container beenden, sobald ein Prozess stirbt, damit die Restart-Policy greift.
wait -n
exit $?
