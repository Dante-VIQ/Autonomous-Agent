# src/specialists/lead.py

import logging
from typing import Dict, Any
from .base import BaseSpecialist
from ..tools.domain.leads import score_lead, suggest_follow_up

logger = logging.getLogger(__name__)

class LeadSpecialist(BaseSpecialist):
    """Lead Specialist for handling lead opportunities."""
    
    def __init__(self):
        tools = [score_lead, suggest_follow_up]
        system_prompt = """
        You are the Lead Specialist. Analyze lead opportunities and propose follow-up actions.
        Consider: lead score, engagement, context.
        """
        super().__init__("Lead Specialist", "leads", tools, system_prompt)
    
    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        """Execute a lead decision."""
        action = decision.get("action", {})
        action_name = action.get("name", "unknown")
        
        if action_name == "notify_lead_response":
            payload = action.get("payload", {})
            result = await self.client.generate_follow_up(brand_id, payload.get("lead_id"))
        else:
            result = await self.client.create_pending_action(brand_id, action, "Lead action")
        
        return {"success": True, "result": result}