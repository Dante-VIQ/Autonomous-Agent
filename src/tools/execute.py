# src/tools/execute.py

import json
import logging
from typing import Dict, Any
from strands import tool
from ..utils.api_client import LaravelApiClient
from ..config import Config

logger = logging.getLogger(__name__)

@tool
def execute_action(action: Dict[str, Any], brand_id: int) -> str:
    """
    Execute an approved action. ONLY call if autonomous flag is true.
    
    ⚠️ HARD SAFETY GATE: This function checks the _autonomous flag.
    If not set, it queues for human review instead of executing.
    
    Returns:
        JSON string with execution result or approval request
    """
    client = LaravelApiClient()
    
    try:
        # ✅ HARD SAFETY GATE – Not just a prompt instruction
        if not action.get("_autonomous", False):
            logger.warning(f"Action '{action.get('name', 'unknown')}' requires approval - queuing for review")
            
            # Queue for human review
            result = client.create_pending_action(
                brand_id,
                action,
                "Autonomous flag not set. Requires human approval."
            )
            
            return json.dumps({
                "success": True,
                "executed": False,
                "requires_approval": True,
                "message": "Action requires human approval. Queued for review.",
                "result": result
            })
        
        # ✅ Autonomous execution
        action_name = action.get("name", "unknown")
        logger.info(f"Executing autonomous action: {action_name}")
        
        # Execute based on action type
        execution_result = None
        
        if action_name == "resolve_seo_issue":
            execution_result = client.scan(brand_id)
        elif action_name == "trigger_content_generation":
            payload = action.get("payload", {})
            execution_result = client.generate_content(
                brand_id,
                payload.get("topic", "untitled"),
                payload.get("template", "blog")
            )
        elif action_name == "notify_lead_response":
            payload = action.get("payload", {})
            execution_result = client.generate_follow_up(
                brand_id,
                payload.get("lead_id", "")
            )
        elif action_name == "pause_campaign":
            payload = action.get("payload", {})
            execution_result = client.pause_campaign(
                brand_id,
                payload.get("campaign_id", ""),
                payload.get("reason")
            )
        else:
            # Generic execution
            execution_result = client.create_pending_action(brand_id, action, "Autonomous execution")
        
        return json.dumps({
            "success": True,
            "executed": True,
            "requires_approval": False,
            "message": f"Action '{action_name}' executed successfully",
            "result": execution_result
        })
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return json.dumps({
            "success": False,
            "executed": False,
            "error": str(e)
        })