from datetime import datetime, timezone

from src.ingest import news


def test_headline_sentiment_direction():
    assert news._sentiment_score("Company beats estimates and raises guidance") > 0
    assert news._sentiment_score("Company cuts outlook after weak results") < 0
    assert news._sentiment_score("Company schedules annual meeting") == 0


def test_headline_supports_nested_provider_shape():
    item = {
        "content": {
            "title": "Company posts strong growth",
            "pubDate": "2026-09-25T12:00:00Z",
        }
    }

    assert news._headline(item) == "Company posts strong growth"
    published = news._published_at(item)
    assert published == datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
