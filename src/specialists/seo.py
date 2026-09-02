# src/specialists/seo.py

import logging
from typing import Dict, Any
from strands import tool
from .base import BaseSpecialist
from ..tools.domain.seo import analyze_seo_issue, get_ranking_data

logger = logging.getLogger(__name__)

class SeoSpecialist(BaseSpecialist):
    """SEO Specialist for handling SEO issues."""
    
    def __init__(self):
        # Define domain-specific tools
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
        2. Check if similar issues were resolved before
        3. Propose a fix with confidence score
        4. Verify if the fix worked
        5. Record the outcome
        """
        
        super().__init__("SEO Specialist", tools, system_prompt)
    
    def execute(self, opportunity: Dict[str, Any], brand_id: int) -> Dict[str, Any]:
        """Execute the specialist on an SEO opportunity."""
        if opportunity.get("type") != "seo_issue":
            return {
                "success": False,
                "message": f"Not an SEO opportunity. Type: {opportunity.get('type')}"
            }
        
        return self.execute_with_safety(opportunity, brand_id)