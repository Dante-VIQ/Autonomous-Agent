# src/executor.py

import logging
from typing import Dict, Any
from datetime import datetime
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

class Executor:
    """Handles action execution with retry and rollback support."""

    def __init__(self):
        self.client = LaravelApiClient()
        self.retry_count = 3

    async def execute(self, action: Dict, brand_id: int) -> Dict:
        """Execute an action with retry logic."""
        action_name = action.get("name", "unknown")
        payload = action.get("payload", {})
        
        logger.info(f"⚡ Executing action: {action_name}")
        start_time = datetime.now()

        for attempt in range(self.retry_count):
            try:
                # Route to appropriate Laravel endpoint
                result = await self._route_action(action_name, payload, brand_id)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Action {action_name} executed in {elapsed:.2f}s")
                
                return {
                    "status": "executed",
                    "action": action,
                    "result": result,
                    "duration": elapsed,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for {action_name}: {e}")
                if attempt == self.retry_count - 1:
                    logger.error(f"❌ Action {action_name} failed after {self.retry_count} attempts")
                    return {
                        "status": "failed",
                        "action": action,
                        "error": str(e),
                        "duration": (datetime.now() - start_time).total_seconds(),
                        "timestamp": datetime.now().isoformat()
                    }
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # Should never reach here
        return {"status": "failed", "error": "Unknown execution error"}

    async def _route_action(self, name: str, payload: Dict, brand_id: int) -> Dict:
        """Route action to the appropriate Laravel endpoint."""
        # Action mapping to Laravel methods
        action_map = {
            "resolve_seo_issue": self.client.scan,
            "run_site_scan": self.client.scan,
            "trigger_content_generation": self.client.generate_content,
            "notify_lead_response": self.client.generate_follow_up,
            "pause_campaign": self.client.pause_campaign,
        }
        
        func = action_map.get(name)
        if not func:
            # Generic action: log and create pending action
            logger.info(f"No specific handler for {name}, creating pending action")
            return await self.client.create_pending_action(
                brand_id,
                {"name": name, "payload": payload},
                "Generic action"
            )
        
        # Call with appropriate parameters
        if name == "trigger_content_generation":
            return func(brand_id, 
                       payload.get("topic", "Untitled"),
                       payload.get("template", "blog"))
        elif name == "notify_lead_response":
            return func(brand_id, payload.get("lead_id"))
        elif name == "pause_campaign":
            return func(brand_id, payload.get("campaign_id"), 
                       payload.get("reason", "Paused by AI"))
        else:
            return func(brand_id)

    async def rollback(self, execution_result: Dict, brand_id: int) -> Dict:
        """Rollback an executed action."""
        action = execution_result.get("action", {})
        action_name = action.get("name", "unknown")
        logger.warning(f"🔄 Rolling back action: {action_name}")
        
        try:
            # Call Laravel rollback endpoint
            result = await self.client.rollback_action(
                action.get("target", "unknown"),
                brand_id,
                action_name
            )
            return {
                "success": True,
                "message": f"Rollback initiated for {action_name}",
                "result": result
            }
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }