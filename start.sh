#!/bin/bash
set -e

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
