#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот для школы тхэквондо "Достижение"
Версия: 3.0 FINAL (python-telegram-bot 20.8)
"""

import logging
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ================== НАСТРОЙКИ ==================

# Токен бота
BOT_TOKEN = "7974836537:AAGMOVIX5UhizeWij6IN5Z2EsIR2_wdiWvg"

# Chat ID администраторов
ADMINS = {
    "oplata": 5033132467,      # Ксения - справки, страховки, оплата
    "spravka": 5324437110,      # Анастасия - справки, страховки
    "competition": 985903815,   # Людмила - вопросы по соревнованиям
    "other": 1481715825         # Агния - прочие вопросы
}

# Состояния для ConversationHandler
(WAITING_NAME, MAIN_MENU, WAITING_SPRAVKA, WAITING_STRAHOVKA, 
 WAITING_PAYMENT_QUESTION) = range(5)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# База данных пользователей (в памяти)
users_db = {}

# ================== ФУНКЦИИ ЗАГРУЗКИ ДАННЫХ ==================

def load_tournament_info():
    """Загружает информацию о турнире из JSON"""
    try:
        with open('tournament.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "name": "Турнир по тач-спаррингу «ЮНЫЙ ЗАЩИТНИК»",
            "date": "21 февраля",
            "location": "СК «Купол» (ул. Береговая, 3)",
            "registration_link": "https://taekwondo18.ru/uzrek",
            "description": "Подробная информация о турнире будет добавлена администратором."
        }

def load_events_info():
    """Загружает информацию о мероприятиях из JSON"""
    try:
        with open('events.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "events": [
                {
                    "name": "Аттестация на пояса",
                    "date": "15 марта",
                    "description": "Плановая аттестация учащихся"
                }
            ]
        }

# ================== КЛАВИАТУРЫ ==================

def get_main_menu_keyboard():
    """Создаёт клавиатуру главного меню"""
    keyboard = [
        ["📋 Регистрация на Турнир"],
        ["📅 Ближайшие мероприятия"],
        ["📄 Отправить справку", "🏥 Отправить страховку"],
        ["💰 Вопрос по оплате"],
        ["👤 Изменить ФИО ребенка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================== ОБРАБОТЧИКИ КОМАНД ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли пользователь в базе
    if user_id in users_db:
        name = users_db[user_id]['name']
        await update.message.reply_text(
            f"С возвращением, {name}! 👋\n\n"
            f"Ваши данные сохранены. Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    else:
        await update.message.reply_text(
            "👋 Добро пожаловать в бот школы тхэквондо «Достижение»!\n\n"
            "📝 Для начала работы укажите ФИО вашего ребенка:\n"
            "(например: Иванов Иван Иванович)"
        )
        return WAITING_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение имени ребенка"""
    user_id = update.effective_user.id
    name = update.message.text.strip()
    
    if len(name) < 3:
        await update.message.reply_text(
            "❌ Пожалуйста, укажите полное ФИО ребенка (минимум 3 символа):"
        )
        return WAITING_NAME
    
    # Сохраняем данные
    users_db[user_id] = {
        'name': name,
        'username': update.effective_user.username or "Не указан",
        'registered_at': datetime.now().isoformat()
    }
    
    await update.message.reply_text(
        f"✅ Отлично! Данные сохранены:\n"
        f"👤 ФИО ребенка: {name}\n\n"
        f"Выберите нужное действие:",
        reply_markup=get_main_menu_keyboard()
    )
    
    return MAIN_MENU

# ================== ОБРАБОТЧИКИ МЕНЮ ==================

