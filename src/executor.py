# src/executor.py

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self):
        self.client = LaravelApiClient()

    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        action = decision.get("action", {})
        name = action.get("name", "unknown")
        payload = action.get("payload", {})
        logger.info(f"⚡ Executing action: {name}")

        try:
            result = await self._route_action(name, payload, brand_id)
            return {
                "status": "executed",
                "action": action,
                "result": result,
                "duration": 0
            }
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return {
                "status": "failed",
                "action": action,
                "error": str(e)
            }

    async def _route_action(self, name: str, payload: Dict, brand_id: int) -> Any:
        """Route to the appropriate Laravel endpoint."""
        action_map = {
            "resolve_seo_issue": self.client.scan,
            "run_site_scan": self.client.scan,
            "trigger_content_generation": self.client.generate_content,
            "create_blog_post": self.client.generate_content,    # Added alias
            "generate_content": self.client.generate_content,    # Added alias
            "notify_lead_response": self.client.generate_follow_up,
            "pause_campaign": self.client.pause_campaign,
        }
        func = action_map.get(name)
        if not func:
            # Generic action – create pending action
            return await self.client.create_pending_action(
                brand_id, {"name": name, **payload}, "Autonomous execution"
            )

        if name == "trigger_content_generation" or name in ("create_blog_post", "generate_content"):
            return await func(
                brand_id,
                payload.get("topic", "Untitled"),
                payload.get("template", "blog")
            )
        elif name == "notify_lead_response":
            return await func(brand_id, payload.get("lead_id"))
        elif name == "pause_campaign":
            return await func(
                brand_id,
                payload.get("campaign_id"),
                payload.get("reason", "Paused by AI")
            )
        else:
            return await func(brand_id)

    async def rollback(self, execution_result: Dict, brand_id: int) -> Dict:
        """Rollback an executed action (currently only logs)."""
        action = execution_result.get("action", {})
        action_name = action.get("name", "unknown")
        logger.warning(f"🔄 Rolling back action: {action_name}")
        try:
            result = await self.client.rollback_action(
                action.get("target", "unknown"),
                brand_id,
                action_name
            )
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {"success": False, "error": str(e)}