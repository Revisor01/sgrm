#!/bin/bash
set -e

# Starte den Web-Server im Hintergrund
echo "Starte Web-Interface..."
python web_interface.py &

# Starte den Monitoring-Service
echo "Starte Monitoring-Service..."
python monitoring.py