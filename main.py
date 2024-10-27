import asyncio
from telethon import TelegramClient, errors
import logging
import openai
import time
from functools import lru_cache
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from openai.error import OpenAIError, RateLimitError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение переменных из окружения
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
openai_api_key = os.getenv('OPENAI_API_KEY')

CHANNEL_USERNAME_1 = os.getenv('CHANNEL_USERNAME_1')
CHANNEL_USERNAME_2 = os.getenv('CHANNEL_USERNAME_2')
CHANNEL_USERNAME_3 = os.getenv('CHANNEL_USERNAME_3')

# Отладочный вывод для проверки загрузки переменных
logger.info(f"API_ID: {api_id}")
logger.info(f"API_HASH: {api_hash}")
logger.info(f"OPENAI_API_KEY: {'***' if openai_api_key else None}")
logger.info(f"CHANNEL_USERNAME_1: {CHANNEL_USERNAME_1}")
logger.info(f"CHANNEL_USERNAME_2: {CHANNEL_USERNAME_2}")
logger.info(f"CHANNEL_USERNAME_3: {CHANNEL_USERNAME_3}")

# Проверка, что все необходимые переменные заданы
if not all([api_id, api_hash, openai_api_key, CHANNEL_USERNAME_1, CHANNEL_USERNAME_2, CHANNEL_USERNAME_3]):
    logger.error("Одно или несколько необходимых значений не заданы в .env")
    exit(1)

# Установка ключа OpenAI
openai.api_key = openai_api_key

# Создание клиента Telegram
client = TelegramClient('session_name', api_id, api_hash)

# Список каналов для парсинга
channels = [
    CHANNEL_USERNAME_1,
    CHANNEL_USERNAME_2,
    CHANNEL_USERNAME_3
]

# Проверка, что все каналы были загружены
if not all(channels):
    logger.error("Не все ссылки на каналы были найдены в .env")
    exit(1)

# Глобальный DataFrame для хранения объявлений
try:
    ads_df = pd.read_csv('ads_data.csv')
    # Преобразуем колонку 'vector' из строкового представления в массив numpy
    ads_df['vector'] = ads_df['vector'].apply(lambda x: np.fromstring(x.strip('[]'), sep=' '))
    logger.info("Loaded existing data from ads_data.csv")
except FileNotFoundError:
    ads_df = pd.DataFrame(columns=['message_id', 'channel_id', 'url', 'vector'])
    logger.info("No existing data found. Starting with an empty dataset.")

# Определение классов

class Location:
    def __init__(self, city, metro, address=None):
        self.city = city
        self.metro = metro
        self.address = address

class Apartment:
    def __init__(self, rooms, renovation, kitchen_combined, isolated_rooms,
                 bathroom, balcony, wardrobe, furnishing):
        self.rooms = rooms
        self.renovation = renovation
        self.kitchen_combined = kitchen_combined
        self.isolated_rooms = isolated_rooms
        self.bathroom = bathroom
        self.balcony = balcony
        self.wardrobe = wardrobe
        self.furnishing = furnishing

class Building:
    def __init__(self, parking, proximity_to_metro, infrastructure):
        self.parking = parking
        self.proximity_to_metro = proximity_to_metro
        self.infrastructure = infrastructure

class Finance:
    def __init__(self, price_per_month, utilities_payment, deposit, commission,
                 living_conditions, contact_info):
        self.price_per_month = price_per_month
        self.utilities_payment = utilities_payment
        self.deposit = deposit
        self.commission = commission
        self.living_conditions = living_conditions
        self.contact_info = contact_info

class Advertisement:
    def __init__(self, location, apartment, building, finance):
        self.location = location
        self.apartment = apartment
        self.building = building
        self.finance = finance

# Функции для вывода информации об объявлении

