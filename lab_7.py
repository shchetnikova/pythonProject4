from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.dispatcher import FSMContext
import logging
import os
import psycopg2
import re
import requests

bot_token = os.getenv('API_TOKEN')  # Получение токена из переменных окружения
bot = Bot(token=bot_token)  # Создание бота с токеном, который выдал в BotFather при регистрации бота
dp = Dispatcher(bot, storage=MemoryStorage())  # Инициализация диспетчера команд
conn = psycopg2.connect(user='postgres', password='postgres', host='localhost', port='5432',
                        database='lab7')  # Подключение к базе данных
cursor = conn.cursor()  # создаём курсор для выполнения SQL-запросов
saved_state_global = {}  # Обявление словаря


def ADMIN_ID():
    # Подключение к базе данных
    conn = psycopg2.connect(
        host="localhost",
        database="lab7",
        user="postgres",
        password="postgres",
        port="5432"
    )
    cursor = conn.cursor()
    # Выполнение запроса к таблице Admins
    cursor.execute("SELECT chat_id FROM Admins LIMIT 1")
    admin_chat_id = cursor.fetchone()[0]
    # Закрытие соединения с базой данных
    cursor.close()
    conn.close()
    return admin_chat_id


admin_commands = [
    BotCommand(command='/start', description='start'),
    BotCommand(command='/manage_currency', description='Менеджер валют'),
    BotCommand(command='/convert', description='Конвертировать')
]

user_comands = [
    BotCommand(command='/start', description='start'),
    BotCommand(command='/convert', description='Конвертировать')
]


# Создание класса для управления состояний процессов
class ManageStateGroup(StatesGroup):
    check = State()
    num = State()
    con = State()
    save_base = State()
    save_converted = State()
    save_converted_rate = State()
    save = State()


# Обработчик команды start
@dp.message_handler(commands=['start'])
async def start_comand(message: types.Message):
    await bot.set_my_commands(user_comands, scope=BotCommandScopeDefault())
    await message.reply("Добро пожаловать в бота.")


# Обработчик команды manage_currency
@dp.message_handler(commands=['manage_currency'])
async def manage_comand(message: types.Message):
    admin_id = ADMIN_ID()
    admin = str(message.chat.id)  # идентификации пользователя, который написал сообщение

    if admin in admin_id:
        await ManageStateGroup.save_base.set()
        await message.reply("Введите название конвертируемой (основной) валюты")
    else:
        await bot.set_my_commands(user_comands, scope=BotCommandScopeDefault())
        await message.reply("Нет доступа к команде")


# Объявление функции обработчика сообщений с состоянием save_base
@dp.message_handler(state=ManageStateGroup.save_base)
async def save_base(message: types.Message, state: FSMContext):
    await state.update_data(baseCurrency=message.text)  # Сохраняет в память состояния название основной валюты
    await ManageStateGroup.save_converted.set()
    await message.reply("Введите название валюты, в которую можно конвертировать указанную ранее валюту")


# Объявление функции обработчика сообщений с состоянием save_converted
@dp.message_handler(state=ManageStateGroup.save_converted)
async def save_converted(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)  # Сохраняет в память состояния название валюты для конвертации
    await ManageStateGroup.save_converted_rate.set()
    await message.reply("Введите курс")


# Объявление функции обработчика сообщений с состоянием save_converted_rate
@dp.message_handler(state=ManageStateGroup.save_converted_rate)
async def save_converted(message: types.Message, state: FSMContext):
    data = await state.get_data()  # записывает в переменню данные из состояния
    codee = data['code']  # записывает в переменню полученные данные названия конвертируемых валют по ключу
    try:
        ratess = data['rates']  # записывает в переменню полученные данные курса конвертируемых валют по ключу
    except:
        ratess = []  # Создание словаря
    ratess.append({'code': codee, 'rate': float(message.text)})  # записывает в словарь полученные данные
    # конвертируемой валюты по ключам
    await state.update_data(rates=ratess)  # Сохраняет в память состояния название и курс валют для конвертации
    await ManageStateGroup.save.set()
    await message.reply("Добавить еще валюту, в которую может сконвертирована основная валюта. Введите (Да/Нет)")


# Объявление функции обработчика сообщений с состоянием save
@dp.message_handler(state=ManageStateGroup.save)
async def save_converted(message: types.Message, state: FSMContext):
    cur = await state.get_data()  # записывает в переменню данные из состояния
    check = message.text  # записывает в переменню данные из сообщения
    YES = "Да"
    if YES in check:  # проверяет хотим ли добавить ещё валюты для конвертации. Если "Да" то переходим на состояние
        # save_converted
        await message.reply("Введите название валюты в которую будем конвертировать")
        await ManageStateGroup.save_converted.set()
    else:  # если в бота пришло любое другое сообщение:
        saved_state_global["baseCurrency"] = str(
            cur["baseCurrency"])  # записываем в словарь название основной влюты по ключу
        saved_state_global["rates"] = cur["rates"]  # записываем в словарь данные валют для конвертации по ключу
        requests.post("http://localhost:10660/load",
                      json=saved_state_global)  # отправляем запрос с данными в микросервис
        await message.reply("Вы завершили настройку валюты")
        saved_state_global.clear()  # очищаем словарь
        await state.finish()


# Обработчик команды convert
@dp.message_handler(commands=['convert'])
async def convert_comand(message: types.Message):
    await ManageStateGroup.check.set()
    await message.reply("Введите название конвертируемой валюты")


# Объявление функции обработчика сообщений с состоянием check
@dp.message_handler(state=ManageStateGroup.check)
async def process_check(message: types.Message, state: FSMContext):
    await state.update_data(baseCurrency=message.text)  # Сохраняет в память состояния название основной валюты
    await ManageStateGroup.num.set()
    await message.reply("Введите название валюты, в которую будет производится конвертация")


# Объявление функции обработчика сообщений с состоянием num
@dp.message_handler(state=ManageStateGroup.num)
async def process_convert(message: types.Message, state: FSMContext):
    await state.update_data(convertedCurrency=message.text)  # Сохраняет в память состояния название валюты для
    # конвертации
    await ManageStateGroup.con.set()
    await message.reply("Введите сумму")


# Объявление функции обработчика сообщений с состоянием con
@dp.message_handler(state=ManageStateGroup.con)
async def process_convert2(message: types.Message, state: FSMContext):
    num = message.text  # Сохраняет в переменную сумму для конвертации
    cur = await state.get_data()  # записывает в переменню данные из состояния
    saved_state_global["baseCurrency"] = str(
        cur["baseCurrency"])  # записываем в словарь название основной влюты по ключу
    saved_state_global["convertedCurrency"] = str(
        cur["convertedCurrency"])  # записываем в словарь название валюты для конвертации
    # по ключу
    saved_state_global["sum"] = float(num)  # записываем в словарь сумму для конвертации
    result = requests.get("http://localhost:10606/convert",
                          params=saved_state_global)  # отправляем запрос с данными в микросервис
    if result == "<Response [500]>":  # При получении ошибки из микросервиса:
        await message.reply('Произошла ошибка при конвертации валюты')
        saved_state_global.clear()
        await state.finish()
    else:  # При успешном выполнении микросервиса
        res = result.text  # Записываем результат выполнения микросервиса в переменную
        res = float(re.sub(r"[^0-9.]", r"", res))  # убираем лишние сиволы
        await message.reply(f'Результат конвертации: ({res})')  # Отправляем результат в бота
        saved_state_global.clear()
        await state.finish()


# точка входа в приложение
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)  # Настройка логирования
    executor.start_polling(dp, skip_updates=True)  # Запуск бота