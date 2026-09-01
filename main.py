import os

import re

import json

import time

import html

import requests

from pathlib import Path

from urllib.parse import quote, urlparse

# ==========================================

# НАСТРОЙКИ

# ==========================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEARCH_QUERIES = [

    "часы Янтарь",

    "настенные часы Янтарь",

    "часы Янтарь банджо",

    "часы Янтарь банжо",

    "Янтарь часы маятниковые",

]

SITES = {

    "Авито": "site:avito.ru",

    "Мешок": "site:meshok.net",

    "Юла": "site:youla.ru",

    "FarPost": "site:farpost.ru",

}

SEEN_FILE = Path("seen_ads.json")

HEADERS = {

    "User-Agent": (

        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

        "AppleWebKit/537.36 Chrome/120 Safari/537.36"

    )

}

# ==========================================

# РАБОТА С ПАМЯТЬЮ ПРОГРАММЫ

# ==========================================

def load_seen():

    if SEEN_FILE.exists():

        try:

            with open(SEEN_FILE, "r", encoding="utf-8") as file:

                return set(json.load(file))

        except Exception:

            return set()

    return set()

def save_seen(seen):

    with open(SEEN_FILE, "w", encoding="utf-8") as file:

        json.dump(list(seen), file, ensure_ascii=False, indent=2)

# ==========================================

# ПОИСК ЧЕРЕЗ BING

# ==========================================

def search_bing(query):

    url = "https://www.bing.com/search?q=" + quote(query)

    try:

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=20

        )

        response.raise_for_status()

        text = response.text

    except Exception as error:

        print("Ошибка поиска:", error)

        return []

    results = []

    pattern = re.compile(

        r'<li class="b_algo".*?<h2><a href="(.*?)".*?>(.*?)</a>',

        re.DOTALL

    )

    matches = pattern.findall(text)

    for link, title in matches:

        title = re.sub("<.*?>", "", title)

        title = html.unescape(title)

        link = html.unescape(link)

        if link.startswith("http"):

            results.append({

                "title": title.strip(),

                "url": link

            })

    return results

# ==========================================

# ПРОВЕРКА ССЫЛОК

# ==========================================

def is_valid_result(url):

    bad_words = [

        "bing.com",

        "microsoft.com",

        "account",

        "login",

        "support"

    ]

    domain = urlparse(url).netloc.lower()

    for word in bad_words:

        if word in domain:

            return False

    return True

# ==========================================

# ОТПРАВКА В TELEGRAM

# ==========================================

def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:

        print("Не найдены настройки Telegram.")

        print(message)

        return

    url = (

        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    )

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

        response.raise_for_status()

    except Exception as error:

        print("Ошибка Telegram:", error)

# ==========================================

# ОСНОВНОЙ ПОИСК

# ==========================================

def main():

    print("Запуск поиска часов Янтарь...")

    seen = load_seen()

    new_results = []

    for site_name, site_query in SITES.items():

        print(f"\nПоиск на сайте: {site_name}")

        for search_query in SEARCH_QUERIES:

            full_query = (

                f"{site_query} {search_query}"

            )

            print("Запрос:", full_query)

            results = search_bing(full_query)

            for result in results:

                title = result["title"]

                url = result["url"]

                if not is_valid_result(url):

                    continue

                if url in seen:

                    continue

                new_results.append({

                    "site": site_name,

                    "title": title,

                    "url": url

                })

                seen.add(url)

            time.sleep(2)

    save_seen(seen)

    print(f"\nНайдено новых объявлений: {len(new_results)}")

    if not new_results:

        print("Новых объявлений нет.")

        return

    message = "🕰 НОВЫЕ НАХОДКИ ЯНТАРЬ\n\n"

    for item in new_results:

        message += (

            f"📍 {item['site']}\n"

            f"🕰 {item['title']}\n"

            f"{item['url']}\n\n"

        )

    # Telegram ограничивает размер одного сообщения,

    # поэтому отправляем частями.

    max_length = 3500

    while message:

        part = message[:max_length]

        if len(message) > max_length:

            last_break = part.rfind("\n\n")

            if last_break > 0:

                part = part[:last_break]

        send_telegram(part)

        message = message[len(part):].lstrip()

        time.sleep(1)

    print("Новые объявления отправлены в Telegram.")

if __name__ == "__main__":

    main()
