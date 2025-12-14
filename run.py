import os
from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
from aiogram import Bot, Dispatcher
from app.register import register
from app.client import client
from app.studio import studio
from app.admin import admin
from app.database.new_models import  db


async def main():

    bot = Bot(token=os.getenv('TG_TOKEN'))
    dp =  Dispatcher()
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)
    dp.include_routers(register, client, studio, admin)

    await dp.start_polling(bot)


async def startup(dispatcher: Dispatcher):
    await db.connect()
    await db.init_db()
    print("Бот запущен...!")

async def shutdown(dispatcher: Dispatcher):
    await db.close()
    print("Бот остановлен...!")

if __name__ == '__main__':
    try:
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass



