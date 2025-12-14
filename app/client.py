from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo


import app.keyboards as kb
from app.database.new_models import db
from app.states import Review, PortfolioPaginationClient
from app.states import Complaint


client = Router()


@client.message(Command('client_menu'))
async def cmd_client_menu(message: Message):
    await message.answer("Выберите интересующий Вас пункт меню:", reply_markup=kb.client_kb)


@client.callback_query(F.data == 'client_menu')
async def back_client_menu(callback: CallbackQuery):
    if callback.message.text:
        await callback.message.edit_text("Выберите интересующий Вас пункт меню:", reply_markup=kb.client_kb)
    else:
        await callback.message.answer("Выберите интересующий Вас пункт меню:", reply_markup=kb.client_kb)


@client.callback_query(F.data == "find_studio")
async def show_filter_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите фильтр для поиска студий:", reply_markup=await kb.filter_menu())


async def get_studio_page(studios, page: int):
    studio_id, name, description, contact, types, rating = studios[page]

    photo_row = await db.pool.fetchrow('''
    SELECT file_id FROM portfolio WHERE studio_id = $1 AND file_type = 'photo' ORDER BY id LIMIT 1''', studio_id)

    photo_id = photo_row['file_id'] if photo_row else None

    keyboard = [
        [
            InlineKeyboardButton(text="📂 Примеры работ", callback_data=f"view_portfolio_{studio_id}"),
            InlineKeyboardButton(text="📖 Отзывы", callback_data=f"studio_review_{studio_id}")
        ],
        [
            InlineKeyboardButton(text="👍 Оценить", callback_data=f"rate_studio_{studio_id}"),
            InlineKeyboardButton(text="✨ В избранное", callback_data=f"fav_{studio_id}")
        ],
        [
            InlineKeyboardButton(text="📝 Оставить отзыв", callback_data=f"leave_review_{studio_id}"),
            InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"complain_{studio_id}")
        ]
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"filter_page_{page-1}"))
    if page < len(studios) - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡", callback_data=f"filter_page_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(text='⬅ В меню', callback_data='client_menu')])

    caption = (
        f"📸 <b>{name}</b>\n\n"
        f"📝 Описание: {description}\n"
        f"📸 Типы съёмки: {types}\n"
        f"⭐ Рейтинг: {rating}\n"
        f"☎️ Контакты: {contact}"
    )

    return caption, InlineKeyboardMarkup(inline_keyboard=keyboard), photo_id


@client.callback_query(F.data.startswith('filter_type'))
async def filter_type(callback: CallbackQuery, state: FSMContext):
    shoot_type = callback.data.split(':')[1]
    studios = await db.pool.fetch(
        '''SELECT id, studio_name, description, contact_data, shoot_type, rating  
           FROM studios 
           WHERE shoot_type LIKE $1''',
        f"%{shoot_type}%"
    )

    if not studios:
        await callback.message.answer("❌ Студий по выбранному фильтру не найдено", reply_markup=kb.back_client_menu)
        return


    await state.update_data(studios=studios, current_page=0)  # сохраняем список студий в state и устанавливаем начальную страницу

    caption, keyboard, photo_id = await get_studio_page(studios, 0)
    if photo_id:
        media = InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML")
        await callback.message.answer_photo(photo=photo_id, caption=caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)



