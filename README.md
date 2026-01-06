# SGRM - Simple GitHub Release Monitor

Ein einfacher GitHub Release Monitor mit Web-Dashboard und Push-Benachrichtigungen via ntfy.sh.

## Features

- Überwacht GitHub Repositories auf neue Releases
- Push-Benachrichtigungen über ntfy.sh
- Öffentliche Release-Übersicht (ohne Login)
- Admin-Dashboard zur Konfiguration
- Dark Mode
- Docker-ready

## Schnellstart

```bash
docker run -d \
  --name sgrm \
  -p 8080:8080 \
  -v ./config:/app/config \
  -v ./data:/app/data \
  revisoren/sgrm
```

Dann öffne http://localhost:8080 und melde dich mit `admin` / `admin` an.

## Docker Compose

```yaml
version: '3'
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

```bash
docker-compose up -d
```

## Konfiguration

Nach dem ersten Start:

1. Anmelden mit `admin` / `admin`
2. Passwort ändern unter "Benutzer"
3. GitHub Token eintragen (optional, erhöht Rate Limit)
4. Repositories hinzufügen (URL oder `owner/repo`)
5. ntfy Topic konfigurieren
