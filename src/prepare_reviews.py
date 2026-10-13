
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


# Папка проекта находится на уровень выше src
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

APP_STORE_FILE = RAW_DIR / "app_store" / "yandex_music_2026_app_store.json"
GOOGLE_PLAY_FILE = RAW_DIR / "google_play" / "yandex_music_2026_play_market.json"

YEAR = 2026


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"Ожидался список записей в файле {path}")

    return data


def parse_date(value):
    if not value or not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def to_int(value):
    if value is None or value == "":
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def combine_text(title, content):
    title = (title or "").strip()
    content = (content or "").strip()

    if not title:
        return content

    if not content or title == content:
        return title

    return f"{title}. {content}"


def prepare_app_store(records):
    prepared = []

    for record in records:
        date_value = record.get("updated")
        review_date = parse_date(date_value)

        # Оставляем отзывы за нужный год
        if review_date is None or review_date.year != YEAR:
            continue

        rating = to_int(record.get("rating"))
        if rating is None or not 1 <= rating <= 5:
            continue

        prepared.append({
            "source": "App Store",
            "review_id": str(record["review_id"]),
            "review_date": date_value,
            "rating": rating,
            "review_text": combine_text(
                record.get("title"),
                record.get("content"),
            ),
            "title": record.get("title"),
            "content": record.get("content"),
            "app_version": record.get("version"),
            "app_version_source": "version",
            "country": record.get("country"),
            "helpful_votes": to_int(record.get("vote_sum")),
            "vote_count": to_int(record.get("vote_count")),
            "developer_reply": None,
            "developer_reply_date": None,
        })

    return prepared


def prepare_google_play(records):
    prepared = []

    for record in records:
        date_value = record.get("at")
        review_date = parse_date(date_value)

        # Оставляем отзывы за нужный год
        if review_date is None or review_date.year != YEAR:
            continue

        rating = to_int(record.get("score"))
        if rating is None or not 1 <= rating <= 5:
            continue

        # Если версия не указана, берём её из другого поля
        app_version = record.get("appVersion")
        version_source = "appVersion"

        if not app_version:
            app_version = record.get("reviewCreatedVersion")
            version_source = "reviewCreatedVersion"

        prepared.append({
            "source": "Google Play",
            "review_id": str(record["reviewId"]),
            "review_date": date_value,
            "rating": rating,
            "review_text": (record.get("content") or "").strip(),
            "title": None,
            "content": record.get("content"),
            "app_version": app_version,
            "app_version_source": version_source if app_version else None,
            "country": None,
            "helpful_votes": to_int(record.get("thumbsUpCount")),
            "vote_count": None,
            "developer_reply": record.get("replyContent"),
            "developer_reply_date": record.get("repliedAt"),
        })

    return prepared


def save_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def build_summary(records):
    months = Counter()
    ratings = Counter()
    sources = Counter()

    for record in records:
        review_date = parse_date(record["review_date"])

        if review_date:
            months[review_date.strftime("%Y-%m")] += 1

        ratings[str(record["rating"])] += 1
        sources[record["source"]] += 1

    return {
        "year": YEAR,
        "total_records": len(records),
        "records_by_source": dict(sorted(sources.items())),
        "records_by_month": dict(sorted(months.items())),
        "records_by_rating": dict(sorted(ratings.items())),
        "missing_app_version": sum(
            not record["app_version"]
            for record in records
        ),
        "missing_review_text": sum(
            not record["review_text"].strip()
            for record in records
        ),
        "unique_source_review_ids": len({
            (record["source"], record["review_id"])
            for record in records
        }),
    }


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    app_store_raw = load_json(APP_STORE_FILE)
    google_play_raw = load_json(GOOGLE_PLAY_FILE)

    print(f"App Store: загружено {len(app_store_raw):,} отзывов")
    print(f"Google Play: загружено {len(google_play_raw):,} отзывов")

    app_store = prepare_app_store(app_store_raw)
    google_play = prepare_google_play(google_play_raw)
    all_reviews = app_store + google_play

    # Проверяем ID внутри каждого источника
    review_ids = [
        (record["source"], record["review_id"])
        for record in all_reviews
    ]

    if len(review_ids) != len(set(review_ids)):
        raise ValueError("В подготовленных данных есть повторяющиеся ID")

    save_json(PROCESSED_DIR / "app_store_2026.json", app_store)
    save_json(PROCESSED_DIR / "google_play_2026.json", google_play)
    save_json(PROCESSED_DIR / "reviews_2026_normalized.json", all_reviews)

    summary = build_summary(all_reviews)
    save_json(PROCESSED_DIR / "preparation_summary.json", summary)

    print("\nПодготовка завершена")
    print(f"App Store за {YEAR}: {len(app_store):,}")
    print(f"Google Play за {YEAR}: {len(google_play):,}")
    print(f"Всего отзывов: {len(all_reviews):,}")
    print(f"Результаты сохранены в {PROCESSED_DIR}")

    print("\nРаспределение оценок:")
    for rating, count in sorted(summary["records_by_rating"].items()):
        print(f"{rating} звёзд: {count:,}")

    print(f"\nБез версии приложения: {summary['missing_app_version']:,}")
    print(f"Без текста отзыва: {summary['missing_review_text']:,}")


if __name__ == "__main__":
    main()
