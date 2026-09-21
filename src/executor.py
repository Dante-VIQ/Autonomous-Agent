# src/executor.py

import asyncio
import httpx
import logging
from typing import Dict, Any
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

            # ✅ Lift action_id from result to top level
            action_id = None
            if isinstance(result, dict):
                action_id = result.get("action_id") or result.get("id")

            return {
                "status": "executed",
                "action": action,
                "action_id": action_id,     # ← top-level for verifier
                "result": result,
                "duration": 0,
            }
            
        except httpx.ReadTimeout:
            logger.error(f"⏰ Timeout while executing {name} – Laravel is taking too long.")
            return {
                "status": "timeout",
                "action": action,
                "error": "Request timed out – content generation may still be running.",
                "duration": 0,
            }
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "action": action,
                "error": str(e),
                "duration": 0,
            }

    async def _route_action(self, name: str, payload: Dict, brand_id: int) -> Any:
        """Route to the appropriate Laravel endpoint."""

        # Skip no-op actions – don't clutter the queue
        if name == "no_action_needed":
            logger.info("⏭️  No action needed – skipping execution")
            return {"status": "skipped", "reason": "no_action_needed"}

        action_map = {
            "resolve_seo_issue": self.client.scan,
            "run_site_scan": self.client.scan,
            "trigger_content_generation": self.client.generate_content,
            "create_blog_post": self.client.generate_content,
            "generate_content": self.client.generate_content,
            "notify_lead_response": self.client.generate_follow_up,
        }

        func = action_map.get(name)
        if not func:
            # Generic action – create pending action with clear metadata
            return await self.client.create_pending_action(
                brand_id,
                {
                    "name": name,
                    "payload": payload,
                    "reason": "Autonomous execution – action requires manual setup",
                },
                "Autonomous execution",
            )

        if name in ("trigger_content_generation", "create_blog_post", "generate_content"):
            return await func(
                brand_id,
                payload.get("topic", "Untitled"),
                payload.get("template", "blog"),
            )
        elif name == "notify_lead_response":
            return await func(brand_id, payload.get("lead_id"))
        elif name in ("pause_campaign", "adjust_campaign"):
            return await func(
                brand_id,
                payload.get("campaign_id"),
                payload.get("reason", "Paused by AI"),
            )
        else:
            return await func(brand_id)

    async def request_rollback(self, execution_result: Dict, brand_id: int) -> Dict:
        """Request a rollback. Marks intent — does not undo the action."""
        action = execution_result.get("action", {})
        action_name = action.get("name", "unknown")
        action_id = execution_result.get("action_id")

        if not action_id:
            logger.warning(f"Cannot request rollback for {action_name}: no action_id")
            return {"success": False, "reason": "no action_id"}

        logger.warning(f"🔄 Rollback REQUESTED for action: {action_name}")
        try:
            result = await self.client.request_rollback(
                action_id,
                f"Rollback requested: {action_name}",
            )
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Rollback request failed: {e}")
            return {"success": False, "error": str(e)}