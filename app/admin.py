from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import app.keyboards as kb
from app.states import AdminStates
from app.database.new_models import db

from dotenv import load_dotenv
import os
load_dotenv()

admin = Router()
ADMIN_IDS = int(os.getenv('ADMIN_ID'))


async def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ПАНЕЛЬ АДМИНИСТРАТОРА
@admin.message(Command("admin"))
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return

    await message.answer(
        "Панель администратора.\nВыберите действие:",
        reply_markup=kb.admin_kb
    )


@admin.callback_query(F.data == "admin_back")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Панель администратора.\nВыберите действие:",
        reply_markup=kb.admin_kb
    )


# УПРАВЛЕНИЕ СТУДИЯМИ
@admin.callback_query(F.data == "manage_studios")
async def manage_studios(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.managing_studios)
    await callback.message.edit_text(
        "Управление студиями:",
        reply_markup=kb.studio_management_kb
    )


@admin.callback_query(F.data == "list_studios")
async def list_studios(callback: CallbackQuery, state: FSMContext):
    studios = await db.pool.fetch("SELECT id, studio_name FROM studios")

    if not studios:
        await callback.message.answer("Студий не найдено")
        return

    await state.update_data(items=studios, index=0, type="studio")
    await show_studio(callback.message, state)


async def show_studio(message: Message, state: FSMContext):
    data = await state.get_data()
    studios = data["items"]
    index = data["index"]

    studio = studios[index]
    studio_id = studio['id']
    name = studio['studio_name']

    studio_data = await db.pool.fetchrow(
        "SELECT rating, review_count FROM studios WHERE id = $1",
        studio_id
    )

    rating = studio_data['rating'] if studio_data else 0
    review_count = studio_data['review_count'] if studio_data else 0

    text = (f"📸 <b>Студия #{studio_id}</b>\n\n"
            f"Название: {name}\n"
            f"Рейтинг: {rating} ⭐\n"
            f"Отзывов: {review_count}\n\n"
            f"{index + 1}/{len(studios)}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить студию", callback_data=f"delete_studio_{studio_id}")],
        *kb.pagination_kb(index, len(studios)).inline_keyboard
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


async def delete_studio_from_db(studio_id: int):
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM portfolio WHERE studio_id = $1", studio_id)
            await conn.execute("DELETE FROM reviews WHERE studio_id = $1", studio_id)
            await conn.execute("DELETE FROM complaints WHERE studio_id = $1", studio_id)
            await conn.execute("DELETE FROM favorites WHERE studio_id = $1", studio_id)
            await conn.execute("DELETE FROM studios WHERE id = $1", studio_id)


@admin.callback_query(F.data.startswith("delete_studio_"))
async def delete_studio_handler(callback: CallbackQuery):
    studio_id = int(callback.data.split("_")[-1])
    await delete_studio_from_db(studio_id)
    await callback.answer(f"Студия #{studio_id} удалена")
    await callback.message.delete()


# УПРАВЛЕНИЕ КЛИЕНТАМИ
@admin.callback_query(F.data == "manage_clients")
async def manage_clients(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.managing_clients)
    await callback.message.edit_text(
        "Управление клиентами:",
        reply_markup=kb.client_management_kb
    )


@admin.callback_query(F.data == "list_clients")
async def list_clients(callback: CallbackQuery, state: FSMContext):
    clients = await db.pool.fetch("SELECT id, name FROM client")

    if not clients:
        await callback.message.answer("Клиентов не найдено")
        return

    await state.update_data(items=clients, index=0, type="client")
    await show_client(callback.message, state)


async def show_client(message: Message, state: FSMContext):
    data = await state.get_data()
    clients = data["items"]
    index = data["index"]

    client = clients[index]
    client_id = client['id']
    name = client['name']

    reviews_count = await db.pool.fetchval(
        "SELECT COUNT(*) FROM reviews WHERE user_id = (SELECT tg_id FROM client WHERE id = $1)",
        client_id
    )

    complaints_count = await db.pool.fetchval(
        "SELECT COUNT(*) FROM complaints WHERE user_id = (SELECT tg_id FROM client WHERE id = $1)",
        client_id
    )

    text = (f"👤 <b>Клиент #{client_id}</b>\n\n"
            f"Имя: {name}\n"
            f"Отзывов: {reviews_count}\n"
            f"Жалоб: {complaints_count}\n\n"
            f"{index + 1}/{len(clients)}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить клиента", callback_data=f"delete_client_{client_id}")],
        *kb.pagination_kb(index, len(clients)).inline_keyboard
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@admin.callback_query(F.data.startswith("delete_client_"))
async def delete_client(callback: CallbackQuery):
    client_id = int(callback.data.split("_")[-1])

    async with db.pool.acquire() as conn:
        async with conn.transaction():
            client_tg_id = await conn.fetchval(
                "SELECT tg_id FROM client WHERE id = $1",
                client_id
            )

            await conn.execute(
                "DELETE FROM favorites WHERE client_id = $1",
                client_tg_id
            )
            await conn.execute(
                "DELETE FROM reviews WHERE user_id = $1",
                client_tg_id
            )
            await conn.execute(
                "DELETE FROM complaints WHERE user_id = $1",
                client_tg_id
            )
            await conn.execute(
                "DELETE FROM client WHERE id = $1",
                client_id
            )

    await callback.answer(f"Клиент #{client_id} удалён")
    await callback.message.delete()


