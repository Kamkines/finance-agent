import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from agent import analyze, reset_session


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")
    telegram_bot_token: str


settings = Settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я твой личный финансовый аналитик 📊\n\n"
        "Просто напиши мне про любую акцию или облигацию:\n"
        "• _Проанализируй акцию Сбербанка_\n"
        "• _Стоит ли покупать ОФЗ 26238?_\n"
        "• _Что думаешь про Apple?_",
        parse_mode="Markdown",
    )


MAX_MSG_LEN = 4096


async def send_long_message(message: Message, text: str) -> None:
    for i in range(0, len(text), MAX_MSG_LEN):
        await message.answer(text[i : i + MAX_MSG_LEN], parse_mode="Markdown")


@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    await reset_session(message.from_user.id)
    await message.answer("🔄 История диалога очищена. Начнём заново!")


@dp.message(F.text)
async def handle_message(message: Message):
    thinking = await message.answer("🔍 Анализирую, подожди...")
    try:
        response = await analyze(message.text, message.from_user.id)
        await thinking.delete()
        await send_long_message(message, response)
    except Exception as e:
        await thinking.delete()
        logging.error("Ошибка при обработке сообщения: %s", e)
        await message.answer("❌ Что-то пошло не так, попробуй ещё раз")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())