# src/orchestrator.py

import json
import logging
from typing import Dict, Any, List
from .tools.monitor import monitor_opportunities
from .specialists import SeoSpecialist, LeadSpecialist, ContentSpecialist
from .policies.safety import SafetyPolicy
from .executor import Executor
from .verifier import Verifier
from .learner import Learner
from .utils.api_client import LaravelApiClient
from .memory.experience import ExperienceMemory

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, brand_id: int):
        self.brand_id = brand_id
        self.context = {"brand_id": brand_id}  
        self.specialists = {
            "seo_issue": SeoSpecialist(),
            "leads_pending": LeadSpecialist(),
            "content_generation": ContentSpecialist(),
        }
        self.safety = SafetyPolicy()
        self.executor = Executor()
        self.verifier = Verifier()
        self.learner = Learner()
        self.client = LaravelApiClient()
        self.context = {}
        self.memory = ExperienceMemory()

    async def run_cycle(self) -> Dict[str, Any]:
        """Run a full cycle: monitor → process → learn."""
        logger.info(f"🔄 Starting cycle for brand {self.brand_id}")
        try:
            # 1. Monitor
            opportunities = await self._monitor()
            if not opportunities:
                logger.info("No opportunities found, skipping cycle.")
                return {"status": "idle", "message": "No opportunities found"}
            
            # 2. Process each opportunity
            results = []
            for opp in opportunities:
                result = await self._process_opportunity(opp)
                results.append(result)
            
            return {
                "status": "completed",
                "opportunities_processed": len(results),
                "results": results
            }
        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _monitor(self) -> List[Dict]:
        """Monitor for opportunities – async call."""
        result_str = await monitor_opportunities(self.brand_id)
        try:
            data = json.loads(result_str)
            opportunities = data.get("opportunities", [])
            logger.info(f"Found {len(opportunities)} opportunities")
            return opportunities
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse monitor response: {e}")
            return []

    async def _process_opportunity(self, opportunity: Dict) -> Dict:
        """Process a single opportunity through the pipeline."""
        opp_type = opportunity.get("type")
        specialist = self.specialists.get(opp_type)
        if not specialist:
            return {"success": False, "message": f"No specialist for {opp_type}"}
        
        # Gather evidence
        evidence = await self._gather_evidence(opportunity)
        
        # Reason (specialist.reason is async)
        decision = await specialist.reason(opportunity, evidence, self.context)
        
        pattern = await self.memory.analyze_patterns(opportunity, self.brand_id)

        # Safety policy
        safety_result = self.safety.evaluate({
            "action_name": decision.get("action", {}).get("name", "unknown"),
            "brand_id": self.brand_id,
            "confidence": decision.get("confidence", 0.0),
            "estimated_impact": decision.get("estimated_impact", 0)
        })
        
        # Execute or approve
        if safety_result.get("autonomous", False):
            execution_result = await self.executor.execute(decision, self.brand_id)
        else:
            execution_result = {
                "status": "requires_approval",
                "message": "Action requires human review",
                "decision": decision
            }
        
        # Verify if executed
        verification_result = None
        if execution_result.get("status") == "executed":
            verification_result = await self.verifier.verify(execution_result, self.brand_id)
        
        # Learn
        if verification_result:
            await self.learner.record(
                opportunity, decision, execution_result, verification_result, self.brand_id
            )
        
        return {
            "opportunity": opportunity,
            "decision": decision,
            "safety": safety_result,
            "execution": execution_result,
            "verification": verification_result
        }

    async def _gather_evidence(self, opportunity: Dict) -> Dict:
        """Gather evidence for a decision (e.g., analytics, SEO data)."""
        # For now, fetch analytics and SEO issues as evidence
        try:
            analytics = await self.client.get_analytics(self.brand_id)
            seo_issues = await self.client.get_seo_issues(self.brand_id)
            leads = await self.client.get_pending_leads(self.brand_id)
            campaigns = await self.client.get_campaigns(self.brand_id)
            return {
                "analytics": analytics,
                "seo_issues": seo_issues,
                "leads": leads,
                "campaigns": campaigns
            }
        except Exception as e:
            logger.warning(f"Failed to gather some evidence: {e}")
            return {"error": str(e)}