#!/usr/bin/env python3
import os
import json
import yaml
from datetime import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import secrets

# Import der bestehenden Monitoring-Funktionen
from monitoring import check_github, load_last_checks, get_sorted_repos

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
        "check_interval": 3600
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

        # GitHub-Konfiguration
        config['github']['token'] = request.form.get('github_token', '')
        config['github']['repos'] = [r.strip() for r in request.form.get('github_repos', '').split(',') if r.strip()]
        config['github']['ntfy_topic'] = request.form.get('github_ntfy_topic', 'github')

        # Ntfy-Konfiguration
        config['ntfy']['token'] = request.form.get('ntfy_token', '')
        config['ntfy']['base_url'] = request.form.get('ntfy_base_url', 'https://ntfy.sh')

        # Allgemeine Konfiguration
        try:
            config['general']['check_interval'] = int(request.form.get('check_interval', 3600))
        except ValueError:
            config['general']['check_interval'] = 3600

        # Konfiguration speichern
        save_config(config)
        flash('Konfiguration erfolgreich gespeichert!', 'success')
        return redirect(url_for('index'))

    config = load_config()
    return render_template('config.html', config=config)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)