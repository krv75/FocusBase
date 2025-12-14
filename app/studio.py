import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from aiogram.filters import Command
from aiogram.enums import ChatAction
from app.database.new_models import db
import app.keyboards as kb
from app.states import UploadContent, EditStudio, EditPortfolio, PortfolioPagination, StudioReviews

studio = Router()


@studio.message(Command('studio_menu'))
async def cmd_studio_menu(message: Message):
    await message.answer("Выберите интересующий Вас пункт меню:", reply_markup=kb.studio_kb)


@studio.callback_query(F.data == 'studio_menu')
async def back_studio_menu(callback: CallbackQuery):
    await callback.message.answer("Выберите интересующий Вас пункт меню:", reply_markup=kb.studio_kb)


@studio.callback_query(F.data == 'upload')
async def start_upload(callback: CallbackQuery, state: FSMContext):
    await callback.bot.send_chat_action(chat_id=callback.from_user.id, action=ChatAction.TYPING)
    await asyncio.sleep(1)
    await callback.message.edit_text("Отправьте фото или видео для загрузки.\n "
                                     "Файлы следует добавлять по одному.\n\n"
                                     "Либо нажмите кнопку назад для перехода в меню фотостудии.", reply_markup=kb.back_studio_menu)
    await state.set_state(UploadContent.waiting_for_file)


@studio.message(UploadContent.waiting_for_file)
async def receive_file(message: Message, state: FSMContext):
    file_id = None
    file_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'
    else:
        await message.answer("Пожалуйста отправьте фото или видео")
        return

    await state.update_data(file_id=file_id,file_type=file_type)
    await state.set_state(UploadContent.waiting_for_description)
    await message.answer("Добавьте описание к этому файлу")


@studio.message(UploadContent.waiting_for_description)
async def save_file(message: Message, state: FSMContext):
    description = message.text
    data = await state.get_data()

    await db.pool.fetchrow('''
            INSERT INTO portfolio (studio_id, file_id, file_type, description)
            VALUES ((SELECT id FROM studios WHERE tg_id = $1), $2, $3, $4)''',
            message.from_user.id,
            data['file_id'],
            data['file_type'],
            description)

    await message.answer("Файл успешно загружен!", reply_markup=kb.back_upload)
    await state.clear()


# РЕДАКТИРОВАНИЕ ПРОФИЛЯ
@studio.callback_query(F.data == "edit_profile")
async def edit_profile_menu(callback: CallbackQuery):
    await callback.message.edit_text("Что вы хотите изменить?", reply_markup=kb.edit_profile_kb)


@studio.callback_query(F.data == 'edit_name')
async def  edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новое название студии или нажмите кнопку назад, для возврата в меню "
                                     "редактирования профиля.", reply_markup=kb.back_edit_profile)
    await state.set_state(EditStudio.name)


@studio.message(EditStudio.name)
async def save_name(message: Message, state: FSMContext):
    await db.pool.fetchrow("UPDATE studios SET studio_name = $1  WHERE tg_id = $2",
                           message.text,
                           message.from_user.id)

    await message.answer("Название обновлено", reply_markup=kb.back_edit_profile)
    await state.clear()


@studio.callback_query(F.data == 'edit_description')
async def edit_description(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новое описание студии или нажмите кнопку назад, для возврата в меню "
                                     "редактирования профиля.", reply_markup=kb.back_edit_profile)
    await state.set_state(EditStudio.description)


@studio.message(EditStudio.description)
async def save_description(message: Message, state: FSMContext):
    await db.pool.fetchrow("UPDATE  studios SET description = $1 WHERE tg_id = $2",
                           message.text,
                           message.from_user.id)

    await message.answer("Описание студии обновлено", reply_markup=kb.back_edit_profile)
    await state.clear()


@studio.callback_query(F.data == 'edit_contact')
async def edit_contact(callback: CallbackQuery, state:  FSMContext):
    await callback.message.edit_text("Введите новые контактные данные или нажмите кнопку назад, для возврата в меню "
                                     "редактирования профиля.", reply_markup=kb.back_edit_profile)
    await state.set_state(EditStudio.contact)


@studio.message(EditStudio.contact)
async def save_contact(message: Message, state: FSMContext):
    await db.pool.fetchrow("UPDATE  studios SET contact_data = $1 WHERE tg_id = $2",
                           message.text,
                           message.from_user.id)

    await message.answer("Контактные данные студии обновлены", reply_markup=kb.back_edit_profile)
    await state.clear()


