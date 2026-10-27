# Changelog

Alle nennenswerten Änderungen an SGRM werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Geändert
- Das Image liegt jetzt unter `ghcr.io/revisor01/sgrm` statt `revisoren/sgrm` auf Docker Hub; dort erscheinen keine neuen Versionen mehr.

### Sonstiges
- README, Vorlagen und Hinweise gibt es nur noch auf Deutsch.

## [1.3.0] - 2026-10-24

### Hinzugefügt
- `SGRM_ADMIN_PASSWORD`: Startpasswort des Admin-Benutzers beim ersten Start (sonst weiterhin `admin`, mit Warnung im Log)
- Login-Begrenzung: max. 5 Fehlversuche pro Client-IP in 15 Minuten, danach HTTP 429; fehlgeschlagene Logins werden geloggt
- `SGRM_TRUSTED_PROXIES` für den Betrieb hinter Reverse Proxies (echte Client-IP via `X-Forwarded-For`)
- CI: Smoke-Test startet das gebaute Image vor dem Push (Healthcheck, öffentliche Seiten, Nicht-root-Prozesse, Übernahme root-eigener Volumes, schnelles `docker stop`)

### Sicherheit
- Container-Prozesse laufen nicht mehr als root, sondern als Benutzer `sgrm` (UID 1000). `start.sh` übernimmt bestehende Volumes per `chown` und wechselt dann per `setpriv` den Benutzer
- Dependencies aktualisiert (offene Dependabot-PRs #4 und #5): werkzeug 3.1.9, aiohttp 3.14.5, außerdem flask-wtf 1.3.0, pyyaml 6.0.3, markdown 3.11.2, nh3 0.3.7
- Workflow: `image_tag`-Eingabe und Portainer-Webhook-URL werden über Umgebungsvariablen statt per Template-Interpolation an das Shell-Skript übergeben (Script-Injection), das Tag wird validiert
- Session-Cookies mit `SameSite=Lax`

### Behoben
- Releases ohne Beschreibung (`body: null` von der GitHub-API) führten zu einem Fehler, nachdem der Zeitstempel bereits gespeichert war — die Benachrichtigung ging dadurch verloren. Gleiches gilt für fehlenden `name`/`author`
- Schlägt der ntfy-Versand fehl, wird der Zeitstempel nicht fortgeschrieben, sodass die Benachrichtigung im nächsten Zyklus erneut versucht wird
- Prüfintervall wird auf mindestens 60 Sekunden begrenzt (vorher führte `0` zu einer Endlosschleife gegen die GitHub-API)
- Konfigurations- und Datendateien werden atomar geschrieben — Web-UI und Monitoring-Prozess können keine halb geschriebenen Dateien mehr lesen
- Ein manueller Check aus der Web-UI konnte parallel zum regulären Durchlauf laufen und dasselbe Release doppelt melden. Checks und das Entfernen von Repos laufen jetzt unter einer gemeinsamen Dateisperre
- `docker stop` beendet den Container sofort sauber (SIGTERM wird an beide Prozesse weitergereicht) statt nach 10 s per SIGKILL
- CI-Build für Dependabot-PRs schlug fehl, weil der Docker-Hub-Login ohne Secrets lief — Login läuft jetzt nur, wenn auch gepusht wird

### Geändert
- Basis-Image `python:3.13-slim` (vorher 3.11)
- GitHub Actions auf aktuelle Major-Versionen (Node 24) aktualisiert
- Dependabot-Versionsupdates für pip, GitHub Actions und Docker (monatlich, gebündelt) über `.github/dependabot.yml`
- Abhängigkeit `pytz` entfernt (ersetzt durch `datetime.timezone`)
- Abhängigkeit `requests` entfernt: ntfy-Benachrichtigungen laufen über `aiohttp` und die ntfy-JSON-API (Umlaute in Titel/Tags ohne Header-Encoding, blockiert den Event-Loop nicht mehr)

## [1.2.0] - 2026-08-02

### Hinzugefügt
- Konfigurations- und Datenverzeichnis sind über `SGRM_CONFIG_DIR` und `SGRM_DATA_DIR` einstellbar. Die Standardwerte (`/app/config`, `/app/data`) entsprechen den bisherigen fest verdrahteten Pfaden — für den Container ändert sich nichts, ein Start außerhalb von Docker ist damit aber ohne Codeänderung möglich
- README dokumentiert die Umgebungsvariablen und den lokalen Start ohne Docker

## [1.1.3] - 2026-08-02

### Sicherheit
- Dependencies aktualisiert: werkzeug 3.1.6 (`safe_join()` ließ Windows-Gerätenamen zu), flask 3.1.3 (fehlender `Vary: Cookie`-Header)
- Repo-Validierung ohne mehrdeutiges Backtracking umgesetzt, um ReDoS auszuschließen (CodeQL: `py/polynomial-redos`)

## [1.1.2] - 2026-08-02

### Sicherheit
- Repository-Eingabe wird strenger validiert: Owner und Repo müssen dem GitHub-Namensschema entsprechen. Vorher konnten Eingaben wie `evilgithub.com/foo/bar` die URL-Erkennung umgehen und als vermeintliches Repository gespeichert werden (CodeQL: `py/incomplete-url-substring-sanitization`)
- GitHub-Actions-Workflow auf minimale Berechtigungen (`contents: read`) beschränkt (CodeQL: `actions/missing-workflow-permissions`)

### Hinzugefügt
- CodeQL Code Scanning und Dependabot Security Updates für das Repository aktiviert

### Geändert
- README dokumentiert den Deployment-Weg (GitHub Actions → Docker Hub → Portainer-Webhook) inkl. benötigter Secrets

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
