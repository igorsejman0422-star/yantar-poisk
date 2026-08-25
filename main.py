import json

import time

import hashlib

from pathlib import Path

from urllib.parse import quote_plus

import requests

from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

SEARCHES = [

    '"часы Янтарь" настенные',

    '"настенные часы Янтарь"',

    '"Янтарь" "кварцевые" часы',

    '"Янтарь" часы СССР',

    '"Янтарь банжо"',

]

SITES = [

    "avito.ru",

    "meshok.net",

    "ebay.com",

    "allegro.pl",

    "olx.pl",

]

DATA_FILE = Path("found.json")

def load_found():

    if DATA_FILE.exists():

        try:

            return json.loads(DATA_FILE.read_text(encoding="utf-8"))

        except Exception:

            pass

    return {}

def save_found(found):

    DATA_FILE.write_text(

        json.dumps(found, ensure_ascii=False, indent=2),

        encoding="utf-8"

    )

def get_chat_id():

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

    response = requests.get(url, timeout=30)

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):

        return None

    updates = data.get("result", [])

    for update in reversed(updates):

        message = update.get("message")

        if message and message.get("chat"):

            return message["chat"]["id"]

    return None

def send_telegram(chat_id, text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(

        url,

        json={

            "chat_id": chat_id,

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

            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "

            "AppleWebKit/605.1.15 Safari/605.1"

        )

    }

    response = requests.get(

        url,

        headers=headers,

        timeout=30

    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for item in soup.select(".result"):

        link = item.select_one(".result__a")

        snippet = item.select_one(".result__snippet")

        if not link:

            continue

        title = link.get_text(" ", strip=True)

        href = link.get("href", "")

        if snippet:

            description = snippet.get_text(" ", strip=True)

        else:

            description = ""

        results.append({

            "title": title,

            "url": href,

            "description": description,

        })

    return results

def looks_like_yantar(item):

    text = (

        item["title"] + " " +

        item["description"] + " " +

        item["url"]

    ).lower()

    good_words = [

        "янтарь",

        "yantar",

        "yantarь",

    ]

    clock_words = [

        "часы",

        "настенные",

        "wall clock",

        "clock",

        "zegar",

        "uhr",

    ]

    return (

        any(word in text for word in good_words)

        and any(word in text for word in clock_words)

    )

def make_id(item):

    raw = item["url"] + item["title"]

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def main():

    chat_id = get_chat_id()

    if not chat_id:

        print("Не найден чат Telegram.")

        print("Откройте @YantarPoiskBot и нажмите Старт.")

        return

    found = load_found()

    new_items = []

    for search in SEARCHES:

        try:

            results = search_web(search)

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

    save_found(found)

    if not new_items:

        send_telegram(

            chat_id,

            "🕰 Проверка завершена.\n"

            "Новых настенных часов «Янтарь» не найдено."

        )

        return

    send_telegram(

        chat_id,

        f"🕰 Найдено новых объявлений: {len(new_items)}"

    )

    for item in new_items[:10]:

        message = (

            "🕰 НОВАЯ НАХОДКА\n\n"

            f"{item['title']}\n\n"

            f"{item['description'][:500]}\n\n"

            f"🔗 {item['url']}"

        )

        try:

            send_telegram(chat_id, message)

        except Exception as error:

            print(f"Ошибка Telegram: {error}")

if __name__ == "__main__":

    main()
