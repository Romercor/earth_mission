from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

location_keyboard= ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Share Location", request_location=True)],
        [KeyboardButton(text="🏠 Main Menu")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)