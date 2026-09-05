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
2. Check if similar content was successful (use memory)
3. Propose content generation with confidence
4. Verify if the content performs well
5. Record the outcome
"""
        super().__init__("Content Specialist", "content", tools, system_prompt)

    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        """Execute a content decision."""
        action = decision.get("action", {})
        action_name = action.get("name", "unknown")

        if action_name == "trigger_content_generation":
            payload = action.get("payload", {})
            result = await self.client.generate_content(
                brand_id,
                payload.get("topic", "Untitled"),
                payload.get("template", "blog")
            )
        else:
            result = await self.client.create_pending_action(brand_id, action, "Content action")

        return {"success": True, "result": result}