@studio.callback_query(F.data == 'edit_shoot_type')
async def edit_shoot_type(callback: CallbackQuery,state: FSMContext):
    await state.update_data(shoot_type=[])
    await callback.message.answer("Укажите тип съемки, можете выбрать несколько вариантов.\n"
                                  "Нажмите 'Готово, когда закончите.", reply_markup=kb.choices_kb)
    await state.set_state(EditStudio.shoot_type)


@studio.message(EditStudio.shoot_type)
async def save_shoot_type(message: Message, state: FSMContext):
    text = message.text.strip()
    if message.text == 'Готово':
        data = await state.get_data()
        shoot_types = data.get('shoot_type', [])

        if not  shoot_types:
            await message.answer("Вы не указали ни одного типа съемки.", reply_markup=kb.back_edit_profile)
            return

        shoot_types_str = ', '.join(shoot_types)

        await db.execute("UPDATE studios SET shoot_type = $1 WHERE tg_id = $2",
                         shoot_types_str,
                         message.from_user.id)

        await message.answer("Данные о типах съемки обновлены", reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(0.5)
        await message.answer("Для возврата в меню редактирования профиля нажмите\n"
                             " ⬅ Назад", reply_markup=kb.back_edit_profile)
        await state.clear()

    else:
        data = await state.get_data()
        shoot_types = data.get('shoot_type', [])
        shoot_types.append(text)
        await state.update_data(shoot_type=shoot_types)

        await message.answer(f"Добавлено: {text}\n\n"
                             f"Уже выбрано: {', '.join(shoot_types)}\n\n"
                             f"Продолжите выбор или нажмите 'Готово'.")


# РЕДАКТИРОВАНИЕ ПОРТФОЛИО
@studio.callback_query(F.data == 'edit_portfolio')
async def show_portfolio_for_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Ответим на callback
    user_id = callback.from_user.id

    files = await db.pool.fetch('''
        SELECT id, file_id, file_type, description FROM portfolio
        WHERE studio_id = (SELECT id FROM studios WHERE tg_id = $1)
        ORDER BY id''', user_id)

    if not files:
        await callback.message.answer("У вас нет загруженных работ.", reply_markup=kb.back_edit_profile)
        return

    await state.set_state(PortfolioPagination.viewing)
    await state.update_data(files=files, index=0)
    await send_portfolio_item(callback.message, files, 0)

async def send_portfolio_item(message: Message, files: list, index: int):
    portfolio_id, file_id, file_type, description = files[index]

    edit_portfolio_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️", callback_data="portfolio_prev"),
            InlineKeyboardButton(text="▶️", callback_data="portfolio_next")
        ],
        [
            InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_desc_{portfolio_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_file_{portfolio_id}")
        ],
        [
            InlineKeyboardButton(text='⬅ Назад в меню', callback_data='studio_menu')
        ]
    ])

    if file_type == 'photo':
        await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=file_id,
            caption=description,
            reply_markup=edit_portfolio_kb
        )
    elif file_type == 'video':
        await message.bot.send_video(
            chat_id=message.chat.id,
            video=file_id,
            caption=description,
            reply_markup=edit_portfolio_kb
        )

@studio.callback_query(F.data == "portfolio_prev")
async def paginate_prev(callback: CallbackQuery, state: FSMContext):
    await callback.answer() # Ответим на callback
    await paginate(callback, state, direction="prev")

