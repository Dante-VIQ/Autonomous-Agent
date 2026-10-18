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


def test_competitors_are_compacted_and_failed_scans_dropped():
    ev = {"competitors": {
        "tracked": 3, "scanned": 2, "as_of": "2026-10-18",
        "competitors": [
            {"domain": "a.com", "status": "ok", "posts_last_30d": 4, "latest_post_at": "2026-10-15",
             "top_terms": {"maasai": 3, "mara": 2}},
            {"domain": "b.com", "status": "error", "posts_last_30d": None, "top_terms": {}},
            {"domain": "c.com", "status": "ok", "posts_last_30d": None, "latest_post_at": None, "top_terms": {}},
        ],
        "topic_gaps": [{"term": f"t{i}", "competitors": 2, "mentions": 3} for i in range(12)],
    }}
    out = compact_evidence(ev)
    pub = out["competitors"]["publishing"]
    assert [p["domain"] for p in pub] == ["a.com", "c.com"]
    assert pub[0]["topics"] == ["maasai", "mara"]
    assert pub[1]["posts_last_30d"] is None          # unknown stays unknown
    assert out["competitors"]["topic_gaps"] == [f"t{i}" for i in range(8)]


def test_no_scanned_competitors_means_no_block():
    assert "competitors" not in compact_evidence({"competitors": {"tracked": 2, "scanned": 0, "competitors": []}})
