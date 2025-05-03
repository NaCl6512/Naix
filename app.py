from flask import Flask, request, redirect, session, render_template, url_for
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Параметры подключения к MySQL
DB_CONFIG = {
    'host': 'sql7.freesqldatabase.com',
    'user': 'sql7776627',
    'password': 'CA4yivwFEt',
    'database': 'sql7776627',
    'port': 3306
}

# Инициализация базы (создание таблиц, если их нет)
def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat VARCHAR(255) NOT NULL,
            username VARCHAR(255) NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

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
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (name, password))
            conn.commit()
            session['username'] = name
            return redirect(url_for('lobby'))
        except mysql.connector.IntegrityError:
            return "Имя пользователя уже занято"
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (name, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['username'] = name
            return redirect(url_for('lobby'))
        else:
            return "Неверное имя или пароль"
    return render_template('login.html')

# Пароли чатов
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

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    if request.method == 'POST':
        msg = request.form['message']
        if msg.strip():
            cursor.execute("INSERT INTO messages (chat, username, message) VALUES (%s, %s, %s)",
                           (chat_name, session['username'], msg))
            conn.commit()

    cursor.execute("SELECT username, message FROM messages WHERE chat=%s ORDER BY id ASC", (chat_name,))
    messages = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('chat_room.html', chat_name=chat_name, messages=messages)

@app.route('/logout')
def logout():
    session.pop('chat', None)
    session.pop('username', None)
    return redirect(url_for('lobby'))

if __name__ == '__main__':
    app.run(debug=True, port=8080)
