# src/verifier.py

import asyncio
import logging
from typing import Dict, Any, List, Optional
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

ACTION_VERIFICATION_CONFIG = {
    "seo_issue": {
        "wait_seconds": 30,
        "metrics": ["visitors", "conversions", "revenue", "page_views"]
    },
    "lead_notification": {
        "wait_seconds": 5,
        "metrics": ["visitors", "conversions", "revenue"]
    },
    "content_generation": {
        "wait_seconds": 60,
        "metrics": ["visitors", "conversions", "revenue", "page_views"]
    },
    "campaign_pause": {
        "wait_seconds": 120,
        "metrics": ["visitors", "conversions", "revenue"]
    },
    "analytics_alert": {
        "wait_seconds": 30,
        "metrics": ["visitors", "conversions", "revenue"]
    },
    "no_action_needed": {
        "wait_seconds": 5,
        "metrics": ["visitors", "conversions", "revenue"]
    }
}

class Verifier:
    def __init__(self):
        self.client = LaravelApiClient()

    async def verify(self, execution_result: Dict, brand_id: int) -> Dict:
        """
        Verify the outcome of an executed action.
        Called by orchestrator after execution.
        """
        action = execution_result.get("action", {})
        action_name = action.get("name", "unknown")
        action_type = action.get("type", "unknown")

        config = ACTION_VERIFICATION_CONFIG.get(action_type, {})
        wait_seconds = config.get("wait_seconds", 30)
        metrics = config.get("metrics", ["visitors", "conversions", "revenue"])

        logger.info(f"🔍 Verifying {action_name} with {wait_seconds}s wait, metrics: {metrics}")

        # Wait for action to propagate
        await asyncio.sleep(wait_seconds)

        # Get before metrics (from execution context or API)
        before_metrics = execution_result.get("before_metrics", {})
        if not before_metrics:
            # Try to fetch before metrics from the API
            before_metrics = await self._fetch_metrics(brand_id, metrics)

        # Get after metrics
        after_metrics = await self._fetch_metrics(brand_id, metrics)

        # Calculate improvement
        improvement = self._calculate_improvement(before_metrics, after_metrics, metrics)
        was_successful = improvement.get("average", 0) >= 0.05  # 5% threshold

        return {
            "success": True,
            "was_successful": was_successful,
            "improvement": improvement,
            "before_metrics": before_metrics,
            "after_metrics": after_metrics,
            "action_name": action_name,
            "wait_seconds": wait_seconds
        }

    async def _fetch_metrics(self, brand_id: int, metrics: List[str] = None) -> Dict:
        """Fetch metrics from Laravel."""
        try:
            analytics = await self.client.get_analytics(brand_id)
            result = {
                "visitors": analytics.get("visitors", 0),
                "conversions": analytics.get("conversions", 0),
                "revenue": analytics.get("revenue", 0),
                "page_views": analytics.get("pageViews", 0),
                "sessions": analytics.get("sessions", 0),
            }
            # If specific metrics are requested, filter the result
            if metrics:
                return {k: result.get(k, 0) for k in metrics if k in result}
            return result
        except Exception as e:
            logger.warning(f"Failed to fetch metrics: {e}")
            return {}

    def _calculate_improvement(self, before: Dict, after: Dict, metrics: List[str] = None) -> Dict:
        """
        Calculate improvement between two metric snapshots.
        If metrics is None, use all available numeric fields.
        """
        if metrics is None:
            # Use all numeric fields from before/after
            metrics = []
            all_keys = set(before.keys()) | set(after.keys())
            for key in all_keys:
                if key != 'timestamp' and isinstance(before.get(key, 0), (int, float)):
                    metrics.append(key)

        improvements = []
        details = {}

        for metric in metrics:
            before_val = before.get(metric, 0)
            after_val = after.get(metric, 0)

            if not isinstance(before_val, (int, float)) or not isinstance(after_val, (int, float)):
                continue

            change = after_val - before_val
            if before_val == 0:
                # If before is 0 and after is positive, that's infinite improvement
                if after_val > 0:
                    change_percent = 100
                else:
                    change_percent = 0
            else:
                change_percent = (change / before_val) * 100

            details[metric] = {
                "before": before_val,
                "after": after_val,
                "change": change,
                "percentage": change_percent
            }
            improvements.append(change_percent)

        average = sum(improvements) / len(improvements) if improvements else 0

        return {
            "average": average,
            "details": details,
            "overall": "success" if average >= 0 else "failure"
        }