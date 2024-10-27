from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID

admins = [ADMIN_ID]
def main_kb(user_telegram_id: int):
    kb_list = [
        [KeyboardButton(text="Задать фильры")],
        #[KeyboardButton(text="📝 О нас"), KeyboardButton(text = "Кнопка 1")]
    ]
    if user_telegram_id in admins:
        kb_list.append([KeyboardButton(text="⚙️ Админ панель")])
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb_list,
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Воспользуйтесь меню:"
    )
    return keyboard

def main_inline_kb(user_tg_ig:int,price:str='pricee'):

    # Создание кнопок
    kb_list = [[InlineKeyboardButton(text="Цена", callback_data="Price")],
        [InlineKeyboardButton(text="Добавить свой фильтр", callback_data="UniPm")]]

    # Создание inline-клавиатуры и добавление кнопок
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb_list
    )

    return keyboard
    #await message.answer("Выберите действие", reply_markup=keyboard)
def Price_text_field():
    keyboard = ReplyKeyboardMarkup(
        keyboard = [[[KeyboardButton(text="Без ограничений")]]],
        input_field_placeholder="Укажите минимальную и максимальную цену объявления"
    )
    return keyboard
