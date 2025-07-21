import logging
from aiogram import Router, F
from aiogram.types import Message
from keyboards.default_keyboards_showme import sensor_keyboard, location_keyboard
from services.user_sessions import update_user_session, get_user_session, check_and_update_session, init_user_session

router = Router()
logger = logging.getLogger(__name__)

@router.message(lambda message: message.text in [
    "Sentinel 2 (EU - ESA)", "Landsat 8 (US - NASA)", "Landsat 9 (US - NASA)"
])
async def sensor_choice(message: Message):
    user_id = message.from_user.id
    session = get_user_session(user_id)
    logger.info(f"[SENSOR CHOICE] User {user_id} current session: {session}")

    sensor = message.text.split('(')[0].strip()
    init_user_session(user_id, sensor)

    updated_session = get_user_session(user_id)
    logger.info(f"[SENSOR CHOICE] User {user_id} selected sensor: {sensor}. Updated session: {updated_session}")

    await message.answer(
        f"You've selected {sensor}.\n\nPlease share your location in one of the following ways:\n\n"
        "1. 📍 By using the Telegram location button\n"
        "2. 📝 By sending coordinates in text format: latitude, longitude (for example: 48.8584, 2.2945)",
        reply_markup=location_keyboard
    )

@router.message(F.text == "🔙 Change Satellite")
async def change_satellite(message: Message):
    logger.info(f"[CHANGE SATELLITE] User {message.from_user.id} requested to change satellite.")
    await message.answer(
        "Please select the desired satellite",
        reply_markup=sensor_keyboard
    )