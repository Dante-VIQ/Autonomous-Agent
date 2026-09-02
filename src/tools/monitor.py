# src/tools/monitor.py

import json
import logging
from typing import List, Dict, Any
from strands import tool
from ..utils.api_client import LaravelApiClient
from ..config import Config

logger = logging.getLogger(__name__)

@tool
def monitor_opportunities(brand_id: int) -> str:
    """
    Scan for marketing opportunities (SEO issues, pending leads, campaign problems).
    Uses REAL data from Vumbi Ventures Laravel backend.
    
    Returns:
        JSON string with list of opportunities
    """
    client = LaravelApiClient()
    
    try:
        # Fetch real data from Laravel
        opportunities = client.get_opportunities(brand_id)
        
        # Log the count for monitoring
        logger.info(f"Found {len(opportunities)} opportunities for brand {brand_id}")
        
        return json.dumps({
            "success": True,
            "count": len(opportunities),
            "opportunities": opportunities,
            "message": f"Found {len(opportunities)} opportunities"
        })
        
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "opportunities": []
        })