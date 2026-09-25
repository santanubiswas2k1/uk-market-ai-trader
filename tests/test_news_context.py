from datetime import UTC, datetime

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
    assert published == datetime(2026, 9, 25, 12, 0, tzinfo=UTC)



def test_news_fusion_uses_bounded_weight_and_adjusts_probability():
    context = {
        "news_count_24h": 5,
        "news_sentiment": 1.0,
        "days_to_earnings": 10,
    }

    result = news.fuse_news_sentiment(
        base_probability_up=0.50,
        base_expected_return=0.0,
        daily_vol=0.02,
        context=context,
    )

    assert result["news_used_in_algorithm"] is True
    assert result["news_weight"] == news.NEWS_MAX_WEIGHT
    assert result["adjusted_probability_up"] > 0.50
    assert result["adjusted_expected_return"] > 0.0
    assert result["earnings_range_multiplier"] == 1.0
    assert result["news_overlay_backtested"] is False


def test_earnings_proximity_widens_range_without_directional_bias():
    context = {
        "news_count_24h": 0,
        "news_sentiment": 0.0,
        "days_to_earnings": 1,
    }

    result = news.fuse_news_sentiment(
        base_probability_up=0.55,
        base_expected_return=0.01,
        daily_vol=0.02,
        context=context,
    )

    assert result["adjusted_probability_up"] == 0.55
    assert result["adjusted_expected_return"] == 0.01
    assert result["earnings_range_multiplier"] == 1.50
