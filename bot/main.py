import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")
    telegram_bot_token: str


settings = Settings()

logging.basicConfig(level=logging.INFO)

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
        parse_mode="Markdown"
    )


@dp.message(F.text)
async def handle_message(message: Message):
    thinking = await message.answer("🔍 Анализирую, подожди...")

    try:
        from agent import analyze
        response = await analyze(message.text, message.from_user.id)
        await thinking.delete()
        await message.answer(response, parse_mode="Markdown")
    except Exception as e:
        await thinking.delete()
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Что-то пошло не так, попробуй ещё раз")


# @dp.message(F.text)
# async def handle_message(message: Message):
#     thinking = await message.answer("🔍 Анализирую, подожди...")
#     try:
#         from agent import analyze_stream
#         stream = await analyze_stream(message.text)
#         if stream is None:
#             await thinking.delete()
#             await message.answer("❌ Я финансовый аналитик и могу помочь только с анализом акций, облигаций и инвестиций.")
#             return
#         await thinking.delete()
#         sent = await message.answer("...")
#         current_text = ""
#         async for event in stream.stream_events():
#             if event.type == "raw_response_event":
#                 delta = getattr(event.data, "delta", None)
#                 if delta:
#                     current_text += delta
#                     if len(current_text) % 100 < 5:
#                         try:
#                             await sent.edit_text(current_text)
#                         except Exception:
#                             pass
#         if current_text:
#             await sent.edit_text(current_text, parse_mode="Markdown")
#     except Exception as e:
#         await thinking.delete()
#         logging.error(f"Ошибка: {e}")
#         await message.answer("❌ Что-то пошло не так, попробуй ещё раз")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())