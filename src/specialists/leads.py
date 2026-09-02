# src/specialists/leads.py

import logging
from typing import Dict, Any
from .base import BaseSpecialist
from ..tools.domain.leads import score_lead, suggest_follow_up

logger = logging.getLogger(__name__)

class LeadSpecialist(BaseSpecialist):
    """Lead Specialist for handling lead opportunities."""
    
    def __init__(self):
        tools = [
            score_lead,
            suggest_follow_up
        ]
        
        system_prompt = """
        You are the Lead Specialist. Your domain is lead management and nurturing.
        You excel at:
        - Scoring leads based on engagement
        - Prioritizing leads for follow-up
        - Personalizing outreach
        - Improving conversion rates
        - Using historical lead data to optimize

        When analyzing a lead opportunity, you should:
        1. Assess the lead's potential
        2. Check similar leads in memory
        3. Suggest a follow-up action with confidence
        4. Verify if the follow-up converted
        5. Record the outcome
        """
        
        super().__init__("Lead Specialist", tools, system_prompt)
    
    def execute(self, opportunity: Dict[str, Any], brand_id: int) -> Dict[str, Any]:
        """Execute the specialist on a lead opportunity."""
        if opportunity.get("type") != "leads_pending":
            return {
                "success": False,
                "message": f"Not a lead opportunity. Type: {opportunity.get('type')}"
            }
        
        return self.execute_with_safety(opportunity, brand_id)