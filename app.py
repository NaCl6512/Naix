from flask import Flask, request, redirect, session, render_template, url_for
from flask_socketio import SocketIO, emit, join_room
import pymysql
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

DB_CONFIG = {
    'host': 'sql7.freesqldatabase.com',
    'user': 'sql7776627',
    'password': 'CA4yivwFEt',
    'database': 'sql7776627',
    'port': 3306,
    'cursorclass': pymysql.cursors.DictCursor,
    'charset': 'utf8mb4'
}

def init_db():
    connection = pymysql.connect(**DB_CONFIG)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(191) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
            ''')
            cursor.execute("SHOW COLUMNS FROM users LIKE 'is_banned'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN is_banned TINYINT(1) NOT NULL DEFAULT 0")
            cursor.execute("SHOW COLUMNS FROM users LIKE 'ban_reason'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT DEFAULT NULL")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    chat VARCHAR(191) NOT NULL,
                    username VARCHAR(191) NOT NULL,
                    message TEXT NOT NULL
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
            ''')
        connection.commit()

init_db()

@app.before_request
def auto_login():
    if 'username' not in session and request.endpoint not in ['login', 'register', 'static']:
        return redirect(url_for('login'))
    if 'username' in session:
        connection = pymysql.connect(**DB_CONFIG)
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT is_banned, ban_reason FROM users WHERE username = %s", (session['username'],))
                user = cursor.fetchone()
                if user and user['is_banned']:
                    reason = user['ban_reason'] or 'не указана'
                    session.clear()
                    return f"Ваш аккаунт заблокирован. Причина: {reason}"

@app.route('/', methods=['GET'])
def lobby():
    return render_template('lobby.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        try:
            connection = pymysql.connect(**DB_CONFIG)
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (name, password))
                connection.commit()
                session['username'] = name
                return redirect(url_for('lobby'))
        except pymysql.err.IntegrityError:
            return "Имя пользователя уже занято"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        connection = pymysql.connect(**DB_CONFIG)
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (name, password))
                user = cursor.fetchone()
                if user:
                    if user.get('is_banned'):
                        return f"Аккаунт заблокирован. Причина: {user.get('ban_reason') or 'не указана'}"
                    session['username'] = name
                    return redirect(url_for('lobby'))
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

@app.route('/room/<chat_name>', methods=['GET'])
def chat_room(chat_name):
    if 'username' not in session or session.get('chat') != chat_name:
        return redirect(url_for('lobby'))

    connection = pymysql.connect(**DB_CONFIG)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT username, message FROM messages WHERE chat=%s ORDER BY id ASC", (chat_name,))
            messages = [(row['username'], row['message']) for row in cursor.fetchall()]

    return render_template('chat_room.html', chat_name=chat_name, messages=messages)

@socketio.on('join')
def on_join(data):
    join_room(data['room'])

@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username')
    msg = data['message']
    room = data['room']

    connection = pymysql.connect(**DB_CONFIG)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO messages (chat, username, message) VALUES (%s, %s, %s)",
                           (room, username, msg))
        connection.commit()

    emit('receive_message', {'username': username, 'message': msg}, to=room)

@app.route('/logout')
def logout():
    session.pop('chat', None)
    return redirect(url_for('lobby'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
