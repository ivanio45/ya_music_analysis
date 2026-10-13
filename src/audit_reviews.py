import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "raw"

FILES = {
    "App Store": DATA_DIR / "app_store" / "yandex_music_2026_app_store.json",
    "Google Play": DATA_DIR / "google_play" / "yandex_music_2026_play_market.json",
}

REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def parse_date(value):
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_id(review, source):
    if source == "App Store":
        return review.get("review_id")
    return review.get("reviewId")


def get_date(review, source):
    if source == "App Store":
        return parse_date(review.get("updated"))
    return parse_date(review.get("at"))


def get_rating(review, source):
    if source == "App Store":
        return review.get("rating")
    return review.get("score")


def get_text(review, source):
    if source == "App Store":
        return " ".join(
            str(review.get(field) or "").strip()
            for field in ("title", "content")
        ).strip()

    return str(review.get("content") or "").strip()


def audit(source, path):
    if not path.exists():
        print(f"\n[{source}] Файл не найден: {path}")
        return None

    with path.open("r", encoding="utf-8") as file:
        reviews = json.load(file)

    if not isinstance(reviews, list):
        raise ValueError(f"{path}: ожидался JSON-массив")

    ids = [get_id(r, source) for r in reviews]
    dates = [get_date(r, source) for r in reviews]
    ratings = [get_rating(r, source) for r in reviews]

    valid_dates = [d for d in dates if d is not None]
    valid_ratings = [
        r for r in ratings
        if isinstance(r, int)
        and not isinstance(r, bool)
        and 1 <= r <= 5
    ]

    id_counts = Counter(i for i in ids if i)
    duplicates = {
        i: count for i, count in id_counts.items()
        if count > 1
    }

    monthly_counts = Counter(
        d.strftime("%Y-%m")
        for d in valid_dates
    )

    rating_counts = Counter(valid_ratings)

    report = {
        "source": source,
        "file": path.name,
        "total_records": len(reviews),
        "missing_ids": sum(not i for i in ids),
        "duplicate_id_groups": len(duplicates),
        "missing_or_invalid_dates": sum(
            d is None for d in dates
        ),
        "min_date": min(valid_dates).isoformat()
        if valid_dates else None,
        "max_date": max(valid_dates).isoformat()
        if valid_dates else None,
        "records_in_2026": sum(
            d is not None and d.year == 2026
            for d in dates
        ),
        "missing_text": sum(
            not get_text(r, source) for r in reviews
        ),
        "missing_ratings": sum(r is None for r in ratings),
        "invalid_ratings": sum(
            r is not None and (
                not isinstance(r, int)
                or isinstance(r, bool)
                or not 1 <= r <= 5
            )
            for r in ratings
        ),
        "rating_distribution": dict(sorted(rating_counts.items())),
        "monthly_counts": dict(sorted(monthly_counts.items())),
    }

    if source == "App Store":
        report["countries"] = dict(Counter(
            r.get("country") or "MISSING"
            for r in reviews
        ))
        report["missing_versions"] = sum(
            not r.get("version") for r in reviews
        )
    else:
        report["app_versions"] = dict(Counter(
            r.get("appVersion") or "MISSING"
            for r in reviews
        ))
        report["reviews_with_reply"] = sum(
            bool(r.get("replyContent")) for r in reviews
        )

    print(f"\n=== {source} ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    return report


def main():
    reports = []

    for source, path in FILES.items():
        result = audit(source, path)
        if result is not None:
            reports.append(result)

    output = REPORT_DIR / "audit_summary.json"
    output.write_text(
        json.dumps(reports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nОтчёт сохранён: {output}")


if __name__ == "__main__":
    main()