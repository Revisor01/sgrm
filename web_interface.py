#!/usr/bin/env python3
import os
import json
import yaml
from datetime import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import secrets

# Import der bestehenden Monitoring-Funktionen
from monitoring import check_github, load_last_checks, get_sorted_repos, load_releases
import markdown

# Konfigurationsdatei
CONFIG_FILE = "/app/config/config.yaml"
USERS_FILE = "/app/config/users.json"
DATA_DIR = "/app/data"

# Stellt sicher, dass die Verzeichnisse existieren
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Standardkonfiguration
DEFAULT_CONFIG = {
    "github": {
        "token": "",
        "repos": [],
        "ntfy_topic": "github"
    },
    "ntfy": {
        "token": "",
        "base_url": "https://ntfy.sh"
    },
    "general": {
        "check_interval": 3600,
        "base_url": ""
    }
}

# Flask App initialisieren
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Benutzermodell
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# Lade oder erstelle Konfiguration
def load_config():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        # Erstelle Standardkonfiguration, wenn keine existiert
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG

# Speichere Konfiguration
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)

# Lade oder erstelle Benutzer
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Erstelle Standard-Admin-Benutzer
        default_users = {
            "admin": {
                "password_hash": generate_password_hash("admin"),
                "id": "1"
            }
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(default_users, f)
        return default_users

# Speichere Benutzer
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

# Benutzer-Loader für Flask-Login
@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    for username, user_data in users.items():
        if user_data["id"] == user_id:
            return User(user_id, username, user_data["password_hash"])
    return None

# Routen
@app.route('/')
@login_required
def index():
    config = load_config()

    # Lade letzte Checks
    last_checks = load_last_checks()

    # Formatiere die Datumsangaben für die Anzeige
    for repo, published_at in last_checks.get('github', {}).items():
        if published_at and not repo.startswith('last_'):
            dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            last_checks['github'][repo] = dt.strftime('%d.%m.%Y %H:%M')

    # Sortierte Repositories
    sorted_repos = get_sorted_repos()

    return render_template(
        'index.html',
        config=config,
        last_checks=last_checks,
        sorted_repos=sorted_repos
    )

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    if request.method == 'POST':
        # Konfiguration aktualisieren
        config = load_config()

        # GitHub-Konfiguration (Repos werden separat verwaltet)
        config['github']['token'] = request.form.get('github_token', '')
        config['github']['ntfy_topic'] = request.form.get('github_ntfy_topic', 'github')

        # Ntfy-Konfiguration
        config['ntfy']['token'] = request.form.get('ntfy_token', '')
        config['ntfy']['base_url'] = request.form.get('ntfy_base_url', 'https://ntfy.sh')

        # Allgemeine Konfiguration
        try:
            config['general']['check_interval'] = int(request.form.get('check_interval', 3600))
        except ValueError:
            config['general']['check_interval'] = 3600
        config['general']['base_url'] = request.form.get('base_url', '').rstrip('/')

        # Konfiguration speichern
        save_config(config)
        flash('Konfiguration erfolgreich gespeichert!', 'success')
        return redirect(url_for('config'))

    config = load_config()
    return render_template('config.html', config=config)

@app.route('/config/repo/add', methods=['POST'])
@login_required
def add_repo():
    repo = request.form.get('repo', '').strip()
    if repo:
        # Validierung: muss owner/repo Format haben
        if '/' in repo and len(repo.split('/')) == 2:
            config = load_config()
            if repo not in config['github']['repos']:
                config['github']['repos'].append(repo)
                save_config(config)
                flash(f'Repository "{repo}" hinzugefügt.', 'success')
            else:
                flash(f'Repository "{repo}" ist bereits in der Liste.', 'danger')
        else:
            flash('Ungültiges Format. Bitte "owner/repo" verwenden.', 'danger')
    return redirect(url_for('config'))

@app.route('/config/repo/remove', methods=['POST'])
@login_required
def remove_repo():
    repo = request.form.get('repo', '').strip()
    if repo:
        config = load_config()
        if repo in config['github']['repos']:
            config['github']['repos'].remove(repo)
            save_config(config)
            flash(f'Repository "{repo}" entfernt.', 'success')
    return redirect(url_for('config'))

@app.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    if current_user.username != 'admin':
        flash('Nur Administratoren können Benutzer verwalten.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        users_data = load_users()
        
        if action == 'add':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Benutzername und Passwort sind erforderlich!', 'danger')
            elif username in users_data:
                flash('Benutzername existiert bereits!', 'danger')
            else:
                # Generiere neue ID
                user_id = str(max([int(u['id']) for u in users_data.values()]) + 1)
                users_data[username] = {
                    "id": user_id,
                    "password_hash": generate_password_hash(password)
                }
                save_users(users_data)
                flash(f'Benutzer {username} erfolgreich hinzugefügt!', 'success')
        
        elif action == 'delete':
            username = request.form.get('delete_username')
            if username == 'admin':
                flash('Der Admin-Benutzer kann nicht gelöscht werden!', 'danger')
            elif username in users_data:
                del users_data[username]
                save_users(users_data)
                flash(f'Benutzer {username} erfolgreich gelöscht!', 'success')
        
        elif action == 'change_password':
            username = request.form.get('password_username')
            password = request.form.get('new_password')
            
            if username in users_data and password:
                users_data[username]['password_hash'] = generate_password_hash(password)
                save_users(users_data)
                flash(f'Passwort für {username} erfolgreich geändert!', 'success')
        
        return redirect(url_for('users'))
    
    users_data = load_users()
    return render_template('users.html', users=users_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users_data = load_users()
        if username in users_data and check_password_hash(users_data[username]['password_hash'], password):
            user = User(users_data[username]['id'], username, users_data[username]['password_hash'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Falsche Anmeldedaten!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/run-check', methods=['POST'])
@login_required
def run_check():
    check_github()
    flash('GitHub-Check manuell ausgeführt!', 'success')
    return redirect(url_for('index'))

# ============================================
# Öffentliche API & Release-Seiten (kein Login)
# ============================================

def format_relative_time(iso_timestamp):
    """Formatiert einen ISO-Timestamp als relative Zeit"""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        now = datetime.now(pytz.UTC)
        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"vor {years} Jahr{'en' if years > 1 else ''}"
        elif diff.days > 30:
            months = diff.days // 30
            return f"vor {months} Monat{'en' if months > 1 else ''}"
        elif diff.days > 0:
            return f"vor {diff.days} Tag{'en' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"vor {hours} Stunde{'n' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"vor {minutes} Minute{'n' if minutes > 1 else ''}"
        else:
            return "gerade eben"
    except:
        return iso_timestamp

def render_markdown(text):
    """Rendert Markdown zu HTML"""
    if not text:
        return ''
    return markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])

# API-Endpunkte
@app.route('/api/releases')
def api_releases():
    """API: Alle Releases"""
    releases = load_releases()
    config = load_config()
    repos = config.get('github', {}).get('repos', [])

    result = []
    for repo in repos:
        if repo in releases:
            release_data = releases[repo].copy()
            release_data['repo'] = repo
            release_data['relative_time'] = format_relative_time(release_data.get('published_at', ''))
            result.append(release_data)

    # Sortieren nach published_at (neueste zuerst)
    result.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    return jsonify(result)

@app.route('/api/releases/<path:repo>')
def api_release_detail(repo):
    """API: Einzelnes Release"""
    # Konvertiere slug zurück zu repo-name
    repo_name = repo.replace('-', '/', 1)
    releases = load_releases()

    if repo_name in releases:
        release_data = releases[repo_name].copy()
        release_data['repo'] = repo_name
        release_data['relative_time'] = format_relative_time(release_data.get('published_at', ''))
        return jsonify(release_data)

    return jsonify({'error': 'Release not found'}), 404

# Öffentliche Web-Seiten
@app.route('/releases')
def releases_page():
    """Öffentliche Übersichtsseite aller Releases"""
    releases = load_releases()
    config = load_config()
    repos = config.get('github', {}).get('repos', [])

    releases_list = []
    for repo in repos:
        if repo in releases:
            release_data = releases[repo].copy()
            release_data['repo'] = repo
            release_data['repo_slug'] = repo.replace('/', '-')
            release_data['relative_time'] = format_relative_time(release_data.get('published_at', ''))
            # Markdown-Vorschau des Changelogs
            body = release_data.get('body', '')
            if body:
                # Erste 200 Zeichen als Markdown rendern
                preview = body[:200] + ('...' if len(body) > 200 else '')
                release_data['body_preview_html'] = render_markdown(preview)
            releases_list.append(release_data)

    # Sortieren nach published_at (neueste zuerst)
    releases_list.sort(key=lambda x: x.get('published_at', ''), reverse=True)

    return render_template('releases.html', releases=releases_list)

@app.route('/releases/<path:repo_slug>')
def release_detail_page(repo_slug):
    """Öffentliche Detailseite für ein Release"""
    # Konvertiere slug zurück zu repo-name
    repo_name = repo_slug.replace('-', '/', 1)
    releases = load_releases()

    if repo_name not in releases:
        return render_template('release_not_found.html', repo=repo_name), 404

    release_data = releases[repo_name].copy()
    release_data['repo'] = repo_name
    release_data['repo_slug'] = repo_slug
    release_data['relative_time'] = format_relative_time(release_data.get('published_at', ''))
    release_data['body_html'] = render_markdown(release_data.get('body', ''))

    # Formatiere Asset-Größen
    for asset in release_data.get('assets', []):
        size_bytes = asset.get('size', 0)
        if size_bytes > 1024 * 1024:
            asset['size_formatted'] = f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes > 1024:
            asset['size_formatted'] = f"{size_bytes / 1024:.1f} KB"
        else:
            asset['size_formatted'] = f"{size_bytes} B"

    return render_template('release_detail.html', release=release_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)