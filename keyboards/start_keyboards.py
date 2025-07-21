from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="/start")]],
    resize_keyboard=True
)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Show me!")],
        [KeyboardButton(text="🕰️ Time travelling")] 
    ],
    resize_keyboard=True
)