@startuml
actor "User" as user
entity "Telegram-bot" as bot
entity "Currency-manager" as currency_manager
entity "Convertor" as convertor

user -> bot : запрос на добавление новой валюты
bot -> currency_manager : запрос на добавление новой валюты с указанными пользователем данными
currency_manager -> user : ответ об успешном сохранении нового курса валют
user -> bot : запрос на конвертацию валюты
bot -> convertor : запрос на конвертацию валюты с указанными пользователем данными
convertor -> user : ответ с результатом конвертации

@enduml