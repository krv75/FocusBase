from aiogram import Router, F
import asyncio
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from app.database.new_models import db
import app.keyboards as kb
from app.states import Reg
from aiogram.types import ReplyKeyboardRemove


register = Router()


@register.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    client_row = await db.pool.fetchrow("SELECT id FROM client WHERE tg_id = $1", tg_id)

    studio_row = await db.pool.fetchrow("SELECT id FROM studios WHERE tg_id = $1", tg_id)

    if client_row:
        await message.answer("✅ Вы уже зарегистрированы как клиент ✅\n"
                             "Для смены роли перейдите в боковое меню и нажмите на 'Изменить роль'", reply_markup=kb.back_client_menu)
        return
    if studio_row:
        await message.answer("✅ Вы уже зарегистрированы как фотостудия ✅\n"
                             "Для смены роли перейдите в боковое меню и нажмите на 'Изменить роль'", reply_markup=kb.back_studio_menu)
        return
    else:
        user_name = message.from_user.full_name
        await message.bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
        await asyncio.sleep(1)
        await message.answer(f"Здравствуйте {user_name}, рады приветствовать Вас в нашем боте\n"
                            f"FocusBase - это площадка для подбора клиентами профессиональной фотостудии.\n"
                            f"FocusBase абсолютно бесплатен как для регистрации в роли фотостудии, так и для регистрации в роли клиента.\n"
                            f"Для продолжения пройдите регистрацию:", reply_markup=kb.menu_kb)


# СМЕНА РОЛИ
@register.callback_query(F.data == 'change_role')
async  def change_role(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
# Удаление пользователя из обеих таблиц
    await db.pool.execute("DELETE FROM client WHERE tg_id = $1", tg_id)
    await db.pool.execute("DELETE FROM studios WHERE tg_id = $1", tg_id)
    await callback.message.answer("🔄 Ваша роль сброшена. Теперь вы можете пройти регистрацию заново.",
                                  reply_markup=kb.menu_kb)
    await state.clear()

@register.message(Command('change_role'))
async def cmd_change_role(message: Message):
    tg_id = message.from_user.id
    await db.pool.execute("DELETE FROM client WHERE tg_id = $1", tg_id)
    await db.pool.execute("DELETE FROM studios WHERE tg_id = $1", tg_id)
    await message.answer("🔄 Ваша роль сброшена. Теперь вы можете пройти регистрацию заново.",
                                  reply_markup=kb.menu_kb)

@register.callback_query(F.data == 'reg')
async def cmd_reg(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Выберите свою роль:", reply_markup=kb.role_kb)
    await state.set_state(Reg.role)


@register.message(Command('reg'))
async def cmd_start(message: Message, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
    await asyncio.sleep(1)
    await message.answer("Выберите свою роль:", reply_markup=kb.role_kb)
    await state.set_state(Reg.role)


@register.message(Reg.role)
async def selected_role(message: Message, state: FSMContext):
    selected_role = message.text
    await state.update_data(role=selected_role)

    if selected_role == 'Фотостудия':
        await state.set_state(Reg.studio_name)
        await message.answer("Введите название студии")

    if selected_role == 'Клиент':
        await state.set_state(Reg.name)
        await message.answer("Введите Ваше имя")


# РЕГИСТРАЦИЯ ФОТОСТУДИИ
@register.message(Reg.studio_name)
async def reg_studio_name(message: Message, state: FSMContext):
    await state.update_data(studio_name=message.text)
    await state.set_state(Reg.description)
    await message.answer("Опишите свою фотостудию")


@register.message(Reg.description)
async def description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(Reg.contact_data)
    await message.answer("Введите контактные данные Вашей студии")


@register.message(Reg.contact_data)
async def reg_contact_data(message: Message, state: FSMContext):
    await state.update_data(contact_data=message.text)
    await state.set_state(Reg.shoot_type)
    await message.answer("Укажите тип съемки, выберите несколько вариантов."
                         "Нажмите 'Готово, когда закончите.", reply_markup=kb.choices_kb)


@register.message(Reg.shoot_type)
async def reg_shoot_type(message: Message, state: FSMContext):
    if message.text == 'Готово':
        data = await state.get_data()
        shoot_types = data.get('shoot_type', [])
        shoot_types_str = ', '.join(shoot_types)

        await db.pool.fetchrow('''
                INSERT INTO studios (tg_id, studio_name, description, contact_data, shoot_type)
                VALUES($1, $2, $3, $4, $5) ON CONFLICT (tg_id) DO NOTHING
                ''', message.from_user.id,
                      data['studio_name'],
                      data['description'],
                      data['contact_data'],
                      shoot_types_str
                      )

        await message.answer(f"Регистрация завершена как {data['role']}\n"
                             f"Для изменения Вашей роли перейдите в боковое меню и выберите пункт 'Изменить роль'", reply_markup=ReplyKeyboardRemove())
        await message.bot.send_chat_action(chat_id=message.from_user.id, action=ChatAction.TYPING)
        await message.answer("Перейдите в меню для дальнейшего использования бота", reply_markup=kb.studio_kb)
        await state.clear()
        return

    data = await state.get_data()
    shoot_types = data.get('shoot_type', [])

    if message.text not in shoot_types:
        shoot_types.append(message.text)

    await state.update_data(shoot_type=shoot_types)
    await message.answer(f"Добавлено: {message.text}\nВыберите ещё или нажмите 'Готово'.")


# РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ (КЛИЕНТА)

# Пользователь вводит имя
@register.message(Reg.name)
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Теперь укажите номер телефона.\n"
        "Вы можете отправить свой номер из Telegram или ввести вручную:",
        reply_markup=kb.share_phone_kb
    )
    await state.set_state(Reg.phone)


# Пользователь отправил телефон текстом
@register.message(Reg.phone, F.text)
async def reg_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()

    # Простая проверка формата
    if not phone.startswith("+") or not phone[1:].isdigit():
        await message.answer("❌ Введите корректный номер (например: +79991234567)")
        return

    await state.update_data(phone=phone)

    await message.answer(
        f"Мы получили ваш номер: {phone}\n\n"
        f"Хотите оставить его или ввести другой?",
        reply_markup=kb.confirm_phone_kb
    )


# Пользователь отправил контакт
@register.message(Reg.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)

    await message.answer(
        f"Мы получили ваш номер: {phone}\n\n"
        f"Хотите оставить его или ввести другой?",
        reply_markup=kb.confirm_phone_kb
    )

# Пользователь подтверждает номер
@register.callback_query(F.data == "phone_confirm")
async def phone_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone")

    # Сохраняем только после подтверждения
    await db.pool.fetchrow('''
        INSERT INTO client (tg_id, name, phone)
        VALUES ($1, $2, $3) 
        ON CONFLICT (tg_id) DO NOTHING
    ''',
        callback.from_user.id,
        data["name"],
        phone
    )

    await callback.message.answer(
        f"✅ Номер {phone} сохранён!\n"
        f"Регистрация завершена как {data['role']}\n"
        f"Для изменения Вашей роли перейдите в боковое меню и выберите пункт 'Изменить роль'",
        reply_markup=kb.client_kb
    )
    await state.clear()


# Пользователь хочет изменить номер
@register.callback_query(F.data == "phone_change")
async def phone_change(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "✍️ Введите другой номер телефона:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Reg.phone)
