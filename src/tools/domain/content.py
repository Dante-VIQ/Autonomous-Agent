# src/tools/domain/content.py

import json
import logging
from typing import Dict, Any
from strands import tool
from ...utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

@tool
def analyze_content_gap(topic: str, brand_id: int) -> str:
    """
    Identify content gaps based on SEO and competition.
    Uses REAL data from Vumbi Ventures Laravel backend.
    """
    client = LaravelApiClient()
    
    try:
        analysis = client.analyze_content_gap(brand_id, topic)
        
        return json.dumps({
            "success": True,
            "topic": topic,
            "brand_id": brand_id,
            "gaps": analysis.get("gaps", []),
            "opportunities": analysis.get("opportunities", []),
            "competitor_coverage": analysis.get("competitor_coverage", [])
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def generate_outline(topic: str, template: str = "blog") -> str:
    """
    Generate a content outline for a topic.
    Uses REAL data from Vumbi Ventures Laravel backend.
    """
    client = LaravelApiClient()
    
    try:
        outline = client.generate_outline(topic, template)
        
        return json.dumps({
            "success": True,
            "topic": topic,
            "template": template,
            "outline": outline.get("outline", []),
            "target_keyword": outline.get("target_keyword", ""),
            "meta_description": outline.get("meta_description", ""),
            "estimated_word_count": outline.get("estimated_word_count", 0)
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})