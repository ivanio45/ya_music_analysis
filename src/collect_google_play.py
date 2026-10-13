import csv
import json
import time
from datetime import datetime, date
from pathlib import Path
from google_play_scraper import Sort, reviews

APP_ID  = "ru.yandex.music"
LANG    = "ru"
COUNTRY = "ru"
YEAR    = 2026

BATCH_SIZE = 200
SLEEP_SEC  = 1.5
CHECKPOINT_EVERY = 20  # каждые N страниц скидываем прогресс в файл

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data" / "raw" / "google_play"
DATA_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUT = DATA_DIR / f"yandex_music_{YEAR}_play_market.json"
CHECKPOINT = DATA_DIR / f"yandex_music_{YEAR}_checkpoint_play_market.json"


def json_safe(obj):
    """Пробегает по структуре и меняет datetime/date на iso-строки.
    Нужна потому что в отзывах есть поля с датами (at, repliedAt),
    а json.dump их не умеет сериализовать."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    return obj


def collect_year(app_id, lang, country, year):
    """Тянет отзывы постранично, сортировка по свежим.
    Останавливается когда вся очередная партия оказалась старше нужного года —
    значит глубже уже только прошлые годы."""
    start_dt = datetime(year, 1, 1)
    end_dt   = datetime(year, 12, 31, 23, 59, 59)

    collected, token, page = [], None, 0

    while True:
        page += 1
        try:
            batch, token = reviews(
                app_id, lang=lang, country=country,
                sort=Sort.NEWEST, count=BATCH_SIZE,
                continuation_token=token,
            )
        except Exception as e:
            print(f"  стр.{page}: ошибка {e}")
            break

        if not batch:
            print(f"  стр.{page}: пусто, стоп")
            break

        in_year = old = 0
        for r in batch:
            at = r.get("at")
            if not at:
                continue
            if start_dt <= at <= end_dt:
                collected.append(r)
                in_year += 1
            elif at < start_dt:
                old += 1

        print(f"  стр.{page}: всего {len(batch)}, "
              f"{year} — {in_year}, старше — {old}, "
              f"накоплено {len(collected)}")

        # чекпоинт на случай падения — чтоб не начинать с нуля
        if page % CHECKPOINT_EVERY == 0:
            with open(CHECKPOINT, "w", encoding="utf-8") as f:
                json.dump(json_safe(collected), f, ensure_ascii=False)
            print(f"    чекпоинт: {len(collected)}")

        # вся партия старше года — глубже только прошлые, выходим
        if old == len(batch):
            print(f"  дошли до отзывов старше {year}, стоп")
            break
        if not token:
            print("  токен кончился, стоп")
            break

        time.sleep(SLEEP_SEC)

    return collected


def main():
    print(f"сбор за {YEAR}: {APP_ID} (lang={LANG}, country={COUNTRY})\n")
    t0 = time.time()

    items = collect_year(APP_ID, LANG, COUNTRY, YEAR)
    print(f"\nсобрано за {YEAR}: {len(items)} ({time.time()-t0:.1f} сек)")

    if not items:
        print("пусто")
        return

    items.sort(key=lambda r: r["at"], reverse=True)

    # все datetime → строки, иначе json.dump упадёт
    json_ready = json_safe(items)

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(json_ready, f, ensure_ascii=False, indent=2)
    print(f"→ {JSON_OUT}")


    # краткая сводка по оценкам
    scores = [r["score"] for r in items]
    print(f"\nсредний: {sum(scores)/len(scores):.2f}")
    for s in range(5, 0, -1):
        print(f"  {s}★: {scores.count(s)}")


if __name__ == "__main__":
    main()