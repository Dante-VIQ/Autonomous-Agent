# src/specialists/analytics.py

import logging
from typing import Dict, Any
from .base import BaseSpecialist
from ..tools.domain.analytics import analyze_conversions, get_analytics_summary

logger = logging.getLogger(__name__)

class AnalyticsSpecialist(BaseSpecialist):
    """Analytics Specialist for handling conversion and performance alerts."""

    def __init__(self):
        tools = [
            analyze_conversions,
            get_analytics_summary
        ]
        system_prompt = """
You are the Analytics Specialist. Your domain is marketing analytics and performance optimization.
You excel at:
- Identifying conversion bottlenecks
- Analyzing traffic and engagement data
- Suggesting data-driven improvements
- Optimizing campaigns based on metrics

When analyzing an analytics alert (e.g., low conversions), you should:
1. Understand the current metrics
2. Check historical patterns
3. Propose a specific action (e.g., adjust campaign, update content, pause underperforming ads)
4. Provide a confidence score
5. Estimate the potential impact
"""
        super().__init__("Analytics Specialist", "analytics", tools, system_prompt)

    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        """Execute an analytics decision."""
        action = decision.get("action", {})
        action_name = action.get("name", "unknown")

        if action_name == "pause_campaign" or action_name == "adjust_campaign":
            payload = action.get("payload", {})
            result = await self.client.pause_campaign(
                brand_id,
                payload.get("campaign_id"),
                payload.get("reason", "Adjusted by Analytics Specialist")
            )
        else:
            result = await self.client.create_pending_action(brand_id, action, "Analytics action")

        return {"success": True, "result": result}