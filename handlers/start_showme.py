import logging
from aiogram import Router, F
from aiogram.types import Message
from keyboards.start_keyboards import start_keyboard, main_keyboard
from keyboards.default_keyboards_showme import sensor_keyboard
from services.user_sessions import init_mode_session, get_user_session

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "/start")
async def send_welcome(message: Message):
    user_id = message.from_user.id
    logger.info(f"[START] User {user_id} started bot (/start)")
    await message.answer(
        "🌍 Hi! I am an analysing bot to help you understand more about the place where you live!",
        reply_markup=main_keyboard
    )

@router.message(F.text == "🏠 Main Menu")
async def back_main(message: Message):
    user_id = message.from_user.id
    logger.info(f"[MAIN MENU] User {user_id} returned to main menu")
    await message.answer("Welcome back, traveller!", reply_markup=main_keyboard)

@router.message(F.text == "🗺️ Show me!")
async def show_me_handler(message: Message):
    user_id = message.from_user.id
    init_mode_session(user_id, "showme")
    session = get_user_session(user_id)
    logger.info(f"[SHOW ME] User {user_id} selected 'Show me' mode. Session: {session}")
    await message.answer("Please select the desired satellite", reply_markup=sensor_keyboard)

