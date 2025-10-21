import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from linkedin_agent import LinkedInAgent

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация агента
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "mock_token_test_mode")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "").split(",")

# Проверяем тестовый режим
IS_TEST_MODE = LINKEDIN_ACCESS_TOKEN in ["mock_token_test_mode", "test_mode", "mock"]

if IS_TEST_MODE:
    logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ: LinkedIn публикация отключена")
else:
    logger.info("✅ PROD РЕЖИМ: LinkedIn публикация включена")

# Создаем агента
agent = LinkedInAgent(
    ANTHROPIC_API_KEY,
    LINKEDIN_ACCESS_TOKEN,
    industry="product management",
    target_audience="Product Managers, Directors of Product, Product Leads"
)


def check_access(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ"""
    if not ALLOWED_USERS or ALLOWED_USERS[0] == "":
        return True
    return str(user_id) in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    if not check_access(user_id):
        await update.message.reply_text(
            "❌ У вас нет доступа к этому боту.\n"
            f"Ваш ID: {user_id}\n"
            "Свяжитесь с администратором."
        )
        return
    
    mode_status = "🧪 ТЕСТОВЫЙ РЕЖИМ" if IS_TEST_MODE else "✅ PROD РЕЖИМ"
    
    welcome_message = f"""
👋 Привет, {user.first_name}!

Я - LinkedIn Content Agent для продакт менеджеров.

{mode_status}
{"⚠️ LinkedIn публикация ОТКЛЮЧЕНА (показываю посты для копирования)" if IS_TEST_MODE else "✅ LinkedIn публикация ВКЛЮЧЕНА"}

🎯 Что я умею:
- Мониторить актуальные тренды из Mind the Product, Reddit, Hacker News
- Создавать посты специально для PM аудитории
- Анализировать что обсуждает product community
{"• Показывать готовые посты (вы копируете вручную)" if IS_TEST_MODE else "• Публиковать посты в LinkedIn"}

📝 Команды:
/trends - Показать актуальные тренды
/create - Создать пост на актуальную тему
/analyze [тема] - Проверить актуальность темы
/sources - Показать источники данных
/help - Помощь

💬 Или просто напишите что хотите:
"Найди горячую тему и создай пост"
"Что обсуждают PM на этой неделе?"
"""
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = f"""
🤖 Доступные команды:

/start - Начать работу
/trends - Показать актуальные product тренды
/create - Создать пост
/analyze [тема] - Проверить актуальность темы
/sources - Показать источники данных
/reset - Сбросить историю диалога
/help - Эта справка

📝 Примеры запросов:
- "Что сейчас обсуждают на r/ProductManagement?"
- "Создай пост про AI в product discovery"
- "Дай топ-3 тренда недели для PM"
- "Проверь актуальность темы retention metrics"

{'🧪 ТЕСТОВЫЙ РЕЖИМ: Посты будут показаны для ручного копирования' if IS_TEST_MODE else '✅ PROD: Посты публикуются автоматически'}
"""
    await update.message.reply_text(help_text)


async def trends_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для показа актуальных трендов"""
    user_id = update.effective_user.id
    
    if not check_access(user_id):
        await update.message.reply_text("❌ Нет доступа")
        return
    
    await update.message.reply_text("🔍 Ищу актуальные тренды для PM... Это может занять минуту.")
    
    try:
        response = agent.chat(
            "Покажи топ-5 самых актуальных трендов для продакт менеджеров "
            "прямо сейчас. Используй get_product_trends и кратко опиши каждый тренд."
        )
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in trends command: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для создания поста"""
    user_id = update.effective_user.id
    
    if not check_access(user_id):
        await update.message.reply_text("❌ Нет доступа")
        return
    
    if IS_TEST_MODE:
        await update.message.reply_text(
            "✍️ Создаю пост на актуальную тему...\n"
            "🧪 Тестовый режим: покажу пост для ручного копирования\n"
            "⏱️ Займёт 1-2 минуты."
        )
    else:
        await update.message.reply_text(
            "✍️ Создаю пост на актуальную тему...\n"
            "⏱️ Займёт 1-2 минуты."
        )
    
    try:
        if IS_TEST_MODE:
            response = agent.chat(
                "Найди самую актуальную и обсуждаемую тему для продакт менеджеров. "
                "Создай вовлекающий пост в стиле для PM аудитории с практическими советами. "
                "Покажи готовый пост в формате для копирования в LinkedIn. "
                "НЕ вызывай функцию create_linkedin_post - я в тестовом режиме."
            )
        else:
            response = agent.chat(
                "Найди самую актуальную и обсуждаемую тему для продакт менеджеров. "
                "Создай вовлекающий пост в стиле для PM аудитории с практическими советами. "
                "Покажи мне пост для подтверждения перед публикацией."
            )
        
        # Разбиваем длинные сообщения
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(response)
        
        if IS_TEST_MODE:
            await update.message.reply_text(
                "\n📋 ГОТОВО!\n"
                "Скопируйте пост выше и опубликуйте вручную в LinkedIn.\n\n"
                "💡 Чтобы включить автопубликацию:\n"
                "1. Получите LinkedIn Access Token\n"
                "2. Обновите LINKEDIN_ACCESS_TOKEN на Render"
            )
            
    except Exception as e:
        logger.error(f"Error in create command: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для анализа темы"""
    user_id = update.effective_user.id
    
    if not check_access(user_id):
        await update.message.reply_text("❌ Нет доступа")
        return
    
    topic = " ".join(context.args) if context.args else None
    
    if not topic:
        await update.message.reply_text(
            "❓ Укажите тему для анализа.\n"
            "Пример: /analyze AI в product discovery"
        )
        return
    
    await update.message.reply_text(f"🔍 Анализирую актуальность темы: '{topic}'...")
    
    try:
        response = agent.chat(
            f"Проверь насколько актуальна тема '{topic}' для продакт менеджеров прямо сейчас. "
            f"Используй веб-поиск и product источники. Дай оценку и рекомендацию."
        )
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает источники данных"""
    sources_text = """
📡 Источники актуальных трендов:

📰 RSS Фиды:
- Mind the Product
- Product Coalition (Medium)
- Product Talk
- Intercom Blog
- Lenny's Newsletter

💬 Reddit Communities:
- r/ProductManagement
- r/product_design
- r/SaaS
- r/startups
- r/userexperience

🔥 Hacker News:
- Топовые tech обсуждения
- Product-related темы

🌐 Web Search:
- Claude встроенный поиск
- Актуальные новости

Все источники - БЕСПЛАТНЫЕ! 🎉
"""
    await update.message.reply_text(sources_text)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сброс истории диалога"""
    agent.conversation_history = []
    await update.message.reply_text(
        "🔄 История диалога сброшена!\n"
        "Начинаем с чистого листа."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    
    if not check_access(user_id):
        await update.message.reply_text(
            f"❌ Нет доступа. Ваш ID: {user_id}"
        )
        return
    
    user_message = update.message.text
    
    await update.message.chat.send_action(action="typing")
    
    try:
        logger.info(f"User {user_id}: {user_message}")
        
        # Добавляем контекст о тестовом режиме
        if IS_TEST_MODE and any(word in user_message.lower() for word in ['опубликуй', 'publish', 'пост']):
            context_message = user_message + "\n\n(Я в тестовом режиме - НЕ вызывай create_linkedin_post, просто покажи готовый пост)"
        else:
            context_message = user_message
        
        response = agent.chat(context_message)
        
        logger.info(f"Agent response length: {len(response)}")
        
        # Разбиваем длинные сообщения
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(response)
        
        # Напоминание о тестовом режиме при упоминании публикации
        if IS_TEST_MODE and any(word in user_message.lower() for word in ['опубликуй', 'publish']):
            await update.message.reply_text(
                "\n💡 Напоминание: Вы в тестовом режиме.\n"
                "Посты нужно копировать и публиковать вручную."
            )
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Произошла ошибка: {str(e)}\n\n"
            "Попробуйте:\n"
            "• Переформулировать запрос\n"
            "• Использовать команду /reset\n"
            "• Связаться с администратором"
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


def main() -> None:
    """Запуск бота"""
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("❌ ANTHROPIC_API_KEY не установлен!")
        return
    
    logger.info("=" * 60)
    logger.info("🚀 Запуск LinkedIn Agent Telegram Bot")
    logger.info(f"{'🧪 Режим: ТЕСТОВЫЙ (mock token)' if IS_TEST_MODE else '✅ Режим: PRODUCTION'}")
    logger.info("=" * 60)
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("trends", trends_command))
    application.add_handler(CommandHandler("create", create_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("sources", sources_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Бот запущен и готов к работе!")
    if IS_TEST_MODE:
        logger.info("🧪 LinkedIn публикация ОТКЛЮЧЕНА - показываются только готовые посты")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
