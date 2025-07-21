import logging
import requests
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from keyboards.default_keyboards_showme import location_keyboard
from services.get_image_showme import get_image_by_date
from services.user_sessions import update_user_session, get_user_session, check_and_update_session
from keyboards.inline_keyboards_showme import nav_keyboard_universal

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.location, lambda message: get_user_session(message.from_user.id).get("mode") == "showme")
async def handle_location(message: Message):
    user_id = message.from_user.id
    session = get_user_session(user_id)
    logger.info(f"[SHOWME] Received location from user {user_id}. Session: {session}")

    lat = message.location.latitude
    lon = message.location.longitude

    sensor = check_and_update_session(user_id, lat, lon)
    if not sensor:
        logger.warning(f"[SHOWME] No sensor found for user {user_id}.")
        await message.reply("❌ No satellite selected. Please select a sensor first.")
        return

    url, date, sensor_label = get_image_by_date(sensor, lat, lon, current_date_str=None, direction="latest")
    if not url:
        logger.error(f"[SHOWME] Failed to fetch image for user {user_id}, sensor {sensor}.")
        await message.reply(f"❌ Couldn't fetch {sensor} image.")
        return

    update_user_session(user_id, lat, lon, sensor, date)
    logger.info(f"[SHOWME] Sending image to user {user_id} from sensor {sensor_label}.")

    response = requests.get(url)
    photo = BufferedInputFile(response.content, filename=f"{sensor.lower()}.png")

    await message.reply_photo(
        photo=photo,
        caption=f"🛰️ {sensor_label} image\n📅 {date}",
        reply_markup=nav_keyboard_universal(date)
    )

@router.message(F.text.regexp(r'^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$'), lambda message: get_user_session(message.from_user.id).get("mode") == "showme")
async def handle_text_coordinates(message: Message):
    user_id = message.from_user.id
    session = get_user_session(user_id)
    logger.info(f"[SHOWME] Received manual coordinates from user {user_id}. Session: {session}")

    try:
        lat_str, lon_str = map(str.strip, message.text.split(","))
        lat = float(lat_str)
        lon = float(lon_str)

        sensor = check_and_update_session(user_id, lat, lon)
        if not sensor:
            logger.warning(f"[SHOWME] No sensor found for manual coordinates by user {user_id}.")
            await message.reply("❌ No satellite selected. Please select a sensor first.")
            return

        url, date, sensor_label = get_image_by_date(sensor, lat, lon, current_date_str=None, direction="latest")
        if not url:
            logger.error(f"[SHOWME] Couldn't fetch image by manual coordinates for user {user_id}.")
            await message.reply(f"❌ Couldn't fetch {sensor} image for the given coordinates.")
            return

        update_user_session(user_id, lat, lon, sensor, date)
        logger.info(f"[SHOWME] Sending manual coordinates image to user {user_id}, sensor {sensor_label}.")

        response = requests.get(url)
        photo = BufferedInputFile(response.content, filename=f"{sensor.lower()}.png")

        await message.reply_photo(
            photo=photo,
            caption=f"🛰️ {sensor_label} image\n📅 {date}",
            reply_markup=nav_keyboard_universal(date)
        )

    except Exception as e:
        logger.exception(f"[SHOWME] Invalid coordinates format from user {user_id}. Error: {e}")
        await message.reply("❌ Invalid coordinates format. Please send as: `latitude, longitude` (example: `52.5, 13.4`)")