@studio.callback_query(F.data == "portfolio_next")
async def paginate_next(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Ответим на callback
    await paginate(callback, state, direction="next")

async def paginate(callback: CallbackQuery, state: FSMContext, direction: str):
    data = await state.get_data()
    files = data.get('files', [])
    index = data.get('index', 0)

    if not files:
        await callback.message.answer("Ошибка загрузки портфолио.", reply_markup=kb.back_edit_profile)
        return

    if direction == 'prev':
        index = (index - 1) % len(files)
    else:
        index = (index + 1) % len(files)

    await state.update_data(index=index)
    try:
        await callback.message.delete()  # Удаляем предыдущее сообщение
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")
    await send_portfolio_item(callback.message, files, index)

@studio.callback_query(F.data.startswith('delete_file_'))
async def delete_file(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Ответим на callback
    portfolio_id = int(callback.data.split('_')[-1])

    await db.pool.execute("DELETE FROM portfolio WHERE id = $1", portfolio_id)

    data = await state.get_data()
    files = [f for f in data.get('files', []) if f[0] != portfolio_id]

    if not files:
        await state.clear()
        try:
            await callback.message.delete()
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")
        await callback.message.answer("Все работы удалены.", reply_markup=kb.back_edit_profile)
        return

    index = min(data.get("index", 0), len(files) - 1)
    await state.update_data(files=files, index=index)

    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    await send_portfolio_item(callback.message, files, index)

@studio.message(EditPortfolio.waiting_for_description)
async def save_new_description(message: Message, state: FSMContext):
    data = await state.get_data()
    portfolio_id = data.get("portfolio_id")

    await db.pool.execute("UPDATE portfolio SET description = $1 WHERE id = $2", message.text, portfolio_id)

    files = data.get("files", [])
    index = data.get("index", 0)
    updated_files = []

    for entry in files:
        if entry[0] == portfolio_id:
            updated_files.append((entry[0], entry[1], entry[2], message.text))
        else:
            updated_files.append(entry)

    await state.update_data(files=updated_files)
    await state.set_state(PortfolioPagination.viewing)

    try:
        await message.delete()  # Удаляем сообщение с запросом описания
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

    await send_portfolio_item(message, updated_files, index)
    await message.answer("Описание обновлено.", reply_markup=kb.back_edit_profile)

@studio.callback_query(F.data.startswith('edit_desc_'))
async def edit_desc(callback: CallbackQuery, state: FSMContext):
    await callback.answer() # Ответим на callback
    portfolio_id = int(callback.data.split('_')[-1])
    await state.update_data(portfolio_id=portfolio_id)
    await callback.message.answer("Введите новое описание:")
    await state.set_state(EditPortfolio.waiting_for_description)


# ПРОСМОТР  ОТЗЫВОВ И РЕЙТИНГА
@studio.callback_query(F.data == 'view_reviews')
async def start_view_reviews(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    # получаем данные студии
    studio_data = await db.pool.fetchrow(
            "SELECT id, studio_name, rating FROM studios WHERE tg_id = $1",
            user_id)

    if not studio_data:
        await callback.message.answer("❌ Студия не найдена!")
        return

    studio_id = studio_data['id']
    studio_name = studio_data['studio_name']
    rating = studio_data['rating']

    # Получаем отзывы
    reviews = await db.pool.fetch(
            "SELECT text, rating, created_at FROM reviews WHERE studio_id = $1 ORDER BY created_at DESC",
            studio_id)

    if not reviews:
        await callback.message.answer("📭 У вас пока нет отзывов", reply_markup=kb.back_studio_menu)
        return

    # Сохраняем данные для пагинации
    await state.update_data(
        reviews=reviews,
        current_index=0,
        studio_name=studio_name,
        rating=rating
    )
    await state.set_state(StudioReviews.viewing_reviews)
    await show_review(callback.message, state)


async def show_review(message: Message, state: FSMContext):
    data = await state.get_data()
    reviews = data['reviews']
    index = data['current_index']
    studio_name = data['studio_name']
    rating = data['rating']

    if index >= len(reviews):
        await message.answer("✅ Вы просмотрели все отзывы")
        await state.clear()
        return

    review = reviews[index]
    text, review_rating, created_at = review

    # Исправленное форматирование даты
    formatted_date = created_at.strftime("%Y-%m-%d") if created_at else "Дата неизвестна"

    review_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️", callback_data="review_prev"),
            InlineKeyboardButton(text="▶️", callback_data="review_next")
        ],
        [
            InlineKeyboardButton(text='⬅ Назад', callback_data='studio_menu')
        ]
    ])

    await message.answer(
        f"📸 <b>{studio_name}</b>\n"
        f"⭐ Общий рейтинг: {rating}\n\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"📅 <b>Дата отзыва:</b> {formatted_date}\n\n"
        f"⭐ <b>Оценка:</b> {review_rating if review_rating else 'Без оценки'}\n\n"
        f"📝 <b>Отзыв:</b>\n{text}\n\n"
        f"Отзыв {index + 1}/{len(reviews)}",
        parse_mode='HTML',
        reply_markup=review_kb
    )


@studio.callback_query(StudioReviews.viewing_reviews, F.data.startswith("review_"))
async def handle_review_pagination(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]

    data = await state.get_data()
    current_index = data['current_index']

    if action == "prev":
        new_index = max(0, current_index - 1)
    elif action == "next":
        new_index = min(len(data['reviews']) - 1, current_index + 1)
    else:  # exit
        await callback.message.delete()
        await state.clear()
        return

    await state.update_data(current_index=new_index)
    await callback.message.delete()
    await show_review(callback.message, state)