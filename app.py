from flask import Flask, request, redirect, session, render_template, url_for
import sqlite3
import os
import threading
import time
import datetime
import paramiko

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'messenger.db'

# === Настройки SFTP ===
SFTP_HOST = 'sftp.fhgdps.com'
SFTP_PORT = 22
SFTP_USERNAME = 'gdps_naclegdps'
SFTP_PASSWORD = 'vbwaf6p1t6g76hblcms4aq'
SFTP_BACKUP_DIR = '/public_html/naix_db'

# === Бэкап-менеджер ===
def backup_loop():
    time.sleep(120)  # ждать 2 минуты перед первым бэкапом
    while True:
        try:
            if not os.path.exists(DATABASE):
                restore_latest_backup()
            else:
                backup_database()
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(600)  # каждые 10 минут

def backup_database():
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_filename = f"messenger_{timestamp}.db"

    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)

    sftp.chdir(SFTP_BACKUP_DIR)
    files = sorted(sftp.listdir(), key=lambda x: sftp.stat(x).st_mtime)

    if len(files) >= 6:
        sftp.remove(files[0])

    sftp.put(DATABASE, f"{SFTP_BACKUP_DIR}/{backup_filename}")
    print(f"[BACKUP] Uploaded {backup_filename} to SFTP")

    sftp.close()
    transport.close()

def restore_latest_backup():
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)

    sftp.chdir(SFTP_BACKUP_DIR)
    files = sorted(sftp.listdir(), key=lambda x: sftp.stat(x).st_mtime, reverse=True)

    if files:
        sftp.get(f"{SFTP_BACKUP_DIR}/{files[0]}", DATABASE)
        print(f"[RESTORE] Restored {files[0]} as {DATABASE}")
    else:
        print("[RESTORE] No backup files found.")

    sftp.close()
    transport.close()

# === Инициализация базы данных ===
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat TEXT NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL
        )''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
        conn.commit()

init_db()

@app.before_request
def auto_login():
    if 'username' not in session and request.endpoint not in ['login', 'register', 'static']:
        return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def lobby():
    return render_template('lobby.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (name, password))
                conn.commit()
                session['username'] = name
                return redirect(url_for('lobby'))
            except sqlite3.IntegrityError:
                return "Имя пользователя уже занято"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (name, password))
            user = cursor.fetchone()
            if user:
                session['username'] = name
                return redirect(url_for('lobby'))
            else:
                return "Неверное имя или пароль"
    return render_template('login.html')

CHAT_PASSWORDS = {
    'школа': '7z',
    'домик': 'game',
    'developer': 'dev'
}

@app.route('/chat/<chat_name>', methods=['GET', 'POST'])
def chat(chat_name):
    if chat_name not in CHAT_PASSWORDS:
        return "Чат не существует"
    if request.method == 'POST':
        password = request.form.get('password')
        if password != CHAT_PASSWORDS[chat_name]:
            return "Неверный пароль"
        session['chat'] = chat_name
        return redirect(url_for('chat_room', chat_name=chat_name))
    return render_template('chat_password.html', chat_name=chat_name)

@app.route('/room/<chat_name>', methods=['GET', 'POST'])
def chat_room(chat_name):
    if 'username' not in session or session.get('chat') != chat_name:
        return redirect(url_for('lobby'))
    if request.method == 'POST':
        msg = request.form['message']
        if msg.strip():
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("INSERT INTO messages (chat, username, message) VALUES (?, ?, ?)",
                             (chat_name, session['username'], msg))
                conn.commit()
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute("SELECT username, message FROM messages WHERE chat=? ORDER BY id ASC", (chat_name,))
        messages = cursor.fetchall()
    return render_template('chat_room.html', chat_name=chat_name, messages=messages)

@app.route('/logout')
def logout():
    session.pop('chat', None)
    return redirect(url_for('lobby'))

# === Запуск бэкапа в отдельном потоке ===
threading.Thread(target=backup_loop, daemon=True).start()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)
