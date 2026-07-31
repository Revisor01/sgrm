#!/bin/bash
set -e

echo "Starte Web-Interface..."
python web_interface.py &

echo "Starte Monitoring-Service..."
python monitoring.py &

# Beendet den Container, sobald einer der beiden Prozesse stirbt,
# damit Dockers Restart-Policy greifen kann.
wait -n
exit $?