@client.callback_query(F.data.startswith("filter_page_"))
async def filter_pagination(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    studios = data.get("studios")

    if not studios:
        await callback.answer("Ошибка: студии не найдены")
        return


    await state.update_data(current_page=page)

    caption, keyboard, photo_id = await get_studio_page(studios, page)
    if photo_id:
        media = InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML")
        await callback.message.edit_media(media=media, reply_markup=keyboard)
    else:
        await callback.message.edit_text(caption, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


# ПРОСМОТР ОТЗЫВОВ
@client.callback_query(F.data.startswith("studio_review_"))
async def show_review(callback: CallbackQuery):
    parts = callback.data.split('_')
    if len(parts) < 3 or not parts[2].isdigit():
        await callback.answer("❌ Некорректный формат запроса.")
        return

    studio_id = int(parts[2])

    files = await db.pool.fetch(
        '''SELECT studio_id, user_id, text
           FROM reviews
           WHERE studio_id = $1''',
        studio_id
    )

    if not files:
        await callback.message.answer("🤷 Отзывов о студии не найдено", reply_markup=kb.back_client_menu)
    else:
        for review in files:
            await callback.message.answer(f"📝 Отзыв:\n{review['text']}")
            await callback.message.answer("Для возвращения в главное меню нажмите Назад",
                                          reply_markup=kb.back_client_menu)


@client.message(Review.waiting_for_text)
async def get_review_text(message: Message, state: FSMContext):
    await state.update_data(review_text=message.text)
    data = await state.get_data()
    studio_id = data['studio_id']
    review_text = data['review_text']
    file_id = None

    await db.pool.execute(
        '''INSERT INTO reviews (studio_id, user_id, text, rating, file_id)
           VALUES($1, $2, $3, $4, $5)''',
        studio_id, message.from_user.id, review_text, 5, file_id
    )

    row = await db.pool.fetchrow(
        "SELECT AVG(rating) AS avg_rating, COUNT(*) AS review_count FROM reviews WHERE studio_id = $1",
        studio_id
    )
    avg_rating = row["avg_rating"]
    review_count = row["review_count"]

    await db.pool.execute(
        "UPDATE studios SET rating = $1, review_count = $2 WHERE id = $3",
        avg_rating, review_count, studio_id
    )

    await message.answer("Спасибо за Ваш отзыв!", reply_markup=kb.back_client_menu)
    await state.clear()


@client.callback_query(F.data == 'client')
async def client_menu(callback: CallbackQuery):
    await callback.message.answer("Выберите действие:", reply_markup=kb.client_kb)


@client.callback_query(F.data == 'complain')
async def start_complain(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("С каким вопросом Вы хотели бы обратиться?",
                                  reply_markup=kb.back_client_menu)
    await state.set_state(Complaint.waiting_for_text)


@client.message(Complaint.waiting_for_text)
async def save_complain(message: Message, state: FSMContext):
    text = message.text

    await db.pool.execute(
        '''INSERT INTO complaints (user_id, text)
           VALUES ($1, $2)''',
        message.from_user.id, text
    )

    await message.answer("Ваши пожелания отправлены на рассмотрение. Спасибо.", reply_markup=kb.back_client_menu)
    await state.clear()


@client.callback_query(F.data.startswith('rate_studio_'))
async def submit_rating(callback: CallbackQuery):
    studio_id = int(callback.data.split('_')[-1])

    row = await db.pool.fetchrow("SELECT studio_name FROM studios WHERE id = $1", studio_id)
    if row is None:
        await callback.message.answer("Студия не найдена.", reply_markup=kb.back_client_menu)
        return

    studio_name = row["studio_name"]
    await callback.message.answer(
        f"Поставьте оценку студии «{studio_name}» от 1 до 5 ⭐:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐", callback_data=f"rating_1_{studio_id}"),
             InlineKeyboardButton(text="⭐⭐", callback_data=f"rating_2_{studio_id}"),
             InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"rating_3_{studio_id}")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"rating_4_{studio_id}"),
             InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"rating_5_{studio_id}")]
        ])
    )


@client.callback_query(F.data.startswith('rating_'))
async def process_rating(callback: CallbackQuery):
    _, stars, studio_id = callback.data.split('_')
    stars = int(stars)
    studio_id = int(studio_id)

    row = await db.pool.fetchrow(
        "SELECT rating, review_count, studio_name FROM studios WHERE id = $1",
        studio_id
    )
    if row is None:
        await callback.message.answer("Ошибка, студия не найдена.", reply_markup=kb.back_client_menu)
        return

    current_rating, review_count, studio_name = row
    review_count += 1

    # ПЕРЕСЧЕТ СРЕДНЕГО РЕЙТИНГА
    new_rating = round((current_rating * (review_count - 1) + stars) / review_count, 2)

    await db.pool.execute(
        "UPDATE studios SET rating = $1, review_count = $2 WHERE id = $3",
        new_rating, review_count, studio_id
    )

    await callback.message.answer(
        f"Спасибо за Вашу оценку: {stars} ⭐ студии «{studio_name}»",
        reply_markup=kb.back_client_menu
    )