def print_advertisement_info(ad):
    print("Location:")
    print(f"  City: {ad.location.city}")
    print(f"  Metro: {ad.location.metro}")
    print(f"  Address: {ad.location.address if ad.location.address else 'Not specified'}")
    print("\nApartment:")
    print(f"  Number of rooms: {ad.apartment.rooms}")
    print(f"  Renovation: {ad.apartment.renovation}")
    print(f"  Kitchen combined with room: {'Yes' if ad.apartment.kitchen_combined else 'No'}")
    print(f"  Isolated rooms: {ad.apartment.isolated_rooms}")
    print(f"  Bathroom: {ad.apartment.bathroom}")
    print(f"  Balcony/Loggia: {ad.apartment.balcony}")
    print(f"  Wardrobe: {'Yes' if ad.apartment.wardrobe else 'No'}")
    print(f"  Furnishing: {ad.apartment.furnishing}")
    print("\nBuilding:")
    print(f"  Parking: {ad.building.parking}")
    print(f"  Proximity to metro: {ad.building.proximity_to_metro} minutes on foot")
    print(f"  Infrastructure: {ad.building.infrastructure}")
    print("\nFinance:")
    print(f"  Price per month: {ad.finance.price_per_month}₽")
    print(f"  Utilities payment: {ad.finance.utilities_payment}")
    print(f"  Deposit: {ad.finance.deposit}")
    print(f"  Commission: {ad.finance.commission}")
    print(f"  Living conditions: {ad.finance.living_conditions}")
    print(f"  Contact information: {ad.finance.contact_info}")

# Функции для преобразования объявления в вектор

def ad_to_vector(ad):
    vector = []

    # Location
    vector.append(encode_city(ad.location.city))
    vector.append(encode_metro(ad.location.metro))
    vector.append(len(ad.location.address) if ad.location.address else 0)

    # Apartment
    vector.append(ad.apartment.rooms)
    vector.append(encode_renovation(ad.apartment.renovation))
    vector.append(1 if ad.apartment.kitchen_combined else 0)
    vector.append(ad.apartment.isolated_rooms)
    vector.append(encode_bathroom(ad.apartment.bathroom))
    vector.append(encode_balcony(ad.apartment.balcony))
    vector.append(1 if ad.apartment.wardrobe else 0)
    vector.append(len(ad.apartment.furnishing.split()))

    # Building
    vector.append(encode_parking(ad.building.parking))
    vector.append(ad.building.proximity_to_metro)
    vector.append(len(ad.building.infrastructure.split()))

    # Finance
    vector.append(ad.finance.price_per_month)
    vector.append(encode_utilities_payment(ad.finance.utilities_payment))
    vector.append(encode_deposit(ad.finance.deposit))
    vector.append(encode_commission(ad.finance.commission))
    vector.append(len(ad.finance.living_conditions.split()))
    vector.append(len(ad.finance.contact_info))

    return np.array(vector)

# Функции кодирования категориальных признаков

def encode_city(city):
    cities = {
        "Moscow": 1,
        "Saint Petersburg": 2,
        # Добавьте другие города по необходимости
    }
    return cities.get(city, 0)


