import asyncpg
from dotenv import load_dotenv
import os
load_dotenv()


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),  # обязательно привести к int
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}


# ФУНКЦИЯ ДЛЯ СОЗДАНИЯ ТАБЛИЦ
class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(**DB_CONFIG)

    async def close(self):
        if self.pool:
            await self.pool.close()


    async def init_db(self):
        conn = await asyncpg.connect(**DB_CONFIG)

        await conn.execute('''
        CREATE TABLE IF NOT  EXISTS client (
            id BIGSERIAL PRIMARY KEY,
            tg_id BIGINT UNIQUE NOT NULL,
            name TEXT,
            phone TEXT
            )
        ''')

        await conn.execute('''
        CREATE TABLE IF NOT EXISTS studios (
            id BIGSERIAL PRIMARY KEY,
            tg_id BIGINT UNIQUE NOT NULL,
            studio_name TEXT NOT NULL,
            description TEXT,
            contact_data TEXT,
            shoot_type TEXT,
            rating REAL DEFAULT 0,
            review_count INTEGER DEFAULT 0
            )
         ''')

        await  conn.execute('''CREATE TABLE IF NOT EXISTS portfolio(
            id BIGSERIAL PRIMARY KEY,
            studio_id BIGINT REFERENCES studios(id) ON DELETE CASCADE,
            file_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            description TEXT            
            )
        ''')

        await conn.execute('''CREATE TABLE IF NOT EXISTS reviews(
             id BIGSERIAL PRIMARY KEY,
             studio_id BIGINT REFERENCES studios(id) ON DELETE CASCADE,
             user_id BIGINT NOT NULL,
             text TEXT,
             rating INTEGER,
             file_id TEXT,
             is_visible INTEGER DEFAULT 0,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await conn.execute(''' CREATE TABLE IF NOT EXISTS complaints (
            id BIGSERIAL PRIMARY KEY,
            studio_id BIGINT REFERENCES studios(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'new'
            )
        ''')

        await conn.execute('''CREATE TABLE IF NOT EXISTS favorites(
            id BIGSERIAL PRIMARY KEY,
            client_id BIGINT NOT NULL,
            studio_id BIGINT NOT NULL,
            UNIQUE(client_id, studio_id),
            FOREIGN KEY (client_id) REFERENCES client(id) ON DELETE CASCADE,
            FOREIGN KEY (studio_id) REFERENCES studios(id) ON DELETE CASCADE
            )
        ''')


    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

db = Database()


