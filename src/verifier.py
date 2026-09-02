# src/verifier.py

import logging
import time
from typing import Dict, Any
from datetime import datetime
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

# Action-specific verification configuration
VERIFICATION_CONFIG = {
    "seo_issue": {
        "wait_seconds": 30,
        "metrics": ["indexability", "ranking_position", "organic_impressions"],
        "success_threshold": 0.05  # 5% improvement
    },
    "lead_notification": {
        "wait_seconds": 5,
        "metrics": ["reply_rate", "engagement"],
        "success_threshold": 0.10
    },
    "content_generation": {
        "wait_seconds": 60,
        "metrics": ["indexation", "impressions", "ranking"],
        "success_threshold": 0.10
    },
    "campaign_pause": {
        "wait_seconds": 120,
        "metrics": ["roi", "cost_per_conversion"],
        "success_threshold": 0.10
    },
    "default": {
        "wait_seconds": 30,
        "metrics": ["visitors", "conversions", "revenue"],
        "success_threshold": 0.05
    }
}

class Verifier:
    """Verifies action outcomes with action-specific metrics."""

    def __init__(self):
        self.client = LaravelApiClient()

    async def verify(self, execution_result: Dict, brand_id: int) -> Dict:
        """Verify the outcome of an executed action."""
        action = execution_result.get("action", {})
        action_name = action.get("name", "unknown")
        action_type = action.get("type", "default")  # Use type from opportunity if available
        
        # Get config for this action type
        config = VERIFICATION_CONFIG.get(action_type, VERIFICATION_CONFIG["default"])
        wait_seconds = config["wait_seconds"]
        metrics = config["metrics"]
        threshold = config["success_threshold"]
        
        logger.info(f"🔍 Verifying {action_name} with {wait_seconds}s wait, metrics: {metrics}")
        
        # Wait for action to propagate
        time.sleep(wait_seconds)
        
        # Get before metrics (from execution context or API)
        before_metrics = execution_result.get("before_metrics", {})
        if not before_metrics:
            # Fallback: fetch current metrics as before (not ideal)
            before_metrics = await self._fetch_metrics(brand_id)
        
        # Get after metrics
        after_metrics = await self._fetch_metrics(brand_id, metrics)
        
        # Calculate improvement
        improvement = self._calculate_improvement(before_metrics, after_metrics, metrics)
        was_successful = improvement.get("average", 0) >= threshold
        
        logger.info(f"Verification result: {'✅ SUCCESS' if was_successful else '❌ FAILED'}, improvement: {improvement.get('average', 0)*100:.1f}%")
        
        return {
            "success": True,
            "was_successful": was_successful,
            "improvement": improvement,
            "before_metrics": before_metrics,
            "after_metrics": after_metrics,
            "timestamp": datetime.now().isoformat()
        }

    async def _fetch_metrics(self, brand_id: int, metrics: list = None) -> Dict:
        """Fetch metrics from Laravel."""
        try:
            # For now, fetch analytics as a proxy
            analytics = self.client.get_analytics(brand_id)
            # Map to requested metrics
            return {
                "visitors": analytics.get("visitors", 0),
                "conversions": analytics.get("conversions", 0),
                "revenue": analytics.get("revenue", 0),
                "page_views": analytics.get("pageViews", 0),
                "sessions": analytics.get("sessions", 0),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metrics: {e}")
            return {}

    def _calculate_improvement(self, before: Dict, after: Dict, metrics: list) -> Dict:
        """Calculate improvement for specified metrics."""
        improvements = {}
        total = 0
        count = 0
        
        for metric in metrics:
            before_val = before.get(metric, 0)
            after_val = after.get(metric, 0)
            if before_val > 0:
                change = (after_val - before_val) / before_val
                improvements[metric] = change
                total += change
                count += 1
        
        average = total / count if count > 0 else 0
        
        return {
            "metrics": improvements,
            "average": average,
            "overall": "success" if average >= 0 else "failure"
        }