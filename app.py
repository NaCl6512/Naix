from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Подключение к MySQL
db = mysql.connector.connect(
    host="sql7.freesqldatabase.com",
    user="sql7776627",
    password="CA4yivwFEt",  # замени на свой пароль
    database="sql7776627"
)
cursor = db.cursor(dictionary=True)

# Функция инициализации БД
def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password VARCHAR(100)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            password VARCHAR(100)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat_id INT,
            user_id INT,
            text TEXT,
            timestamp DATETIME,
            FOREIGN KEY (chat_id) REFERENCES chat_rooms(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("SELECT COUNT(*) AS count FROM chat_rooms")
    count = cursor.fetchone()['count']
    if count == 0:
        cursor.execute("INSERT INTO chat_rooms (name, password) VALUES (%s, %s)", ("школа", "7z"))
        cursor.execute("INSERT INTO chat_rooms (name, password) VALUES (%s, %s)", ("домик", "1234"))
        cursor.execute("INSERT INTO chat_rooms (name, password) VALUES (%s, %s)", ("developer", "code"))
    db.commit()

# Вызов инициализации
init_db()

@app.route('/')
def index():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        db.commit()
        session['user_id'] = cursor.lastrowid
        session['username'] = username
        return redirect('/lobby')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/lobby')
    return render_template('login.html')

@app.route('/lobby')
def lobby():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('lobby.html')

@app.route('/chat/<chat_name>', methods=['GET', 'POST'])
def chat_password(chat_name):
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        password = request.form['password']
        cursor.execute("SELECT * FROM chat_rooms WHERE LOWER(name) = %s", (chat_name.lower(),))
        room = cursor.fetchone()
        if room and room['password'] == password:
            session['chat_id'] = room['id']
            session['chat_name'] = room['name']
            return redirect('/chatroom')
        else:
            return render_template('password_prompt.html', chat_name=chat_name, error="Неверный пароль")
    
    return render_template('password_prompt.html', chat_name=chat_name)

@app.route('/chatroom', methods=['GET', 'POST'])
def chatroom():
    if 'user_id' not in session or 'chat_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        message = request.form['message']
        cursor.execute("INSERT INTO messages (chat_id, user_id, text, timestamp) VALUES (%s, %s, %s, %s)", (
            session['chat_id'], session['user_id'], message, datetime.now()))
        db.commit()

    cursor.execute("""
        SELECT m.*, u.username FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE chat_id = %s
        ORDER BY timestamp ASC
    """, (session['chat_id'],))
    messages = cursor.fetchall()
    return render_template('chat.html', messages=messages, username=session['username'], chat_name=session['chat_name'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
