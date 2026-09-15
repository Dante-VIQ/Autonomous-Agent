# src/orchestrator.py

import asyncio
import json
import logging
from typing import Dict, Any, List

from .tools.monitor import monitor_opportunities
from .specialists import SeoSpecialist, LeadSpecialist, ContentSpecialist, AnalyticsSpecialist
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
            "analytics_alert": AnalyticsSpecialist(),
        }
        self.safety = SafetyPolicy()
        self.executor = Executor()
        self.verifier = Verifier()
        self.learner = Learner()
        self.client = LaravelApiClient()
        self.memory = ExperienceMemory()
        self._evidence_cache = None

    async def run_cycle(self) -> Dict[str, Any]:
        """Run a full agent cycle: freshness → discovery → evidence → process."""
        logger.info("━" * 50)
        logger.info(f"🔄 AGENT CYCLE — Brand {self.brand_id}")
        logger.info("━" * 50)

        try:
            # 0. DATA FRESHNESS CHECK (conversational!)
            logger.info("🗣️  Checking if today's data is fresh...")
            try:
                status = await self.client.check_data_status(self.brand_id)

                if not status.get("all_fresh", False):
                    logger.info(f"   ⏳ Data is stale: {status.get('freshness', {})}")
                    logger.info("   📥 Asking Laravel to collect fresh data...")
                    refresh = await self.client.refresh_data(self.brand_id)
                    logger.info(f"   ✅ Laravel queued: {refresh.get('queued', [])}")
                    if refresh.get('errors'):
                        logger.warning(f"   ⚠️  Collection errors: {refresh['errors']}")
                else:
                    logger.info("   ✅ All data is already fresh!")
            except Exception as e:
                logger.warning(f"   ⚠️  Freshness check failed (continuing): {e}")

            # 1. DISCOVERY
            logger.info("📡 DISCOVERY")
            opportunities = await self._monitor()
            if not opportunities:
                logger.info("No opportunities found, skipping cycle.")
                return {"status": "idle", "message": "No opportunities found"}

            # 2. EVIDENCE (cached once per cycle)
            logger.info("📊 EVIDENCE")
            evidence = await self._gather_evidence_snapshot()
            self._evidence_cache = evidence
            logger.info(f"   ✅ Evidence snapshot cached ({len(evidence)} items)")

            # 3. PROCESS OPPORTUNITIES
            logger.info(f"⚙️ PROCESSING {len(opportunities)} OPPORTUNITIES")
            results = []
            for i, opp in enumerate(opportunities):
                logger.info(f"   → Opportunity #{i+1}: {opp.get('type')} - {opp.get('title', 'Untitled')}")
                result = await self._process_opportunity(opp, evidence)
                results.append(result)

            logger.info("━" * 50)
            logger.info("✅ CYCLE COMPLETE")
            logger.info(f"   Processed: {len(results)} opportunities")
            logger.info("━" * 50)

            return {
                "status": "completed",
                "opportunities_processed": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def _gather_evidence_snapshot(self) -> Dict:
        """Gather all evidence once per cycle."""
        try:
            analytics, seo_issues, leads, campaigns = await asyncio.gather(
                self.client.get_analytics(self.brand_id),
                self.client.get_seo_issues(self.brand_id),
                self.client.get_pending_leads(self.brand_id),
                self.client.get_campaigns(self.brand_id),
                return_exceptions=True,
            )

            evidence = {
                "analytics": analytics if not isinstance(analytics, Exception) else {},
                "seo_issues": seo_issues if not isinstance(seo_issues, Exception) else [],
                "leads": leads if not isinstance(leads, Exception) else [],
                "campaigns": campaigns if not isinstance(campaigns, Exception) else [],
            }

            logger.info(f"   ✅ Analytics: {len(evidence['analytics']) if evidence['analytics'] else 0}")
            logger.info(f"   ✅ SEO issues: {len(evidence['seo_issues'])}")
            logger.info(f"   ✅ Leads: {len(evidence['leads'])}")
            logger.info(f"   ✅ Campaigns: {len(evidence['campaigns'])}")

            return evidence
        except Exception as e:
            logger.error(f"Failed to gather evidence snapshot: {e}")
            return {}

    async def _process_opportunity(self, opportunity: Dict, evidence: Dict) -> Dict:
        """Process a single opportunity through the pipeline."""
        opp_type = opportunity.get("type")
        specialist = self.specialists.get(opp_type)
        if not specialist:
            logger.warning(f"⏭️ No specialist for opportunity type '{opp_type}', skipping")
            return {"success": False, "message": f"No specialist for {opp_type}"}

        # Reason (specialist.reason is async). This already calls
        # self.memory.analyze_patterns() internally.
        decision = await specialist.reason(opportunity, evidence, self.context)

        # Safety policy
        safety_result = self.safety.evaluate({
            "action_name": decision.get("action", {}).get("name", "unknown"),
            "brand_id": self.brand_id,
            "confidence": decision.get("confidence", 0.0),
            "estimated_impact": decision.get("estimated_impact", 0),
        })

        # Execute or approve
        if safety_result.get("autonomous", False):
            execution_result = await self.executor.execute(decision, self.brand_id)
        else:
            execution_result = {
                "status": "requires_approval",
                "message": "Action requires human review",
                "decision": decision,
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
            "verification": verification_result,
        }

    async def _monitor(self) -> List[Dict]:
        """Monitor for opportunities."""
        result_str = await monitor_opportunities(self.brand_id)
        try:
            data = json.loads(result_str)
            opportunities = data.get("opportunities", [])
            logger.info(f"   ✅ Found {len(opportunities)} opportunities")
            return opportunities
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse monitor response: {e}")
            return []