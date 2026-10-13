
import json
import getpass
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "processed" / "reviews_2026_normalized.json"

DB_NAME = "ya_music_analysis"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = 5432


def clean_nul(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value


def load_reviews():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data["reviews"]

    return data


def main():
    reviews = load_reviews()

    nul_count = 0

    for review in reviews:
        for key, value in review.items():
            if isinstance(value, str) and "\x00" in value:
                nul_count += value.count("\x00")
                review[key] = clean_nul(value)

    print(f"Удалено нулевых символов: {nul_count}")

    password = getpass.getpass("Пароль PostgreSQL: ")

    query = """
        INSERT INTO reviews (
            source,
            review_id,
            review_date,
            rating,
            review_text,
            title,
            content,
            app_version,
            app_version_source,
            country,
            helpful_votes,
            vote_count,
            developer_reply,
            developer_reply_date
        )
        VALUES (
            %(source)s,
            %(review_id)s,
            %(review_date)s,
            %(rating)s,
            %(review_text)s,
            %(title)s,
            %(content)s,
            %(app_version)s,
            %(app_version_source)s,
            %(country)s,
            %(helpful_votes)s,
            %(vote_count)s,
            %(developer_reply)s,
            %(developer_reply_date)s
        )
        ON CONFLICT (source, review_id) DO NOTHING;
    """

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=password,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, reviews)

    print(f"Обработано отзывов: {len(reviews)}")


if __name__ == "__main__":
    main()
