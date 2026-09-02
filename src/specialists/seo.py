# src/specialists/seo.py

import logging
from typing import Dict, Any
from .base import BaseSpecialist
from ..tools.domain.seo import analyze_seo_issue, get_ranking_data

logger = logging.getLogger(__name__)

class SeoSpecialist(BaseSpecialist):
    """SEO Specialist for handling SEO issues."""
    
    def __init__(self):
        tools = [analyze_seo_issue, get_ranking_data]
        system_prompt = """
        You are the SEO Specialist. Analyze SEO issues and propose fixes.
        Consider: meta tags, broken links, rankings, content gaps.
        """
        super().__init__("SEO Specialist", "seo", tools, system_prompt)
    
    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        """Execute an SEO decision."""
        action = decision.get("action", {})
        action_name = action.get("name", "unknown")
        
        if action_name == "resolve_seo_issue":
            result = await self.client.scan(brand_id)
        else:
            result = await self.client.create_pending_action(brand_id, action, "SEO action")
        
        return {"success": True, "result": result}