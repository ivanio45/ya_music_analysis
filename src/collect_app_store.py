import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

APP_ID = "520797969"

# сторфронты, откуда тянем отзывы. каждый даёт до ~500 последних
COUNTRIES = [
    "ru", "by", "kz", "am", "az",
    "kg", "md", "tj", "tm", "uz",
]

MAX_PAGES = 10          # больше 10 страниц apple не отдаёт
SORT_BY = "mostrecent"  # сортировка фида
WORKERS = 8             # потоков на страны
TIMEOUT = 15

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "app_store"
DATA_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUT = DATA_DIR / f"yandex_music_2026_app_store.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    )
}


def fetch_page(country, page):
    """Тянет одну страницу rss-фида для страны и парсит отзывы в список словарей."""
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews/"
        f"page={page}/id={APP_ID}/sortby={SORT_BY}/json"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        # сеть/таймаут/битый json — просто пропускаем страницу
        print(f"{country} p{page}: {e}")
        return []

    entries = data.get("feed", {}).get("entry", [])
    # иногда приходит один объект вместо массива
    if isinstance(entries, dict):
        entries = [entries]

    result = []
    for e in entries:
        # первый entry — метаданные приложения, у отзыва есть im:rating
        if "im:rating" not in e:
            continue
        result.append({
            "review_id":  e.get("id", {}).get("label"),
            "country":    country,
            "author":     e.get("author", {}).get("name", {}).get("label"),
            "author_uri": e.get("author", {}).get("uri", {}).get("label"),
            "rating":     int(e["im:rating"]["label"]),
            "title":      e.get("title", {}).get("label"),
            "content":    e.get("content", {}).get("label"),
            "version":    e.get("im:version", {}).get("label"),
            "vote_sum":   e.get("im:voteSum", {}).get("label"),
            "vote_count": e.get("im:voteCount", {}).get("label"),
            "updated":    e.get("updated", {}).get("label"),
            "link":       e.get("link", {}).get("attributes", {}).get("href"),
        })
    return result


def fetch_country(country):
    """Обходит все страницы для одной страны и возвращает общий список отзывов."""
    reviews = []
    for page in range(1, MAX_PAGES + 1):
        chunk = fetch_page(country, page)
        if not chunk:
            # страница пустая — дальше нет смысла долбить
            break
        reviews.extend(chunk)
        time.sleep(0.2)  # пауза чтоб не злить apple
    print(f"{country}: {len(reviews)}")
    return reviews


def dedupe(reviews):
    """Убирает дубли по review_id. один и тот же отзыв может прийти из разных стран."""
    seen = set()
    out = []
    for r in reviews:
        rid = r.get("review_id")
        if rid and rid not in seen:
            seen.add(rid)
            out.append(r)
    return out


def main():
    print(f"app id: {APP_ID}, countries: {len(COUNTRIES)}")

    # страны тянем параллельно — сильно быстрее чем по очереди
    all_reviews = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch_country, c) for c in COUNTRIES]
        for fut in as_completed(futures):
            all_reviews.extend(fut.result())

    unique = dedupe(all_reviews)
    # сортируем по дате, свежие сверху
    unique.sort(key=lambda x: x.get("updated") or "", reverse=True)

    print(f"raw: {len(all_reviews)}, unique: {len(unique)}")

    # json — для программной обработки, csv — чтоб глазами глянуть в excel
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)



if __name__ == "__main__":
    main()