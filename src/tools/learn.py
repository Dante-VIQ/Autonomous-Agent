# src/tools/learn.py

import json
import logging
from typing import Dict, Any
from strands import tool
from ..utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

@tool
def record_learning(brand_id: int, outcome: Dict[str, Any]) -> str:
    """
    Record learning outcomes for future decisions.
    Uses REAL data from Vumbi Ventures Laravel backend.
    
    Args:
        brand_id: Brand ID
        outcome: Dictionary with outcome data
    
    Returns:
        JSON string with recording result
    """
    client = LaravelApiClient()
    
    try:
        # Build the learning record
        data = {
            "action_name": outcome.get("action_name", "unknown"),
            "opportunity_type": outcome.get("opportunity_type", "unknown"),
            "severity": outcome.get("severity", "medium"),
            "confidence": outcome.get("confidence", 0.0),
            "was_autonomous": outcome.get("was_autonomous", False),
            "was_successful": outcome.get("was_successful", False),
            "improvement_percentage": outcome.get("improvement_percentage", 0),
            "duration_seconds": outcome.get("duration_seconds", 0),
            "context": outcome.get("context", {}),
            "decision": outcome.get("decision", {}),
            "outcome": outcome.get("outcome", {})
        }
        
        # Record in Laravel
        result = client.record_learning(brand_id, data)
        
        logger.info(f"📝 Recorded learning for brand {brand_id}: {outcome.get('action_name')}")
        
        return json.dumps({
            "success": True,
            "message": "Learning recorded successfully",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Failed to record learning: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })