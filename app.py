from flask import Flask, request, redirect, session, render_template, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'messenger.db'

# Функция для создания базы данных и таблиц (если не существует)
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Таблица сообщений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat TEXT NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL
        )
        ''')

        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        ''')

        conn.commit()

# Вызываем функцию инициализации базы данных
init_db()

@app.before_request
def auto_login():
    if 'username' not in session and request.endpoint not in ['login', 'register', 'static']:
        return redirect(url_for('login'))  # Редирект на страницу логина, если пользователя нет в сессии


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

    if request.method == 'POST':
        msg = request.form['message']
        if msg.strip():  # Убедимся, что сообщение не пустое
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("INSERT INTO messages (chat, username, message) VALUES (?, ?, ?)",
                             (chat_name, session['username'], msg))
                conn.commit()
                print(f"Message from {session['username']} inserted: {msg}")  # Дебаг: проверка сообщения

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute("SELECT username, message FROM messages WHERE chat=? ORDER BY id ASC", (chat_name,))
        messages = cursor.fetchall()
        print(f"Messages for {chat_name}: {messages}")  # Дебаг: проверка вывода сообщений

    return render_template('chat_room.html', chat_name=chat_name, messages=messages)


@app.route('/logout')
def logout():
    session.pop('chat', None)
    return redirect(url_for('lobby'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)
