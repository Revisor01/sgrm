<h1 align="center">SGRM</h1>

<p align="center">
  Simple GitHub Release Monitor mit Web-Dashboard und Push-Benachrichtigungen via <a href="https://ntfy.sh">ntfy</a>.
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/Revisor01/sgrm/docker-publish.yml?logo=github" alt="Build">
  <img src="https://img.shields.io/badge/Python-3.13-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Docker-ready-blue?logo=docker" alt="Docker">
  <img src="https://img.shields.io/github/license/Revisor01/sgrm" alt="License">
  <img src="https://img.shields.io/github/v/release/Revisor01/sgrm" alt="Version">
</p>

## Worum es geht

Wer Software selbst betreibt, will wissen, wann es eine neue Version gibt —
für viele Projekte auf GitHub, ohne jedes einzeln zu beobachten. SGRM prüft
die eingetragenen Repositories in festen Abständen, schickt bei einem neuen
Release eine Mitteilung über [ntfy](https://ntfy.sh) und zeigt alle Releases
auf einer öffentlichen Seite. Eine Demo läuft unter
[sgrm.godsapp.de/releases](https://sgrm.godsapp.de/releases).

## Funktionen

- **Release-Überwachung** — Überwacht Repositories auf neue Releases
- **Mitteilungen** — Sofortige Notifications via ntfy.sh (self-hosted oder Cloud)
- **Öffentliche Übersicht** — Schöne Web-UI ohne Login erforderlich
- **Verwaltung** — Einfache Konfiguration über Web-Interface
- Hell und Dunkel
- **Ein Container** — keine Datenbank nötig

## Installation

```bash
docker run -d \
  --name sgrm \
  -p 8080:8080 \
  -v ./config:/app/config \
  -v ./data:/app/data \
  revisoren/sgrm
```

Öffne http://localhost:8080 und melde dich mit `admin` / `admin` an — oder setze beim ersten Start `-e SGRM_ADMIN_PASSWORD=...`, dann gilt dieses Passwort.

### Docker Compose

```yaml
services:
  sgrm:
    image: revisoren/sgrm
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    restart: unless-stopped
```

## Einrichtung

Nach dem ersten Start:

1. **Anmelden** mit `admin` / `admin`
2. **Passwort ändern** unter "Benutzer"
3. **GitHub Token** eintragen (optional, erhöht Rate Limit von 60 auf 5000 Anfragen/Stunde)
4. **Repositories** hinzufügen (GitHub-URL oder `owner/repo`)
5. **ntfy** konfigurieren (Server-URL und Topic)

### Einstellungen

| Einstellung | Beschreibung |
|-------------|--------------|
| GitHub Token | Personal Access Token (keine Scopes nötig für public repos) |
| ntfy Topic | Topic für Push-Benachrichtigungen |
| ntfy Token | Access Token für authentifizierte ntfy-Server |
| ntfy Base URL | URL deines ntfy-Servers (Standard: https://ntfy.sh) |
| Intervall | Prüfintervall in Sekunden (Standard: 3600) |
| Base URL | Öffentliche URL deiner SGRM-Instanz (für Links in Notifications) |

## Gut zu wissen

- Beim ersten Check eines neu hinzugefügten Repositories wird nur eine Baseline gesetzt — benachrichtigt wird erst ab dem nächsten neuen Release.
- Konfigurationsänderungen (Repos, Intervall, Token) wirken ohne Neustart ab dem nächsten Prüfzyklus.
- Release-Notes werden serverseitig sanitisiert (XSS-Schutz auf den öffentlichen Seiten).
- Login: nach 5 Fehlversuchen innerhalb von 15 Minuten wird die Client-IP für den Rest des Zeitfensters gesperrt.
- Die Anwendung läuft im Container als Benutzer `sgrm` (UID 1000). Beim Start übernimmt sie die Config-/Data-Verzeichnisse per `chown`, bestehende Volumes funktionieren also ohne manuellen Eingriff.

## Versionen

Was sich wann geändert hat, steht in [CHANGELOG.md](CHANGELOG.md) — nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), aus Sicht der
Nutzer:innen geschrieben. Die
[Releases](https://github.com/Revisor01/sgrm/releases) fassen jede Version
zusammen.

## Selbst betreiben

Das Image `revisoren/sgrm` auf Docker Hub ist der einfachste Weg (siehe
Installation). Konfiguration und Daten liegen in zwei Verzeichnissen, eine
Datenbank gibt es nicht.

### Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `SGRM_CONFIG_DIR` | `/app/config` | Verzeichnis für `config.yaml`, `users.json` und `secret_key` |
| `SGRM_DATA_DIR` | `/app/data` | Verzeichnis für `releases.json` und `last_checks.json` |
| `SGRM_ADMIN_PASSWORD` | `admin` | Startpasswort des Admin-Benutzers. Wirkt nur beim ersten Start (solange noch keine `users.json` existiert) |
| `SGRM_TRUSTED_PROXIES` | `0` | Anzahl vorgeschalteter Reverse Proxies (z. B. `1` hinter Traefik/nginx). Nötig, damit die Login-Begrenzung die echte Client-IP aus `X-Forwarded-For` nutzt — sonst teilen sich alle Clients die IP des Proxys |

Im Container müssen beide nicht gesetzt werden — die Standardwerte entsprechen den Volume-Mounts. Für einen lokalen Start ohne Docker:

```bash
pip install -r requirements.txt
SGRM_CONFIG_DIR=./config SGRM_DATA_DIR=./data python web_interface.py
```

## Aufbau

```
sgrm
├── web_interface.py   — Weboberfläche, Anmeldung, JSON-API (Flask)
├── monitoring.py      — Prüfschleife: GitHub abfragen, ntfy benachrichtigen
├── templates/ static/ — Seiten und Stylesheets
├── start.sh           — startet beide Prozesse im Container ohne root
└── Dockerfile
```

**Worauf es beim Bauen ankommt:**
- **Zwei Prozesse, eine Datenlage.** Oberfläche und Prüfschleife teilen sich
  nur die Dateien in `config/` und `data/`; Schreibzugriffe sind atomar.
- **Release-Notes sind fremder Inhalt.** Sie werden vor der Anzeige bereinigt.
- **Kein root im Container.**

### API

SGRM bietet eine einfache JSON-API:

```
GET /api/releases          # Alle Releases
GET /api/releases/{slug}   # Einzelnes Release (z.B. owner-repo)
GET /health                # Healthcheck (für Docker/Uptime-Monitoring)
```

## Mitmachen

Fehlermeldungen und Vorschläge sind willkommen — gern als
[Issue](https://github.com/Revisor01/sgrm/issues). Sicherheitslücken bitte
vertraulich melden, wie in [SECURITY.md](SECURITY.md) beschrieben. Pull
Requests laufen durch einen Smoke-Test des Images und einen Secret-Scan; die
Grundsätze für Beiträge stehen in [CLAUDE.md](CLAUDE.md).

## Lizenz

SGRM steht unter der [GNU Affero General Public License v3.0](LICENSE).

## Kontakt

Pastor Simon Luthe · [mail@simonluthe.de](mailto:mail@simonluthe.de) ·
[simonluthe.de](https://simonluthe.de)