def encode_metro(metro):
    metro_stations = {
        "Aeroport": 1,
        "Akademicheskaya": 2,
        "Aleksandrovsky Sad": 3,
        "Alma-Atinskaya": 4,
        "Altufyevo": 5,
        "Arbatskaya": 6,
        "Aviamotornaya": 7,
        "Babushkinskaya": 8,
        "Bagrationovskaya": 9,
        "Belyayevo": 10,
        "Belorusskaya": 11,
        "Bibirevo": 12,
        "Borisovo": 13,
        "Borovitskaya": 14,
        "Botanichesky Sad": 15,
        "Bratislavskaya": 16,
        "Bulvar Admirala Ushakova": 17,
        "Bulvar Dmitriya Donskogo": 18,
        "Butyrskaya": 19,
        "Chertanovskaya": 20,
        "Chekhovskaya": 21,
        "Chistye Prudy": 22,
        "Chkalovskaya": 23,
        "Dmitrovskaya": 24,
        "Dinamo": 25,
        "Dobryninskaya": 26,
        "Domodedovskaya": 27,
        "Dostoyevskaya": 28,
        "Dubrovka": 29,
        "Elektrozavodskaya": 30,
        "Fili": 31,
        "Filyovsky Park": 32,
        "Fonvizinskaya": 33,
        "Frunzenskaya": 34,
        "Kaluzhskaya": 35,
        "Kantemirovskaya": 36,
        "Kashirskaya": 37,
        "Kitay-Gorod": 38,
        "Kolomenskaya": 39,
        "Komsomolskaya": 40,
        "Kropotkinskaya": 41,
        "Krylatskoye": 42,
        "Kuznetsky Most": 43,
        "Leninsky Prospekt": 44,
        "Lermontovsky Prospekt": 45,
        "Lomonosovsky Prospekt": 46,
        "Lubyanka": 47,
        "Marksistskaya": 48,
        "Marino": 49,
        "Maryina Roshcha": 50,
        "Mayakovskaya": 51,
        "Medvedkovo": 52,
        "Mezhdunarodnaya": 53,
        "Michurinsky Prospekt": 54,
        "Molodezhnaya": 55,
        "Molodyozhnaya": 56,
        "Moskovskaya": 57,
        "Nagatinskaya": 58,
        "Nagornaya": 59,
        "Nakhimovsky Prospekt": 60,
        "Nekrasovka": 61,
        "Novogireyevo": 62,
        "Novokosino": 63,
        "Novokuznetskaya": 64,
        "Novoslobodskaya": 65,
        "Okhotny Ryad": 66,
        "Oktyabrskaya": 67,
        "Orekhovo": 68,
        "Otradnoye": 69,
        "Paveletskaya": 70,
        "Pechatniki": 71,
        "Perovo": 72,
        "Pervomayskaya": 73,
        "Petrovsko-Razumovskaya": 74,
        "Pionerskaya": 75,
        "Planernaya": 76,
        "Ploshchad Ilyicha": 77,
        "Ploshchad Revolyutsii": 78,
        "Polezhayevskaya": 79,
        "Polyanka": 80,
        "Prazhskaya": 81,
        "Preobrazhenskaya Ploshchad": 82,
        "Proletarskaya": 83,
        "Prospekt Mira": 84,
        "Pushkinskaya": 85,
        "Ramenki": 86,
        "Rechnoy Vokzal": 87,
        "Rimskaya": 88,
        "Rizhskaya": 89,
        "Rumyantsevo": 90,
        "Ryazansky Prospekt": 91,
        "Savyolovskaya": 92,
        "Sevastopolskaya": 93,
        "Semyonovskaya": 94,
        "Serpukhovskaya": 95,
        "Sokol": 96,
        "Sokolniki": 97,
        "Sportivnaya": 98,
        "Sretensky Bulvar": 99,
        "Strogino": 100,
        "Studencheskaya": 101,
        "Sukharevskaya": 102,
        "Sviblovo": 103,
        "Taganskaya": 104,
        "Tekstilshchiki": 105,
        "Teatralnaya": 106,
        "Teply Stan": 107,
        "Tverskaya": 108,
        "Timiryazevskaya": 109,
        "Troparevo": 110,
        "Tulskaya": 111,
        "Turgenevskaya": 112,
        "Tushinskaya": 113,
        "Ulitsa 1905 Goda": 114,
        "Ulitsa Akademika Korolyova": 115,
        "Ulitsa Gorchakova": 116,
        "Ulitsa Starokachalovskaya": 117,
        "Universitet": 118,
        "Varshavskaya": 119,
        "VDNKh": 120,
        "Vernadskogo Prospekt": 121,
        "Vladykino": 122,
        "Vodny Stadion": 123,
        "Voykovskaya": 124,
        "Vykhino": 125,
        "Yasenevo": 126,
        "Yugo-Zapadnaya": 127,
        "Yuzhnaya": 128,
        "Vorobyovy Gory": 129,
        "Zyablikovo": 130,
        "Pionerskaya": 131,
        "Slavyansky Bulvar": 132,
        "Kuntsevskaya": 133,
        "Kaluzhskaya": 134,
        "Kitay-Gorod": 135,
        "Komsomolskaya": 136,
        "Krasnye Vorota": 137,
        "Park Kultury": 138,
        "Vorobyevy Gory": 139,
        "Medvedkovo": 140,
        "Skhodnenskaya": 141,
        "Strogino": 142,
        "Ulitsa Starokachalovskaya": 143,
        "Troparevo": 144,
        "Vladykino": 145,
        "Mitino": 146,
        "Sokol": 147,
        "Zhulebino": 148,
        "Vorobyovy Gory": 149,
        "Lubyanka": 150,
        "Leninsky Prospekt": 151,
        "Ulitsa 1905 Goda": 152,
        "Universitet": 153,
        "Avtozavodskaya": 154,
        "Molodezhnaya": 155,
        "Pionerskaya": 156,
        "Petrovsko-Razumovskaya": 157,
        "Savyolovskaya": 158,
        "Trubnaya": 159,
        "Sheremetyevskaya": 160,
        "Kantemirovskaya": 161,
        "Turgenevskaya": 162,
        "Avtozavodskaya": 163,
        "Yasenevo": 164,
        "Pionerskaya": 165,
        "Paveletskaya": 166,
        "Ulitsa Starokachalovskaya": 167,
        "Vorobyovy Gory": 168,
        "Nagornaya": 169,
        "Polyanka": 170,
        "Novoslobodskaya": 171,
        "Ploshchad Ilyicha": 172,
        "Ryazansky Prospekt": 173,
        "Shabolovskaya": 174,
        "Kropotkinskaya": 175,
        "Rimskaya": 176,
        "Kitay-Gorod": 177,
        "Baumanskaya": 178,
        "Dinamo": 179,
        "Aleksandrovsky Sad": 180,
        "Kievskaya": 181,
        "Nagatinskaya": 182,
        "Novokosino": 183,
        "Mitino": 184,
        "Arbatskaya": 185,
        "Smolenskaya": 186,
        "Novye Cheryomushki": 187,
        "Otradnoye": 188,
        "Paveletskaya": 189,
        "Park Pobedy": 190,
        "Partizanskaya": 191,
        "Petrovsko-Razumovskaya": 192,
        "Ploshchad Ilyicha": 193,
        "Polezhayevskaya": 194,
        "Polyanka": 195,
        "Prazhskaya": 196,
        "Preobrazhenskaya Ploshchad": 197,
        "Profsoyuznaya": 198,
        "Prokshino": 199,
        "Proletarskaya": 200,
        "Pushkinskaya": 201,
        "Ramenki": 202,
        "Rechnoy Vokzal": 203,
        "Rizhskaya": 204,
        "Rumyantsevo": 205,
        "Ryazansky Prospekt": 206,
        "Sevastopolskaya": 207,
        "Shabolovskaya": 208,
        "Shchelkovskaya": 209,
        "Semyonovskaya": 210,
        "Serpukhovskaya": 211,
        "Shchyolkovskaya": 212,
        "Skhodnenskaya": 213,
        "Sokolniki": 214,
        "Solntsevo": 215,
        "Sportivnaya": 216,
        "Sretensky Bulvar": 217,
        "Strogino": 218,
        "Studencheskaya": 219,
        "Sukharevskaya": 220,
        "Sviblovo": 221,
        "Taganskaya": 222,
        "Tekstilshchiki": 223,
        "Teatralnaya": 224,
        "Teply Stan": 225,
        "Timiryazevskaya": 226,
        "Tretyakovskaya": 227,
        "Trubnaya": 228,
        "Tulskaya": 229,
        "Turgenevskaya": 230,
        "Tushinskaya": 231,
        "Ulitsa 1905 Goda": 232,
        "Ulitsa Akademika Korolyova": 233,
        "Ulitsa Dmitriya Donskogo": 234,
        "Universitet": 235,
        "Varshavskaya": 236,
        "VDNKh": 237,
        "Vernadskogo Prospekt": 238,
        "Vladykino": 239,
        "Vodny Stadion": 240,
        "Voykovskaya": 241,
        "Vykhino": 242,
        "Yasenevo": 243,
        "Yugo-Zapadnaya": 244,
        "Yuzhnaya": 245,
        "Zyablikovo": 246,
        "Tsvetnoy Bulvar": 247,
        "Nekrasovka": 248,
        "Kashirskaya": 249,
        "Kantemirovskaya": 250,
        "Troparevo": 251,
        "Kuzminki": 252,
        "Savelovskaya": 253,
        "Streshnevo": 254,
        "Shelepikha": 255,
        "Khoroshevskaya": 256,
        "Nizhegorodskaya": 257,
        "Lefortovo": 258
        }
    return metro_stations.get(metro, 0)

