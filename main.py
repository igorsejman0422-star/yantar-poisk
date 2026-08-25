import os
import json

import time

import hashlib

from pathlib import Path

from urllib.parse import quote_plus

import requests

from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

DATA_FILE = Path("found.json")

SEARCHES = [

    '"Янтарь банжо" часы',

    '"Янтарь" "банжо" часы купить',

    '"Янтарь" настенные часы СССР',

    '"Янтарь" кварцевые часы СССР',

    '"Янтарь" часы СССР аукцион',

    '"Yantar" wall clock USSR',

    '"Yantar" banjo clock',

    '"Yantar" quartz wall clock',

    '"Янтарь" часы купить',

    '"Янтарь" часы коллекционные',

]

SITES = [

    "avito.ru",

    "meshok.net",

    "auction.ru",

    "ebay.com",

    "etsy.com",

    "catawiki.com",

    "delcampe.net",

    "allegro.pl",

    "kleinanzeigen.de",

    "leboncoin.fr",

    "todocoleccion.net",

    "ricardo.ch",

    "vinted.fr",

    "facebook.com",

    "instagram.com",

]

def load_found():

    if not DATA_FILE.exists():

        return {}

    try:

        return json.loads(DATA_FILE.read_text(encoding="utf-8"))

    except Exception:

        return {}

def save_found(found):

    DATA_FILE.write_text(

        json.dumps(found, ensure_ascii=False, indent=2),

        encoding="utf-8",

    )

def send_telegram(text):

    if not BOT_TOKEN or not CHAT_ID:

        print("Не задан TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")

        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(

        url,

        json={

            "chat_id": CHAT_ID,

            "text": text,

            "disable_web_page_preview": False,

        },

        timeout=30,

    )

    response.raise_for_status()

def search_web(query):

    url = (

        "https://html.duckduckgo.com/html/"

        f"?q={quote_plus(query)}"

    )

    headers = {

        "User-Agent": (

            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 "

            "like Mac OS X) AppleWebKit/605.1.15 "

            "Version/17.0 Mobile/15E148 Safari/604.1"

        )

    }

    response = requests.get(

        url,

        headers=headers,

        timeout=30,

    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for item in soup.select(".result"):

        link = item.select_one(".result__a")

        if not link:

            continue

        title = link.get_text(" ", strip=True)

        href = link.get("href", "")

        snippet_el = item.select_one(".result__snippet")

        description = (

            snippet_el.get_text(" ", strip=True)

            if snippet_el

            else ""

        )

        if not href:

            continue

        results.append(

            {

                "title": title,

                "url": href,

                "description": description,

            }

        )

    return results

def looks_like_yantar(item):

    text = (

        item.get("title", "")

        + " "

        + item.get("description", "")

        + " "

        + item.get("url", "")

    ).lower()

    good_words = [

        "янтарь",

        "yantar",

        "yantarb",

        "yantarь",

    ]

    clock_words = [

        "часы",

        "настенные",

        "wall clock",

        "clock",

        "uhr",

        "zegar",

    ]

    has_brand = any(word in text for word in good_words)

    has_clock = any(word in text for word in clock_words)

    return has_brand and has_clock

def make_id(item):

    raw = item["url"] + item["title"]

    return hashlib.sha256(

        raw.encode("utf-8")

    ).hexdigest()

def main():

    if not BOT_TOKEN:

        print("Ошибка: не найден TELEGRAM_BOT_TOKEN")

        return

    if not CHAT_ID:

        print("Ошибка: не найден TELEGRAM_CHAT_ID")

        return

    found = load_found()

    new_items = []

    print("Начинаю поиск часов Янтарь...")

    for query in SEARCHES:

        print(f"Поиск: {query}")

        try:

            results = search_web(query)

        except Exception as error:

            print(f"Ошибка поиска: {error}")

            continue

        for item in results:

            if not looks_like_yantar(item):

                continue

            item_id = make_id(item)

            if item_id in found:

                continue

            found[item_id] = {

                "title": item["title"],

                "url": item["url"],

                "date": time.strftime("%Y-%m-%d %H:%M:%S"),

            }

            new_items.append(item)

        time.sleep(2)

    save_found(found)

    if not new_items:

        send_telegram(

            "🕰 Проверка завершена.\n\n"

            "Новых объявлений с часами «Янтарь» не найдено."

        )

        print("Новых объявлений нет.")

        return

    send_telegram(

        f"🕰 НАЙДЕНО НОВЫХ ОБЪЯВЛЕНИЙ: {len(new_items)}"

    )

    for item in new_items[:10]:

        message = (

            "🕰 НОВАЯ НАХОДКА\n\n"

            f"{item['title']}\n\n"

            f"{item['description'][:500]}\n\n"

            f"🔗 {item['url']}"

        )

        try:

            send_telegram(message)

        except Exception as error:

            print(f"Ошибка Telegram: {error}")

        time.sleep(1)

if __name__ == "__main__":

    main()
