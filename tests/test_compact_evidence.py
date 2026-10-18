from src.specialists.base import compact_evidence


def test_empty_evidence_is_empty():
    assert compact_evidence({}) == {}
    assert compact_evidence(None or {}) == {}


def test_no_ga4_data_is_omitted_not_zeroed():
    out = compact_evidence({"analytics": {"has_data": False}, "data_quality": {"ga4": {"has_data": False}}})
    assert "analytics" not in out
    assert out["data_quality"]["ga4"]["has_data"] is False


def test_trims_lists_and_keeps_quality():
    ev = {
        "analytics": {"has_data": True, "as_of": "2026-10-16", "stale_days": 1, "current": {"visitors": 10},
                      "changes_pct": {"visitors": 5.0}, "trend": "up", "top_pages": list(range(9)),
                      "channels": list(range(9))},
        "seo": {
            "authority": {"domain_rating": 30},
            "keywords": {"tracked": 40, "as_of": "2026-10-15",
                         "movers": {"up": list(range(9)), "down": list(range(9))},
                         "striking_distance": list(range(9))},
            "backlinks": {"new_last_30d": 2, "lost_last_30d": 1, "lost_top": list(range(9))},
            "open_issues": {"high": 2},
        },
        "data_quality": {"ahrefs": {"keywords_as_of": "2026-10-15"}},
    }
    out = compact_evidence(ev)
    assert len(out["analytics"]["channels"]) == 5
    assert len(out["analytics"]["top_pages"]) == 5
    assert len(out["keywords"]["movers"]["up"]) == 3
    assert len(out["keywords"]["striking_distance"]) == 5
    assert len(out["backlinks"]["lost_top"]) == 3
    assert out["authority"]["domain_rating"] == 30
    assert out["data_quality"]["ahrefs"]["keywords_as_of"] == "2026-10-15"


def test_untracked_keywords_not_shown():
    out = compact_evidence({"seo": {"keywords": {"tracked": 0}}})
    assert "keywords" not in out


def test_listening_zero_mentions_is_kept_as_a_baseline():
    out = compact_evidence({"listening": {
        "state": "no_mentions_yet", "checked_on": "2026-10-18",
        "brand": {"last_7d": 0, "previous_7d": 0, "change_pct": None, "sentiment_30d": {}},
        "share_of_voice": [], "conversations": [], "sources": {"reddit": "blocked"}}})
    lis = out["listening"]
    assert lis["state"] == "no_mentions_yet"
    assert lis["change_pct"] is None            # no baseline: no trend
    assert lis["sources"]["reddit"] == "blocked"


def test_listening_is_trimmed():
    out = compact_evidence({"listening": {
        "state": "active", "checked_on": "2026-10-18",
        "brand": {"last_7d": 4, "change_pct": 33.3, "sentiment_30d": {"positive": 3}},
        "share_of_voice": [{"term": str(i), "mentions": i} for i in range(9)],
        "conversations": [{"title": f"t{i}"} for i in range(9)], "sources": {}}})
    assert len(out["listening"]["share_of_voice"]) == 5
    assert out["listening"]["conversations"] == ["t0", "t1", "t2", "t3", "t4"]


def test_no_listening_key_means_no_block():
    assert "listening" not in compact_evidence({"data_quality": {"x": 1}})
