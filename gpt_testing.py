
import os
import json
from openai import OpenAI
from config import *

client = OpenAI()
history_file = 'DataStore/history.json'
vs_file = 'DataStore/vector_store.json'
msgtmp_file = 'DataStore/message_template.json'

def load_json(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r',encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_json(data,file_name):
    with open(file_name, 'w',encoding='utf-8') as file:
        json.dump(data, file, indent=4)


def get_gpt_ans(req, id):
    id = str(id)
    history = load_json(history_file)

    if id not in history:
        history[id] = []

    history[id].append({"role": "user", "content": req})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # gpt-4o-mini; text-embedding-ada-002
        messages=history[id]  # Передаём всю историю для этого id
    )

    response = completion.choices[0].message.content

    history[id].append({"role": "assistant", "content": response})
    if len(history[id])>message_limit:
        history[id] = history[id][-message_limit:]

    save_json(history,history_file)

    return response

a = load_json('DataStore/message_template.json')
a['StartMessage'] = 'Привет! 👋\nЯ ваш помощник в поиске недвижимости 🏡. Расскажите, что именно вы ищете, и я помогу найти лучшие варианты на торговых площадках — быстро и удобно! Укажите основные критерии, такие как:\n• Тип недвижимости (квартира, дом, офис)\n• Район или метро Москвы\n• Бюджет\n• Желаемые параметры (количество комнат, этаж, площадь)\nНачнем? Напишите, что вас интересует, и я найду подходящие объявления! 🕵️‍♂'
save_json(a, 'DataStore/message_template.json')