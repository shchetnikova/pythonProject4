from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import aiogram.utils.markdown as md
import os


bot_token = os.getenv('API_TOKEN')

bot = Bot(bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())


class States(StatesGroup):
    CURRENCY = State()
    EXCHANGE_RATES = State()


# Help flag
flag = ''


# Help function
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


@dp.message_handler(commands=['save_currency'])
async def save(message: types.Message):
    global flag
    flag = 'save_currency'
    await States.CURRENCY.set()
    await message.answer("Введите название валюты")


# Convert
@dp.message_handler(commands=['convert'])
async def convert(message: types.Message):
    global flag
    flag = 'convert'
    await States.CURRENCY.set()
    await message.answer("Введите название валюты")


@dp.message_handler(state=States.CURRENCY)
async def process_currency(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['CURRENCY'] = message.text

    await States.next()

    global flag

    if flag == 'save_currency':
        await message.answer("Введите курс валюты к рублю")

    if flag == 'convert':
        await message.answer("Введите сумму в указанной валюте")


@dp.message_handler(lambda message: not is_number(message.text), state=States.EXCHANGE_RATES)
async def exchange_currency_invalid(message: types.Message):
    global flag

    if flag == 'save_currency':
        return await message.answer("Курс должен быть числом")

    if flag == 'convert':
        return await message.answer("Сумма должна быть числом")


@dp.message_handler(lambda message: is_number(message.text), state=States.EXCHANGE_RATES)
async def exchange_currency(message: types.Message, state: FSMContext):
    await States.next()

    global flag

    if flag == 'save_currency':
        await state.update_data(EXCHANGE_RATES=float(message.text))

        async with state.proxy() as data:
            await bot.send_message(
                message.chat.id,
                md.text(
                    md.text('Отлично, название валюты и курс записаны'),
                    md.text('Валюта:', md.code(data['CURRENCY'])),
                    md.text('Курс:', data['EXCHANGE_RATES']),
                    sep='\n',
                ),
            )

    if flag == 'convert':
        async with state.proxy() as data:
            converted = float(message.text) * float(data['EXCHANGE_RATES'])

            await bot.send_message(message.chat.id, md.text('Сумма в рублях:', converted))


async def on_startup(_):
    print('Бот запущен')


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)