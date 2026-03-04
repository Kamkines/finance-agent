import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str

    class Config:
        env_file = ".env"


settings = Settings()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher() # оркестратор, для вход сообщений

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я твой личный финансовый аналитик 📊\n\n"
        "Просто напиши мне про любую акцию или облигацию:\n"
        "• _Проанализируй акцию Сбербанка_\n"
        "• _Стоит ли покупать ОФЗ 26238?_\n"
        "• _Что думаешь про Apple?_",
        parse_mode="Markdown"
    )


@dp.message(F.text)
async def handle_message(message: Message):
    # Показываем что думаем
    thinking = await message.answer("🔍 Анализирую, подожди...")

    try:
        from agent import analyze
        response = await analyze(message.text)
        await thinking.delete()
        await message.answer(response, parse_mode="Markdown")
    except Exception as e:
        await thinking.delete()
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Что-то пошло не так, попробуй ещё раз")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())