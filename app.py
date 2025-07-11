import logging
from flask import Flask, request, render_template, jsonify
import sqlite3
import os
import re

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

app = Flask(__name__, template_folder='../front/templates', static_folder='../front/static')

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_file(file):
    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    max_size = 2 * 1024 * 1024
    if file.mimetype not in allowed_types:
        return False, 'Недопустимый тип файла. Разрешены только JPEG, PNG, GIF.'
    if file.content_length > max_size:
        return False, 'Файл слишком большой. Максимальный размер: 2MB.'
    return True, ''

def init_db():
    if not os.path.exists('database.db'):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            about TEXT NOT NULL,
            avatar BLOB
        )''')
        conn.commit()
        conn.close()
        logging.info("База данных успешно инициализирована")

init_db()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        about = request.form.get('about')
        avatar = request.files.get('avatar')

        print(f"Login: {login}, Password: {password}, Confirm: {confirm_password}")
        logging.info(f"Попытка регистрации: login={login}, full_name={full_name}, email={email}, phone={phone}, about={about}")

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE login = ?', (login,))
        if c.fetchone():
            conn.close()
            logging.warning(f"Ошибка регистрации: логин {login} уже существует")
            return "Этот логин уже занят!"

        if not is_valid_email(email):
            conn.close()
            logging.warning(f"Ошибка регистрации: неверный формат email={email}")
            return "Неверный формат email!"

        if password != confirm_password:
            conn.close()
            logging.warning(f"Ошибка регистрации: пароли не совпадают для login={login}")
            return "Пароли не совпадают!"

        if avatar:
            is_valid, error_message = is_valid_file(avatar)
            if not is_valid:
                conn.close()
                logging.warning(f"Ошибка регистрации: {error_message} для login={login}")
                return error_message
            avatar_data = avatar.read()
        else:
            conn.close()
            logging.warning(f"Ошибка регистрации: файл аватара не загружен для login={login}")
            return "Файл аватара обязателен!"

        try:
            c.execute('''INSERT INTO users (login, password, full_name, email, phone, about, avatar)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (login, password, full_name, email, phone, about, avatar_data))
            conn.commit()
            conn.close()
            logging.info(f"Пользователь успешно зарегистрирован: login={login}")
        except Exception as e:
            conn.close()
            logging.error(f"Ошибка при сохранении пользователя login={login}: {str(e)}")
            return f"Ошибка при сохранении: {str(e)}"

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, login, full_name, email, phone, about FROM users')
    users = c.fetchall()
    conn.close()

    return render_template('index.html', users=users)

@app.route('/api/users', methods=['POST'])
def api_users():
    data = request.form
    login = data.get('login')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    full_name = data.get('full_name')
    email = data.get('email')
    phone = data.get('phone')
    about = data.get('about')
    avatar = request.files.get('avatar')

    logging.info(f"API: Попытка регистрации: login={login}, full_name={full_name}, email={email}, phone={phone}, about={about}")

    if not all([login, password, confirm_password, full_name, email, phone, about]):
        logging.warning(f"API: Ошибка регистрации: не все обязательные поля заполнены для login={login}")
        return jsonify({
            'status': 'error',
            'message': 'Все обязательные поля должны быть заполнены'
        }), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE login = ?', (login,))
    if c.fetchone():
        conn.close()
        logging.warning(f"API: Ошибка регистрации: логин {login} уже существует")
        return jsonify({
            'status': 'error',
            'message': 'Этот логин уже занят'
        }), 400

    if not is_valid_email(email):
        conn.close()
        logging.warning(f"API: Ошибка регистрации: неверный формат email={email}")
        return jsonify({
            'status': 'error',
            'message': 'Неверный формат email'
        }), 400

    if password != confirm_password:
        conn.close()
        logging.warning(f"API: Ошибка регистрации: пароли не совпадают для login={login}")
        return jsonify({
            'status': 'error',
            'message': 'Пароли не совпадают'
        }), 400

    if avatar:
        is_valid, error_message = is_valid_file(avatar)
        if not is_valid:
            conn.close()
            logging.warning(f"API: Ошибка регистрации: {error_message} для login={login}")
            return jsonify({
                'status': 'error',
                'message': error_message
            }), 400
        avatar_data = avatar.read()
    else:
        conn.close()
        logging.warning(f"API: Ошибка регистрации: файл аватара не загружен для login={login}")
        return jsonify({
            'status': 'error',
            'message': 'Файл аватара обязателен'
        }), 400

    try:
        c.execute('''INSERT INTO users (login, password, full_name, email, phone, about, avatar)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (login, password, full_name, email, phone, about, avatar_data))
        conn.commit()
        conn.close()
        logging.info(f"API: Пользователь успешно зарегистрирован: login={login}")
        return jsonify({
            'status': 'success',
            'message': 'Пользователь успешно зарегистрирован',
            'data': {
                'login': login,
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'about': about
            }
        }), 201
    except Exception as e:
        conn.close()
        logging.error(f"API: Ошибка при сохранении пользователя login={login}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Ошибка при сохранении: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)