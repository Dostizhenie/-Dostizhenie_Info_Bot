import logging
import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "7974836537:AAGZnPxR8m0CQRmU2Hx117_KkhWKfBb4-yc"

# ID администраторов
ADMINS = {
    "ksenia": "5033132467",      # Ксения - оплата
    "anastasia": "5324437110",   # Анастасия - справки/страховки
    "lyudmila": "9655903815",    # Людмила - резервный админ
    "agnia": "1481715825"        # Агния - все вопросы + главный админ
}

# Файл базы данных
DATABASE_FILE = "users_database.json"

# База данных пользователей
users_db = {}

# Статистика по категориям
statistics = {
    "questions": [],      # Общие вопросы
    "documents": [],      # Справки/страховки
    "payments": []        # Вопросы по оплате
}

# Состояния для ConversationHandler
(ASKING_CHILD_NAME, ASKING_QUESTION, UPLOADING_SPRAVKA, ASKING_PAYMENT_QUESTION, 
 ASKING_OTHER_QUESTION, ADMIN_BROADCAST_MESSAGE, ADMIN_BROADCAST_CATEGORY) = range(7)


# ============= ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ =============

def load_database():
    """Загрузка базы данных из файла"""
    global users_db, statistics
    try:
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                users_db = data.get('users', {})
                # Конвертируем ключи обратно в int
                users_db = {int(k): v for k, v in users_db.items()}
                statistics = data.get('statistics', {
                    "questions": [],
                    "documents": [],
                    "payments": []
                })
            logger.info(f"База данных загружена: {len(users_db)} пользователей")
    except Exception as e:
        logger.error(f"Ошибка загрузки базы данных: {e}")


def save_database():
    """Сохранение базы данных в файл"""
    try:
        data = {
            'users': users_db,
            'statistics': statistics
        }
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("База данных сохранена")
    except Exception as e:
        logger.error(f"Ошибка сохранения базы данных: {e}")


def add_user(user_id, username, full_name, child_name):
    """Добавление пользователя в базу"""
    users_db[user_id] = {
        'username': username,
        'full_name': full_name,
        'child_name': child_name,
        'registered_at': datetime.now().isoformat()
    }
    save_database()


def update_child_name(user_id, child_name):
    """Обновление ФИО ребёнка"""
    if user_id in users_db:
        users_db[user_id]['child_name'] = child_name
    save_database()


def add_statistic(category, user_id, username, full_name, child_name, question_text):
    """Добавление записи в статистику"""
    record = {
        'user_id': user_id,
        'username': username,
        'full_name': full_name,
        'child_name': child_name,
        'question': question_text,
        'timestamp': datetime.now().isoformat()
    }
    statistics[category].append(record)
    save_database()


def export_database():
    """Экспорт базы данных в текстовый формат"""
    output = "📊 БАЗА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ\n\n"
    output += f"Всего пользователей: {len(users_db)}\n"
    output += f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
    output += "="*50 + "\n\n"
    
    for user_id, data in users_db.items():
        output += f"👤 ID: {user_id}\n"
        output += f"Имя: {data.get('full_name', 'Не указано')}\n"
        output += f"Username: @{data.get('username', 'нет')}\n"
        output += f"ФИО ребёнка: {data.get('child_name', 'Не указано')}\n"
        output += f"Зарегистрирован: {data.get('registered_at', 'Неизвестно')}\n"
        output += "-"*50 + "\n\n"
    
    return output


