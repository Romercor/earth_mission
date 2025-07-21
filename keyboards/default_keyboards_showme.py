from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

sensor_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Sentinel 2 (EU - ESA)")],
        [KeyboardButton(text="Landsat 8 (US - NASA)")],
        [KeyboardButton(text="Landsat 9 (US - NASA)")],
        [KeyboardButton(text="🏠 Main Menu")]
    ],
    resize_keyboard=True
)

location_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Share Location", request_location=True)],
        [KeyboardButton(text="🔙 Change Satellite")],
        [KeyboardButton(text="🏠 Main Menu")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