# ДОБАВЛЕНИЕ В ИЗБРАННОЕ
@client.callback_query(F.data.startswith('fav_'))
async def add_to_favorites(callback: CallbackQuery):
    studio_id = int(callback.data.split('_')[-1])
    tg_id = callback.from_user.id

    # Проверяем, есть ли клиент в таблице client
    client_exists = await db.pool.fetchrow(
        "SELECT id FROM client WHERE tg_id = $1", tg_id
    )
    if not client_exists:
        await callback.answer("ℹ️ Сначала зарегистрируйтесь в системе.")
        return

    client_id = client_exists['id']
    # Проверяем, есть ли уже запись в избранном
    favorite_exists = await db.pool.fetchval(
        "SELECT 1 FROM favorites WHERE client_id = $1 AND studio_id = $2",
        client_id, studio_id
    )
    if favorite_exists:
        await callback.answer("ℹ️ Студия уже в избранном")
        return

    # Добавляем в избранное
    await db.pool.execute(
        "INSERT INTO favorites (client_id, studio_id) VALUES ($1, $2)",
        client_id, studio_id
    )
    await callback.answer("⭐ Студия добавлена в избранное!")


# УДАЛЕНИЕ ИЗ ИЗБРАННОГО
@client.callback_query(F.data.startswith('unfav_'))
async def del_from_favorites(callback: CallbackQuery):
    studio_id = int(callback.data.split('_')[-1])
    tg_id = callback.from_user.id

    # Получаем client_id по tg_id
    client_row = await db.pool.fetchrow("SELECT id FROM client WHERE tg_id = $1", tg_id)
    if not client_row:
        await callback.answer("ℹ️ Сначала зарегистрируйтесь в системе.")
        return

    client_id = client_row['id']

    # Удаляем из избранного
    result = await db.pool.execute(
        "DELETE FROM favorites WHERE client_id = $1 AND studio_id = $2",
        client_id, studio_id
    )

    if result.endswith('0'):
        await callback.answer("Студия не найдена в избранном.")
    else:
        await callback.answer("Студия удалена из избранного!")


# ПРОСМОТР ИЗБРАННОГО
async def get_fav_studio_page(studios, page: int):
    # Формируем сообщение и клавиатуру для конкретной студии
    studio = studios[page]

    photo_row = await db.pool.fetchrow('''
    SELECT file_id FROM portfolio WHERE studio_id = $1 AND file_type = 'photo' ORDER by id LIMIT 1''', studio['id'])

    photo_id = photo_row['file_id'] if photo_row else None

    caption = (
        f"⭐ <b>{studio['studio_name']}</b>\n\n"
        f"📝 Описание: {studio['description']}\n\n"
        f"📸 Типы съёмки: {studio['shoot_type']}\n\n"
        f"⭐ Рейтинг: {studio['rating']}\n\n"
        f"☎️ Контакты: {studio['contact_data']}\n\n"
        f"Студия {page + 1} из {len(studios)}"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                text="📂 Примеры работ", callback_data=f"view_portfolio_{studio['id']}"
            ),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"unfav_{studio['id']}"
            )
        ],
        [
            InlineKeyboardButton(text="📝 Оставить отзыв", callback_data=f"leave_review_{studio['id']}"),
            InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"complain_{studio['id']}")
        ],
        [
            InlineKeyboardButton(
                text="⬅", callback_data=f"favpg_{page - 1}" if page > 0 else "ignore"
            ),
            InlineKeyboardButton(
                text="➡", callback_data=f"favpg_{page + 1}" if page < len(studios) - 1 else "ignore"
            )
        ],
        [InlineKeyboardButton(text="⬅ Назад в меню", callback_data="client_menu")]
    ]

    return caption, InlineKeyboardMarkup(inline_keyboard=keyboard), photo_id