def encode_renovation(renovation):
    options = {
        "No renovation": 0,
        "Cosmetic": 1,
        "Euro": 2,
        "Designer": 3
    }
    return options.get(renovation, 0)

def encode_bathroom(bathroom):
    options = {
        "Combined": 0,
        "Separate": 1,
        "Two or more": 2
    }
    return options.get(bathroom, 0)

def encode_balcony(balcony):
    options = {
        "No": 0,
        "Balcony": 1,
        "Loggia": 2,
        "Two or more": 3
    }
    return options.get(balcony, 0)

def encode_parking(parking):
    options = {
        "No": 0,
        "In the yard": 1,
        "Guarded": 2,
        "Underground": 3
    }
    return options.get(parking, 0)

def encode_utilities_payment(payment):
    options = {
        "Included": 0,
        "Separately": 1,
        "Partially": 2
    }
    return options.get(payment, 0)

def encode_deposit(deposit):
    options = {
        "No deposit": 0,
        "0.5 month": 0.5,
        "1 month": 1,
        "2 months": 2
    }
    return options.get(deposit, 0)

def encode_commission(commission):
    options = {
        "No commission": 0,
        "50%": 0.5,
        "100%": 1
    }
    return options.get(commission, 0)

# Создание пула потоков для асинхронного вызова OpenAI API
executor = ThreadPoolExecutor(max_workers=5)

