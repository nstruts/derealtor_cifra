from gpt_testing import *
import os
from openai import OpenAI
from config import *
import threading,time
from flask import Flask, send_file, request, jsonify

client = OpenAI()
vs_file = 'DataStore/vector_store.json'

app = Flask(__name__)

# Папка с изображениями
IMAGE_FOLDER = 'ads/1'
os.makedirs(IMAGE_FOLDER, exist_ok=True)  # Создание папки, если её нет


@app.route('/get-image', methods=['GET'])
def get_image():
    # Получение имени файла из параметров запроса
    filename = request.args.get('filename')
    print(filename)
    if not filename:
        return jsonify({"error": "Filename not provided"}), 400

    # Путь к изображению
    file_path = os.path.join(IMAGE_FOLDER, filename)
    print(file_path)

    # Проверка, существует ли файл
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404  # Не забывайте return

    # Отправка изображения
    return send_file(file_path, mimetype='image/jpeg')  # Не забудьте return

def make_prompt():
    pass

def make_image_url():
    pass

def run_nota_flask():
    vs = load_json(vs_file)
    for s in os.listdir('ads'):
        if s in ['text','Summaries']:
            continue
        images = []
        for filename in os.listdir('ads/'+s):
            # Проверяем, является ли файл изображением
            if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                print(filename)  # Выводим имя файла





if __name__ == '__main__':
    nota_flask_thread = threading.Thread(target=run_nota_flask)
    nota_flask_thread.start()
    app.run(debug=True, port=PORT)
    # Основной поток может выполнять другие задачи
    # Добавим небольшую задержку для наглядности