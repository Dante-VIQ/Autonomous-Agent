# src/specialists/base.py

import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from strands import Agent
from ..config import Config
from ..utils.api_client import LaravelApiClient
from ..policies.safety import SafetyPolicy
from ..memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)


class _ActionSchema(BaseModel):
    name: str
    target: str = "system"
    payload: Dict[str, Any] = Field(default_factory=dict)


class _DecisionSchema(BaseModel):
    """Schema the model must fill via structured_output_async."""
    action: _ActionSchema
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    estimated_impact: float = 0.0

class BaseSpecialist:
    """
    Base class for all specialists.
    A specialist is responsible for reasoning about opportunities in its domain.
    """

    def __init__(self, name: str, domain: str, tools: List, system_prompt: str):
        self.name = name
        self.domain = domain
        self.client = LaravelApiClient()
        self.safety = SafetyPolicy()
        self.memory = ExperienceMemory()
        self.tools = tools
        self.system_prompt = system_prompt
        self.brand_id = None

        # Setup model (Ollama first, Gemini fallback)
        self.model = self._setup_model()

        # The actual agent loop: gives the model access to this specialist's
        # domain tools and a guaranteed decision shape via structured_output_async.
        self.agent = Agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

    def _setup_model(self):
        """Setup model with Ollama as primary, Gemini as fallback."""
        from strands.models import OllamaModel, GeminiModel

        try:
            return OllamaModel(
                host=Config.OLLAMA_HOST,
                model_id=Config.OLLAMA_MODEL,
                temperature=0.7,
                max_tokens=2048
            )
        except Exception as e:
            logger.warning(f"Ollama not available: {e}. Falling back to Gemini.")
            return GeminiModel(
                client_args={"api_key": Config.GEMINI_API_KEY},
                model_id=Config.GEMINI_MODEL,
                temperature=0.7,
                max_tokens=2048
            )


    async def reason(self, opportunity: Dict, evidence: Dict, context: Dict) -> Dict:
        """
        Reason about an opportunity and produce a decision.
        """
        brand_id = context.get("brand_id")

        # 1. Get similar experiences
        pattern = await self.memory.analyze_patterns(opportunity, brand_id)

        # 2. Build the reasoning prompt
        prompt = self._build_reasoning_prompt(opportunity, evidence, pattern, context)

        # 3. Get AI reasoning (structured output)
        response = await self._get_ai_reasoning(prompt)

        # 4. Parse and return decision
        decision = self._parse_decision(response)

        # 5. Apply safety policy (overrides autonomous flag)
        safety_result = self.safety.evaluate({
            "action_name": decision.get("action", {}).get("name", "unknown"),
            "brand_id": brand_id,
            "confidence": decision.get("confidence", 0.0),
            "estimated_impact": decision.get("estimated_impact", 0)
        })

        decision["autonomous"] = safety_result.get("autonomous", False)
        decision["requires_approval"] = safety_result.get("requires_approval", True)
        decision["safety_reason"] = safety_result.get("reason", "Safety policy applied")

        return decision

    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        """Execute a decision. Override in subclasses."""
        return {
            "success": True,
            "message": f"Executed {decision.get('action', {}).get('name', 'unknown')}",
            "result": decision
        }

    def _build_reasoning_prompt(self, opportunity: Dict, evidence: Dict, pattern: Dict, context: Dict) -> str:
        return f"""
You are the {self.name}. Analyze this opportunity:

Opportunity: {opportunity}
Evidence: {evidence}
Historical Pattern: {pattern}
Context: {context}

Use your available tools if you need more information before deciding.
Then propose a single action: its name, target, and payload, your
confidence (0.0-1.0), your reasoning, and the estimated dollar impact.
"""

    async def _get_ai_reasoning(self, prompt: str) -> str:
        """Get AI reasoning by calling the agent's structured_output_async."""
        try:
            decision = await self.agent.structured_output_async(
                output_model=_DecisionSchema,
                prompt=prompt,
            )
            return decision.model_dump_json()
        except Exception as e:
            logger.error(f"AI reasoning failed for {self.name}: {e}")
            return json.dumps({
                "action": {"name": "no_action_needed", "target": "none", "payload": {}},
                "confidence": 0.0,
                "reasoning": f"AI reasoning failed: {e}",
                "estimated_impact": 0,
            })

    def _parse_decision(self, response: str) -> Dict:
        """Parse the AI response into a decision."""
        try:
            return json.loads(response)
        except Exception:
            return {
                "action": {"name": "no_action_needed", "target": "none", "payload": {}},
                "confidence": 0.0,
                "reasoning": "Failed to parse response",
                "estimated_impact": 0,
                "autonomous": False
            }