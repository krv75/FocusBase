from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

 ################################ КЛАВИАТУРЫ РЕГИСТРАЦИИ################################
menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📝 Регистрация', callback_data= 'reg')]
])


# Клавиатура выбора роли
role_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Фотостудия'),
    KeyboardButton(text='Клиент')]
], resize_keyboard=True)

# Клавиатура смены роли
change_role_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🔄 Изменить роль', callback_data='change_role')]
])

# Подтверждение номера телефона
confirm_phone_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="✅ Оставить этот номер", callback_data="phone_confirm"),
        InlineKeyboardButton(text="🔄 Ввести другой", callback_data="phone_change")
    ]
])

# Клавиатура для отправки телефона
share_phone_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)],
        [KeyboardButton(text="✍️ Ввести вручную")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)


################################ КЛАВИАТУРЫ СТУДИИ ################################

# меню студии
studio_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🖼 Загрузить работы", callback_data="upload")
    ],
    [
        InlineKeyboardButton(text="⭐Рейтинг и отзывы", callback_data="view_reviews")
    ],
    [
        InlineKeyboardButton(text="✏ Редактировать профиль", callback_data="edit_profile")
    ],
    [
        InlineKeyboardButton(text="🖼 Редактировать портфолио", callback_data='edit_portfolio')
    ]
])


# клавиатура выбора видов съемки
choices_kb = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text='Fashion'),
        KeyboardButton(text='Предметная')
    ],
    [
        KeyboardButton(text='Готово')
    ]
], resize_keyboard=True)


# Клавиатура редактирования профиля фотостудии
edit_profile_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='🧾 Название', callback_data='edit_name')
    ],
    [
        InlineKeyboardButton(text='📝 Описание', callback_data='edit_description')
    ],
    [
        InlineKeyboardButton(text='☎️ Контакты', callback_data='edit_contact')
    ],
    [
        InlineKeyboardButton(text="📸 Типы съемки", callback_data='edit_shoot_type')
    ],
    [
        InlineKeyboardButton(text='⬅ Назад в меню', callback_data='studio_menu')
    ]
])


# Кнопка возврата в меню студии
back_studio_menu = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='⬅ Назад в меню', callback_data='studio_menu')
    ]
])


# Кнопка назад для подменю редактирования профиля студии
back_edit_profile = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='⬅ Назад', callback_data='edit_profile')
    ]
])


# Кнопка назад для подменю загрузить работы
back_upload = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='⬅ Назад в меню', callback_data='studio_menu'),
        InlineKeyboardButton(text="🖼 Загрузить работы", callback_data="upload")
    ]
])



################################ КЛАВИАТУРЫ КЛИЕНТА ################################

# Меню клиента
client_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🔍 Найти студию", callback_data='find_studio')
    ],
    [
        InlineKeyboardButton(text="❤️ Оставить отзыв", callback_data='client_review')
    ],
    [
        InlineKeyboardButton(text="📩 Служба заботы", callback_data='complain')
    ],
    [
        InlineKeyboardButton(text="✨ Избранные студии", callback_data='view_favorites')
    ]
])


# Клавиатура фильтра поиска студии
async def filter_menu():
    shoot_types = ['Fashion', 'Предметная']
    keyboard = InlineKeyboardBuilder()

    for shoot_type in shoot_types:
        keyboard.add(InlineKeyboardButton(text=shoot_type, callback_data=f'filter_type:{shoot_type}'))
    return keyboard.adjust(3).as_markup()


# Кнопка возврата в главное меню клиента
back_client_menu = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='⬅ Назад в меню', callback_data='client_menu')
    ]
])


################################ КЛАВИАТУРЫ АДМИНИСТРАТОРА ################################

# Панель администратора
admin_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='🚫 Жалобы', callback_data='view_complains')
    ],
    [
        InlineKeyboardButton(text="⏳ Модерация отзывов", callback_data='moderate_reviews')
    ],
    [
        InlineKeyboardButton(text="Управление студиями", callback_data='manage_studios')
    ],
    [
        InlineKeyboardButton(text="Управление клиентами", callback_data='manage_clients')
    ],
    [
        InlineKeyboardButton(text="Статистика", callback_data='statistics')
    ]
])


# Клавиатура модерации жалоб
def complaint_action_kb(comp_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Закрыть жалобу", callback_data=f"close_complaint_{comp_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Удалить студию",callback_data=f"delete_studio_{comp_id}")
        ],
        [
            InlineKeyboardButton(text='◀️ Назад', callback_data='admin_back')
        ]
    ])


# Клавиатура для управления студиями
studio_management_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Список студий', callback_data='list_studios')
    ],
    [
        InlineKeyboardButton(text='Поиск студии', callback_data='search_studio')
    ],
    [
        InlineKeyboardButton(text='◀️ Назад', callback_data='admin_back')
    ]
])


# Клавиатура для управления клиентами
client_management_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text='Список клиентов', callback_data='list_clients')
    ],
    [
        InlineKeyboardButton(text='Поиск клиента', callback_data='search_client')
    ],
    [
        InlineKeyboardButton(text='◀️ Назад', callback_data='admin_back')
    ]
])


# Клавиатура пагинации
def pagination_kb(current_index, total_items):
    keyboard = []
    if total_items > 1:
        row = []
        if current_index > 0:
            row.append(InlineKeyboardButton(text="◀️", callback_data="prev_item"))
        if current_index < total_items - 1:
            row.append(InlineKeyboardButton(text="▶️", callback_data="next_item"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="manage_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
