# src/tools/domain/leads.py

import json
import logging
from typing import Dict, Any
from strands import tool
from ...utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

@tool
def score_lead(lead_id: str, brand_id: int) -> str:
    """
    Score a lead based on their activity and engagement.
    Uses REAL data from Vumbi Ventures Laravel backend.
    """
    client = LaravelApiClient()
    
    try:
        lead = client.get_lead(brand_id, lead_id)
        engagement = client.get_lead_engagement(brand_id, lead_id)
        
        # Calculate score based on real data
        score = 50  # base
        if engagement.get("activities", 0) > 5:
            score += 20
        if engagement.get("emailsOpened", 0) > 3:
            score += 15
        if lead.get("status") == "qualified":
            score += 15
        score = min(score, 100)
        
        return json.dumps({
            "success": True,
            "lead_id": lead_id,
            "score": score,
            "lead": lead,
            "engagement": engagement,
            "reasoning": f"Score based on {engagement.get('activities', 0)} activities and {engagement.get('emailsOpened', 0)} emails opened."
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def suggest_follow_up(lead_id: str, brand_id: int) -> str:
    """
    Suggest a personalized follow-up message for a lead.
    Uses REAL data from Vumbi Ventures Laravel backend.
    """
    client = LaravelApiClient()
    
    try:
        lead = client.get_lead(brand_id, lead_id)
        message = client.generate_follow_up(brand_id, lead_id)
        
        return json.dumps({
            "success": True,
            "lead_id": lead_id,
            "message": message.get("message", "Follow-up message"),
            "lead": lead
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})