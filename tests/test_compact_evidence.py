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


<<<<<<< HEAD
def test_no_scanned_competitors_means_no_block():
    assert "competitors" not in compact_evidence({"competitors": {"tracked": 2, "scanned": 0, "competitors": []}})
=======
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


def test_personas_keep_confidence_and_zero_count_note():
    out = compact_evidence({"personas": {"count": 0, "personas": [], "note": "No personas defined yet."}})
    assert out["personas"]["count"] == 0
    assert "No personas" in out["personas"]["note"]


def test_personas_are_trimmed_and_carry_confidence():
    ps = [{"name": f"P{i}", "confidence": "hypothesis", "stale": False, "goals": ["g"], "pains": ["p"],
           "objections": [], "channels": [], "extra": "x"} for i in range(6)]
    out = compact_evidence({"personas": {"count": 6, "personas": ps, "note": "n"}})
    assert len(out["personas"]["personas"]) == 4
    assert out["personas"]["personas"][0]["confidence"] == "hypothesis"
    assert "extra" not in out["personas"]["personas"][0]
>>>>>>> 1585b64 (Specialists see buyer personas with their confidence)


def test_content_too_early_carries_no_leaders_and_posting_note():
    out = compact_evidence({"content": {"plan": {"ideas": 2, "ready": 1, "posted": 3},
        "performance": {"state": "too_early", "measured_posts": 3, "overall_engagement_rate_pct": 4.1, "leaders": {}},
        "note": "Posting is done manually by a human."}})
    c = out["content"]
    assert c["performance_state"] == "too_early" and c["leaders"] == {}
    assert "manually" in c["note"]


def test_content_absent_is_omitted():
    assert "content" not in compact_evidence({})
