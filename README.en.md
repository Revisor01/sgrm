<h1 align="center">SGRM</h1>

<p align="center">
  Simple GitHub Release Monitor with a web dashboard and push notifications via <a href="https://ntfy.sh">ntfy</a>.
</p>

<p align="center">
  <a href="README.md">Deutsch</a> · <b>English</b>
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/Revisor01/sgrm/docker-publish.yml?logo=github" alt="Build">
  <img src="https://img.shields.io/badge/Python-3.13-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Docker-ready-blue?logo=docker" alt="Docker">
  <img src="https://img.shields.io/github/license/Revisor01/sgrm" alt="License">
  <img src="https://img.shields.io/github/v/release/Revisor01/sgrm" alt="Version">
</p>

## What it is about

If you run software yourself, you want to know when a new version is out — for
many projects on GitHub, without watching each one. SGRM checks the
repositories you add at fixed intervals, sends a notification via
[ntfy](https://ntfy.sh) when a new release appears and lists all releases on a
public page. A demo runs at
[sgrm.godsapp.de/releases](https://sgrm.godsapp.de/releases).

## Features

- **Release monitoring** — watches repositories for new releases
- **Notifications** — instant notifications via ntfy.sh (self-hosted or cloud)
- **Public overview** — a clean web UI, no login required
- **Management** — simple configuration in the web interface
- Light and dark mode
- **One container** — no database needed

## Installation

```bash
docker run -d \
  --name sgrm \
  -p 8080:8080 \
  -v ./config:/app/config \
  -v ./data:/app/data \
  ghcr.io/revisor01/sgrm
```

Open http://localhost:8080 and sign in with `admin` / `admin` — or set
`-e SGRM_ADMIN_PASSWORD=...` on first start, then that password applies.

### Docker Compose

```yaml
services:
  sgrm:
    image: ghcr.io/revisor01/sgrm
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    restart: unless-stopped
```

## Setup

After the first start:

1. **Sign in** with `admin` / `admin`
2. **Change the password** under “Benutzer” (users)
3. **GitHub token** (optional, raises the rate limit from 60 to 5,000 requests per hour)
4. **Add repositories** (GitHub URL or `owner/repo`)
5. **Configure ntfy** (server URL and topic)

The web interface itself is in German.

### Settings

| Setting | Description |
|---------|-------------|
| GitHub token | Personal access token (no scopes needed for public repos) |
| ntfy topic | Topic for push notifications |
| ntfy token | Access token for ntfy servers with authentication |
| ntfy base URL | URL of your ntfy server (default: https://ntfy.sh) |
| Interval | Check interval in seconds (default: 3600) |
| Base URL | Public URL of your SGRM instance (for links in notifications) |

## Good to know

- The first check of a newly added repository only sets a baseline — you get
  notified from the next new release on.
- Configuration changes (repos, interval, token) take effect from the next
  check cycle, without a restart.
- Release notes are sanitised on the server (XSS protection on the public pages).
- Login: after 5 failed attempts within 15 minutes, the client IP is blocked for
  the rest of that window.
- In the container the application runs as user `sgrm` (UID 1000). On start it
  takes ownership of the config and data directories via `chown`, so existing
  volumes work without manual steps.

## Versions

What changed when is in [CHANGELOG.md](CHANGELOG.md) (in German, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)). The
[releases](https://github.com/Revisor01/sgrm/releases) summarise each version.

## Running it yourself

The `ghcr.io/revisor01/sgrm` image is the simplest way (see Installation).
Configuration and data live in two directories; there is no database.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SGRM_CONFIG_DIR` | `/app/config` | Directory for `config.yaml`, `users.json` and `secret_key` |
| `SGRM_DATA_DIR` | `/app/data` | Directory for `releases.json` and `last_checks.json` |
| `SGRM_ADMIN_PASSWORD` | `admin` | Initial password of the admin user. Only used on first start (while no `users.json` exists) |
| `SGRM_TRUSTED_PROXIES` | `0` | Number of reverse proxies in front (e.g. `1` behind Traefik/nginx). Needed so the login limit uses the real client IP from `X-Forwarded-For` — otherwise all clients share the proxy's IP |

Inside the container you do not need to set either directory — the defaults
match the volume mounts. To run locally without Docker:

```bash
pip install -r requirements.txt
SGRM_CONFIG_DIR=./config SGRM_DATA_DIR=./data python web_interface.py
```

## Structure

```
sgrm
├── web_interface.py   — web interface, login, JSON API (Flask)
├── monitoring.py      — check loop: query GitHub, notify via ntfy
├── templates/ static/ — pages and stylesheets
├── start.sh           — starts both processes in the container without root
└── Dockerfile
```

**What matters when building it:**
- **Two processes, one set of data.** The interface and the check loop only
  share the files in `config/` and `data/`; writes are atomic.
- **Release notes are third-party content.** They are sanitised before display.
- **No root in the container.**

### API

SGRM offers a simple JSON API:

```
GET /api/releases          # all releases
GET /api/releases/{slug}   # a single release (e.g. owner-repo)
GET /health                # health check (for Docker/uptime monitoring)
```

## Contributing

Bug reports and suggestions are welcome as an
[issue](https://github.com/Revisor01/sgrm/issues). Please report security
issues privately as described in [SECURITY.md](SECURITY.md). Pull requests go
through a smoke test of the image and a secret scan; see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

SGRM is licensed under the [GNU Affero General Public License v3.0](LICENSE).
If you modify it and make it available to others, you publish your source code
under the same license. The [LICENSE](LICENSE) file is authoritative;
contributions follow [CONTRIBUTING.md](CONTRIBUTING.md).

## Contact

Pastor Simon Luthe · [mail@simonluthe.de](mailto:mail@simonluthe.de) ·
[simonluthe.de](https://simonluthe.de)
