import logging
from aiogram import Router, F
from aiogram.types import Message
from services.user_sessions import init_timetravelling_location, get_user_session

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.location, lambda message: get_user_session(message.from_user.id).get("mode") == "timetravelling")
async def handle_location_timetravelling(message: Message):
    user_id = message.from_user.id
    session = get_user_session(user_id)
    logger.info(f"[TIMETRAVELLING] Received location from user {user_id}. Session: {session}")

    if not session or session.get("mode") != "timetravelling":
        logger.warning(f"[TIMETRAVELLING] Location received, but user {user_id} not in 'timetravelling' mode.")
        return

    lat = message.location.latitude
    lon = message.location.longitude

    init_timetravelling_location(user_id, lat, lon)
    logger.info(f"[TIMETRAVELLING] Saved location (lat={lat}, lon={lon}) for user {user_id}.")

    await message.answer("✅ Location received!\nNow please select the time range 📅.")

@router.message(F.text.regexp(r'^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$'), lambda message: get_user_session(message.from_user.id).get("mode") == "timetravelling")
async def handle_text_coordinates_timetravelling(message: Message):
    user_id = message.from_user.id
    session = get_user_session(user_id)
    logger.info(f"[TIMETRAVELLING] Received manual coordinates from user {user_id}. Session: {session}")

    if not session or session.get("mode") != "timetravelling":
        logger.warning(f"[TIMETRAVELLING] Manual coordinates received, but user {user_id} not in 'timetravelling' mode.")
        return

    try:
        lat_str, lon_str = map(str.strip, message.text.split(","))
        lat = float(lat_str)
        lon = float(lon_str)

        init_timetravelling_location(user_id, lat, lon)
        logger.info(f"[TIMETRAVELLING] Saved manual coordinates (lat={lat}, lon={lon}) for user {user_id}.")

        await message.answer("✅ Coordinates received!\nNow please select the time range 📅.")

    except Exception as e:
        logger.exception(f"[TIMETRAVELLING] Invalid manual coordinates format from user {user_id}. Error: {e}")
        await message.answer(
            "❌ Invalid format. Please send coordinates like: `latitude, longitude`.\nExample: `48.8584, 2.2945`"
        )