async def handle_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик: Регистрация на турнир"""
    tournament = load_tournament_info()
    
    message = f"🏆 **{tournament['name']}**\n\n"
    message += f"📅 Дата: {tournament['date']}\n"
    message += f"📍 Место: {tournament['location']}\n\n"
    message += f"📝 Зарегистрировать ребенка можно по ссылке:\n"
    message += f"👉 {tournament['registration_link']}\n\n"
    
    if 'description' in tournament:
        message += f"ℹ️ {tournament['description']}\n\n"
    
    message += "❓ Если у вас остались вопросы по турниру, они будут переадресованы администратору Людмиле."
    
    await update.message.reply_text(message, reply_markup=get_main_menu_keyboard())
    
    # Уведомляем администратора
    user_id = update.effective_user.id
    user_data = users_db.get(user_id, {})
    name = user_data.get('name', 'Неизвестно')
    username = user_data.get('username', 'Не указан')
    
    await notify_admin(
        context,
        ADMINS['competition'],
        f"📊 Просмотр информации о турнире\n\n"
        f"👤 ФИО ребенка: {name}\n"
        f"🆔 Username: @{username}\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    return MAIN_MENU

async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик: Ближайшие мероприятия"""
    events_data = load_events_info()
    
    message = "📅 **Ближайшие мероприятия:**\n\n"
    
    for idx, event in enumerate(events_data.get('events', []), 1):
        message += f"{idx}. **{event['name']}**\n"
        message += f"   📅 {event['date']}\n"
        if 'description' in event:
            message += f"   ℹ️ {event['description']}\n"
        message += "\n"
    
    if not events_data.get('events'):
        message = "📅 В данный момент нет запланированных мероприятий.\n\n"
        message += "Следите за обновлениями!"
    
    await update.message.reply_text(message, reply_markup=get_main_menu_keyboard())
    return MAIN_MENU

