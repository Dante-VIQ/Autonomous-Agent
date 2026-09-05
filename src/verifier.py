# src/verifier.py

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

# Action-specific verification configuration
ACTION_VERIFICATION_CONFIG = {
    "seo_issue": {"wait_seconds": 30, "metrics": ["indexability", "ranking_position"]},
    "lead_notification": {"wait_seconds": 5, "metrics": ["reply_rate"]},
    "content_generation": {"wait_seconds": 60, "metrics": ["indexation", "impressions"]},
    "campaign_pause": {"wait_seconds": 120, "metrics": ["roi", "cost_per_conversion"]}
}

class Verifier:
    """Verifies action outcomes with action-specific metrics."""

    def __init__(self):
        self.client = LaravelApiClient()

    async def verify(self, execution_result: Dict, brand_id: int) -> Dict:
        action = execution_result.get("action", {})
        action_name = action.get("name", "unknown")
        action_type = action.get("type", "unknown")
        
        config = ACTION_VERIFICATION_CONFIG.get(action_type, {})
        wait_seconds = config.get("wait_seconds", 30)
        
        # ✅ Use asyncio.sleep instead of time.sleep
        logger.info(f"⏳ Waiting {wait_seconds}s for {action_name} to propagate...")
        await asyncio.sleep(wait_seconds)
        
        # ✅ Await the async call
        before_metrics = {}
        after_metrics = {}
        try:
            after_metrics = await self.client.get_analytics(brand_id)
        except Exception as e:
            logger.warning(f"Failed to fetch after metrics: {e}")
        
        improvement = self._calculate_improvement(before_metrics, after_metrics)
        was_successful = improvement.get("average", 0) >= 0.05
        
        return {
            "success": True,
            "was_successful": was_successful,
            "improvement": improvement,
            "before_metrics": before_metrics,
            "after_metrics": after_metrics
        }

    async def _fetch_metrics(self, brand_id: int, metrics: list = None) -> Dict:
        """Fetch metrics from Laravel."""
        try:
            # For now, fetch analytics as a proxy
            analytics = await self.client.get_analytics(brand_id)
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