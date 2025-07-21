import logging
from aiogram import Router, F
from aiogram.types import Message
from keyboards.start_keyboards import main_keyboard
from keyboards.default_keyboards_timetravelling import location_keyboard
from services.user_sessions import init_mode_session

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "🕰️ Time travelling")
async def start_time_travelling(message: Message):
    user_id = message.from_user.id
    init_mode_session(user_id, "timetravelling")
    from services.user_sessions import get_user_session
    session = get_user_session(user_id)
    logger.info(f"[TIME TRAVELLING] User {user_id} selected 'Time travelling' mode. Session: {session}")
    
    await message.answer(
        "Welcome to Time travelling mode! 🚀\n\nPlease share your location in one of the following ways:\n\n"
        "1. 📍 By using the Telegram location button\n"
        "2. 📝 By sending coordinates in text format: latitude, longitude (for example: 48.8584, 2.2945)",
        reply_markup=location_keyboard
    )