def get_statistics_text():
    """Получение текста статистики"""
    output = "📈 СТАТИСТИКА ОБРАЩЕНИЙ\n\n"
    output += f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
    
    output += f"❓ Общие вопросы: {len(statistics['questions'])}\n"
    output += f"📄 Справки/страховки: {len(statistics['documents'])}\n"
    output += f"💰 Вопросы по оплате: {len(statistics['payments'])}\n\n"
    output += f"👥 Всего пользователей: {len(users_db)}\n\n"
    output += "="*50 + "\n\n"
    
    # Последние 10 обращений
    all_records = []
    for category, records in statistics.items():
        for record in records:
            record['category'] = category
            all_records.append(record)
    
    all_records.sort(key=lambda x: x['timestamp'], reverse=True)
    
    if all_records:
        output += "🕐 ПОСЛЕДНИЕ 10 ОБРАЩЕНИЙ:\n\n"
        for i, record in enumerate(all_records[:10], 1):
            cat_emoji = {"questions": "❓", "documents": "📄", "payments": "💰"}.get(record['category'], "❓")
            output += f"{i}. {cat_emoji} {record['full_name']}\n"
            output += f"   Ребёнок: {record['child_name']}\n"
            output += f"   Вопрос: {record['question'][:50]}...\n"
            output += f"   Дата: {record['timestamp'][:10]}\n\n"
    
    return output


# ============= ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА =============

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    return str(user_id) in ADMINS.values()


def is_main_admin(user_id):
    """Проверка, является ли пользователь главным админом (Агния)"""
    return str(user_id) == ADMINS["agnia"]


# ============= ОБРАБОТЧИКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Проверяем, есть ли пользователь в базе
    if user_id not in users_db:
        # Новый пользователь - запрашиваем ФИО ребёнка
        welcome_text = (
            f"Здравствуйте, {user.first_name}! 👋\n\n"
            f"Добро пожаловать в бот школы тхэквондо «Достижение»!\n\n"
            f"Для начала работы, пожалуйста, укажите ФИО вашего ребёнка:"
        )
        await update.message.reply_text(welcome_text)
        return ASKING_CHILD_NAME
    else:
        # Существующий пользователь - показываем меню
        child_name = users_db[user_id]['child_name']
        welcome_text = (
            f"С возвращением, {user.first_name}! 👋\n\n"
            f"Ребёнок: {child_name}\n\n"
            f"Выберите нужный раздел:"
        )
        
        keyboard = [
            [KeyboardButton("📅 Ближайшие мероприятия")],
            [KeyboardButton("📄 Отправить справку/страховку")],
            [KeyboardButton("💰 Вопрос по оплате")],
            [KeyboardButton("❓ Другой вопрос")],
            [KeyboardButton("✏️ Изменить ФИО ребёнка")]
        ]
        
        # Для администраторов добавляем админ-панель
        if is_admin(user_id):
            keyboard.insert(0, [KeyboardButton("⚙️ Админ-панель")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        return ConversationHandler.END


async def save_initial_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение ФИО ребёнка при первой регистрации"""
    user = update.effective_user
    child_name = update.message.text
    
    # Добавляем пользователя в базу
    add_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        child_name=child_name
    )
    
    # Показываем главное меню
    welcome_text = (
        f"✅ Спасибо! ФИО ребёнка сохранено: {child_name}\n\n"
        f"Выберите нужный раздел:"
    )
    
    keyboard = [
        [KeyboardButton("📅 Ближайшие мероприятия")],
        [KeyboardButton("📄 Отправить справку/страховку")],
        [KeyboardButton("💰 Вопрос по оплате")],
        [KeyboardButton("❓ Другой вопрос")],
        [KeyboardButton("✏️ Изменить ФИО ребёнка")]
    ]
    
    # Для администраторов добавляем админ-панель
    if is_admin(user.id):
        keyboard.insert(0, [KeyboardButton("⚙️ Админ-панель")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    return ConversationHandler.END


async def handle_change_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Изменить ФИО ребёнка'"""
    user = update.effective_user
    current_name = users_db.get(user.id, {}).get('child_name', 'Не указано')
    
    await update.message.reply_text(
        f"Текущее ФИО ребёнка: {current_name}\n\n"
        f"Введите новое ФИО ребёнка:"
    )
    return ASKING_CHILD_NAME


async def save_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение нового ФИО ребёнка"""
    user = update.effective_user
    child_name = update.message.text
    
    # Обновляем в базе
    update_child_name(user.id, child_name)
    
    await update.message.reply_text(
        f"✅ ФИО ребёнка обновлено: {child_name}\n\n"
        f"Выберите нужный раздел из меню."
    )
    
    logger.info(f"Пользователь {user.id} обновил ФИО ребёнка: {child_name}")
    
    return ConversationHandler.END


async def handle_spravka_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Отправить справку/страховку'"""
    await update.message.reply_text(
        "📄 Отправьте фото или файл справки/страховки.\n\n"
        "Вы можете отправить документ одним сообщением."
    )
    return UPLOADING_SPRAVKA


async def handle_spravka_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки справки/страховки"""
    user = update.effective_user
    user_data = users_db.get(user.id, {})
    child_name = user_data.get('child_name', 'Не указано')
    
    # Формируем сообщение для админа
    message = (
        f"📄 НОВАЯ СПРАВКА/СТРАХОВКА\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}"
    )
    
    # Добавляем в статистику
    add_statistic("documents", user.id, user.username, user.full_name, child_name, "Отправлена справка/страховка")
    
    # Отправляем Анастасии (справки/страховки)
    admin_id = ADMINS.get("anastasia")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
            
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=update.message.photo[-1].file_id
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=admin_id,
                    document=update.message.document.file_id
                )
            
            await update.message.reply_text(
                "✅ Справка/страховка получена и отправлена администратору!\n"
                "Ожидайте подтверждения."
            )
            logger.info(f"Справка от {user.id} отправлена Анастасии ({admin_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки справки администратору: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при отправке. Попробуйте позже."
            )
    
    return ConversationHandler.END


async def handle_payment_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Вопрос по оплате'"""
    await update.message.reply_text(
        "💰 Напишите ваш вопрос по оплате.\n\n"
        "Администратор ответит вам в ближайшее время."
    )
    return ASKING_PAYMENT_QUESTION


async def receive_payment_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение вопроса по оплате"""
    user = update.effective_user
    question_text = update.message.text
    user_data = users_db.get(user.id, {})
    child_name = user_data.get('child_name', 'Не указано')
    
    # Формируем сообщение
    message = (
        f"💰 ВОПРОС ПО ОПЛАТЕ\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}\n\n"
        f"Вопрос:\n{question_text}"
    )
    
    # Добавляем в статистику
    add_statistic("payments", user.id, user.username, user.full_name, child_name, question_text)
    
    # Отправляем Ксении (оплата)
    admin_id = ADMINS.get("ksenia")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
            await update.message.reply_text(
                "✅ Ваш вопрос по оплате отправлен администратору!\n"
                "Ожидайте ответа."
            )
            logger.info(f"Вопрос по оплате от {user.id} отправлен Ксении ({admin_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки вопроса по оплате: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при отправке. Попробуйте позже."
            )
    
    return ConversationHandler.END


async def handle_other_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Другой вопрос'"""
    await update.message.reply_text(
        "❓ Напишите ваш вопрос.\n\n"
        "Я передам его администратору."
    )
    return ASKING_OTHER_QUESTION


async def receive_other_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение другого вопроса"""
    user = update.effective_user
    question_text = update.message.text
    user_data = users_db.get(user.id, {})
    child_name = user_data.get('child_name', 'Не указано')
    
    # Формируем сообщение для Агнии
    message = (
        f"❓ ДРУГОЙ ВОПРОС\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}\n\n"
        f"Вопрос:\n{question_text}"
    )
    
    # Добавляем в статистику
    add_statistic("questions", user.id, user.username, user.full_name, child_name, question_text)
    
    # Отправляем Агнии
    admin_id = ADMINS.get("agnia")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
            await update.message.reply_text(
                "✅ Ваш вопрос отправлен администратору!\n"
                "Ожидайте ответа."
            )
            logger.info(f"Другой вопрос от {user.id} отправлен Агнии ({admin_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки вопроса Агнии: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при отправке. Попробуйте позже."
            )
    
    return ConversationHandler.END


async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Ближайшие мероприятия'"""
    events_text = (
        "📅 БЛИЖАЙШИЕ МЕРОПРИЯТИЯ:\n\n"
        "🥋 Тренировка для начинающих\n"
        "📆 Дата: 10 февраля 2026, 18:00\n"
        "📍 Место: Спортзал №1\n\n"
        "🏆 Соревнования по тхэквондо\n"
        "📆 Дата: 25 февраля 2026, 10:00\n"
        "📍 Место: Дворец спорта\n\n"
        "Для регистрации свяжитесь с тренером."
    )
    
    await update.message.reply_text(events_text)


async def handle_any_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик любого текста - отправляет Агнии"""
    user = update.effective_user
    question_text = update.message.text
    
    # Пропускаем текст кнопок
    button_texts = [
        "📅 Ближайшие мероприятия", 
        "📄 Отправить справку/страховку", 
        "💰 Вопрос по оплате",
        "❓ Другой вопрос",
        "✏️ Изменить ФИО ребёнка", 
        "⚙️ Админ-панель"
    ]
    if question_text in button_texts:
        return
    
    user_data = users_db.get(user.id, {})
    child_name = user_data.get('child_name', 'Не указано')
    
    # Формируем сообщение для Агнии
    message = (
        f"💬 НОВОЕ СООБЩЕНИЕ\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}\n\n"
        f"Сообщение:\n{question_text}"
    )
    
    # Добавляем в статистику
    add_statistic("questions", user.id, user.username, user.full_name, child_name, question_text)
    
    # Отправляем Агнии
    admin_id = ADMINS.get("agnia")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
            await update.message.reply_text(
                "✅ Ваше сообщение отправлено администратору!\n"
                "Ожидайте ответа."
            )
            logger.info(f"Сообщение от {user.id} отправлено Агнии ({admin_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения Агнии: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при отправке. Попробуйте позже."
            )


# ============= АДМИН-ПАНЕЛЬ =============

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ У вас нет доступа к админ-панели.")
        return
    
    # Клавиатура админ-панели
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📤 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💾 Выгрузить базу", callback_data="admin_export")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = "⚙️ АДМИН-ПАНЕЛЬ\n\nВыберите действие:"
    
    await update.message.reply_text(admin_text, reply_markup=reply_markup)


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ статистики админу"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔ У вас нет доступа к статистике.")
        return
    
    stats_text = get_statistics_text()
    
    await query.edit_message_text(stats_text)


async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню рассылки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔ У вас нет доступа к рассылке.")
        return
    
    # Определяем доступные категории в зависимости от админа
    keyboard = []
    
    if is_main_admin(user_id):
        # Агния может делать рассылку всем
        keyboard.append([InlineKeyboardButton("👥 Все пользователи", callback_data="broadcast_all")])
    
    # Каждый админ может делать рассылку по своей категории
    if str(user_id) == ADMINS["agnia"]:
        keyboard.append([InlineKeyboardButton("❓ Общие вопросы", callback_data="broadcast_questions")])
    if str(user_id) == ADMINS["anastasia"]:
        keyboard.append([InlineKeyboardButton("📄 Справки/страховки", callback_data="broadcast_documents")])
    if str(user_id) == ADMINS["ksenia"]:
        keyboard.append([InlineKeyboardButton("💰 Оплата", callback_data="broadcast_payments")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📤 РАССЫЛКА\n\nВыберите категорию получателей:",
        reply_markup=reply_markup
    )


async def admin_broadcast_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбрана категория для рассылки"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("broadcast_", "")
    context.user_data['broadcast_category'] = category
    
    await query.edit_message_text(
        "📝 Отправьте текст сообщения для рассылки:\n\n"
        "(Напишите сообщение в следующем сообщении)"
    )
    
    return ADMIN_BROADCAST_MESSAGE


async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка рассылки"""
    message_text = update.message.text
    category = context.user_data.get('broadcast_category', 'all')
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к рассылке.")
        return ConversationHandler.END
    
    # Определяем список получателей
    recipients = set()
    
    if category == "all":
        # Все пользователи
        recipients = set(users_db.keys())
    else:
        # По категории из статистики
        for record in statistics.get(category, []):
            recipients.add(record['user_id'])
    
    # Отправляем рассылку
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text(f"📤 Начинаю рассылку для {len(recipients)} пользователей...")
    
    for recipient_id in recipients:
        try:
            await context.bot.send_message(chat_id=recipient_id, text=message_text)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки рассылки пользователю {recipient_id}: {e}")
            fail_count += 1
    
    result_text = (
        f"✅ Рассылка завершена!\n\n"
        f"Успешно: {success_count}\n"
        f"Ошибок: {fail_count}"
    )
    
    await update.message.reply_text(result_text)
    
    return ConversationHandler.END


async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт базы данных"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_main_admin(user_id):
        await query.edit_message_text("⛔ Только главный администратор может выгружать базу данных.")
        return
    
    # Генерируем текст базы данных
    db_text = export_database()
    
    # Отправляем как файл
    filename = f"database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    await query.message.reply_document(
        document=db_text.encode('utf-8'),
        filename=filename,
        caption="📊 База данных пользователей"
    )
    
    await query.edit_message_text("✅ База данных выгружена!")


# ============= ОБРАБОТЧИКИ CALLBACK =============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    
    if query.data == "admin_stats":
        await admin_stats(update, context)
    elif query.data == "admin_broadcast":
        await admin_broadcast_menu(update, context)
    elif query.data == "admin_export":
        await admin_export(update, context)
    elif query.data.startswith("broadcast_"):
        await admin_broadcast_category_selected(update, context)
        return ADMIN_BROADCAST_MESSAGE


# ============= ГЛАВНАЯ ФУНКЦИЯ =============

def main():
    """Запуск бота"""
    # Загружаем базу данных
    load_database()
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для пользователей
    user_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^✏️ Изменить ФИО ребёнка$"), handle_change_child_name),
            MessageHandler(filters.Regex("^📄 Отправить справку/страховку$"), handle_spravka_request),
            MessageHandler(filters.Regex("^💰 Вопрос по оплате$"), handle_payment_question),
            MessageHandler(filters.Regex("^❓ Другой вопрос$"), handle_other_question),
            MessageHandler(filters.Regex("^📅 Ближайшие мероприятия$"), handle_events),
        ],
        states={
            ASKING_CHILD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_initial_child_name)],
            UPLOADING_SPRAVKA: [MessageHandler(filters.PHOTO | filters.Document.ALL, handle_spravka_upload)],
            ASKING_PAYMENT_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_question)],
            ASKING_OTHER_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_other_question)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # ConversationHandler для админ-рассылки
    admin_broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_category_selected, pattern="^broadcast_")],
        states={
            ADMIN_BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Добавляем обработчики
    application.add_handler(user_conv_handler)
    application.add_handler(admin_broadcast_handler)
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Админ-панель$"), admin_panel))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_text))
    
    # Запускаем бота
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info(f"Администраторы настроены:")
    logger.info(f"  - Агния (главный): {ADMINS['agnia']}")
    logger.info(f"  - Анастасия (справки): {ADMINS['anastasia']}")
    logger.info(f"  - Ксения (оплата): {ADMINS['ksenia']}")
    logger.info(f"  - Людмила (резерв): {ADMINS['lyudmila']}")
    logger.info(f"Загружено пользователей: {len(users_db)}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
