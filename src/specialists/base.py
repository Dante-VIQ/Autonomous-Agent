# src/specialists/base.py

import logging
from typing import Dict, Any, List, Optional
from ..config import Config
from ..utils.api_client import LaravelApiClient
from ..policies.safety import SafetyPolicy
from ..memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)

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
        
        # Setup model (Ollama first, Gemini fallback)
        self.model = self._setup_model()
    
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
        This is the primary method that specialists implement.
        """
        # 1. Get similar experiences
        pattern = self.memory.analyze_patterns(opportunity, context.get("brand_id"))
        
        # 2. Build the reasoning prompt
        prompt = self._build_reasoning_prompt(opportunity, evidence, pattern, context)
        
        # 3. Get AI reasoning
        response = await self._get_ai_reasoning(prompt)
        
        # 4. Parse and return decision
        decision = self._parse_decision(response)
        
        # 5. Apply safety policy
        safety_result = self.safety.evaluate({
            "action_name": decision.get("action", {}).get("name", "unknown"),
            "brand_id": context.get("brand_id"),
            "confidence": decision.get("confidence", 0.0),
            "estimated_impact": decision.get("estimated_impact", 0)
        })
        
        decision["autonomous"] = safety_result.get("autonomous", False)
        decision["requires_approval"] = safety_result.get("requires_approval", True)
        decision["safety_reason"] = safety_result.get("reason", "Safety policy applied")
        
        return decision
    
    async def execute(self, decision: Dict, brand_id: int) -> Dict:
        """
        Execute a decision. This is called by the orchestrator after safety approval.
        """
        # Default implementation - can be overridden by specialists
        return {
            "success": True,
            "message": f"Executed {decision.get('action', {}).get('name', 'unknown')}",
            "result": decision
        }
    
    def _build_reasoning_prompt(self, opportunity: Dict, evidence: Dict, pattern: Dict, context: Dict) -> str:
        """Build the reasoning prompt for the AI."""
        return f"""
You are the {self.name}. Analyze this opportunity:

Opportunity: {opportunity}
Evidence: {evidence}
Historical Pattern: {pattern}
Context: {context}

Based on this information, propose an action.
Return a JSON with:
- action: {name, target, payload}
- confidence: 0.0-1.0
- reasoning: your reasoning
- estimated_impact: dollar value
- autonomous: true/false (if you think it can be done without human approval)
"""
    
    async def _get_ai_reasoning(self, prompt: str) -> str:
        """Get AI reasoning. Subclasses can override for domain-specific prompting."""
        # This would call the actual AI model
        # For now, return a placeholder
        return '{"action": {"name": "no_action_needed", "target": "none", "payload": {}}, "confidence": 0.0, "reasoning": "No action needed", "estimated_impact": 0, "autonomous": false}'
    
    def _parse_decision(self, response: str) -> Dict:
        """Parse the AI response into a decision."""
        import json
        try:
            return json.loads(response)
        except:
            return {
                "action": {"name": "no_action_needed", "target": "none", "payload": {}},
                "confidence": 0.0,
                "reasoning": "Failed to parse response",
                "estimated_impact": 0,
                "autonomous": False
            }