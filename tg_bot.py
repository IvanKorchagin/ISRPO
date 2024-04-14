import telebot
import sqlite3
from telebot import types
import config

# Инициализация бота
bot = telebot.TeleBot(config.bot_token)

# Подключение к базе данных
conn = sqlite3.connect('crypto_wallet.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    balance REAL NOT NULL DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    from_user_id INTEGER,
    to_address TEXT,
    amount REAL,
    FOREIGN KEY (from_user_id) REFERENCES users (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
''')

conn.commit()

# Функция для получения баланса пользователя
def get_balance(user_id):
    cursor.execute('SELECT balance FROM users WHERE id=?', (user_id,))
    balance = cursor.fetchone()
    return balance[0] if balance else 0

# Функция для получения истории транзакций пользователя
def get_transactions(user_id):
    cursor.execute('SELECT * FROM transactions WHERE from_user_id=?', (user_id,))
    transactions = cursor.fetchall()
    return transactions

# Функция для создания нового пользователя
def create_user(user_id):
    cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
    conn.commit()

# Функция для выполнения транзакции
def make_transaction(from_user_id, to_address, amount):
    # Проверка наличия средств на балансе пользователя
    if get_balance(from_user_id) < amount:
        return False

    # Вычитаем сумму из баланса отправителя
    cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, from_user_id))
    # Прибавляем сумму к балансу получателя (предполагается, что адрес кошелька уже проверен)
    # В этом примере предполагается, что всегда есть получатель, поэтому баланс не изменяется
    # cursor.execute('UPDATE users SET balance = balance + ? WHERE address = ?', (amount, to_address))

    # Записываем транзакцию в историю
    cursor.execute('INSERT INTO transactions (from_user_id, to_address, amount) VALUES (?, ?, ?)', (from_user_id, to_address, amount))
    conn.commit()
    return True

# Функция для проверки, является ли пользователь администратором
def is_admin(user_id):
    cursor.execute('SELECT * FROM admins WHERE user_id=?', (user_id,))
    return cursor.fetchone() is not None

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    create_user(user_id)  # Создаем пользователя, если его еще нет
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Кошелек')
    btn2 = types.KeyboardButton('Перевести')
    btn3 = types.KeyboardButton('История')
    markup.add(btn1, btn2, btn3)
    text = f'Привет, {message.from_user.full_name}, я твой бот-криптокошелек.'
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработчик кнопки "Кошелек"
@bot.message_handler(func=lambda message: message.text == 'Кошелек')
def wallet(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Меню')
    markup.add(btn1)
    text = f'Ваш баланс: {balance} BTC'
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработчик кнопки "Перевести"
@bot.message_handler(func=lambda message: message.text == 'Перевести')
def transfer(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Меню')
    markup.add(btn1)
    text = 'Введите адрес кошелька, сумму и секретный пароль через пробел:\n' \
           'Например: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa 0.1 password'
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработчик кнопки "История"
@bot.message_handler(func=lambda message: message.text == 'История')
def history(message):
    user_id = message.from_user.id
    transactions = get_transactions(user_id)
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Меню')
    markup.add(btn1)
    text = 'Ваши транзакции:\n' + '\n'.join([f'{t[2]} -> {t[3]}: {t[4]}' for t in transactions])
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработчик кнопки "Меню"
@bot.message_handler(func=lambda message: message.text == 'Меню')
def menu(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Кошелек')
    btn2 = types.KeyboardButton('Перевести')
    btn3 = types.KeyboardButton('История')
    if is_admin(user_id):
        btn4 = types.KeyboardButton('Просмотр пользователя')
        btn5 = types.KeyboardButton('Удаление пользователя')
        markup.add(btn1, btn2, btn3, btn4, btn5)
    else:
        markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "Главное меню", reply_markup=markup)

# Обработчик для админ-панели
@bot.message_handler(func=lambda message: message.text == "Админка")
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('Общий баланс')
    btn2 = types.KeyboardButton('Все юзеры')
    btn3 = types.KeyboardButton('Данные по юзеру')
    btn4 = types.KeyboardButton('Удалить юзера')
    markup.add(btn1, btn2, btn3, btn4)
    text = f'Админ-панель'
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Функция для получения общего баланса
def get_total_balance():
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()
    return total_balance[0] if total_balance else 0

# Функция для получения списка всех пользователей
def get_all_users():
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    return [user[0] for user in users]

# Функция для получения данных по пользователю
def get_user_data(user_id):
    cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
    user_data = cursor.fetchone()
    return user_data

# Функция для удаления пользователя
def delete_user(user_id):
    cursor.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()

# Обработчики для кнопок админ-панели
@bot.message_handler(func=lambda message: message.from_user.id == config.tg_admin_id and message.text == "Общий баланс")
def total_balance(message):
    total_balance = get_total_balance()
    bot.send_message(message.chat.id, f'Общий баланс: {total_balance} BTC')

@bot.message_handler(func=lambda message: message.from_user.id == config.tg_admin_id and message.text == "Все юзеры")
def all_users(message):
    users = get_all_users()
    bot.send_message(message.chat.id, 'Список всех пользователей:\n' + '\n'.join(map(str, users)))

@bot.message_handler(func=lambda message: message.from_user.id == config.tg_admin_id and message.text == "Данные по юзеру")
def user_data(message):
    bot.send_message(message.chat.id, 'Введите ID пользователя:')
    bot.register_next_step_handler(message, process_user_data_request)

@bot.message_handler(func=lambda message: message.from_user.id == config.tg_admin_id and message.text == "Удаление пользователя")
def delete_user_prompt(message):
    bot.send_message(message.chat.id, 'Введите ID пользователя для удаления:')
    bot.register_next_step_handler(message, process_user_deletion_request)

# Обработчик для обработки запроса данных по пользователю
def process_user_data_request(message):
    user_id = message.text
    if not user_id.isdigit():
        bot.send_message(message.chat.id, 'Некорректный ID пользователя.')
        return
    user_data = get_user_data(int(user_id))
    if user_data:
        bot.send_message(message.chat.id, f'Данные пользователя {user_id}:\nID: {user_data[0]}\nБаланс: {user_data[1]} BTC')
    else:
        bot.send_message(message.chat.id, 'Пользователь не найден.')

# Обработчик для обработки запроса на удаление пользователя
def process_user_deletion_request(message):
    user_id = message.text
    if not user_id.isdigit():
        bot.send_message(message.chat.id, 'Некорректный ID пользователя.')
        return
    delete_user(int(user_id))
    bot.send_message(message.chat.id, f'Пользователь {user_id} удален.')

# Запуск бота
bot.polling(none_stop=True)