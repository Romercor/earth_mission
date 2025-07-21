from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def nav_keyboard_universal(current_date):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Previous", callback_data="nav_universal:previous"),
            InlineKeyboardButton(text="Next ➡️", callback_data="nav_universal:next")
        ],
        [
            InlineKeyboardButton(text="Latest", callback_data="nav_universal:latest")
        ]
    ])
