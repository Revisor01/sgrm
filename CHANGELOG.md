# Changelog

Alle nennenswerten Änderungen an SGRM werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.1.1] - 2026-07-31

### Sicherheit
- Dependencies aktualisiert und damit alle offenen Dependabot-Alerts behoben: aiohttp 3.14.1 (u. a. 1× high), werkzeug 3.1.5, requests 2.33.0, markdown 3.8.2

## [1.1.0] - 2026-07-31

### Sicherheit
- Produktions-WSGI-Server (Waitress) statt Flask-Entwicklungsserver mit `debug=True` (Werkzeug-Debugger war ein RCE-Risiko)
- Release-Notes werden vor der Anzeige sanitisiert (nh3) — XSS-Schutz auf den öffentlichen Release-Seiten
- CSRF-Schutz (Flask-WTF) für alle Formulare (Login, Konfiguration, Repos, Benutzer, manueller Check)
- Secret Key wird persistent in `/app/config/secret_key` gespeichert — Sessions überleben Container-Neustarts

### Hinzugefügt
- `GET /health` Healthcheck-Endpoint + Docker `HEALTHCHECK` im Image
- GitHub-Rate-Limit-Erkennung mit verständlicher Log-Meldung inkl. Reset-Zeitpunkt
- CHANGELOG.md (diese Datei)

### Geändert
- Monitoring lädt die Konfiguration vor jedem Prüfzyklus neu — Änderungen aus der Web-UI (Repos, Intervall, Token) wirken ohne Container-Neustart
- Beim ersten Check eines neu hinzugefügten Repos wird nur eine Baseline gesetzt statt sofort das bestehende Release als "neu" zu pushen
- ntfy: `Authorization`-Header wird nur noch gesendet, wenn ein Token konfiguriert ist
- Timeouts für alle HTTP-Requests (GitHub-API 30 s, ntfy 15 s)
- Standard-Konfiguration und Admin-User werden beim Start angelegt statt erst beim ersten Seitenaufruf
- `start.sh`: Container beendet sich, sobald Web- oder Monitoring-Prozess stirbt, damit die Docker-Restart-Policy greift
- Beim Entfernen eines Repos werden auch dessen gespeicherte Release- und Check-Daten gelöscht

### Behoben
- Absturz des Monitoring-Services bei fehlender Konfigurationsdatei (wartet jetzt und versucht es erneut)
- Fehlende Fehlerbehandlung beim manuellen Check über die Web-UI (500er-Fehler)
- Irreführende Log-Meldung bei Repos ohne Releases ("nicht gefunden")

## [1.0.0] - 2026-01-12

### Hinzugefügt
- Erstes Release: GitHub-Release-Tracking, ntfy-Push-Benachrichtigungen, öffentliche Release-Übersicht, Admin-Dashboard, Dark Mode, Docker-Image
