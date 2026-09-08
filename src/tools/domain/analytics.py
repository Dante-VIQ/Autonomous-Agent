# src/tools/domain/analytics.py

import json
import logging
from strands import tool
from ...utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

@tool
async def analyze_conversions(brand_id: int) -> str:
    """
    Analyze conversion data and identify issues using Laravel's analysis endpoint.
    """
    client = LaravelApiClient()
    try:
        result = await client._request("GET", f"/agent/analytics/analyze/{brand_id}")
        return json.dumps({
            "success": True,
            "analysis": result,
        })
    except Exception as e:
        logger.error(f"Failed to analyze conversions: {e}")
        return json.dumps({"success": False, "error": str(e)})
        
@tool
async def get_analytics_summary(brand_id: int) -> str:
    """Get a summary of key analytics metrics."""
    client = LaravelApiClient()
    try:
        analytics = await client.get_analytics(brand_id)
        return json.dumps({
            "success": True,
            "summary": {
                "visitors": analytics.get("visitors", 0),
                "conversions": analytics.get("conversions", 0),
                "revenue": analytics.get("revenue", 0),
                "trend": "up" if analytics.get("conversions", 0) > 5 else "down"
            }
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})