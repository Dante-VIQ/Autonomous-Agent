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
        logger.info("━" * 50)
        logger.info(f"🔄 AGENT CYCLE — Brand {self.brand_id}")
        logger.info("━" * 50)

        try:
            # 0. DATA FRESHNESS CHECK
            logger.info("🗣  Checking if today's data is fresh...")
            try:
                status = await self.client.check_data_status(self.brand_id)
                if not status.get("all_fresh", False):
                    logger.info(f"   ⏳ Data is stale: {status.get('freshness', {})}")
                    refresh = await self.client.refresh_data(self.brand_id)
                    logger.info(f"   ✅ Laravel queued: {refresh.get('queued', [])}")
                else:
                    logger.info("   ✅ All data is already fresh!")
            except Exception as e:
                logger.warning(f"   ⚠  Freshness check failed (continuing): {e}")

            # 1. PROCESS HUMAN OUTCOMES (NEW)
            logger.info("📬 PROCESSING HUMAN OUTCOMES")
            outcomes_processed = await self._process_outcomes()

            # 2. DISCOVERY
            logger.info("📡 DISCOVERY")
            opportunities = await self._monitor()
            if not opportunities:
                logger.info("No opportunities found, skipping cycle.")
                return {
                    "status": "idle",
                    "message": "No opportunities found",
                    "outcomes_processed": outcomes_processed,
                }

            # 3. IDEMPOTENCY CHECK
            logger.info("🔑 IDEMPOTENCY CHECK")
            filtered, check_result = await self._filter_new_opportunities(opportunities)
            already = len(check_result.get("already_processed_today", []))
            logger.info(f"   ✅ {len(filtered)} to process, {already} already processed today")

            if not filtered:
                logger.info("   ✅ Nothing new to process.")
                return {
                    "status": "idle",
                    "message": "All opportunities already processed",
                    "outcomes_processed": outcomes_processed,
                }

            # 4. EVIDENCE
            logger.info("📊 EVIDENCE")
            evidence = await self._gather_evidence_snapshot()
            logger.info(f"   ✅ Evidence snapshot cached ({len(evidence)} items)")

            # 5. PROCESS OPPORTUNITIES
            logger.info(f"⚙️ PROCESSING {len(filtered)} OPPORTUNITIES")
            results = []
            for i, (opp, fp_info) in enumerate(filtered):
                title = opp.get("title", "Untitled")
                logger.info(f"   → Opportunity #{i+1}: {opp.get('type')} - {title}")
                result = await self._process_one_with_tracking(opp, evidence, fp_info)
                results.append(result)

            logger.info("━" * 50)
            logger.info("✅ CYCLE COMPLETE")
            logger.info(f"   Processed: {len(results)} opportunities")
            logger.info(f"   Outcomes handled: {outcomes_processed}")
            logger.info("━" * 50)

            return {
                "status": "completed",
                "opportunities_processed": len(results),
                "outcomes_processed": outcomes_processed,
                "results": results,
            }

        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def _process_outcomes(self) -> int:
        """Process human decisions on actions the agent created."""
        try:
            response = await self.client.get_pending_outcomes(self.brand_id)
        except Exception as e:
            logger.warning(f"Failed to fetch outcomes: {e}")
            return 0

        outcomes = response.get("outcomes", [])
        if not outcomes:
            logger.info("   ✅ No pending outcomes")
            return 0

        logger.info(f"   📬 {len(outcomes)} outcomes to process")
        handled_ids = []

        for outcome in outcomes:
            action_id = outcome.get("action_id")
            status = outcome.get("status")
            try:
                await self._handle_outcome(outcome)
                handled_ids.append(action_id)
            except Exception as e:
                logger.error(f"   ❌ Failed to handle outcome {action_id}: {e}")

        if handled_ids:
            try:
                await self.client.acknowledge_outcomes(self.brand_id, handled_ids)
                logger.info(f"   ✅ Acknowledged {len(handled_ids)} outcomes")
            except Exception as e:
                logger.warning(f"   ⚠  Failed to acknowledge outcomes: {e}")

        return len(handled_ids)

    async def _handle_outcome(self, outcome: dict):
        """Handle a single human decision."""
        action_id = outcome.get("action_id")
        status = outcome.get("status")
        retry_status = outcome.get("retry_status", "none")

        if status == "approved":
            # Approval is recorded, but execution happens in the next cycle
            # via the human's explicit "authorize_retry" or a scheduled executor
            logger.info(f"   ✅ Action {action_id} approved — will be picked up by executor")

        elif status == "rejected":
            reason = outcome.get("rejection_reason", "unknown")
            notes = outcome.get("review_notes", "")
            logger.info(f"   🚫 Action {action_id} rejected: {reason}")

            # Record the rejection for learning
            await self.learner.record_rejection(
                action_id=action_id,
                reason=reason,
                brand_id=self.brand_id,
                notes=notes,
            )

            # If human authorized a retry, log it (will show as an opportunity on next cycle)
            if retry_status == "authorized":
                logger.info(
                    f"   🔄 Retry authorized for {action_id}. "
                    f"Approach: {outcome.get('expected_retry_approach', 'none')}"
                )
            elif retry_status == "held":
                logger.info(f"   ⏸  Retry held for {action_id}. Waiting for human to release.")

        elif status == "revision":
            notes = outcome.get("review_notes", "")
            logger.info(f"   🔄 Action {action_id} needs revision: {notes}")
            # Future: trigger content regeneration with feedback

        else:
            logger.debug(f"   Skipping unknown status: {status}")
    async def _filter_new_opportunities(self, opportunities: list):
        """Compute fingerprints, ask Laravel which are new, return filtered list."""
        from .utils.fingerprints import fingerprint, stable_key

        enriched = []
        for opp in opportunities:
            fp = fingerprint(opp, self.brand_id)
            sk = stable_key(opp, self.brand_id)
            enriched.append({
                "fingerprint": fp,
                "stable_key": sk,
                "type": opp.get("type", "unknown"),
                "_original": opp,
            })

        response = await self.client.check_opportunities(self.brand_id, enriched)

        new_fps = {item["fingerprint"] for item in response.get("new", [])}
        recurring_fps = {
            item["fingerprint"]: item
            for item in response.get("recurring", [])
        }

        filtered = []
        for item in enriched:
            fp = item["fingerprint"]
            if fp in new_fps:
                filtered.append((item["_original"], {**item, "is_recurring": False}))
            elif fp in recurring_fps:
                merged = {**item, "is_recurring": True}
                merged.update(recurring_fps[fp])
                filtered.append((item["_original"], merged))

        return filtered, response

    async def _process_one_with_tracking(self, opportunity, evidence, fp_info):
        """Process a single opportunity and mark it in Laravel."""
        fingerprint_val = fp_info["fingerprint"]
        stable_key_val = fp_info["stable_key"]
        opp_type = opportunity.get("type", "unknown")

        # Mark as processing
        try:
            await self.client.mark_opportunity(
                brand_id=self.brand_id,
                fingerprint=fingerprint_val,
                stable_key=stable_key_val,
                opportunity_type=opp_type,
                status="processing",
                opportunity_data=opportunity,
            )
        except Exception as e:
            logger.warning(f"Failed to mark opportunity as processing: {e}")

        try:
            # Pass recurrence info to specialists
            self.context["recurrence"] = fp_info

            result = await self._process_opportunity(opportunity, evidence)

            # Extract action_id if present
            action_id = None
            result_data = (result.get("execution", {}) or {}).get("result", {}) or {}
            if isinstance(result_data, dict):
                action_id = result_data.get("action_id")

            # Mark as processed
            try:
                await self.client.mark_opportunity(
                    brand_id=self.brand_id,
                    fingerprint=fingerprint_val,
                    stable_key=stable_key_val,
                    opportunity_type=opp_type,
                    status="processed",
                    opportunity_data=opportunity,
                    action_id=action_id,
                )
            except Exception as e:
                logger.warning(f"Failed to mark opportunity as processed: {e}")

            return result

        except Exception as e:
            logger.error(f"Failed to process opportunity: {e}", exc_info=True)
            try:
                await self.client.mark_opportunity(
                    brand_id=self.brand_id,
                    fingerprint=fingerprint_val,
                    stable_key=stable_key_val,
                    opportunity_type=opp_type,
                    status="failed",
                    opportunity_data=opportunity,
                )
            except Exception as mark_err:
                logger.warning(f"Failed to mark opportunity as failed: {mark_err}")

            return {"success": False, "error": str(e)}
            
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