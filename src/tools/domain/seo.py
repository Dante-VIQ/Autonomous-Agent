# src/tools/domain/seo.py

import json
import logging
from typing import Dict, Any
from strands import tool
from ...utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

@tool
async def analyze_seo_issue(issue_id: str, brand_id: int) -> str:
    """
    Deep-dive into a specific SEO issue and suggest a remediation.
    Uses REAL data from Vumbi Ventures Laravel backend.
    """
    client = LaravelApiClient()
    
    try:
        analysis = client.analyze_seo_issue(brand_id, issue_id)
        recommendations = client.get_seo_recommendations(brand_id, issue_id)
        issue = await client.get_seo_issue(brand_id, issue_id)
        analysis = await client.analyze_seo_issue(brand_id, issue_id)
        recommendations = await client.get_seo_recommendations(brand_id, issue_id)
        
        return json.dumps({
            "success": True,
            "issue": issue,
            "analysis": analysis.get("analysis", "Detailed analysis"),
            "recommendations": recommendations,
            "similar_issues": analysis.get("similar_issues", [])
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def get_ranking_data(page_url: str, brand_id: int) -> str:
    """
    Get keyword ranking data for a page.
    Uses REAL data from Vumbi Ventures Laravel backend.
    """
    client = LaravelApiClient()
    
    try:
        rankings = client.get_keyword_rankings(brand_id, page_url)
        return json.dumps({
            "success": True,
            "page_url": page_url,
            "rankings": rankings
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})