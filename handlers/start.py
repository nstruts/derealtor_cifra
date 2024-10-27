from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from gpt_testing import *
from keyboards.all_kb import *
router = Router()

# Состояния для FSM
"""class Form(StatesGroup):
    waiting_for_price = State()"""

# Обработчик для нажатия на кнопку "Цена"
@router.callback_query(F.data == 'Price')
async def send_random_person(call: CallbackQuery):
    print('Price')
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=Price_text_field())
    #await call.message.answer(' 1',reply_markup=Price_text_field())

@router.message(CommandStart())
async def cmd_start(message: Message):
    msgtmp = load_json(msgtmp_file)
    await message.answer(msgtmp['StartMessage'],
                         reply_markup=main_kb(message.from_user.id))
    await message.answer("Ваши фильтры:", reply_markup=main_inline_kb(message.from_user.id))

@router.message(lambda message: message.text == "Задать фильры")
async def handle_button_1(message: Message):
    await message.answer("Ваши фильтры:",reply_markup=main_inline_kb(message.from_user.id))


"""
@router.message(Form.waiting_for_price)
async def process_price_input(message: Message, state: FSMContext):
    user_price = message.text
    await message.delete()  # Удаляем сообщение пользователя
    await state.clear()  # Завершаем состояние
    await message.answer("Ваши фильтры обновлены:", reply_markup=main_inline_kb(message.from_user.id, price=user_price))
"""


@router.message()
async def echo_handler(message: Message) -> None:
    user_req = message.text
    if user_req:
        user_id = message.from_user.id
        ans = get_gpt_ans(user_req,user_id)
        print(user_id,message.text)
        await message.answer(ans)
