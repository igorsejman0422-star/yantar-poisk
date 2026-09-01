import os

import re

import json

import time

import hashlib

from pathlib import Path

from urllib.parse import quote_plus

import requests

# ============================================================

# НАСТРОЙКИ

# ============================================================

# Telegram

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID = os.getenv("CHAT_ID")

# Файл, в котором будут храниться уже найденные объявления

SEEN_FILE = "seen.json"

# Сколько результатов брать по каждому запросу

MAX_RESULTS = 10

# Поисковые запросы

SEARCH_QUERIES = [

    # Основной поиск

    "часы Янтарь банджо",

    "часы Янтарь банжо",

    "Янтарь часы банджо",

    "Янтарь часы банжо",

    # Возможные варианты написания

    "часы Янтарь маятниковые",

    "Янтарь настенные маятник",

    "часы Янтарь необычная форма",

    "часы Янтарь редкие",

    # Поиск по конкретным российским площадкам

    "site:avito.ru часы Янтарь банджо",

    "site:meshok.net часы Янтарь банджо",

    "site:youla.ru часы Янтарь",

    "site:auction.ru часы Янтарь",

    "site:festima.ru часы Янтарь банджо",

    # Дополнительные варианты

    "часы Янтарь СССР банджо",

    "часы Янтарь кварцевые банджо",

    "часы Янтарь настенные необычные СССР",

]

# ============================================================

# РАБОТА С СОХРАНЁННЫМИ ОБЪЯВЛЕНИЯМИ

# ============================================================

def load_seen():

    """Загружает список уже найденных объявлений."""

    if not os.path.exists(SEEN_FILE):

        return set()

    try:

        with open(SEEN_FILE, "r", encoding="utf-8") as file:

            data = json.load(file)

        return set(data)

    except Exception as error:

        print("Ошибка загрузки seen.json:", error)

        return set()

def save_seen(seen):

    """Сохраняет список уже найденных объявлений."""

    try:

        with open(SEEN_FILE, "w", encoding="utf-8") as file:

            json.dump(

                list(seen),

                file,

                ensure_ascii=False,

                indent=2

            )

    except Exception as error:

        print("Ошибка сохранения seen.json:", error)

# ============================================================

# TELEGRAM

# ============================================================

def send_telegram(message):

    """Отправляет сообщение в Telegram."""

    if not BOT_TOKEN:

        print("BOT_TOKEN не найден")

        return

    if not CHAT_ID:

        print("CHAT_ID не найден")

        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {

        "chat_id": CHAT_ID,

        "text": message,

        "disable_web_page_preview": False

    }

    try:

        response = requests.post(

            url,

            data=data,

            timeout=20

        )

        print("Telegram:", response.status_code)

    except Exception as error:

        print("Ошибка Telegram:", error)

# ============================================================

# ПОИСК

# ============================================================

def search_duckduckgo(query):

    """

    Ищет объявления через DuckDuckGo.

    """

    print()

    print("=" * 60)

    print("ПОИСК:", query)

    print("=" * 60)

    url = "https://html.duckduckgo.com/html/"

    headers = {

        "User-Agent": (

            "Mozilla/5.0 "

            "(iPhone; CPU iPhone OS 17_0 like Mac OS X) "

            "AppleWebKit/605.1.15 "

            "Version/17.0 "

            "Mobile/15E148 Safari/604.1"

        )

    }

    try:

        response = requests.post(

            url,

            data={

                "q": query

            },

            headers=headers,

            timeout=30

        )

        response.raise_for_status()

        html_text = response.text

    except Exception as error:

        print("Ошибка поиска:", error)

        return []

    # --------------------------------------------------------

    # Ищем ссылки

    # --------------------------------------------------------

    results = []

    pattern = (

        r'<a[^>]+class="result__a"'

        r'[^>]+href="([^"]+)"'

        r'[^>]*>(.*?)</a>'

    )

    matches = re.findall(

        pattern,

        html_text,

        re.DOTALL

    )

    for link, title in matches:

        # Убираем HTML-теги

        title = re.sub(

            r"<.*?>",

            "",

            title

        )

        title = title.strip()

        # Пропускаем пустые результаты

        if not title:

            continue

        results.append(

            {

                "title": title,

                "url": link

            }

        )

        if len(results) >= MAX_RESULTS:

            break

    return results

# ============================================================

# ПРОВЕРКА ПОДХОДЯЩЕГО ОБЪЯВЛЕНИЯ

# ============================================================

def is_interesting(title, url):

    """

    Проверяет, похоже ли объявление

    на интересующие часы Янтарь.

    """

    text = (

        title + " " + url

    ).lower()

    # Должно быть слово Янтарь

    if "янтар" not in text:

        return False

    # Особо интересные слова

    keywords = [

        "банджо",

        "банжо",

        "маятник",

        "маятников",

        "настенн",

        "кварц",

        "редк",

        "винтаж",

        "ссср"

    ]

    for word in keywords:

        if word in text:

            return True

    return False

# ============================================================

# СОЗДАНИЕ УНИКАЛЬНОГО ID

# ============================================================

def make_id(title, url):

    text = (

        title.strip().lower()

        +

        url.strip().lower()

    )

    return hashlib.md5(

        text.encode("utf-8")

    ).hexdigest()

# ============================================================

# ОСНОВНАЯ ПРОГРАММА

# ============================================================

def main():

    print()

    print("ЗАПУСК ПОИСКА ЧАСОВ ЯНТАРЬ")

    print()

    seen = load_seen()

    print(

        "Уже известных объявлений:",

        len(seen)

    )

    new_results = []

    # --------------------------------------------------------

    # Выполняем все поисковые запросы

    # --------------------------------------------------------

    for query in SEARCH_QUERIES:

        results = search_duckduckgo(query)

        print(

            "Найдено результатов:",

            len(results)

        )

        for item in results:

            title = item["title"]

            url = item["url"]

            # Проверяем интересность

            if not is_interesting(

                title,

                url

            ):

                continue

            item_id = make_id(

                title,

                url

            )

            # Если уже отправляли — пропускаем

            if item_id in seen:

                print(

                    "Уже было:",

                    title

                )

                continue

            print(

                "НОВОЕ:",

                title

            )

            seen.add(item_id)

            new_results.append(

                item

            )

        # Небольшая пауза между запросами

        time.sleep(2)

    # --------------------------------------------------------

    # Сохраняем найденные объявления

    # --------------------------------------------------------

    save_seen(seen)

    # --------------------------------------------------------

    # Отправляем результаты

    # --------------------------------------------------------

    if not new_results:

        message = (

            "🔍 Поиск часов Янтарь завершён.\n\n"

            "Новых подходящих объявлений "

            "в этот раз не найдено."

        )

        print(message)

        send_telegram(message)

        return

    # --------------------------------------------------------

    # Формируем сообщение

    # --------------------------------------------------------

    message = (

        "🕰 НАЙДЕНЫ НОВЫЕ ЧАСЫ ЯНТАРЬ\n\n"

    )

    for number, item in enumerate(

        new_results,

        start=1

    ):

        message += (

            f"{number}. {item['title']}\n"

            f"{item['url']}\n\n"

        )

    # Если сообщений слишком много —

    # Telegram может не принять длинный текст

    if len(message) > 3500:

        message = message[:3500]

        message += (

            "\n\n⚠️ Сообщение сокращено."

        )

    send_telegram(message)

    print()

    print("ГОТОВО")

    print(

        "Новых объявлений:",

        len(new_results)

    )

# ============================================================

# ЗАПУСК

# ============================================================

if __name__ == "__main__":

    main()
