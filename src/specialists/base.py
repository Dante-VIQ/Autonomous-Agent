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
    payload_json: str = Field(
        default="{}",
        description='A JSON object string, e.g. \'{"topic": "...", "template": "blog"}\'. Use "{}" if none.'
    )


class _DecisionSchema(BaseModel):
    action: _ActionSchema
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    estimated_impact: float = 0.0


class BaseSpecialist:
    def __init__(self, name: str, domain: str, tools: List, system_prompt: str):
        self.name = name
        self.domain = domain
        self.client = LaravelApiClient()
        self.safety = SafetyPolicy()
        self.memory = ExperienceMemory()
        self.tools = tools
        self.system_prompt = system_prompt
        self.brand_id = None

        # Build both models; fallback decision happens at call time
        self.model, self.fallback_model = self._setup_models()

        # Create primary and fallback agents
        self.agent = Agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.system_prompt,
        ) if self.model else None

        self.fallback_agent = Agent(
            model=self.fallback_model,
            tools=self.tools,
            system_prompt=self.system_prompt,
        ) if self.fallback_model else None

    def _setup_models(self):
        from strands.models import OllamaModel, GeminiModel

        primary = None
        try:
            primary = OllamaModel(
                host=Config.OLLAMA_HOST,
                model_id=Config.OLLAMA_MODEL,
                temperature=0.7,
                max_tokens=2048
            )
        except Exception as e:
            logger.warning(f"Could not construct Ollama model: {e}")

        fallback = None
        if Config.GEMINI_API_KEY:
            try:
                fallback = GeminiModel(
                    client_args={"api_key": Config.GEMINI_API_KEY},
                    model_id=Config.GEMINI_MODEL,
                    params={"temperature": 0.7, "max_output_tokens": 2048}
                )
            except Exception as e:
                logger.warning(f"Could not construct Gemini model: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set – no fallback model if Ollama is unreachable.")

        if primary is None and fallback is None:
            raise RuntimeError("No usable model could be configured – both Ollama and Gemini failed to construct.")

        return primary, fallback

    async def reason(self, opportunity: Dict, evidence: Dict, context: Dict) -> Dict:
        brand_id = context.get("brand_id")
        pattern = await self.memory.analyze_patterns(opportunity, brand_id)
        prompt = self._build_reasoning_prompt(opportunity, evidence, pattern, context)
        response = await self._get_ai_reasoning(prompt)
        decision = self._parse_decision(response)

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

**Allowed action names (use exactly one of these):**
- trigger_content_generation  (for creating blog posts, social media, or email content)
- resolve_seo_issue           (for fixing SEO problems)
- notify_lead_response        (for following up with leads)
- pause_campaign              (for pausing underperforming campaigns)
- no_action_needed            (if no action is needed)

Return a JSON object with: action {{name, target, payload}}, confidence, reasoning, estimated_impact.
"""

async def _get_ai_reasoning(self, prompt: str) -> str:
    last_error: Optional[Exception] = None

    if self.agent:
        try:
            decision = await self.agent.structured_output_async(
                output_model=_DecisionSchema,
                prompt=prompt,
            )
            return self._decision_to_json(decision)
        except Exception as e:
            last_error = e
            # ✅ Check if the error is due to empty response
            if "EOF" in str(e) or "Invalid JSON" in str(e):
                logger.warning(f"Ollama returned empty response for {self.name}, falling back")
                # Continue to fallback
            else:
                logger.warning(f"Primary model failed for {self.name}: {e}")

    # If we reached here, structured output failed — use regular generation
    try:
        # Use the model's generate method directly (not structured)
        response = await self.model.generate(prompt)
        content = response.get("content", "") if isinstance(response, dict) else str(response)
        if not content or content.strip() == "":
            raise ValueError("Empty response from model")
        # Try to parse JSON from the response
        return self._extract_json_from_response(content)
    except Exception as e:
        logger.error(f"All AI methods failed for {self.name}: {e}")
        return self._get_fallback_decision()


        def _extract_json_from_response(self, content: str) -> str:
    """Extract JSON from a free-text response."""
    import re
    # Try to find a JSON object in the response
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Validate it's valid JSON
        try:
            json.loads(json_str)
            return json_str
        except:
            pass
    # Fallback: return a default decision
    return json.dumps({
        "action": {"name": "no_action_needed", "target": "none", "payload": {}},
        "confidence": 0.0,
        "reasoning": "Could not extract valid JSON from model response",
        "estimated_impact": 0,
    })

    
    @staticmethod
    def _decision_to_json(decision: "_DecisionSchema") -> str:
        try:
            payload = json.loads(decision.action.payload_json)
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

        return json.dumps({
            "action": {
                "name": decision.action.name,
                "target": decision.action.target,
                "payload": payload,
            },
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "estimated_impact": decision.estimated_impact,
        })

    def _parse_decision(self, response: str) -> Dict:
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