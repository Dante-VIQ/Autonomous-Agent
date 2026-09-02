# src/learner.py

import logging
from typing import Dict, Any
from .utils.api_client import LaravelApiClient
from .memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)

class Learner:
    """Records learning outcomes for future decisions."""
    
    def __init__(self):
        self.client = LaravelApiClient()
        self.memory = ExperienceMemory()
    
    async def record(self, opportunity: Dict, decision: Dict, execution: Dict, verification: Dict, brand_id: int) -> Dict:
        """Record a complete learning cycle."""
        
        # Build structured learning record
        learning = {
            "opportunity_type": opportunity.get("type", "unknown"),
            "severity": opportunity.get("severity", "medium"),
            "action_name": decision.get("action", {}).get("name", "unknown"),
            "confidence": decision.get("confidence", 0.0),
            "was_autonomous": execution.get("status") == "executed",
            "was_successful": verification.get("was_successful", False),
            "improvement_percentage": verification.get("improvement", {}).get("average", 0) * 100,
            "duration_seconds": execution.get("duration", 0),
            "context": {
                "opportunity": opportunity,
                "decision": decision,
                "execution": execution,
                "verification": verification
            },
            "learning_type": self._determine_learning_type(verification)
        }
        
        # Store in Laravel
        result = await self.client.record_learning(brand_id, learning)
        
        logger.info(f"📝 Learning recorded for {learning['action_name']}")
        
        return result
    
    def _determine_learning_type(self, verification: Dict) -> str:
        """Determine what type of learning occurred."""
        if not verification.get("was_successful", False):
            return "failure"
        
        improvement = verification.get("improvement", {}).get("average", 0)
        if improvement > 0.15:
            return "significant_success"
        elif improvement > 0.05:
            return "moderate_success"
        else:
            return "marginal_success"