# src/tools/decision.py

import json
import logging
from typing import Dict, Any
from strands import tool
from ..utils.api_client import LaravelApiClient
from ..policies.safety import SafetyPolicy
from ..memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)

@tool
def intelligent_decision(opportunity: Dict[str, Any], brand_id: int) -> str:
    """
    Analyze an opportunity using AI reasoning and safety policies.
    Uses REAL data from Vumbi Ventures Laravel backend.
    
    Returns:
        JSON string with decision: autonomous or requires approval
    """
    client = LaravelApiClient()
    safety = SafetyPolicy()
    memory = ExperienceMemory()
    
    try:
        # 1. Gather evidence (real data)
        evidence = {
            "analytics": client.get_analytics(brand_id),
            "seo_data": client.get_seo_issues(brand_id),
            "leads": client.get_pending_leads(brand_id),
            "campaigns": client.get_campaigns(brand_id),
        }
        
        # 2. Get similar experiences (real learning)
        similar = memory.find_similar(opportunity, brand_id)
        pattern = memory.analyze_patterns(opportunity, brand_id)
        
        # 3. Build context for AI
        context = {
            "opportunity": opportunity,
            "evidence": evidence,
            "similar_experiences": similar,
            "pattern_analysis": pattern,
            "brand_id": brand_id
        }
        
        # 4. The AI reasoning will happen in the agent loop
        # This tool provides the structured data for the agent to reason about
        
        # 5. Safety policy check (hard gate)
        safety_result = safety.evaluate({
            "action_name": opportunity.get("type", "unknown"),
            "brand_id": brand_id,
            "estimated_impact": opportunity.get("impact", 0),
            "payload": opportunity.get("payload", {})
        })
        
        return json.dumps({
            "success": True,
            "opportunity": opportunity,
            "evidence": evidence,
            "pattern_analysis": pattern,
            "safety_result": safety_result,
            "autonomous": safety_result.get("autonomous", False),
            "reasoning": f"Based on evidence and pattern analysis, action requires {'autonomous execution' if safety_result.get('autonomous') else 'human approval'}."
        })
        
    except Exception as e:
        logger.error(f"Decision failed: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "autonomous": False,
            "reasoning": "Decision failed, routing to human review."
        })