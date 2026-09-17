# src/specialists/base.py

import json
import logging
import re
import asyncio
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

        # Build both models
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

    # ============================================================
    # MODEL SETUP
    # ============================================================

    def _setup_models(self):
        """Build primary (Gemini) and optional fallback (Ollama) models."""
        from strands.models import OllamaModel, GeminiModel

        primary = None
        fallback = None

        # Gemini is primary (reliable)
        if Config.GEMINI_API_KEY:
            try:
                primary = GeminiModel(
                    client_args={"api_key": Config.GEMINI_API_KEY},
                    model_id=Config.GEMINI_MODEL,
                    params={"temperature": 0.7, "max_output_tokens": 2048}
                )
            except Exception as e:
                logger.warning(f"Could not construct Gemini model: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set.")

        # Ollama as fallback (optional)
        if Config.OLLAMA_HOST and Config.OLLAMA_MODEL:
            try:
                fallback = OllamaModel(
                    host=Config.OLLAMA_HOST,
                    model_id=Config.OLLAMA_MODEL,
                    temperature=0.7,
                    max_tokens=2048
                )
            except Exception as e:
                logger.warning(f"Could not construct Ollama model: {e}")

        if primary is None and fallback is None:
            raise RuntimeError(
                "No usable model could be configured – "
                "set GEMINI_API_KEY or configure Ollama."
            )

        return primary, fallback

    # ============================================================
    # REASON (public entry point)
    # ============================================================

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
            "estimated_impact": decision.get("estimated_impact", 0),
        })
        decision["autonomous"] = safety_result.get("autonomous", False)
        decision["requires_approval"] = safety_result.get("requires_approval", True)
        decision["safety_reason"] = safety_result.get("reason", "Safety policy applied")
        return decision

    # ============================================================
    # PROMPT BUILDER
    # ============================================================
    def _build_reasoning_prompt(self, opportunity, evidence, pattern, context):
        # Trim evidence to essentials
        trimmed_evidence = {
            "analytics": evidence.get("analytics", {}),
            "seo_count": len(evidence.get("seo_issues", [])),
            "lead_count": len(evidence.get("leads", [])),
            "campaign_count": len(evidence.get("campaigns", [])),
        }

        # Trim pattern insights to top 3
        trimmed_pattern = {
            "success_rate": pattern.get("success_rate"),
            "avg_improvement": pattern.get("avg_improvement"),
            "insights": pattern.get("insights", [])[:3],
        }

        # --- Strategic Brief block ---
        brief = context.get("brief", {}) or {}
        brief_block = ""
        if brief.get("strategic_diagnosis"):
            suggested = brief.get("suggested_actions", []) or []
            brief_block = f"""
📋 TODAY'S STRATEGIC BRIEF (from the business):
  Diagnosis: {brief['strategic_diagnosis']}
  Estimated revenue impact: ${brief.get('estimated_revenue_impact', 0):,.2f}
  Confidence: {brief.get('confidence_score', 0):.1f}%
  Suggested actions: {', '.join(str(s) for s in suggested)}

⚡ Weight your decision toward opportunities that align with this brief.
"""

        # --- Recurrence block ---
        recurrence_block = ""
        recurrence = context.get("recurrence", {})
        history = context.get("recurrence_history", {})

        if recurrence and recurrence.get("is_recurring"):
            count = recurrence.get("recurrence_count", 1)
            first_seen = recurrence.get("first_seen_at", "unknown")
            summary = history.get("summary", {})
            attempts = history.get("attempts", [])

            recurrence_block = f"\n⚠️  RECURRING ISSUE — This is attempt #{count}\n"
            recurrence_block += f"First seen: {first_seen}\n"
            recurrence_block += f"Prior attempts: {summary.get('total_attempts', count - 1)}\n"
            recurrence_block += f"Prior successes: {summary.get('successful', 0)}\n"
            recurrence_block += f"Prior failures: {summary.get('failed', 0)}\n"

            if summary.get("rejection_reasons"):
                recurrence_block += (
                    f"Human rejection reasons: {', '.join(summary['rejection_reasons'])}\n"
                )

            if attempts:
                recurrence_block += "\nRecent attempts:\n"
                for attempt in attempts[-3:]:
                    status = attempt.get("status", "unknown")
                    date = attempt.get("date", "unknown")
                    reason = attempt.get("rejection_reason") or "—"
                    notes = attempt.get("review_notes") or "—"
                    recurrence_block += (
                        f"  • {date} — status: {status}, "
                        f"rejection: {reason}, notes: {notes}\n"
                    )

            recurrence_block += (
                "\nIMPORTANT: Previous approaches have failed to resolve this permanently. "
                "Consider:\n"
                "  1. Is the root cause different than previous attempts assumed?\n"
                "  2. Is the fix actually being deployed to production?\n"
                "  3. Do you need to take a DIFFERENT approach this time?\n"
            )

        # --- SINGLE return with everything ---
        return f"""
You are the {self.name}. Analyze this opportunity:

{brief_block}
Opportunity: {opportunity}
Evidence: {trimmed_evidence}
Historical Pattern: {trimmed_pattern}
{recurrence_block}

Use your available tools if you need more information before deciding.
Then propose a single action: its name, target, and payload, your
confidence (0.0-1.0), your reasoning, and the estimated dollar impact.

**Allowed action names (use exactly one of these):**
- trigger_content_generation  (for creating blog posts, social media, or email content)
- resolve_seo_issue           (for fixing SEO problems)
- notify_lead_response        (for following up with leads)
- pause_campaign              (for pausing underperforming campaigns)
- adjust_campaign             (for adjusting campaign settings)
- no_action_needed            (if no action is needed)

Return a JSON object with: action {{name, target, payload}}, confidence, reasoning, estimated_impact.
"""

    # ============================================================
    # AI REASONING
    # ============================================================

    async def _get_ai_reasoning(self, prompt: str) -> str:
        last_error = None

        # --- Try primary (Gemini) with 120s timeout ---
        if self.agent:
            try:
                decision = await asyncio.wait_for(
                    self.agent.structured_output_async(
                        output_model=_DecisionSchema,
                        prompt=prompt,
                    ),
                    timeout=120.0
                )
                return self._decision_to_json(decision)
            except asyncio.TimeoutError:
                last_error = "Primary model timed out after 120s"
                logger.warning(f"⏰ Primary model timed out for {self.name}")
            except Exception as e:
                last_error = e
                logger.warning(f"Primary model failed for {self.name}: {e}")

        # --- Try fallback (Ollama) with 120s timeout ---
        if self.fallback_agent:
            try:
                decision = await asyncio.wait_for(
                    self.fallback_agent.structured_output_async(
                        output_model=_DecisionSchema,
                        prompt=prompt,
                    ),
                    timeout=120.0
                )
                return self._decision_to_json(decision)
            except asyncio.TimeoutError:
                last_error = "Fallback model timed out after 120s"
                logger.error(f"⏰ Fallback model timed out for {self.name}")
            except Exception as e:
                last_error = e
                logger.error(f"Fallback model failed for {self.name}: {e}")

        # --- Final fallback: plain generation ---
        try:
            model_to_use = self.model or self.fallback_model
            if not model_to_use:
                raise ValueError("No model available")
            response = await asyncio.wait_for(
                model_to_use.generate(prompt),
                timeout=60.0
            )
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            if not content or content.strip() == "":
                raise ValueError("Empty response from model")
            return self._extract_json_from_response(content)
        except Exception as e:
            logger.error(f"All AI methods failed for {self.name}: {last_error or e}")
            return self._get_fallback_decision()

    # ============================================================
    # HELPERS
    # ============================================================

    def _extract_json_from_response(self, content: str) -> str:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                pass

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
                "autonomous": False,
            }

    def _get_fallback_decision(self) -> str:
        return json.dumps({
            "action": {"name": "no_action_needed", "target": "none", "payload": {}},
            "confidence": 0.0,
            "reasoning": "AI reasoning failed, fallback to no action",
            "estimated_impact": 0,
        })