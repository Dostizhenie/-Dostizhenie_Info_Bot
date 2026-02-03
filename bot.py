#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot для школы тхэквондо "Достижение"
Версия: 4.0 для Railway.app (python-telegram-bot 20.8)
"""

import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# =======================
# НАСТРОЙКИ
# =======================

# ВАЖНО! Замените на ваш токен от @BotFather
BOT_TOKEN = "7958818251:AAH0r0gfsFnlHOD6K0lfvXJV7mxEgz9AVDQ"

# Chat ID администраторов (используйте @userinfobot для получения)
ADMINS = {
    "oplata": 5033132467,      # Ксения - оплата
    "spravka": 5324437110,     # Анастасия - справки/страховки
    "competition": 985903815,   # Людмила - турниры
    "other": 1481715825         # Агния - другие вопросы
}

# Состояния разговора
WAITING_NAME, MAIN_MENU, WAITING_SPRAVKA, WAITING_STRAHOVKA, WAITING_PAYMENT_QUESTION = range(5)

# База данных пользователей (в памяти)
users_db = {}

# =======================
# ЗАГРУЗКА ДАННЫХ
# =======================

def load_tournament_data():
    """Загружает данные о турнире из tournament.json"""
    try:
        with open('tournament.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "name": "Турнир по тхэквондо",
            "date": "21 февраля 2026",
            "location": "СК «Купол»",
            "registration_link": "https://forms.gle/example",
            "price": "1500 ₽",
            "deadline": "15 февраля 2026",
            "description": "Открытый турнир для всех возрастных категорий.\n\nТребования:\n• Защитное снаряжение\n• Добок (форма)\n• Медицинская справка"
        }

def load_events_data():
    """Загружает данные о мероприятиях из events.json"""
    try:
        with open('events.json', 'r', encoding='utf-8') as f:
            return json.load(f).get("events", [])
    except FileNotFoundError:
        return [
            {
                "name": "Аттестация на пояса",
                "date": "28 февраля 2026",
                "description": "Экзамен на повышение поясов для всех учеников"
            },
            {
                "name": "Мастер-класс",
                "date": "10 марта 2026",
                "description": "Специальный мастер-класс от чемпиона России"
            }
        ]

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =======================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =======================

def get_main_menu_keyboard():
    """Возвращает клавиатуру главного меню"""
    keyboard = [
        [KeyboardButton("🏆 Регистрация на Турнир")],
        [KeyboardButton("📅 Ближайшие мероприятия")],
        [KeyboardButton("📄 Отправить справку")],
        [KeyboardButton("📄 Отправить страховку")],
        [KeyboardButton("💰 Вопрос по оплате")],
        [KeyboardButton("✏️ Изменить ФИО ребенка")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, admin_type: str, message: str):
    """Отправляет уведомление администратору"""
    admin_id = ADMINS.get(admin_type)
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
        except Exception as e:
            logger.error(f"Ошибка отправки администратору {admin_type}: {e}")

# =======================
# ОБРАБОТЧИКИ КОМАНД
# =======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    if user_id in users_db:
        # Пользователь уже зарегистрирован
        child_name = users_db[user_id]
        await update.message.reply_text(
            f"С возвращением! Ребёнок: {child_name}\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    else:
        # Новый пользователь
        await update.message.reply_text(
            "👋 Добро пожаловать в бот школы тхэквондо «Достижение»!\n\n"
            "Пожалуйста, введите ФИО вашего ребёнка:"
        )
        return WAITING_NAME

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода ФИО ребёнка"""
    user_id = update.effective_user.id
    child_name = update.message.text.strip()
    
    if len(child_name) < 3:
        await update.message.reply_text("Пожалуйста, введите полное ФИО ребёнка:")
        return WAITING_NAME
    
    users_db[user_id] = child_name
    
    await update.message.reply_text(
        f"✅ Спасибо! Ребёнок зарегистрирован: {child_name}\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

async def handle_change_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изменения ФИО ребёнка"""
    await update.message.reply_text("Введите новое ФИО ребёнка:")
    return WAITING_NAME

# =======================
# ОБРАБОТЧИКИ МЕНЮ
# =======================

async def handle_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Регистрация на Турнир'"""
    tournament = load_tournament_data()
    
    message = (
        f"🏆 **{tournament['name']}**\n\n"
        f"📅 Дата: {tournament['date']}\n"
        f"📍 Место: {tournament['location']}\n"
        f"💰 Взнос: {tournament['price']}\n"
        f"⏰ Срок регистрации до: {tournament['deadline']}\n\n"
        f"{tournament['description']}\n\n"
        f"🔗 [Зарегистрироваться]({tournament['registration_link']})"
    )
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=get_main_menu_keyboard()
    )
    
    # Уведомляем администратора о запросе турнира
    user = update.effective_user
    child_name = users_db.get(user.id, "Не указано")
    await notify_admin(
        context,
        "competition",
        f"🏆 Запрос информации о турнире\n\n"
        f"От: {user.full_name} (@{user.username})\n"
        f"Ребёнок: {child_name}"
    )
    
    return MAIN_MENU

