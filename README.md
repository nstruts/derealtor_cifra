# derealtor_cifra

Документация к коду в main.py

1. Библиотеки и модули

1. asyncio: для асинхронного управления задачами.
2. telethon: для взаимодействия с API Telegram.
3. logging: для системного логирования и вывода отладочной информации.
4. openai: для интеграции с сервисами OpenAI.
5. dotenv: для загрузки переменных окружения из файла .env.
6. pandas и numpy: для работы с данными и выполнения численных операций.
7. sklearn.metrics.pairwise: для расчета косинусного сходства.
8. csv и json: для чтения и записи данных в форматах CSV и JSON.
9. concurrent.futures: для выполнения параллельных задач.

2. Конфигурация и настройка

1. Загружает переменные окружения, включая ключи API и названия каналов.
2. Инициализирует TelegramClient с этими учетными данными.
3. Создает глобальный DataFrame, ads_df, для хранения данных объявлений.
4. Если файл CSV (ads_data.csv) существует, загружает предыдущие объявления, иначе инициализирует пустой DataFrame.

3. Классы

1. Location: хранит атрибуты местоположения, такие как city, metro и необязательный address.
2. Apartment: содержит характеристики квартиры, такие как количество комнат, тип ремонта и наличие мебели.
3. Building: описывает атрибуты здания, такие как наличие парковки, удаленность от метро и близлежащая инфраструктура.
4. Finance: содержит финансовые параметры, такие как ежемесячная цена, коммунальные платежи, залог и комиссия.
5. Advertisement: объединяет Location, Apartment, Building и Finance для представления полного объявления о недвижимости.

4. Основные функции
1. print_advertisement_info(ad): форматирует и отображает все детали объявления, получая каждый атрибут из Location, Apartment, Building и Finance.
2. ad_to_vector(ad): преобразует экземпляр Advertisement в числовой вектор. Каждый атрибут преобразуется или кодируется для создания структурированного вектора признаков, который может быть полезен для сравнения схожести или использования в моделях машинного обучения.
3. Функции кодирования категориальных признаков:
4. encode_city(city): кодирует названия городов в уникальные целые числа.
5. encode_metro(metro): преобразует названия станций метро в уникальные значения.
6. Дополнительные функции кодирования (не полностью показаны) вероятно обрабатывают категориальные признаки, такие как тип ремонта, наличие балкона, тип парковки и т.д.

5. Хранение и обработка данных

1. DataFrame ads_df сохраняется в ads_data.csv после каждого обновления, что гарантирует сохранение данных.
2. Каждое объявление обрабатывается и сохраняется в виде вектора для простого извлечения и анализа сходства.

6. Обработка ошибок и логирование

1. Убеждается, что все необходимые переменные окружения загружены, и завершает работу, если каких-либо данных не хватает.
2. Логирует информацию о конфигурации для отладки, маскируя конфиденциальные данные, такие как ключи API.
