"""The frequency cap must query by category: ai_actions has no action-name column."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator import ACTION_CATEGORY


def test_known_actions_map_to_categories():
    assert ACTION_CATEGORY["pause_campaign"] == "strategy"
    assert ACTION_CATEGORY["resolve_seo_issue"] == "seo"
    assert ACTION_CATEGORY["create_blog_post"] == "content"


def test_categories_are_valid_laravel_categories():
    assert set(ACTION_CATEGORY.values()) <= {"seo", "content", "strategy"}
