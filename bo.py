import telebot
from telebot import types
import sqlite3
from datetime import datetime
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
TOKEN = "8443195735:AAEJ-DA_4r-1GKezj2VwYiiQzoawXmh1q1E"

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Определение рангов
RANKS = [
    {"id": 1, "name": "Новенький", "min_exp": 0, "max_exp": 10, "icon": "👶"},
    {"id": 2, "name": "Следопыт", "min_exp": 10, "max_exp": 25, "icon": "🔍"},
    {"id": 3, "name": "Профессор", "min_exp": 25, "max_exp": 30, "icon": "🎓"},
    {"id": 4, "name": "Учёный", "min_exp": 30, "max_exp": 45, "icon": "🔬"},
    {"id": 5, "name": "Гадалка", "min_exp": 45, "max_exp": 50, "icon": "🔮"},
    {"id": 6, "name": "Повелитель", "min_exp": 50, "max_exp": 50, "icon": "👑"}
]

# Стикеры
STICKERS = {
    "welcome": "CAACAgIAAxkBAAIBMWchPb9y4Kk0V_1auF8K7-AJxqkAAAgjAAOw3n0S6E6F6OR8plc1BA",
    "questions": "CAACAgIAAxkBAAIBM2chPc9yGkHss5f8L6_4N1o4zXqPAAJCAAM7YCQUsYD_f2ZMr0c1BA",
    "profile": "CAACAgIAAxkBAAIBNWchPdLAyDKScNvqM-j6jEQFjKKLAAJMAAM7YCQUBhNa5Wp19iY1BA",
    "ranks": "CAACAgIAAxkBAAIBN2chPdfPlRbl2_TZk4QgyUlsJeyyAAJJAAM7YCQUIQ0sNv-3RfY1BA"
}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        experience INTEGER DEFAULT 0,
        rank_id INTEGER DEFAULT 1,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица вопросов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_answered BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица ответов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS answers (
        answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        user_id INTEGER,
        answer_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        likes INTEGER DEFAULT 0,
        FOREIGN KEY (question_id) REFERENCES questions (question_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица лайков
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS answer_likes (
        like_id INTEGER PRIMARY KEY AUTOINCREMENT,
        answer_id INTEGER,
        user_id INTEGER,
        FOREIGN KEY (answer_id) REFERENCES answers (answer_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        UNIQUE(answer_id, user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Функции для работы с БД
def get_or_create_user(user_id, username=None, full_name=None):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
        INSERT INTO users (user_id, username, full_name) 
        VALUES (?, ?, ?)
        ''', (user_id, username, full_name))
        conn.commit()
    
    conn.close()

def update_experience(user_id, exp):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT experience FROM users WHERE user_id = ?', (user_id,))
    current = cursor.fetchone()[0]
    new_exp = current + exp
    
    # Определяем ранг
    new_rank = 1
    for rank in RANKS:
        if new_exp >= rank["min_exp"]:
            if rank["max_exp"] == 50 and new_exp >= rank["min_exp"]:
                new_rank = rank["id"]
                break
            elif new_exp < rank["max_exp"]:
                new_rank = rank["id"]
                break
    
    cursor.execute('''
    UPDATE users 
    SET experience = ?, rank_id = ? 
    WHERE user_id = ?
    ''', (new_exp, new_rank, user_id))
    
    conn.commit()
    conn.close()
    return new_exp, new_rank

def get_user_info(user_id):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT u.user_id, u.username, u.full_name, u.experience, u.rank_id, 
           r.name as rank_name
    FROM users u
    WHERE u.user_id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        user_dict = {
            'user_id': user[0],
            'username': user[1],
            'full_name': user[2],
            'experience': user[3],
            'rank_id': user[4],
            'rank_name': user[5] if user[5] else "Новенький"
        }
        return user_dict
    return None

def add_question(user_id, text):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO questions (user_id, question_text) 
    VALUES (?, ?)
    ''', (user_id, text))
    
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return question_id

def get_questions(limit=5, offset=0):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT q.question_id, q.question_text, q.created_at, q.is_answered,
           u.user_id, u.username
    FROM questions q
    JOIN users u ON q.user_id = u.user_id
    ORDER BY q.created_at DESC
    LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    questions = cursor.fetchall()
    conn.close()
    return questions

# Клавиатуры
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("📝 Посмотреть вопросы"),
        types.KeyboardButton("❓ Задать вопрос")
    )
    keyboard.add(
        types.KeyboardButton("👤 Профиль"),
        types.KeyboardButton("🏆 Ранги")
    )
    keyboard.add(
        types.KeyboardButton("📊 Мои вопросы"),
        types.KeyboardButton("💬 Мои ответы")
    )
    return keyboard

def questions_keyboard(question_id, offset):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("💬 Ответить", callback_data=f"answer_{question_id}"),
        types.InlineKeyboardButton("📋 Ответы", callback_data=f"show_answers_{question_id}")
    )
    keyboard.add(
        types.InlineKeyboardButton("◀️", callback_data=f"prev_{offset}"),
        types.InlineKeyboardButton("▶️", callback_data=f"next_{offset}")
    )
    return keyboard

# Обработчики
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    get_or_create_user(user_id, username, full_name)
    
    try:
        bot.send_sticker(message.chat.id, STICKERS["welcome"])
    except:
        pass
    
    bot.send_message(
        message.chat.id,
        f"👋 Привет, {full_name}!\n\n"
        f"Добро пожаловать в бот вопросов и ответов!\n"
        f"Здесь вы можете задавать вопросы и отвечать на вопросы других пользователей.\n\n"
        f"🎯 **Система опыта:**\n"
        f"• За ответ на вопрос: +3 опыта\n"
        f"• За лайк на ваш ответ: +1 опыт\n\n"
        f"🏆 **Повышайте свой ранг и становитесь лучшим!**",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "📝 Посмотреть вопросы")
def show_questions(message):
    try:
        bot.send_sticker(message.chat.id, STICKERS["questions"])
    except:
        pass
    
    questions = get_questions(limit=5)
    
    if not questions:
        bot.send_message(message.chat.id, "📭 Пока нет вопросов. Будьте первым, кто задаст вопрос!")
        return
    
    send_question(message.chat.id, questions[0], 0)

def send_question(chat_id, question, offset):
    q_id, text, created, answered, user_id, username = question
    
    status = "✅ Отвечено" if answered else "⏳ Ожидает ответа"
    user_display = f"@{username}" if username else f"ID: {user_id}"
    
    message_text = (
        f"❓ **Вопрос #{q_id}**\n\n"
        f"{text}\n\n"
        f"👤 *От:* {user_display}\n"
        f"📅 *Дата:* {created}\n"
        f"📊 *Статус:* {status}\n\n"
        f"Страница {offset//5 + 1}"
    )
    
    bot.send_message(
        chat_id,
        message_text,
        reply_markup=questions_keyboard(q_id, offset),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "👤 Профиль")
def show_profile(message):
    try:
        bot.send_sticker(message.chat.id, STICKERS["profile"])
    except:
        pass
    
    user_info = get_user_info(message.from_user.id)
    
    if not user_info:
        bot.send_message(message.chat.id, "❌ Профиль не найден.")
        return
    
    # Находим текущий и следующий ранги
    current_rank = None
    next_rank = None
    
    for i, rank in enumerate(RANKS):
        if rank["id"] == user_info["rank_id"]:
            current_rank = rank
            if i + 1 < len(RANKS):
                next_rank = RANKS[i + 1]
            break
    
    # Создаем прогресс-бар
    if current_rank and next_rank:
        current_exp = user_info["experience"]
        min_exp = current_rank["min_exp"]
        max_exp = next_rank["min_exp"] if next_rank else current_rank["max_exp"]
        
        progress = ((current_exp - min_exp) / (max_exp - min_exp)) * 100 if max_exp > min_exp else 100
        progress = min(100, max(0, progress))
        
        bars = int(progress / 10)
        progress_bar = "[" + "█" * bars + "░" * (10 - bars) + "]"
        
        next_info = f"\n🎯 До {next_rank['icon']} *{next_rank['name']}*: {max_exp - current_exp} опыта"
    else:
        progress_bar = "[██████████]"
        next_info = "\n🎉 Вы достигли максимального ранга!"
    
    profile_text = (
        f"{current_rank['icon'] if current_rank else '👤'} **Ваш профиль**\n\n"
        f"📛 *Имя:* {user_info['full_name']}\n"
        f"🏆 *Ранг:* {current_rank['name'] if current_rank else 'Новенький'}\n"
        f"⭐ *Опыт:* {user_info['experience']}\n"
        f"📈 *Прогресс:* {progress_bar} {progress:.1f}%"
        f"{next_info}"
    )
    
    bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🏆 Ранги")
def show_ranks(message):
    try:
        bot.send_sticker(message.chat.id, STICKERS["ranks"])
    except:
        pass
    
    ranks_text = "🏆 **Система рангов:**\n\n"
    
    for rank in RANKS:
        icon = rank["icon"]
        name = rank["name"]
        if rank["max_exp"] == 50:
            exp_range = f"{rank['min_exp']}+ опыта"
        else:
            exp_range = f"{rank['min_exp']}/{rank['max_exp']} опыта"
        
        ranks_text += f"{icon} *{name}* - {exp_range}\n"
    
    ranks_text += "\n⚡ **Получение опыта:**\n"
    ranks_text += "• Ответ на вопрос: +3 опыта\n"
    ranks_text += "• Лайк на ваш ответ: +1 опыт"
    
    bot.send_message(message.chat.id, ranks_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "❓ Задать вопрос")
def ask_question(message):
    msg = bot.send_message(
        message.chat.id,
        "📝 *Опишите свой вопрос:*\n\n"
        "Будьте максимально подробны, чтобы получить качественный ответ.\n"
        "Отправьте текст вопроса одним сообщением.",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_question)

def process_question(message):
    if len(message.text) < 10:
        bot.send_message(message.chat.id, "❌ Вопрос слишком короткий. Напишите более развернутый вопрос.")
        return
    
    user_id = message.from_user.id
    question_id = add_question(user_id, message.text)
    
    bot.send_message(
        message.chat.id,
        f"✅ *Ваш вопрос #{question_id} успешно добавлен!*\n\n"
        f"Дождитесь ответов от других пользователей.",
        parse_mode='Markdown',
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📊 Мои вопросы")
def show_my_questions(message):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT question_id, question_text, created_at, is_answered
    FROM questions
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT 10
    ''', (message.from_user.id,))
    
    questions = cursor.fetchall()
    conn.close()
    
    if not questions:
        bot.send_message(message.chat.id, "📭 У вас пока нет вопросов.")
        return
    
    text = "📋 *Ваши вопросы:*\n\n"
    
    for q in questions:
        q_id, q_text, created, answered = q
        status = "✅ Отвечено" if answered else "⏳ Ожидает"
        
        # Обрезаем текст
        short_text = q_text[:100] + "..." if len(q_text) > 100 else q_text
        
        text += f"*#{q_id}* - {short_text}\n"
        text += f"📅 {created[:10]} | {status}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "💬 Мои ответы")
def show_my_answers(message):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT a.answer_id, a.answer_text, a.likes, a.created_at,
           q.question_id, q.question_text
    FROM answers a
    JOIN questions q ON a.question_id = q.question_id
    WHERE a.user_id = ?
    ORDER BY a.created_at DESC
    LIMIT 10
    ''', (message.from_user.id,))
    
    answers = cursor.fetchall()
    conn.close()
    
    if not answers:
        bot.send_message(message.chat.id, "📭 Вы еще не отвечали на вопросы.")
        return
    
    text = "💬 *Ваши ответы:*\n\n"
    
    for a in answers:
        a_id, a_text, likes, created, q_id, q_text = a
        
        # Обрезаем тексты
        short_answer = a_text[:80] + "..." if len(a_text) > 80 else a_text
        short_question = q_text[:60] + "..." if len(q_text) > 60 else q_text
        
        text += f"*Ответ #{a_id}* (к вопросу #{q_id})\n"
        text += f"❓ Вопрос: {short_question}\n"
        text += f"💬 Ваш ответ: {short_answer}\n"
        text += f"👍 Лайков: {likes} | 📅 {created[:10]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# Обработка callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith("answer_"):
        question_id = call.data.split("_")[1]
        msg = bot.send_message(
            call.message.chat.id,
            f"💬 *Вы отвечаете на вопрос #{question_id}*\n\n"
            f"Напишите ваш ответ:",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_answer, question_id)
        
    elif call.data.startswith("show_answers_"):
        question_id = call.data.split("_")[2]
        show_answers(call.message, question_id)
        
    elif call.data.startswith("prev_"):
        offset = int(call.data.split("_")[1])
        new_offset = max(0, offset - 5)
        questions = get_questions(limit=5, offset=new_offset)
        
        if questions:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_question(call.message.chat.id, questions[0], new_offset)
        else:
            bot.answer_callback_query(call.id, "Это первая страница")
            
    elif call.data.startswith("next_"):
        offset = int(call.data.split("_")[1])
        new_offset = offset + 5
        questions = get_questions(limit=5, offset=new_offset)
        
        if questions:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_question(call.message.chat.id, questions[0], new_offset)
        else:
            bot.answer_callback_query(call.id, "Это последняя страница")

def process_answer(message, question_id):
    if len(message.text) < 5:
        bot.send_message(message.chat.id, "❌ Ответ слишком короткий.")
        return
    
    # Добавляем ответ в БД
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO answers (question_id, user_id, answer_text)
    VALUES (?, ?, ?)
    ''', (question_id, message.from_user.id, message.text))
    
    # Начисляем опыт
    update_experience(message.from_user.id, 3)
    
    # Обновляем статус вопроса
    cursor.execute('''
    UPDATE questions SET is_answered = TRUE WHERE question_id = ?
    ''', (question_id,))
    
    conn.commit()
    conn.close()
    
    bot.send_message(
        message.chat.id,
        f"✅ *Ответ добавлен!*\n\n"
        f"Вы получили +3 опыта!\n"
        f"Теперь ваш ответ могут оценить другие пользователи.",
        parse_mode='Markdown',
        reply_markup=main_keyboard()
    )

def show_answers(message, question_id):
    conn = sqlite3.connect('questions_bot.db')
    cursor = conn.cursor()
    
    # Получаем вопрос
    cursor.execute('''
    SELECT q.question_text, u.username
    FROM questions q
    JOIN users u ON q.user_id = u.user_id
    WHERE q.question_id = ?
    ''', (question_id,))
    
    question = cursor.fetchone()
    
    if not question:
        bot.send_message(message.chat.id, "❌ Вопрос не найден.")
        return
    
    # Получаем ответы
    cursor.execute('''
    SELECT a.answer_id, a.answer_text, a.likes, a.created_at,
           u.username, u.user_id
    FROM answers a
    JOIN users u ON a.user_id = u.user_id
    WHERE a.question_id = ?
    ORDER BY a.likes DESC, a.created_at DESC
    ''', (question_id,))
    
    answers = cursor.fetchall()
    conn.close()
    
    q_text, q_username = question
    
    text = f"❓ *Вопрос:* {q_text}\n\n"
    text += f"📋 *Ответы ({len(answers)}):*\n\n"
    
    if not answers:
        text += "Пока нет ответов. Будьте первым!"
    else:
        for i, ans in enumerate(answers, 1):
            a_id, a_text, likes, created, username, user_id = ans
            user_display = f"@{username}" if username else f"ID: {user_id}"
            
            text += f"{i}. {a_text[:100]}...\n"
            text += f"   👤 {user_display} | 👍 {likes} | 📅 {created[:10]}\n\n"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# Запуск бота
if __name__ == "__main__":
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    bot.polling(none_stop=True)