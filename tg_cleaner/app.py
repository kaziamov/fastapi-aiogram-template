import logging

from aiogram import Bot, Dispatcher, Router, types
from aiogram.methods import DeleteMessage

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from . import settings


app = FastAPI()
webhook_api_router = APIRouter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
messages_bot_router = Router()
TELEGRAM_WEBHOOK_URL = f"{settings.WEBHOOK_URL}/webhook"

logger = logging.getLogger(__name__)


@app.post("/webhook")
async def telegram_webhook(request: dict):
    update = types.Update(**request)
    await dp.feed_update(bot=bot, update=update)


async def register_webhook():
    await bot.set_webhook(url=TELEGRAM_WEBHOOK_URL)
    logger.info(f"""Webhook registered {TELEGRAM_WEBHOOK_URL}""")
    webhook_info = await bot.get_webhook_info()
    logger.info(f"""Webhook info: {webhook_info}""")


def delete_messages_filter(message: types.Message):
    if message.chat.type == "private":
        logger.debug("delete_messages_filter: Private chat")
        return False
    if hasattr(message, "new_chat_participant"):
        if message.new_chat_participant:
            logger.debug("delete_messages_filter: New chat participant")
            return True
    if hasattr(message, "left_chat_participant"):
        if message.left_chat_participant:
            logger.debug("delete_messages_filter: Left chat participant")
            return True
    if hasattr(message, "pinned_message"):
        if message.pinned_message:
            logger.debug("delete_messages_filter: Pinned message")
            return True
    return False

@messages_bot_router.message()
async def delete_messages_handler(message: types.Message):
    if message.chat.id not in settings.CHATS_TO_CLEAN:
        logger.debug(f"From {message.chat.id} not allowed chat {settings.CHATS_TO_CLEAN}")
        return
    if not delete_messages_filter(message):
        logger.debug("Message delete function skipped")
        return
    try:
        await bot(DeleteMessage(chat_id=message.chat, message_id=message.message_id))
        logger.debug("Message DELETED")
    except:
        return


@app.on_event("startup")
async def on_startup():
    logger.info("Starting up actions")
    await register_webhook()
    dp.include_router(messages_bot_router)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()