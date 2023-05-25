# Подключение
import logging
from typing import List

import uvicorn
import psycopg2 as pg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.responses import JSONResponse
import re

app = FastAPI()
# подключение к бд
conn = pg.connect(user='postgres', password='postgres', host='localhost', port='5432', database='lab7')
cursor = conn.cursor()


# Создание классов для корректной обработки запроса
class Converted(BaseModel):
    code: str
    rate: float


class RequestBody(BaseModel):
    baseCurrency: str
    rates: List[Converted]


# Функция проверяющая наличее основной валюты в бд и возвращения её айди при наличии
def check(name):
    cursor.execute("""select id from currency_rates where base_currency = %s""", (name,))
    data_id = cursor.fetchall()
    data_id = re.sub(r"[^0-9]", r"", str(data_id))
    print(data_id)
    return (data_id)


# Функция получающая данные по валюте в которую конвертируем, осуществляет поиск по айди основной валюты
def get(name):
    id = check(name)
    cursor.execute("""select rate from currency_rates_values 
                              where  currency_rate_id = %s""", (id,))
    data_id = cursor.fetchall()
    data_id = re.sub(r"[^0-9]", r"", str(data_id))
    return data_id


# Микросервис который получает из бота информацию по основной валюте и валютам для конвертации
@app.post("/load")
async def payload(Request: RequestBody):
    name = Request.baseCurrency  # записывает в переменную название основной валюты
    rates = Request.rates  # Записывает в переменную информацию по валютам для конвертации
    logging.debug(f"rates = {rates}")  # Системные функции для отладки, показывают записанные данные в консоле
    logging.debug(f"name = {name}")
    id_cur = check(name)  # Записывают в переменню выполнение функции чек (айди или ничего)
    try:  # метод который в котором происходит попытка выполнения
        if id_cur:  # если не пустое, то выполняется
            logging.error("Duplicate currency code")  # Системная функция для отладки, показывает в терминале, что в
            # бд уже есть данная основная валюта
            raise HTTPException(500)  # Вовращает в бота ошибку выполнения
        cursor.execute(""" Insert into currency_rates  (base_currency)
                                        values (%s);""", (name,))  # Если в бд нет такой основной валюты, то записывает
        conn.commit()
        id_cur = check(name)  # Записывают в переменню выполнение функции чек (айди)
        logging.debug(f"id_cur = {id_cur}")  # Системная функция для отладки, показывает в терминале айди основной
        # валюты
        for i in rates:  # Цикл для записи всех валют для конвертации
            code = i.code  # записывает в переменную название конвертируемой валюты
            rate = i.rate  # записывает в переменную курс конвертируемой валюты

            cursor.execute("""insert into currency_rates_values (currency_code,rate,currency_rate_id)
                                         values (%(code)s, %(rate)s, %(id_cur)s);""",
                           {"code": code, "rate": rate, "id_cur": id_cur}
                           )
            conn.commit()
        return

    except Exception as e:  # в случае ошибки при выполнение основного тела выполняет следующее тело
        logging.error("Error while saving currency rate", e)  # Системная функция для отладки, показывает в терминале
        # ошибку
        raise HTTPException(500)  # Вовращает в бота ошибку выполнения


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, port=10660, host='localhost')
