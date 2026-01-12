<h1 align="center">SGRM</h1>

<p align="center">
  Simple GitHub Release Monitor mit Web-Dashboard und Push-Benachrichtigungen via <a href="https://ntfy.sh">ntfy</a>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Docker-ready-blue?logo=docker" alt="Docker">
  <img src="https://img.shields.io/github/license/Revisor01/sgrm" alt="License">
  <img src="https://img.shields.io/github/v/release/Revisor01/sgrm" alt="Version">
</p>

<p align="center">
  <a href="https://sgrm.godsapp.de/releases">Demo</a> •
  <a href="#features">Features</a> •
  <a href="#schnellstart">Schnellstart</a> •
  <a href="#konfiguration">Konfiguration</a> •
  <a href="#api">API</a>
</p>

---

## Features

- **GitHub Release Tracking**: Überwacht Repositories auf neue Releases
- **Push-Benachrichtigungen**: Sofortige Notifications via ntfy.sh (self-hosted oder Cloud)
- **Öffentliche Release-Übersicht**: Schöne Web-UI ohne Login erforderlich
- **Admin-Dashboard**: Einfache Konfiguration über Web-Interface
- **Dark Mode**: Vollständige Unterstützung
- **Docker-ready**: Ein Container, keine Datenbank nötig

## Schnellstart

```bash
docker run -d \
  --name sgrm \
  -p 8080:8080 \
  -v ./config:/app/config \
  -v ./data:/app/data \
  revisoren/sgrm
```

Öffne http://localhost:8080 und melde dich mit `admin` / `admin` an.

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

## Konfiguration

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

## API

SGRM bietet eine einfache JSON-API:

```
GET /api/releases          # Alle Releases
GET /api/releases/{slug}   # Einzelnes Release (z.B. owner-repo)
```

## Lizenz

AGPL-3.0 - siehe [LICENSE](LICENSE)