# Функции для работы с OpenAI API

@lru_cache(maxsize=10000)
async def is_rental_ad(text):
    try:
        prompt = f"Is this message an advertisement for renting an apartment? Answer 'Yes' or 'No'.\n\nMessage: {text}"
        response = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=1,
                temperature=0
            )
        )
        answer = response.choices[0].text.strip()
        return answer.lower() == 'yes'
    except error.RateLimitError:
        logger.warning("OpenAI API rate limit reached. Waiting for 60 seconds.")
        await asyncio.sleep(60)
        return await is_rental_ad(text)
    except error.OpenAIError as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

async def extract_data_from_text(text):
    try:
        prompt = f"Extract information from the advertisement and present it in JSON format with keys: 'city', 'metro', 'address', 'rooms', 'renovation', 'kitchen_combined', 'isolated_rooms', 'bathroom', 'balcony', 'wardrobe', 'furnishing', 'parking', 'proximity_to_metro', 'infrastructure', 'price_per_month', 'utilities_payment', 'deposit', 'commission', 'living_conditions', 'contact_info'.\n\nAdvertisement: {text}\n\nJSON:"
        response = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=500,
                temperature=0
            )
        )
        json_data = response.choices[0].text.strip()
        data = json.loads(json_data)

        # Создание объектов на основе данных
        location = Location(
            city=data.get('city'),
            metro=data.get('metro'),
            address=data.get('address')
        )

        apartment = Apartment(
            rooms=int(data.get('rooms', 0)),
            renovation=data.get('renovation'),
            kitchen_combined=data.get('kitchen_combined') == 'Yes',
            isolated_rooms=int(data.get('isolated_rooms', 0)),
            bathroom=data.get('bathroom'),
            balcony=data.get('balcony'),
            wardrobe=data.get('wardrobe') == 'Yes',
            furnishing=data.get('furnishing')
        )

        building = Building(
            parking=data.get('parking'),
            proximity_to_metro=int(data.get('proximity_to_metro', 0)),
            infrastructure=data.get('infrastructure')
        )

        finance = Finance(
            price_per_month=int(data.get('price_per_month', 0)),
            utilities_payment=data.get('utilities_payment'),
            deposit=data.get('deposit'),
            commission=data.get('commission'),
            living_conditions=data.get('living_conditions'),
            contact_info=data.get('contact_info')
        )

        ad = Advertisement(
            location=location,
            apartment=apartment,
            building=building,
            finance=finance
        )

        return ad

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from OpenAI response.")
        return None
    except error.OpenAIError as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting data: {e}")
        return None

