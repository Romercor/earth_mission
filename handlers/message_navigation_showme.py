from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, BufferedInputFile
from services.get_image_showme import get_image_by_date
from services.user_sessions import update_user_session
from keyboards.inline_keyboards_showme import nav_keyboard_universal
import requests
import logging

router = Router()

@router.callback_query(F.data.startswith("nav_universal:"))
async def navigate_universal_callback_handler(callback_query: CallbackQuery):
    direction = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    from services.user_sessions import get_user_session
    session = get_user_session(user_id)
    if not session:
        await callback_query.answer("No session data found.")
        return

    lat = session["lat"]
    lon = session["lon"]
    sensor = session["sensor"]
    current_date = session["current_date"]

    logging.info("About to call get_image_by_date...")
    loading_message = await callback_query.message.answer("📷 Loading satellite image, please wait...")
    try:
        try:
            url, new_date, sensor_label = get_image_by_date(sensor, lat, lon, current_date, direction)
        except:
            await callback_query.answer("No image found in this direction.")
        logging.info(f"Returned: url={url}, date={new_date}")
        if not url or not new_date:
            await callback_query.answer("No image found in this direction.")
            return

        response = requests.get(url)
        photo = BufferedInputFile(response.content, filename=f"{sensor.lower()}.png")
        update_user_session(user_id, lat, lon, sensor, new_date)
        await callback_query.message.edit_media(
            InputMediaPhoto(media=photo, caption=f"🛰️ {sensor_label} image\n📅 {new_date}"),
            reply_markup=nav_keyboard_universal(new_date)
        )
    finally:
        await loading_message.delete()

    await callback_query.answer()
