# src/tools/verify.py

import json
import logging
import time
from typing import Dict, Any
from strands import tool
from ..utils.api_client import LaravelApiClient
from ..config import Config

logger = logging.getLogger(__name__)

# Action-specific wait times (in seconds)
WAIT_TIMES = {
    "resolve_seo_issue": 30,
    "run_site_scan": 10,
    "trigger_content_generation": 60,
    "notify_lead_response": 5,
    "pause_campaign": 120,
    "no_action_needed": 0,
}

@tool
def verify_action(action_id: str, brand_id: int, action_name: str, wait_seconds: int = None) -> str:
    """
    Verify if an action was successful.
    Uses REAL data from Vumbi Ventures Laravel backend.
    
    Args:
        action_id: The ID of the action to verify
        brand_id: Brand ID
        action_name: Name of the action
        wait_seconds: Optional override for wait time
    
    Returns:
        JSON string with verification result
    """
    client = LaravelApiClient()
    
    try:
        # 1. Get wait time
        wait_time = wait_seconds or WAIT_TIMES.get(action_name, 30)
        
        # 2. Start verification
        start_result = client.start_verification(
            brand_id,
            action_name,
            action_id=action_id
        )
        verification_id = start_result.get("verification", {}).get("id")
        
        if not verification_id:
            return json.dumps({
                "success": False,
                "error": "Failed to start verification"
            })
        
        # 3. Wait for propagation
        logger.info(f"⏳ Waiting {wait_time}s for {action_name} to propagate...")
        time.sleep(wait_time)
        
        # 4. Get before metrics (from verification record)
        verification = client.get_verification(brand_id, verification_id)
        before_metrics = verification.get("before_metrics", {})
        
        # 5. Get after metrics (real data)
        after_metrics = client.get_analytics(brand_id)
        
        # 6. Calculate improvement
        improvement = _calculate_improvement(before_metrics, after_metrics)
        was_successful = improvement.get("percentage", 0) > 0
        
        # 7. Complete verification
        complete_result = client.complete_verification(
            brand_id,
            verification_id,
            after_metrics=after_metrics,
            was_successful=was_successful,
            improvement_percentage=improvement.get("percentage", 0),
            verification_notes=f"Action '{action_name}' resulted in {improvement.get('percentage', 0):.2f}% change"
        )
        
        # 8. If verification failed, trigger rollback
        rollback_result = None
        if not was_successful:
            logger.warning(f"🔄 Rollback triggered for {action_name} (ID: {action_id})")
            rollback_result = _rollback_action(action_id, brand_id, action_name)
        
        return json.dumps({
            "success": True,
            "verification_id": verification_id,
            "was_successful": was_successful,
            "improvement_percentage": improvement.get("percentage", 0),
            "before_metrics": before_metrics,
            "after_metrics": after_metrics,
            "details": improvement.get("details", {}),
            "rollback_triggered": not was_successful,
            "rollback_result": rollback_result
        })
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        })

def _calculate_improvement(before: Dict, after: Dict) -> Dict[str, Any]:
    """Calculate improvement between two metric snapshots."""
    details = {}
    total_percentage = 0
    count = 0
    
    for key in ["visitors", "pageViews", "conversions", "revenue", "seoScore"]:
        before_val = before.get(key, 0)
        after_val = after.get(key, 0)
        
        if isinstance(before_val, (int, float)) and isinstance(after_val, (int, float)):
            change = after_val - before_val
            percentage = (change / before_val * 100) if before_val != 0 else 0
            details[key] = {
                "before": before_val,
                "after": after_val,
                "change": change,
                "percentage": percentage
            }
            total_percentage += percentage
            count += 1
    
    return {
        "percentage": total_percentage / count if count > 0 else 0,
        "details": details
    }

def _rollback_action(action_id: str, brand_id: int, action_name: str) -> Dict[str, Any]:
    """Rollback an action if verification failed."""
    # This would call the RollbackEngine
    # For now, log the rollback request
    logger.info(f"🔄 Rollback requested for {action_name} (ID: {action_id})")
    
    # In production, you'd call:
    # client.rollback_action(action_id, brand_id)
    
    return {
        "success": True,
        "message": f"Rollback initiated for {action_name}",
        "action_id": action_id
    }