# ПАГИНАЦИЯ
@admin.callback_query(F.data == "prev_item")
async def prev_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data["index"]
    items = data["items"]
    item_type = data["type"]

    if index > 0:
        await state.update_data(index=index - 1)
        await callback.message.delete()

        if item_type == "client":
            await show_client(callback.message, state)
        elif item_type == "studio":
            await show_studio(callback.message, state)
        elif item_type == "complaint":
            await show_complaint(callback.message, state)
        elif item_type == "review":
            await show_review_admin(callback.message, state)


@admin.callback_query(F.data == "next_item")
async def next_item(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data["index"]
    items = data["items"]
    item_type = data["type"]

    if index < len(items) - 1:
        await state.update_data(index=index + 1)
        await callback.message.delete()

        if item_type == "client":
            await show_client(callback.message, state)
        elif item_type == "studio":
            await show_studio(callback.message, state)
        elif item_type == "complaint":
            await show_complaint(callback.message, state)
        elif item_type == "review":
            await show_review_admin(callback.message, state)


# ЖАЛОБЫ
@admin.callback_query(F.data == "view_complains")  # Изменено с manage_complaints на view_complains
async def manage_complaints(callback: CallbackQuery, state: FSMContext):
    complaints = await db.pool.fetch(
        "SELECT id, user_id, studio_id, text, status FROM complaints WHERE status = 'new'"
    )

    if not complaints:
        await callback.message.edit_text("🚨 Новых жалоб нет.")
        return

    await state.update_data(items=complaints, index=0, type="complaint")
    await show_complaint(callback.message, state)


async def show_complaint(message: Message, state: FSMContext):
    data = await state.get_data()
    complaints = data.get("items", [])
    index = data.get("index", 0)

    if not complaints:
        try:
            await message.edit_text("🚨 Все жалобы рассмотрены.")
        except Exception:
            await message.answer("🚨 Все жалобы рассмотрены.")
        return

    complaint = complaints[index]
    comp_id = complaint['id']
    user_id = complaint['user_id']
    studio_id = complaint['studio_id']
    text = complaint['text']
    status = complaint['status']

    # ПОЛУЧЕНИЕ ИНФОРМАЦИИ О СТУДИИ
    studio_info = await db.pool.fetchrow(
        "SELECT studio_name FROM studios WHERE id = $1",
        studio_id
    )
    studio_name = studio_info['studio_name'] if studio_info else "Неизвестная студия"

    complaint_text = (
        f"🚨 <b>Жалоба #{comp_id}</b>\n\n"
        f"👤 Пользователь ID: {user_id}\n"
        f"📸 Студия: {studio_name} (ID: {studio_id})\n"
        f"💬 Текст: {text}\n"
        f"📌 Статус: {status}\n\n"
        f"{index + 1}/{len(complaints)}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_complaint_{comp_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_complaint_{comp_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить студию", callback_data=f"delete_complaint_studio_{studio_id}")],
        [InlineKeyboardButton(text='◀️ Назад меню администратора', callback_data='admin_back')],
        *kb.pagination_kb(index, len(complaints)).inline_keyboard
    ])

    try:
        await message.edit_text(complaint_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await message.answer(complaint_text, reply_markup=keyboard, parse_mode="HTML")


@admin.callback_query(F.data.startswith("approve_complaint_"))
async def approve_complaint(callback: CallbackQuery, state: FSMContext):
    comp_id = int(callback.data.split("_")[-1])

    await db.pool.execute(
        "UPDATE complaints SET status = 'approved' WHERE id = $1",
        comp_id
    )

    data = await state.get_data()
    complaints = [c for c in data.get("items", []) if c['id'] != comp_id]
    await state.update_data(items=complaints)

    await callback.answer("Жалоба одобрена ✅")
    await show_complaint(callback.message, state)


@admin.callback_query(F.data.startswith("reject_complaint_"))
async def reject_complaint(callback: CallbackQuery, state: FSMContext):
    comp_id = int(callback.data.split("_")[-1])

    await db.pool.execute(
        "UPDATE complaints SET status = 'rejected' WHERE id = $1",
        comp_id
    )

    data = await state.get_data()
    complaints = [c for c in data.get("items", []) if c['id'] != comp_id]
    await state.update_data(items=complaints)

    await callback.answer("Жалоба отклонена ❌")
    await show_complaint(callback.message, state)


@admin.callback_query(F.data.startswith("delete_complaint_studio_"))
async def delete_complaint_studio(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[-1])

    # НАХОДИМ ЖАЛОБЬЫ НА СТУДИЮ
    complaints = await db.pool.fetch(
        "SELECT id FROM complaints WHERE studio_id = $1",
        studio_id
    )

    # УДАЛЕНИЕ СТУДИИ И ВСЕХ СВЯЗАННЫХ ДАННЫХ
    await delete_studio_from_db(studio_id)

    # ОБНОВЛЕНИЕ СПИСКА ЖАЛОБ В СОСТОЯНИИ
    data = await state.get_data()
    current_complaints = data.get("items", [])
    updated_complaints = [c for c in current_complaints if c['studio_id'] != studio_id]
    await state.update_data(items=updated_complaints)

    await callback.answer(f"Студия #{studio_id} и все связанные жалобы удалены")
    await show_complaint(callback.message, state)


# ОТЗЫВЫ
@admin.callback_query(F.data == "moderate_reviews")
async def moderate_reviews(callback: CallbackQuery, state: FSMContext):
    reviews = await db.pool.fetch(
        "SELECT id, user_id, studio_id, rating, text FROM reviews ORDER BY id DESC LIMIT 20"
    )

    if not reviews:
        await callback.message.edit_text("💬 Отзывов нет.")
        return

    await state.update_data(items=reviews, index=0, type="review")
    await show_review_admin(callback.message, state)


async def show_review_admin(message: Message, state: FSMContext):
    data = await state.get_data()
    reviews = data["items"]
    index = data["index"]

    review = reviews[index]
    rev_id = review['id']
    user_id = review['user_id']
    studio_id = review['studio_id']
    rating = review['rating']
    text = review['text']

    # ПОЛУЧЕНИЕ ИНФОРМАЦИИ О СТУДИИ
    studio_info = await db.pool.fetchrow(
        "SELECT studio_name FROM studios WHERE id = $1",
        studio_id
    )
    studio_name = studio_info['studio_name'] if studio_info else "Неизвестная студия"

    review_text = (
        f"💬 <b>Отзыв #{rev_id}</b>\n\n"
        f"👤 Пользователь ID: {user_id}\n"
        f"📸 Студия: {studio_name} (ID: {studio_id})\n"
        f"⭐ Оценка: {rating}\n"
        f"Текст: {text}\n\n"
        f"{index + 1}/{len(reviews)}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_review_{rev_id}")],
        [InlineKeyboardButton(text='◀️ Назад в меню администратора', callback_data='admin_back')],
        *kb.pagination_kb(index, len(reviews)).inline_keyboard
    ])

    await message.answer(review_text, reply_markup=keyboard, parse_mode="HTML")


@admin.callback_query(F.data.startswith("delete_review_"))
async def delete_review(callback: CallbackQuery):
    rev_id = int(callback.data.split("_")[-1])

    await db.pool.execute("DELETE FROM reviews WHERE id = $1", rev_id)

    await callback.answer("Отзыв удалён 🗑")
    await callback.message.delete()


# СТАТИСТИКА
@admin.callback_query(F.data == "statistics")
async def show_statistics(callback: CallbackQuery):
    studios_count = await db.pool.fetchval("SELECT COUNT(*) FROM studios")
    clients_count = await db.pool.fetchval("SELECT COUNT(*) FROM client")
    reviews_count = await db.pool.fetchval("SELECT COUNT(*) FROM reviews")
    complaints_count = await db.pool.fetchval("SELECT COUNT(*) FROM complaints")
    active_complaints = await db.pool.fetchval("SELECT COUNT(*) FROM complaints WHERE status = 'new'")

    # ПОЛУЧЕНИЕ СРЕДНЕГО РЕЙТИНГА СТУДИИ
    avg_rating = await db.pool.fetchval("SELECT AVG(rating) FROM studios WHERE rating > 0")

    text = (f"📊 <b>Статистика системы</b>\n\n"
            f"📸 Студий: {studios_count}\n"
            f"👤 Клиентов: {clients_count}\n"
            f"💬 Отзывов: {reviews_count}\n"
            f"⭐ Средний рейтинг: {avg_rating:.2f}\n"
            f"⚠️ Жалоб всего: {complaints_count}\n"
            f"🚨 Активных жалоб: {active_complaints}")

    await callback.message.answer(text, parse_mode="HTML")