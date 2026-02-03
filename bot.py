import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

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
    "agnia": "1481715825"        # Агния - другие вопросы
}

# База данных пользователей (упрощённая - в памяти)
users_db = {}

# Состояния для ConversationHandler
ASKING_CHILD_NAME, ASKING_QUESTION, UPLOADING_SPRAVKA, ASKING_PAYMENT_QUESTION = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с обновлённым меню"""
    user = update.effective_user
    
    # Приветственное сообщение
    welcome_text = (
        f"Здравствуйте, {user.first_name}! 👋\n\n"
        f"Добро пожаловать в бот школы тхэквондо «Достижение»!\n\n"
        f"Выберите нужный раздел:"
    )
    
    # Обновлённые кнопки меню
    keyboard = [
        [KeyboardButton("❓ Свой вопрос")],
        [KeyboardButton("📅 Ближайшие мероприятия")],
        [KeyboardButton("📄 Отправить справку/страховку")],
        [KeyboardButton("💰 Вопрос по оплате")],
        [KeyboardButton("✏️ Изменить ФИО ребёнка")]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    return ConversationHandler.END


async def handle_own_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Свой вопрос' - отправляет вопрос Агнии"""
    await update.message.reply_text(
        "Напишите ваш вопрос, и я передам его администратору Агнии.\n\n"
        "Пожалуйста, опишите ваш вопрос подробно."
    )
    return ASKING_QUESTION


async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение вопроса и отправка Агнии"""
    user = update.effective_user
    question_text = update.message.text
    child_name = users_db.get(user.id, "Не указано")
    
    # Формируем сообщение для админа Агнии
    message = (
        f"❓ НОВЫЙ ВОПРОС\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}\n\n"
        f"Вопрос:\n{question_text}"
    )
    
    # Отправляем Агнии
    admin_id = ADMINS.get("agnia")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
            await update.message.reply_text(
                "✅ Ваш вопрос отправлен администратору Агнии!\n"
                "Ожидайте ответа."
            )
            logger.info(f"Вопрос от {user.id} отправлен Агнии ({admin_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки вопроса Агнии: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при отправке. Попробуйте позже или свяжитесь напрямую."
            )
    else:
        await update.message.reply_text(
            "⚠️ Администратор не настроен. Обратитесь к разработчику бота."
        )
    
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
    child_name = users_db.get(user.id, "Не указано")
    
    # Формируем сообщение для админа
    message = (
        f"📄 НОВАЯ СПРАВКА/СТРАХОВКА\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}"
    )
    
    # Отправляем Анастасии (справки/страховки)
    admin_id = ADMINS.get("anastasia")
    if admin_id:
        try:
            # Отправляем текст
            await context.bot.send_message(chat_id=admin_id, text=message)
            
            # Отправляем файл
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
    else:
        await update.message.reply_text(
            "⚠️ Администратор не настроен. Обратитесь к разработчику бота."
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
    child_name = users_db.get(user.id, "Не указано")
    
    # Формируем сообщение
    message = (
        f"💰 ВОПРОС ПО ОПЛАТЕ\n\n"
        f"От: {user.full_name} (@{user.username or 'без username'})\n"
        f"ID: {user.id}\n"
        f"Ребёнок: {child_name}\n\n"
        f"Вопрос:\n{question_text}"
    )
    
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
    else:
        await update.message.reply_text(
            "⚠️ Администратор не настроен. Обратитесь к разработчику бота."
        )
    
    return ConversationHandler.END


async def handle_change_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Изменить ФИО ребёнка'"""
    user = update.effective_user
    current_name = users_db.get(user.id, "Не указано")
    
    await update.message.reply_text(
        f"Текущее ФИО ребёнка: {current_name}\n\n"
        f"Введите новое ФИО ребёнка:"
    )
    return ASKING_CHILD_NAME


async def save_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение ФИО ребёнка"""
    user = update.effective_user
    child_name = update.message.text
    
    # Сохраняем в базу
    users_db[user.id] = child_name
    
    await update.message.reply_text(
        f"✅ ФИО ребёнка сохранено: {child_name}\n\n"
        f"Выберите нужный раздел из меню."
    )
    
    logger.info(f"Пользователь {user.id} сохранил ФИО ребёнка: {child_name}")
    
    return ConversationHandler.END


async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Ближайшие мероприятия'"""
    # Здесь можно загрузить данные из файла events.json
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


def main():
    """Запуск бота"""
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для всех диалогов
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^❓ Свой вопрос$"), handle_own_question),
            MessageHandler(filters.Regex("^📄 Отправить справку/страховку$"), handle_spravka_request),
            MessageHandler(filters.Regex("^💰 Вопрос по оплате$"), handle_payment_question),
            MessageHandler(filters.Regex("^✏️ Изменить ФИО ребёнка$"), handle_change_child_name),
            MessageHandler(filters.Regex("^📅 Ближайшие мероприятия$"), handle_events),
        ],
        states={
            ASKING_CHILD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_child_name)],
            ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)],
            UPLOADING_SPRAVKA: [MessageHandler(filters.PHOTO | filters.Document.ALL, handle_spravka_upload)],
            ASKING_PAYMENT_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_question)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    
    # Запускаем бота
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info(f"Администраторы настроены:")
    logger.info(f"  - Агния (вопросы): {ADMINS['agnia']}")
    logger.info(f"  - Анастасия (справки): {ADMINS['anastasia']}")
    logger.info(f"  - Ксения (оплата): {ADMINS['ksenia']}")
    logger.info(f"  - Людмила (резерв): {ADMINS['lyudmila']}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