async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Ближайшие мероприятия'"""
    events = load_events_data()
    
    if not events:
        await update.message.reply_text(
            "📅 В данный момент нет запланированных мероприятий.\n"
            "Следите за обновлениями!",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    
    message = "📅 **Ближайшие мероприятия:**\n\n"
    for event in events:
        message += (
            f"🔹 **{event['name']}**\n"
            f"Дата: {event['date']}\n"
            f"{event['description']}\n\n"
        )
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

async def handle_spravka_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Отправить справку'"""
    await update.message.reply_text(
        "📄 Пожалуйста, отправьте фото или файл справки.\n\n"
        "Для отмены введите /cancel"
    )
    return WAITING_SPRAVKA

async def handle_spravka_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки справки"""
    user = update.effective_user
    child_name = users_db.get(user.id, "Не указано")
    
    # Отправляем справку администраторам
    message = (
        f"📄 Новая справка\n\n"
        f"От: {user.full_name} (@{user.username})\n"
        f"Ребёнок: {child_name}"
    )
    
    # Пересылаем Ксении и Анастасии
    for admin_type in ["oplata", "spravka"]:
        admin_id = ADMINS.get(admin_type)
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
            except Exception as e:
                logger.error(f"Ошибка отправки справки администратору {admin_type}: {e}")
    
    await update.message.reply_text(
        "✅ Справка отправлена администраторам!\n"
        "Спасибо!",
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

async def handle_strahovka_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Отправить страховку'"""
    await update.message.reply_text(
        "📄 Пожалуйста, отправьте фото или файл страховки.\n\n"
        "Для отмены введите /cancel"
    )
    return WAITING_STRAHOVKA

async def handle_strahovka_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки страховки"""
    user = update.effective_user
    child_name = users_db.get(user.id, "Не указано")
    
    # Отправляем страховку администраторам
    message = (
        f"📄 Новая страховка\n\n"
        f"От: {user.full_name} (@{user.username})\n"
        f"Ребёнок: {child_name}"
    )
    
    # Пересылаем Ксении и Анастасии
    for admin_type in ["oplata", "spravka"]:
        admin_id = ADMINS.get(admin_type)
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
            except Exception as e:
                logger.error(f"Ошибка отправки страховки администратору {admin_type}: {e}")
    
    await update.message.reply_text(
        "✅ Страховка отправлена администраторам!\n"
        "Спасибо!",
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

async def handle_payment_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Вопрос по оплате'"""
    await update.message.reply_text(
        "💰 Опишите ваш вопрос по оплате:\n\n"
        "Для отмены введите /cancel"
    )
    return WAITING_PAYMENT_QUESTION

async def handle_payment_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста вопроса по оплате"""
    user = update.effective_user
    child_name = users_db.get(user.id, "Не указано")
    question = update.message.text
    
    # Отправляем вопрос Ксении
    message = (
        f"💰 Вопрос по оплате\n\n"
        f"От: {user.full_name} (@{user.username})\n"
        f"Ребёнок: {child_name}\n\n"
        f"Вопрос:\n{question}"
    )
    
    await notify_admin(context, "oplata", message)
    
    await update.message.reply_text(
        "✅ Ваш вопрос отправлен администратору!\n"
        "Ксения ответит вам в ближайшее время.",
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel"""
    await update.message.reply_text(
        "❌ Действие отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

# =======================
# ГЛАВНАЯ ФУНКЦИЯ
# =======================

def main():
    """Запуск бота"""
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаём ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)
            ],
            MAIN_MENU: [
                MessageHandler(filters.Regex('^🏆 Регистрация на Турнир$'), handle_tournament),
                MessageHandler(filters.Regex('^📅 Ближайшие мероприятия$'), handle_events),
                MessageHandler(filters.Regex('^📄 Отправить справку$'), handle_spravka_request),
                MessageHandler(filters.Regex('^📄 Отправить страховку$'), handle_strahovka_request),
                MessageHandler(filters.Regex('^💰 Вопрос по оплате$'), handle_payment_question),
                MessageHandler(filters.Regex('^✏️ Изменить ФИО ребенка$'), handle_change_name),
            ],
            WAITING_SPRAVKA: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, handle_spravka_upload)
            ],
            WAITING_STRAHOVKA: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, handle_strahovka_upload)
            ],
            WAITING_PAYMENT_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_question_text)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # Запускаем бота
    logger.info("✅ Бот запущен и готов к работе!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
