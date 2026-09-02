# src/specialists/content.py

import logging
from typing import Dict, Any
from .base import BaseSpecialist
from ..tools.domain.content import analyze_content_gap, generate_outline

logger = logging.getLogger(__name__)

class ContentSpecialist(BaseSpecialist):
    """Content Specialist for handling content opportunities."""
    
    def __init__(self):
        tools = [
            analyze_content_gap,
            generate_outline
        ]
        
        system_prompt = """
        You are the Content Specialist. Your domain is content creation and strategy.
        You excel at:
        - Identifying content gaps
        - Generating content outlines
        - Repurposing content across channels
        - Improving content quality
        - Using performance data to optimize

        When analyzing a content opportunity, you should:
        1. Assess what's needed
        2. Check if similar content was successful
        3. Propose content generation with confidence
        4. Verify if the content performs well
        5. Record the outcome
        """
        
        super().__init__("Content Specialist", tools, system_prompt)
    
    def execute(self, opportunity: Dict[str, Any], brand_id: int) -> Dict[str, Any]:
        """Execute the specialist on a content opportunity."""
        if opportunity.get("type") != "content_generation":
            return {
                "success": False,
                "message": f"Not a content opportunity. Type: {opportunity.get('type')}"
            }
        
        return self.execute_with_safety(opportunity, brand_id)