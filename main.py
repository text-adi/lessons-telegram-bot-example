import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

TOKEN = getenv("BOT_TOKEN")
USE_WEBHOOK = getenv("USE_WEBHOOK", "false").lower() == "true"

# Налаштування для Webhook
WEBHOOK_HOST = getenv("WEBHOOK_HOST", "https://your-domain.com")
WEBHOOK_PATH = getenv("WEBHOOK_PATH", "/webhook")
WEBAPP_HOST = getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(getenv("WEBAPP_PORT", 8000))

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# Реєстрація базового хендлера
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обробник команди /start"""
    await message.answer(f"Привіт, {html.quote(message.from_user.full_name)}! Бот успішно запущений.")

@dp.message()
async def something(message: Message) -> None:
    await message.answer(message.text)

async def on_startup(bot: Bot) -> None:
    """Дії при запуску (встановлення вебхука)"""
    if USE_WEBHOOK:
        webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
        await bot.set_webhook(webhook_url)
        logging.info(f"Вебхук встановлено: {webhook_url}")


async def main() -> None:
    """Головна функція для запуску бота"""
    # Налаштування логування
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if USE_WEBHOOK:
        # --- ЗАПУСК ЧЕРЕЗ WEBHOOK (Aiohttp) ---
        logging.info("Запуск бота в режимі Webhook...")
        
        app = web.Application()
        
        # Реєстрація події запуску для встановлення webhook
        app.on_startup.append(lambda a: on_startup(bot))
        
        # Реєстрація обробника запитів від Telegram
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        
        # Налаштування додатка aiohttp
        setup_application(app, dp, bot=bot)
        
        # Запуск серверну
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
        await site.start()
        
        logging.info(f"Сервер запущено на http://{WEBAPP_HOST}:{WEBAPP_PORT}")
        
        # Утримуємо асинхронний цикл живим
        await asyncio.Event().wait()
    else:
        # --- ЗАПУСК ЧЕРЕЗ POLLING ---
        logging.info("Запуск бота в режимі Polling...")
        # Видаляємо вебхук перед запуском polling, щоб уникнути конфліктів
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинений!")
