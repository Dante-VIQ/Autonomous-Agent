# src/specialists/seo.py

import logging
from typing import Dict, Any
from .base import BaseSpecialist
from ..tools.domain.seo import analyze_seo_issue, get_ranking_data

logger = logging.getLogger(__name__)

class SeoSpecialist(BaseSpecialist):
    """SEO Specialist for handling SEO issues."""

    def __init__(self):
        tools = [
            analyze_seo_issue,
            get_ranking_data
        ]
        system_prompt = """
You are the SEO Specialist. Your domain is search engine optimization.
You excel at:
- Identifying SEO issues (meta tags, broken links, content gaps)
- Prioritizing issues by impact
- Suggesting actionable fixes
- Monitoring SEO performance over time
- Using historical SEO data to guide decisions

When you analyze an SEO opportunity, you should:
1. Understand the specific issue
2. Check if similar issues were resolved before (use memory)
3. Propose a fix with confidence score
4. Verify if the fix worked
5. Record the outcome
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