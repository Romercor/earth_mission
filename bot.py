import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from handlers import start_showme, sensor_choice_showme, get_location_showme, message_navigation_showme
from services.init import init_earth_engine
from handlers import start_timetravelling, get_location_timetravelling
from handlers import personalized_locations
import logging
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
### router registration ###
dp.include_router(start_showme.router)
dp.include_router(sensor_choice_showme.router)
dp.include_router(get_location_showme.router)
dp.include_router(message_navigation_showme.router)
dp.include_router(start_timetravelling.router)
dp.include_router(get_location_timetravelling.router)
dp.include_router(personalized_locations.router)
async def main():
    init_earth_engine()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
