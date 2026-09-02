# src/specialists/base.py

import json
import logging
from typing import Dict, Any, List, Optional
from strands import Agent
from strands.models import OllamaModel, GeminiModel
from ..config import Config
from ..utils.api_client import LaravelApiClient
from ..policies.safety import SafetyPolicy
from ..memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)

class BaseSpecialist:
    """Base class for all specialists."""
    
    def __init__(self, name: str, tools: List, system_prompt: str):
        self.name = name
        self.client = LaravelApiClient()
        self.safety = SafetyPolicy()
        self.memory = ExperienceMemory()
        
        # Setup model (Ollama first, Gemini fallback)
        self.model = self._setup_model()
        
        # Create the specialist agent
        self.agent = Agent(
            model=self.model,
            tools=tools,
            system_prompt=system_prompt
        )
    
    def _setup_model(self):
        """Setup model with Ollama as primary, Gemini as fallback."""
        # Try Ollama first (cost savings)
        try:
            return OllamaModel(
                host=Config.OLLAMA_HOST,
                model_id=Config.OLLAMA_MODEL,
                params={"temperature": 0.7, "max_tokens": 2048}
            )
        except Exception as e:
            logger.warning(f"Ollama not available: {e}. Falling back to Gemini.")
            return GeminiModel(
                client_args={"api_key": Config.GEMINI_API_KEY},
                model_id=Config.GEMINI_MODEL,
                params={"temperature": 0.7, "max_tokens": 2048}
            )
    
    def execute_with_safety(self, opportunity: Dict[str, Any], brand_id: int) -> Dict[str, Any]:
        """Execute with hard safety gate."""
        try:
            # 1. Gather evidence
            evidence = {
                "analytics": self.client.get_analytics(brand_id),
                "seo_data": self.client.get_seo_issues(brand_id),
                "leads": self.client.get_pending_leads(brand_id),
                "campaigns": self.client.get_campaigns(brand_id),
            }
            
            # 2. Get pattern analysis
            pattern = self.memory.analyze_patterns(opportunity, brand_id)
            
            # 3. Build the analysis prompt
            analysis_prompt = f"""
            Analyze this opportunity for brand {brand_id}:
            
            Opportunity: {json.dumps(opportunity, indent=2)}
            Evidence: {json.dumps(evidence, indent=2)}
            Pattern Analysis: {json.dumps(pattern, indent=2)}
            
            Based on the evidence and pattern analysis, decide if this should be autonomous.
            Return a JSON response with:
            - proposed_action: The action to take
            - confidence: 0.0-1.0 score
            - reasoning: Your reasoning
            - estimated_impact: Dollar value
            - autonomous: true/false
            """
            
            # 4. Get AI reasoning
            response = self.agent.invoke(analysis_prompt)
            
            # 5. Parse the response
            decision = self._parse_decision(response)
            
            # 6. ✅ HARD SAFETY GATE
            safety_result = self.safety.evaluate({
                "action_name": decision.get("proposed_action", {}).get("name", "unknown"),
                "brand_id": brand_id,
                "estimated_impact": decision.get("estimated_impact", 0),
                "confidence": decision.get("confidence", 0.0)
            })
            
            # 7. Override with safety result
            decision["autonomous"] = safety_result.get("autonomous", False)
            decision["requires_approval"] = safety_result.get("requires_approval", True)
            decision["safety_reason"] = safety_result.get("reason", "Safety policy applied")
            
            return {
                "success": True,
                "decision": decision,
                "requires_approval": decision.get("requires_approval", True)
            }
            
        except Exception as e:
            logger.error(f"Execution with safety failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "requires_approval": True
            }
    
    def _parse_decision(self, response: Any) -> Dict[str, Any]:
        """Parse the AI response."""
        try:
            # Try to extract JSON from response
            content = str(response)
            # Find JSON block
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = content[start:end]
                return json.loads(json_str)
            
            # Fallback: parse from text
            return {
                "proposed_action": {
                    "name": "no_action_needed",
                    "target": "none",
                    "payload": {}
                },
                "confidence": 0.0,
                "reasoning": "Could not parse AI response, defaulting to no action",
                "estimated_impact": 0,
                "autonomous": False
            }
        except Exception as e:
            logger.error(f"Failed to parse decision: {e}")
            return {
                "proposed_action": {
                    "name": "no_action_needed",
                    "target": "none",
                    "payload": {}
                },
                "confidence": 0.0,
                "reasoning": "Failed to parse response, defaulting to no action",
                "estimated_impact": 0,
                "autonomous": False
            }