# Функции для работы с таблицей данных

def save_to_table(record):
    global ads_df
    new_row = {
        'message_id': record['message_id'],
        'channel_id': record['channel_id'],
        'url': record['url'],
        'vector': record['vector']
    }
    ads_df = ads_df.append(new_row, ignore_index=True)
    # Сохраняем DataFrame в CSV файл
    # Преобразуем вектор в строку для сохранения
    ads_df['vector'] = ads_df['vector'].apply(lambda x: np.array2string(x, separator=' ')[1:-1])
    ads_df.to_csv('ads_data.csv', index=False)
    # Восстанавливаем вектор обратно после сохранения
    ads_df['vector'] = ads_df['vector'].apply(lambda x: np.fromstring(x.strip('[]'), sep=' '))

def find_similar_ads(vector, threshold=0.9):
    global ads_df
    if ads_df.empty:
        return []
    vectors = np.vstack(ads_df['vector'].values)
    similarities = cosine_similarity([vector], vectors)[0]
    similar_indices = np.where(similarities >= threshold)[0]
    similar_ads = ads_df.iloc[similar_indices]
    return similar_ads.to_dict('records')

# Основные функции обработки сообщений

async def handle_message(message, channel_username):
    text = message.text
    if not text:
        return

    try:
        if await is_rental_ad(text):
            ad = await extract_data_from_text(text)
            if ad is None:
                logger.warning("Failed to extract data from advertisement.")
                return
            vector = ad_to_vector(ad)
            similar_ads = find_similar_ads(vector)
            if not similar_ads:
                url = f"https://t.me/{channel_username}/{message.id}"
                record = {
                    'message_id': message.id,
                    'channel_id': message.chat_id,
                    'url': url,
                    'vector': vector
                }
                save_to_table(record)
                logger.info(f"Saved advertisement from channel {channel_username}: {url}")
            else:
                logger.info(f"Similar advertisement already exists. Channel: {channel_username}")
        else:
            logger.info(f"Message is not an apartment rental advertisement. Channel: {channel_username}")
    except Exception as e:
        logger.error(f"Error processing message {message.id} from channel {channel_username}: {e}")

async def process_channel_messages(channel_username):
    logger.info(f"Starting to process channel: {channel_username}")
    try:
        async for message in client.iter_messages(channel_username, limit=100):
            await handle_message(message, channel_username)
    except errors.RPCError as e:
        logger.error(f"Telegram API error while processing channel {channel_username}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while processing channel {channel_username}: {e}")

async def process_messages():
    try:
        await client.start()
        logger.info("Telegram client started successfully.")
        tasks = []
        for channel in channels:
            task = asyncio.create_task(process_channel_messages(channel))
            tasks.append(task)
        await asyncio.gather(*tasks)
    except errors.RPCError as e:
        logger.error(f"Telegram API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await client.disconnect()
        logger.info("Telegram client disconnected.")

# Функция для проверки доступа к каналам (опционально)

async def check_channels():
    logger.info("Checking access to channels...")
    for channel in channels:
        try:
            entity = await client.get_entity(channel)
            logger.info(f"Access to channel {channel} granted.")
        except errors.UsernameNotOccupiedError:
            logger.error(f"No user has {channel} as username.")
        except errors.ChannelPrivateError:
            logger.error(f"Channel {channel} is private or you don't have access.")
        except Exception as e:
            logger.error(f"Failed to access channel {channel}: {e}")

# Основная асинхронная функция

async def main():
    await client.start()
    await check_channels()
    await process_messages()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    finally:
        loop.close()