async def handle_spravka_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик: Отправить справку"""
    user_id = update.effective_user.id
    user_data = users_db.get(user_id, {})
    name = user_data.get('name', 'Не указано')
    
    await update.message.reply_text(
        f"📄 **Отправка медицинской справки**\n\n"
        f"👤 ФИО ребенка: {name}\n\n"
        f"📸 Пожалуйста, отправьте фотографию или PDF-файл справки.\n\n"
        f"ℹ️ Справка будет отправлена администраторам Ксении и Анастасии.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return WAITING_SPRAVKA

async def receive_spravka(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение справки от пользователя"""
    user_id = update.effective_user.id
    user_data = users_db.get(user_id, {})
    name = user_data.get('name', 'Не указано')
    username = user_data.get('username', 'Не указан')
    
    # Проверяем, что отправлено фото или документ
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "Фото"
        send_func = context.bot.send_photo
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "Документ"
        send_func = context.bot.send_document
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте фотографию или PDF-файл справки.",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    
    # Отправляем администраторам
    admin_message = (
        f"📄 **НОВАЯ СПРАВКА**\n\n"
        f"👤 ФИО ребенка: {name}\n"
        f"🆔 Username родителя: @{username}\n"
        f"📎 Тип файла: {file_type}\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Отправляем Ксении и Анастасии
    for admin_key in ['oplata', 'spravka']:
        try:
            await send_func(
                chat_id=ADMINS[admin_key],
                photo=file_id if file_type == "Фото" else None,
                document=file_id if file_type == "Документ" else None,
                caption=admin_message
            )
        except Exception as e:
            logger.error(f"Ошибка отправки справки администратору {admin_key}: {e}")
    
    await update.message.reply_text(
        "✅ **Справка получена и отправлена администраторам!**\n\n"
        "Вы получите ответ в ближайшее время.",
        reply_markup=get_main_menu_keyboard()
    )
    
    return MAIN_MENU

async def handle_strahovka_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик: Отправить страховку"""
    user_id = update.effective_user.id
    user_data = users_db.get(user_id, {})
    name = user_data.get('name', 'Не указано')
    
    await update.message.reply_text(
        f"🏥 **Отправка страховки**\n\n"
        f"👤 ФИО ребенка: {name}\n\n"
        f"📸 Пожалуйста, отправьте фотографию или PDF-файл страховки.\n\n"
        f"ℹ️ Страховка будет отправлена администраторам Ксении и Анастасии.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return WAITING_STRAHOVKA

async def receive_strahovka(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение страховки от пользователя"""
    user_id = update.effective_user.id
    user_data = users_db.get(user_id, {})
    name = user_data.get('name', 'Не указано')
    username = user_data.get('username', 'Не указан')
    
    # Проверяем, что отправлено фото или документ
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "Фото"
        send_func = context.bot.send_photo
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "Документ"
        send_func = context.bot.send_document
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте фотографию или PDF-файл страховки.",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU
    
    # Отправляем администраторам
    admin_message = (
        f"🏥 **НОВАЯ СТРАХОВКА**\n\n"
        f"👤 ФИО ребенка: {name}\n"
        f"🆔 Username родителя: @{username}\n"
        f"📎 Тип файла: {file_type}\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Отправляем Ксении и Анастасии
    for admin_key in ['oplata', 'spravka']:
        try:
            await send_func(
                chat_id=ADMINS[admin_key],
                photo=file_id if file_type == "Фото" else None,
                document=file_id if file_type == "Документ" else None,
                caption=admin_message
            )
        except Exception as e:
            logger.error(f"Ошибка отправки страховки администратору {admin_key}: {e}")
    
    await update.message.reply_text(
        "✅ **Страховка получена и отправлена администраторам!**\n\n"
        "Вы получите ответ в ближайшее время.",
        reply_markup=get_main_menu_keyboard()
    )
    
    return MAIN_MENU

async def handle_payment_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик: Вопрос по оплате"""
    await update.message.reply_text(
        "💰 **Вопрос по оплате**\n\n"
        "📝 Напишите ваш вопрос, и он будет отправлен администратору Ксении.\n\n"
        "Вы получите ответ в ближайшее время.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return WAITING_PAYMENT_QUESTION

async def receive_payment_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение вопроса по оплате"""
    user_id = update.effective_user.id
    user_data = users_db.get(user_id, {})
    name = user_data.get('name', 'Не указано')
    username = user_data.get('username', 'Не указан')
    question = update.message.text
    
    # Отправляем администратору
    admin_message = (
        f"💰 **ВОПРОС ПО ОПЛАТЕ**\n\n"
        f"👤 ФИО ребенка: {name}\n"
        f"🆔 Username родителя: @{username}\n\n"
        f"❓ Вопрос:\n{question}\n\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    await notify_admin(context, ADMINS['oplata'], admin_message)
    
    await update.message.reply_text(
        "✅ **Ваш вопрос отправлен администратору Ксении!**\n\n"
        "Вы получите ответ в ближайшее время.",
        reply_markup=get_main_menu_keyboard()
    )
    
    return MAIN_MENU

async def handle_change_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик: Изменить ФИО ребенка"""
    await update.message.reply_text(
        "📝 **Изменение ФИО ребенка**\n\n"
        "Введите новое ФИО ребенка:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return WAITING_NAME

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, admin_id: int, message: str):
    """Отправляет уведомление администратору"""
    try:
        await context.bot.send_message(chat_id=admin_id, text=message)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления администратору {admin_id}: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущей операции"""
    await update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=get_main_menu_keyboard()
    )
    return MAIN_MENU

# ================== ГЛАВНАЯ ФУНКЦИЯ ==================

def main():
    """Запуск бота"""
    logger.info("🚀 Запуск бота...")
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаём ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)
            ],
            MAIN_MENU: [
                MessageHandler(filters.Regex('^📋 Регистрация на Турнир$'), handle_tournament),
                MessageHandler(filters.Regex('^📅 Ближайшие мероприятия$'), handle_events),
                MessageHandler(filters.Regex('^📄 Отправить справку$'), handle_spravka_request),
                MessageHandler(filters.Regex('^🏥 Отправить страховку$'), handle_strahovka_request),
                MessageHandler(filters.Regex('^💰 Вопрос по оплате$'), handle_payment_question),
                MessageHandler(filters.Regex('^👤 Изменить ФИО ребенка$'), handle_change_name),
            ],
            WAITING_SPRAVKA: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_spravka)
            ],
            WAITING_STRAHOVKA: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_strahovka)
            ],
            WAITING_PAYMENT_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_question)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info("Нажмите Ctrl+C для остановки")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