@client.callback_query(F.data == "view_favorites")
async def view_favorites(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id

    client_row = await db.pool.fetchrow("SELECT id FROM client WHERE tg_id = $1", tg_id)
    if not client_row:
        await callback.message.answer("ℹ️ Сначала зарегистрируйтесь в системе.", reply_markup=kb.back_client_menu)
        return

    client_id = client_row["id"]

    studios = await db.pool.fetch(
        '''SELECT s.id, s.studio_name, s.description, s.contact_data, s.shoot_type, s.rating
           FROM studios s
           JOIN favorites f ON s.id = f.studio_id
           WHERE f.client_id = $1''',
        client_id
    )

    if not studios:
        await callback.message.answer("У Вас пока нет избранных студий.", reply_markup=kb.back_client_menu)
        return

    # сохраняем студии в state (чтобы можно было листать)
    await state.update_data(fav_studios=studios)

    caption, keyboard, photo_id = await get_fav_studio_page(studios, 0)

    if photo_id:
        await callback.message.answer_photo(photo=photo_id, caption=caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=keyboard)


@client.callback_query(F.data.startswith("favpg_"))
async def paginate_favorites(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    studios = data.get("fav_studios", [])

    if not studios:
        await callback.answer("Нет данных для отображения", show_alert=True)
        return

    page = int(callback.data.split("_")[-1])
    if page < 0 or page >= len(studios):
        await callback.answer("Дальше листать нельзя")
        return

    caption, keyboard, photo_id = await get_fav_studio_page(studios, page)

    if photo_id:
        media = InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML")
        await callback.message.edit_media(media=media, reply_markup=keyboard)
    else:
        await callback.message.edit_text(caption, parse_mode="HTML", reply_markup=keyboard)


# ОСТАВИТЬ ОТЗЫВ
@client.callback_query(F.data.startswith("leave_review_"))
async def leave_review_from_card(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[-1])

    # сохраняем studio_id в состоянии
    await state.update_data(studio_id=studio_id)

    await callback.message.answer("Введите текст отзыва:", reply_markup=kb.back_client_menu)
    await state.set_state(Review.waiting_for_text)

# ПОЖАЛОВАТЬСЯ
@client.callback_query(F.data.startswith("complain_"))
async def complain_from_card(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[-1])

    # сохраняем studio_id в состоянии
    await state.update_data(studio_id=studio_id)

    await callback.message.answer("Опишите проблему:", reply_markup=kb.back_client_menu)
    await state.set_state(Complaint.waiting_for_text)


# ПАГИНАЦИЯ ПОРТФОЛИО СТУДИИ ДЛЯ КЛИЕНТА С ВОЗВРАТОМ К ФИЛЬТРУ
async def studio_portfolio_pagination_kb(current_idx: int, total: int, studio_id: int, return_to_filter: bool = True):
    buttons = []
    if current_idx > 0:
        buttons.append(InlineKeyboardButton(
            text="⏮ Назад",
            callback_data=f"studioportfolio_prev_{studio_id}_{current_idx - 1}"
        ))
    if current_idx < total - 1:
        buttons.append(InlineKeyboardButton(
            text="Вперед ⏭",
            callback_data=f"studioportfolio_next_{studio_id}_{current_idx + 1}"
        ))

    # Добавляем кнопку возврата в зависимости от контекста
    back_button = []
    if return_to_filter:
        back_button.append(InlineKeyboardButton(
            text="⬅ Назад к студиям",
            callback_data="back_to_filtered_studios"
        ))
    else:
        back_button.append(InlineKeyboardButton(
            text="⬅ В меню",
            callback_data="client_menu"
        ))

    keyboard = [buttons] if buttons else []
    keyboard.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@client.callback_query(F.data.startswith('view_portfolio_'))
async def view_studio_portfolio(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[-1])

    # Получаем файлы портфолио
    files = await db.pool.fetch(
        "SELECT file_id, file_type, description FROM portfolio WHERE studio_id = $1",
        studio_id
    )

    if not files:
        await callback.message.answer("Нет загруженных работ", reply_markup=kb.back_client_menu)
        return

    # Сохраняем данные для возврата
    data = await state.get_data()
    if 'studios' in data:  # Если пришли из фильтра
        await state.update_data(
            portfolio_files=files,
            current_idx=0,
            portfolio_studio_id=studio_id,
            return_context='filter'  # Помечаем, что нужно вернуться к фильтру
        )
        return_to_filter = True
    else:
        await state.update_data(
            portfolio_files=files,
            current_idx=0,
            portfolio_studio_id=studio_id,
            return_context='menu'  # Иначе возврат в меню
        )
        return_to_filter = False

    # Показываем первый файл
    file_id, file_type, description = files[0]
    kb_pagination = await studio_portfolio_pagination_kb(0, len(files), studio_id, return_to_filter)

    if file_type == 'photo':
        await callback.message.answer_photo(
            photo=file_id,
            caption=description,
            reply_markup=kb_pagination
        )
    elif file_type == 'video':
        await callback.message.answer_video(
            video=file_id,
            caption=description,
            reply_markup=kb_pagination
        )

    await state.set_state(PortfolioPaginationClient.viewing)


@client.callback_query(F.data.startswith("studioportfolio_"))
async def paginate_studio_portfolio(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    direction = data_parts[1]
    studio_id = int(data_parts[2])
    idx = int(data_parts[3])

    data = await state.get_data()
    files = data.get("portfolio_files")

    if not files:
        # Если файлы не найдены в state, загружаем заново
        files = await db.pool.fetch(
            "SELECT file_id, file_type, description FROM portfolio WHERE studio_id = $1",
            studio_id
        )
        await state.update_data(portfolio_files=files)

    # Определяем новый индекс в зависимости от направления
    if direction == "prev":
        new_idx = max(0, idx - 1)
    else:  # next
        new_idx = min(len(files) - 1, idx + 1)

    file_id, file_type, description = files[new_idx]

    # Определяем контекст возврата
    return_context = data.get('return_context', 'menu')
    return_to_filter = (return_context == 'filter')

    kb_pagination = await studio_portfolio_pagination_kb(new_idx, len(files), studio_id, return_to_filter)

    if file_type == "photo":
        media = InputMediaPhoto(media=file_id, caption=description)
        await callback.message.edit_media(media=media, reply_markup=kb_pagination)
    elif file_type == "video":
        media = InputMediaVideo(media=file_id, caption=description)
        await callback.message.edit_media(media=media, reply_markup=kb_pagination)

    await state.update_data(current_idx=new_idx)
    await callback.answer()


# ОБРАБОТЧИК ВОЗВРАТА К ОТФИЛЬТРОВАННЫМ СТУДИЯМ
@client.callback_query(F.data == "back_to_filtered_studios")
async def back_to_filtered_studios(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    studios = data.get("studios")
    current_page = data.get("current_page", 0)  # Сохраняем текущую страницу

    if not studios:
        await callback.message.answer("❌ Данные о студиях не найдены", reply_markup=kb.back_client_menu)
        return

    # Показываем ту же страницу, на которой был пользователь
    caption, keyboard, photo_id = await get_studio_page(studios, current_page)

    if photo_id:
        media = InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML")
        await callback.message.edit_media(media=media, reply_markup=keyboard)
    else:
        await callback.message.edit_text(caption, parse_mode="HTML", reply_markup=keyboard)

    await callback.answer()


@client.callback_query(F.data == "client_review")
async def review_choose_favorite(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    client_row = await db.pool.fetchrow("SELECT id FROM client WHERE tg_id = $1", tg_id)
    if not client_row:
        await callback.message.answer("Профиль не найден.", reply_markup=kb.back_client_menu)
        return

    client_id = client_row["id"]

    fav_studios = await db.pool.fetch(
        "SELECT s.id, s.studio_name FROM studios s JOIN favorites f ON s.id = f.studio_id WHERE f.client_id = $1",
        client_id
    )

    if not fav_studios:
        await callback.message.answer("У вас нет избранных студий.", reply_markup=kb.back_client_menu)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                                        [InlineKeyboardButton(text=studio["studio_name"],
                                                                              callback_data=f"selectreviewstudio_{studio['id']}")]
                                                        for studio in fav_studios
                                                    ] + [[InlineKeyboardButton(text="⬅ Назад",
                                                                               callback_data="client_menu")]])

    await callback.message.answer("Выберите студию для отзыва:", reply_markup=keyboard)


@client.callback_query(F.data.startswith("selectreviewstudio_"))
async def select_studio_for_review(callback: CallbackQuery, state: FSMContext):
    studio_id = int(callback.data.split("_")[1])
    await state.update_data(studio_id=studio_id)
    await callback.message.answer("Введите текст отзыва:", reply_markup=kb.back_client_menu)
    await state.set_state(Review.waiting_for_text)