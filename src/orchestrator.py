# src/orchestrator.py

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from .tools.monitor import monitor_opportunities
from .specialists import SeoSpecialist, LeadSpecialist, ContentSpecialist
from .policies.safety import SafetyPolicy
from .executor import Executor
from .verifier import Verifier
from .learner import Learner
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

class Orchestrator:
    """Central orchestrator for the autonomous agent system."""

    def __init__(self, brand_id: int):
        self.brand_id = brand_id
        self.client = LaravelApiClient()
        
        # Specialists
        self.specialists = {
            "seo_issue": SeoSpecialist(),
            "leads_pending": LeadSpecialist(),
            "content_generation": ContentSpecialist(),
        }
        
        # Core components
        self.safety = SafetyPolicy()
        self.executor = Executor()
        self.verifier = Verifier()
        self.learner = Learner()
        
        # Runtime state
        self.context = {}          # Working memory
        self.last_run = None

    async def run_cycle(self) -> Dict[str, Any]:
        """Execute a complete agent cycle: monitor → delegate → execute → verify → learn."""
        logger.info(f"🔄 Starting agent cycle for brand {self.brand_id}")
        start_time = datetime.now()

        try:
            # 1. Monitor - get opportunities from Laravel
            opportunities = await self._monitor()
            if not opportunities:
                logger.info("No opportunities found, skipping cycle.")
                return {"status": "idle", "message": "No opportunities found"}

            # 2. Process each opportunity sequentially
            results = []
            for opp in opportunities:
                result = await self._process_opportunity(opp)
                results.append(result)

            # 3. Update runtime state
            self.last_run = datetime.now()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Cycle completed in {elapsed:.2f}s")
            
            return {
                "status": "completed",
                "opportunities_processed": len(results),
                "results": results,
                "elapsed_seconds": elapsed
            }

        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _monitor(self) -> List[Dict]:
        """Fetch opportunities from Laravel."""
        try:
            result = await monitor_opportunities(self.brand_id)
            # monitor_opportunities returns a JSON string; parse it
            import json
            data = json.loads(result) if isinstance(result, str) else result
            return data.get("opportunities", [])
        except Exception as e:
            logger.error(f"Monitor failed: {e}")
            return []

    async def _process_opportunity(self, opportunity: Dict) -> Dict:
        """Process a single opportunity through the pipeline."""
        opp_type = opportunity.get("type")
        logger.info(f"🎯 Processing {opp_type} opportunity: {opportunity.get('title', 'Untitled')}")

        # 1. Get the appropriate specialist
        specialist = self.specialists.get(opp_type)
        if not specialist:
            logger.warning(f"No specialist for {opp_type}, skipping.")
            return {"success": False, "message": f"No specialist for {opp_type}"}

        # 2. Gather evidence (analytics, SEO, etc.)
        evidence = await self._gather_evidence(opportunity)

        # 3. Get AI reasoning from specialist
        decision = await specialist.reason(opportunity, evidence, self.context)

        # 4. Apply safety policy
        safety_result = self.safety.evaluate({
            "action_name": decision.get("action", {}).get("name", "unknown"),
            "brand_id": self.brand_id,
            "confidence": decision.get("confidence", 0.0),
            "estimated_impact": decision.get("estimated_impact", 0)
        })

        # 5. Execute or request approval
        if safety_result.get("autonomous", False):
            execution_result = await self.executor.execute(
                decision.get("action"),
                self.brand_id
            )
        else:
            # Queue for human approval
            await self.client.create_pending_action(
                self.brand_id,
                decision.get("action"),
                safety_result.get("reason", "Requires approval")
            )
            execution_result = {
                "status": "requires_approval",
                "message": "Action requires human review",
                "decision": decision
            }

        # 6. Verify if executed
        verification_result = None
        if execution_result.get("status") == "executed":
            verification_result = await self.verifier.verify(
                execution_result,
                self.brand_id
            )
            # If verification failed, rollback
            if verification_result and not verification_result.get("was_successful", True):
                await self.executor.rollback(execution_result, self.brand_id)

        # 7. Learn from outcome
        if verification_result:
            await self.learner.record(
                opportunity,
                decision,
                execution_result,
                verification_result,
                self.brand_id
            )

        return {
            "opportunity": opportunity,
            "decision": decision,
            "safety": safety_result,
            "execution": execution_result,
            "verification": verification_result
        }

    async def _gather_evidence(self, opportunity: Dict) -> Dict:
        """Gather evidence from Laravel for a decision."""
        brand_id = self.brand_id
        try:
            analytics = self.client.get_analytics(brand_id)
            seo_issues = self.client.get_seo_issues(brand_id)
            leads = self.client.get_pending_leads(brand_id)
            campaigns = self.client.get_campaigns(brand_id)
            
            return {
                "analytics": analytics,
                "seo_issues": seo_issues,
                "leads": leads,
                "campaigns": campaigns
            }
        except Exception as e:
            logger.warning(f"Failed to gather some evidence: {e}")
            return {}