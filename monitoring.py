#!/usr/bin/env python3
import requests
import json
import time
import os
import logging
from datetime import datetime, timedelta
import pytz
import traceback
import yaml
import asyncio
import aiohttp

# Konfiguration für das Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Konfigurationsdatei und Datenverzeichnis
CONFIG_FILE = "/app/config/config.yaml"
DATA_DIR = "/app/data"
LAST_CHECK_FILE = f"{DATA_DIR}/last_checks.json"
RELEASES_FILE = f"{DATA_DIR}/releases.json"

# Stellt sicher, dass die Verzeichnisse existieren
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

class ConfigManager:
    """Verwaltet die Konfiguration des Monitoring-Services"""
    
    @staticmethod
    def load_config():
        """Lädt die Konfiguration aus der YAML-Datei"""
        try:
            logger.info(f"Lade Konfiguration aus {CONFIG_FILE}")
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Konfiguration erfolgreich geladen")
                return config
        except FileNotFoundError:
            logger.error(f"Konfigurationsdatei {CONFIG_FILE} nicht gefunden")
            return None
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration: {str(e)}")
            return None

class DataManager:
    """Verwaltet die Zustandsdaten des Monitoring-Services"""

    @staticmethod
    def load_last_checks():
        """Lädt die letzten Prüfzeitpunkte"""
        try:
            logger.info(f"Lade letzte Checks aus {LAST_CHECK_FILE}")
            with open(LAST_CHECK_FILE, 'r') as f:
                data = json.load(f)
                logger.info("Letzte Checks erfolgreich geladen")
                return data
        except:
            logger.info("Keine vorherigen Checks gefunden, erstelle neue Datei")
            return {'github': {}}

    @staticmethod
    def save_last_checks(data):
        """Speichert die letzten Prüfzeitpunkte"""
        try:
            logger.info(f"Speichere Checks in {LAST_CHECK_FILE}")
            with open(LAST_CHECK_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                logger.info("Checks erfolgreich gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Checks: {e}")

    @staticmethod
    def load_releases():
        """Lädt die gespeicherten Release-Daten"""
        try:
            with open(RELEASES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}

    @staticmethod
    def save_release(repo, release_data):
        """Speichert Release-Daten für ein Repository"""
        try:
            releases = DataManager.load_releases()
            releases[repo] = release_data
            with open(RELEASES_FILE, 'w') as f:
                json.dump(releases, f, indent=2)
            logger.info(f"Release-Daten für {repo} gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Release-Daten: {e}")

class NotificationService:
    """Stellt Benachrichtigungsdienste bereit"""
    
    def __init__(self, config):
        self.config = config
        self.ntfy_token = config['ntfy']['token']
        self.ntfy_base_url = config['ntfy']['base_url']
    
    def send_ntfy(self, topic, title, message, tags=None, priority="default", extra_headers=None):
        """Sendet eine Benachrichtigung über ntfy.sh"""
        try:
            logger.info(f"Sende ntfy Nachricht an Topic {topic}")
            logger.debug(f"Title: {title}")
            logger.debug(f"Message: {message}")
            
            headers = {
                "Authorization": f"Bearer {self.ntfy_token}",
                "Title": title.encode('utf-8'),
                "Tags": (tags or "").encode('utf-8'),
                "Priority": priority,
                "Markdown": "true"
            }
            
            if extra_headers:
                headers.update({k: v.encode('utf-8') if isinstance(v, str) else v 
                             for k, v in extra_headers.items()})
            
            response = requests.post(
                f"{self.ntfy_base_url}/{topic}",
                headers=headers,
                data=message.encode('utf-8')
            )
            
            logger.info(f"ntfy Response Status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"ntfy Error Response: {response.text}")
                
            return response.status_code
        except Exception as e:
            logger.error(f"Fehler beim Senden der ntfy Nachricht: {str(e)}")
            logger.error(traceback.format_exc())
            return None

class GitHubMonitor:
    """Überwacht GitHub Repositories auf neue Releases"""

    def __init__(self, config, notification_service, base_url=None):
        self.config = config['github']
        self.notification_service = notification_service
        self.github_token = self.config['token']
        self.repos = self.config['repos']
        self.ntfy_topic = self.config['ntfy_topic']
        self.base_url = base_url or config.get('general', {}).get('base_url', '')

    async def check_repo(self, session, repo):
        """Prüft ein einzelnes Repository auf neue Releases"""
        try:
            logger.info(f"Prüfe Repository: {repo}")

            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': f'token {self.github_token}'
            }

            async with session.get(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers=headers
            ) as response:
                if response.status == 404:
                    logger.warning(f"Repository nicht gefunden: {repo}")
                    return None
                elif response.status != 200:
                    logger.error(f"GitHub API Error für {repo}: {await response.text()}")
                    return None

                release = await response.json()
                published_at = release['published_at']
                tag_name = release['tag_name']
                logger.info(f"Letztes Release für {repo}: {tag_name} vom {published_at}")

                # Release-Daten für API speichern
                release_data = {
                    'tag_name': tag_name,
                    'name': release.get('name', tag_name),
                    'body': release.get('body', ''),
                    'published_at': published_at,
                    'html_url': release['html_url'],
                    'author': release.get('author', {}).get('login', 'unknown'),
                    'author_avatar': release.get('author', {}).get('avatar_url', ''),
                    'assets': [
                        {
                            'name': asset['name'],
                            'size': asset['size'],
                            'download_url': asset['browser_download_url'],
                            'download_count': asset['download_count']
                        }
                        for asset in release.get('assets', [])
                    ]
                }
                DataManager.save_release(repo, release_data)

                # Prüfen, ob das Release neu ist
                last_checks = DataManager.load_last_checks()
                last_check = last_checks['github'].get(repo)
                logger.info(f"Letzter Check für {repo}: {last_check}")

                # Immer den Zeitstempel aktualisieren
                last_checks['github'][repo] = published_at
                DataManager.save_last_checks(last_checks)

                if published_at != last_check:
                    logger.info(f"Neues Release gefunden für {repo}: {tag_name}")

                    # Link zur eigenen Release-Seite
                    repo_slug = repo.replace('/', '-')
                    release_url = f"{self.base_url}/releases/{repo_slug}" if self.base_url else release['html_url']

                    # Kurze Beschreibung für Push
                    body_preview = release.get('body', '')[:200]
                    if len(release.get('body', '')) > 200:
                        body_preview += '...'

                    message = f"""**{tag_name}** veröffentlicht!

{body_preview}

[Details ansehen]({release_url})"""

                    status_code = self.notification_service.send_ntfy(
                        self.ntfy_topic,
                        f"Neues Release: {repo}",
                        message,
                        "github,release",
                        extra_headers={
                            "Click": release_url,
                            "Icon": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                        }
                    )
                    logger.info(f"GitHub Release Benachrichtigung gesendet für {repo}, Status: {status_code}")
                    return True
                else:
                    logger.info(f"Kein neues Release für {repo}")
                    return False

        except Exception as e:
            logger.error(f"Fehler bei GitHub-Check für {repo}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def check(self):
        """Prüft alle konfigurierten Repositories auf neue Releases"""
        logger.info("Starte GitHub Release Check")
        
        # Parallele Anfragen für alle Repositories
        async with aiohttp.ClientSession() as session:
            tasks = [self.check_repo(session, repo) for repo in self.repos]
            results = await asyncio.gather(*tasks)
        
        logger.info("GitHub-Check abgeschlossen")

class MonitoringService:
    """Hauptklasse des Monitoring-Services"""
    
    def __init__(self):
        self.config = ConfigManager.load_config()
        
        if not self.config:
            logger.critical("Keine Konfiguration gefunden, beende")
            return
        
        self.notification_service = NotificationService(self.config)
        self.github_monitor = GitHubMonitor(self.config, self.notification_service)

        self.check_interval = self.config['general']['check_interval']
    
    async def run_checks(self):
        """Führt alle Checks aus"""
        try:
            await self.github_monitor.check()
        except Exception as e:
            logger.error(f"Fehler bei der Ausführung der Checks: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def start(self):
        """Startet den Monitoring-Service"""
        try:
            logger.info("Monitoring Service gestartet")
            logger.info(f"Konfiguration:")
            logger.info(f"  GITHUB_REPOS: {self.config['github']['repos']}")
            logger.info(f"  CHECK_INTERVAL: {self.check_interval}")
            
            while True:
                try:
                    await self.run_checks()
                    logger.info(f"Warte {self.check_interval} Sekunden...")
                    await asyncio.sleep(self.check_interval)
                except Exception as e:
                    logger.error(f"Fehler im Hauptloop: {str(e)}")
                    logger.error(traceback.format_exc())
                    await asyncio.sleep(60)
                    
        except Exception as e:
            logger.critical(f"Kritischer Fehler: {str(e)}")
            logger.critical(traceback.format_exc())

# Diese Funktionen sind für die Integration mit der Web-UI
def check_github():
    """Führt einen GitHub-Check durch (wird von der Web-UI aufgerufen)"""
    logger.info("Manueller GitHub-Check gestartet")
    config = ConfigManager.load_config()
    notification_service = NotificationService(config)
    github_monitor = GitHubMonitor(config, notification_service)
    
    asyncio.run(github_monitor.check())
    logger.info("Manueller GitHub-Check abgeschlossen")

def load_last_checks():
    """Lädt die letzten Checks (wird von der Web-UI aufgerufen)"""
    return DataManager.load_last_checks()

def load_releases():
    """Lädt alle Release-Daten (wird von der Web-UI/API aufgerufen)"""
    return DataManager.load_releases()

def get_sorted_repos():
    """Gibt die nach Zeitstempel sortierten Repositories zurück"""
    config = ConfigManager.load_config()
    if not config or 'github' not in config or not config['github']['repos']:
        return []
        
    repos = config['github']['repos']
    last_checks = DataManager.load_last_checks()
    
    # Sortieren der Repos nach Zeitstempel (neueste zuerst)
    def get_timestamp(repo):
        timestamp = last_checks.get('github', {}).get(repo, "")
        return timestamp if timestamp else "0000-00-00T00:00:00Z"
    
    sorted_repos = sorted(repos, key=get_timestamp, reverse=True)
    return sorted_repos

def main():
    """Hauptfunktion zum Starten des Monitoring-Services"""
    service = MonitoringService()
    asyncio.run(service.start())

if __name__ == "__main__":
    main()