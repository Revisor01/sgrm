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
            return {'github': {}, 'plausible': {}}
    
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

class PlausibleMonitor:
    """Überwacht Plausible Analytics Statistiken"""
    
    def __init__(self, config, notification_service):
        self.config = config['plausible']
        self.notification_service = notification_service
        self.plausible_token = self.config['token']
        self.plausible_url = self.config['url']
        self.plausible_sites = self.config['sites']
        self.report_time = self.config['report_time']
        self.ntfy_topic = self.config['ntfy_topic']
        self.message_template = self.config.get('message_template', 
"""**Tagesstatistik für {site}**

📊 Besucher: {visitors}
👀 Seitenaufrufe: {pageviews}
↩️ Absprungrate: {bounce_rate}%
⏱️ Durchschn. Besuchsdauer: {visit_duration}s""")
    
    async def fetch_sites(self):
        """Holt die verfügbaren Seiten von Plausible"""
        try:
            logger.info("Hole verfügbare Plausible-Seiten")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.plausible_url}/api/v1/sites",
                    headers={"Authorization": f"Bearer {self.plausible_token}"}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Plausible API Error: {await response.text()}")
                        return []
                    
                    sites = await response.json()
                    logger.info(f"Erhaltene Sites: {len(sites)}")
                    return [site['domain'] for site in sites]
        except Exception as e:
            logger.error(f"Fehler beim Holen der Plausible-Seiten: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    async def check_site_stats(self, session, site):
        """Holt Statistiken für eine einzelne Website"""
        try:
            logger.info(f"Hole Statistiken für {site}")
            async with session.get(
                f"{self.plausible_url}/api/v1/stats/aggregate",
                headers={"Authorization": f"Bearer {self.plausible_token}"},
                params={
                    "site_id": site,
                    "period": "day",
                    "metrics": "visitors,pageviews,bounce_rate,visit_duration"
                }
            ) as response:
                if response.status != 200:
                    logger.error(f"Plausible API Error für {site}: {await response.text()}")
                    return None
                
                stats = await response.json()
                logger.info(f"Erhaltene Stats für {site}")
                
                # Verwende die Nachrichtenvorlage mit Variablenersetzung
                visitors = stats['results']['visitors']['value']
                pageviews = stats['results']['pageviews']['value']
                bounce_rate = stats['results']['bounce_rate']['value']
                visit_duration = int(stats['results']['visit_duration']['value'])
                
                message = self.message_template.format(
                    site=site,
                    visitors=visitors,
                    pageviews=pageviews,
                    bounce_rate=bounce_rate,
                    visit_duration=visit_duration
                )
                
                status_code = self.notification_service.send_ntfy(
                    self.ntfy_topic,
                    f"📈 Tagesstatistik: {site}",
                    message,
                    "stats,website"
                )
                logger.info(f"Plausible Benachrichtigung gesendet für {site}, Status: {status_code}")
                
                # Speichere die geprüften Seiten
                last_checks = DataManager.load_last_checks()
                if 'checked_sites' not in last_checks.get('plausible', {}):
                    last_checks['plausible']['checked_sites'] = {}
                
                last_checks['plausible']['checked_sites'][site] = datetime.now(
                    pytz.timezone('Europe/Berlin')).strftime('%Y-%m-%d %H:%M:%S')
                DataManager.save_last_checks(last_checks)
                
                return True
        except Exception as e:
            logger.error(f"Fehler bei Plausible-Check für {site}: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    async def check(self, manual=False):
        """Prüft ob ein Tagesbericht fällig ist und sendet diesen ggf."""
        logger.info("Starte Plausible Check")
        
        # Aktuelle Zeit in der korrekten Zeitzone ermitteln
        now = datetime.now(pytz.timezone('Europe/Berlin'))
        current_time = now.strftime('%H:%M')
        logger.info(f"Aktuelle Zeit: {current_time}")
        
        try:
            report_hour = int(self.report_time.split(":")[0])
            report_minute = int(self.report_time.split(":")[1])
            logger.info(f"Report Zeit konfiguriert für {report_hour}:{report_minute}")
        except Exception as e:
            logger.error(f"Fehler beim Parsen der Report-Zeit: {str(e)}")
            return
        
        # Prüfen, ob heute bereits ein Report gesendet wurde
        last_checks = DataManager.load_last_checks()
        today = now.strftime('%Y-%m-%d')
        last_report = last_checks.get('plausible', {}).get('last_report')
        
        logger.info(f"Heute: {today}, Letzter Report: {last_report}")
        logger.info(f"Aktuelle Stunde: {now.hour}, Minute: {now.minute}")
        
        # Report senden, wenn die Zeit erreicht ist, heute noch kein Report gesendet wurde
        # oder ein manueller Check angefordert wurde
        if (manual or (now.hour == report_hour and now.minute >= report_minute and last_report != today)):
            logger.info("Starte Plausible Report...")
            
            # Parallele Anfragen für alle Sites
            async with aiohttp.ClientSession() as session:
                tasks = [self.check_site_stats(session, site) for site in self.plausible_sites]
                results = await asyncio.gather(*tasks)
            
            # Speichern des letzten Report-Datums und Zeitstempels
            if 'plausible' not in last_checks:
                last_checks['plausible'] = {}
            
            if not manual and last_report != today:
                last_checks['plausible']['last_report'] = today
            
            # Speichere Zeitstempel und ob es ein manueller Check war
            last_checks['plausible']['last_check'] = now.strftime('%Y-%m-%d %H:%M:%S')
            last_checks['plausible']['manual'] = manual
            
            DataManager.save_last_checks(last_checks)
            logger.info(f"Plausible Report abgeschlossen und Zeitstempel {now.strftime('%Y-%m-%d %H:%M:%S')} gespeichert")
            return True
        else:
            logger.info(
                f"Kein Report nötig. "
                f"Bedingungen: Stunde={now.hour == report_hour}, "
                f"Minute>={now.minute >= report_minute}, "
                f"Nicht gesendet heute={last_report != today}, "
                f"Manuell={manual}"
            )
            return False

class GitHubMonitor:
    """Überwacht GitHub Repositories auf neue Releases"""
    
    def __init__(self, config, notification_service):
        self.config = config['github']
        self.notification_service = notification_service
        self.github_token = self.config['token']
        self.repos = self.config['repos']
        self.ntfy_topic = self.config['ntfy_topic']
    
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
                logger.info(f"Letztes Release für {repo}: {release['tag_name']} vom {published_at}")
                
                # Prüfen, ob das Release neu ist
                last_checks = DataManager.load_last_checks()
                last_check = last_checks['github'].get(repo)
                logger.info(f"Letzter Check für {repo}: {last_check}")
                
                # Immer den Zeitstempel aktualisieren, auch wenn keine Benachrichtigung gesendet wird
                last_checks['github'][repo] = published_at
                DataManager.save_last_checks(last_checks)
                
                if published_at != last_check:
                    logger.info(f"Neues Release gefunden für {repo}: {release['tag_name']}")
                    
                    # Benachrichtigung senden
                    message = f"""**{release['tag_name']}** veröffentlicht!

{release.get('body', 'Keine Beschreibung verfügbar')}

[Download & Changelog]({release['html_url']})"""
                    
                    status_code = self.notification_service.send_ntfy(
                        self.ntfy_topic,
                        f"🚀 Neues Release: {repo}",
                        message,
                        "github,release",
                        extra_headers={
                            "Click": release['html_url'],
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
        self.plausible_monitor = PlausibleMonitor(self.config, self.notification_service)
        
        self.check_interval = self.config['general']['check_interval']
    
    async def run_checks(self):
        """Führt alle Checks aus"""
        try:
            await self.github_monitor.check()
            await self.plausible_monitor.check()
        except Exception as e:
            logger.error(f"Fehler bei der Ausführung der Checks: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def start(self):
        """Startet den Monitoring-Service"""
        try:
            logger.info("Monitoring Service gestartet")
            logger.info(f"Konfiguration:")
            logger.info(f"  PLAUSIBLE_SITES: {self.config['plausible']['sites']}")
            logger.info(f"  PLAUSIBLE_REPORT_TIME: {self.config['plausible']['report_time']}")
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

def check_plausible():
    """Führt einen Plausible-Check durch (wird von der Web-UI aufgerufen)"""
    logger.info("Manueller Plausible-Check gestartet")
    config = ConfigManager.load_config()
    notification_service = NotificationService(config)
    plausible_monitor = PlausibleMonitor(config, notification_service)
    
    asyncio.run(plausible_monitor.check(manual=True))
    logger.info("Manueller Plausible-Check abgeschlossen")

def load_last_checks():
    """Lädt die letzten Checks (wird von der Web-UI aufgerufen)"""
    return DataManager.load_last_checks()

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

def get_plausible_sites():
    """Gibt die verfügbaren Plausible-Seiten zurück"""
    config = ConfigManager.load_config()
    notification_service = NotificationService(config)
    plausible_monitor = PlausibleMonitor(config, notification_service)
    
    return asyncio.run(plausible_monitor.fetch_sites())

def main():
    """Hauptfunktion zum Starten des Monitoring-Services"""
    service = MonitoringService()
    asyncio.run(service.start())

if __name__ == "__main__":
    main()