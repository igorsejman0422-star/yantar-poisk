import os

import json

import time

import hashlib

from pathlib import Path

from urllib.parse import quote_plus

import requests

from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

DATA_FILE = Path("found.json")

SEARCHES = [

    '"Янтарь банжо" часы',

    '"Янтарь" банжо часы купить',

    '"Янтарь" настенные часы СССР',

    '"Янтарь" кварцевые часы СССР',

    '"Янтарь" часы СССР аукцион',

    '"Yantar" wall clock USSR',

    '"Yantar" banjo clock',

    '"Yantar" quartz wall clock',

    '"Янтарь" часы купить',

    '"Янтарь" часы коллекционные',

]

def send_telegram(text):

    if not BOT_TOKEN or not CHAT_ID:

        print("Ошибка: Telegram secrets не найдены")

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

    print("Сообщение отправлено в Telegram")

def search_web(query):

    url = (

        "https://html.duckduckgo.com/html/"

        f"?q={quote_plus(query)}"

    )

    headers = {

        "User-Agent": (

            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "

            "AppleWebKit/605.1.15 "

            "Version/17.0 Mobile/15E148 Safari/604.1"

        )

    }

    try:

        response = requests.get(

            url,

            headers=headers,

            timeout=30,

        )

        response.raise_for_status()

    except Exception as error:

        print(f"Ошибка поиска: {error}")

        return []

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for item in soup.select(".result"):

        link = item.select_one("a.result__a")

        if not link:

            continue

        title = link.get_text(" ", strip=True)

        href = link.get("href", "")

        snippet = item.select_one(".result__snippet")

        description = ""

        if snippet:

            description = snippet.get_text(" ", strip=True)

        if not href or not title:

            continue

        results.append({

            "title": title,

            "url": href,

            "description": description,

        })

    print(f"Найдено результатов: {len(results)}")

    return results

def looks_like_yantar(item):

    text = (

        item.get("title", "")

        + " "

        + item.get("description", "")

        + " "

        + item.get("url", "")

    ).lower()

    brand_words = [

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

        "кварцев",

        "quartz",

        "банжо",

        "banjo",

        "uhr",

        "zegar",

    ]

    has_brand = any(word in text for word in brand_words)

    has_clock = any(word in text for word in clock_words)

    return has_brand and has_clock

def make_id(item):

    raw = item.get("url", "") + item.get("title", "")

    return hashlib.sha256(

        raw.encode("utf-8")

    ).hexdigest()

def load_found():

    if not DATA_FILE.exists():

        return set()

    try:

        data = json.loads(

            DATA_FILE.read_text(encoding="utf-8")

        )

        return set(data)

    except Exception:

        return set()

def save_found(found):

    DATA_FILE.write_text(

        json.dumps(

            sorted(found),

            ensure_ascii=False,

            indent=2,

        ),

        encoding="utf-8",

    )

def main():

    print("Начинаю поиск часов Янтарь...")

    found = load_found()

    all_results = []

    for query in SEARCHES:

        print(f'Поиск: "{query}"')

        results = search_web(query)

        for item in results:

            if looks_like_yantar(item):

                all_results.append(item)

        time.sleep(1)

    unique = {}

    for item in all_results:

        unique[make_id(item)] = item

    new_items = []

    for item_id, item in unique.items():

        if item_id not in found:

            new_items.append(item)

    print(f"Всего подходящих результатов: {len(unique)}")

    print(f"Новых объявлений: {len(new_items)}")

    if new_items:

        message = (

            f"🕰 НАЙДЕНО НОВЫХ ОБЪЯВЛЕНИЙ: "

            f"{len(new_items)}"

        )

        send_telegram(message)

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

            found.add(make_id(item))

            time.sleep(1)

    else:

        print("Новых объявлений нет.")

    save_found(found)

    print("Поиск завершён.")

if __name__ == "__main__":

    main()
