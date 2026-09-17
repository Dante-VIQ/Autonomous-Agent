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
from .services.calibration import CalibrationService

ESCALATION_THRESHOLD = 5
CRITICAL_ESCALATION_THRESHOLD = 2

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
        self.learner = Learner()

        # ✅ These three lines must be present
        self.client = LaravelApiClient()
        self.memory = ExperienceMemory()
        self.verifier = Verifier(self.client)
        self.calibration = CalibrationService(self.client, brand_id)
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

                # 0.5. FETCH DAILY BRIEF
            logger.info("📋 FETCHING DAILY BRIEF")
            try:
                brief_response = await self.client.get_brief(self.brand_id)
                if brief_response.get("success"):
                    brief = brief_response.get("brief", {})
                    self.context["brief"] = brief
                    diagnosis = brief.get("strategic_diagnosis", "")[:120]
                    impact = brief.get("estimated_revenue_impact", 0)
                    logger.info(f"   📌 {diagnosis}...")
                    logger.info(f"   💰 Est. impact: ${impact}")
                else:
                    logger.info(f"   ℹ️  No brief available yet")
                    self.context["brief"] = {}
            except Exception as e:
                logger.warning(f"   ⚠  Brief fetch failed: {e}")
                self.context["brief"] = {}
                
                # 0.6. FETCH TOURS
                logger.info("🎫 FETCHING TOURS")
                tours_response = await self.client.get_tours(self.brand_id)
                tours = tours_response.get("tours", [])
                self.context["tours"] = tours
                logger.info(f"   ✅ {len(tours)} tours available")
            
            # 1. PROCESS HUMAN OUTCOMES
            logger.info("📬 PROCESSING HUMAN OUTCOMES")
            try:
                outcomes_processed = await self._process_outcomes()
            except Exception as e:
                logger.warning(f"   ⚠  Outcomes processing failed: {e}")
                outcomes_processed = 0

            # 1.5. RUN DUE VERIFICATIONS (Phase 6)
            logger.info("🔍 CHECKING VERIFICATIONS")
            try:
                due_results = await self.verifier.run_due_verifications(self.brand_id)
                if due_results.get("hour_1") or due_results.get("day_1"):
                    logger.info(
                        f"   ✅ Ran {due_results.get('hour_1', 0)} hour-1, "
                        f"{due_results.get('day_1', 0)} day-1 verifications"
                    )
                else:
                    logger.info("   ✅ No verifications due")
            except Exception as e:
                logger.warning(f"   ⚠  Verification run failed: {e}")

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
                # Handle escalation responses FIRST
                if outcome.get("human_response"):
                    await self._handle_escalation_response(outcome)
                    handled_ids.append(action_id)
                    continue

                # Otherwise, handle by status
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
        """Process a single opportunity with recurrence awareness."""
        fingerprint_val = fp_info["fingerprint"]
        stable_key_val = fp_info["stable_key"]
        opp_type = opportunity.get("type", "unknown")
        recurrence = fp_info.get("recurrence_count", 1)

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
            # --- ESCALATION CHECK ---
            if self._should_escalate(fp_info, opportunity):
                logger.warning(
                    f"   🚨 Escalating: {opp_type} recurrence #{recurrence}"
                )
                result = await self._escalate_opportunity(
                    opportunity, fp_info, stable_key_val
                )
                status_to_mark = "escalated"
            else:
                # --- NORMAL PROCESSING (with pattern context if recurring) ---
                if recurrence > 1:
                    logger.info(f"   🔁 Recurrence #{recurrence} — fetching history")
                    history = await self._fetch_history(stable_key_val)
                    self.context["recurrence_history"] = history
                    self.context["recurrence"] = fp_info

                result = await self._process_opportunity(opportunity, evidence)
                status_to_mark = "processed"

            # Extract action_id if present
            action_id = None
            result_data = (result.get("execution", {}) or {}).get("result", {}) or {}
            if isinstance(result_data, dict):
                action_id = result_data.get("action_id")

            # Mark as processed/escalated
            try:
                await self.client.mark_opportunity(
                    brand_id=self.brand_id,
                    fingerprint=fingerprint_val,
                    stable_key=stable_key_val,
                    opportunity_type=opp_type,
                    status=status_to_mark,
                    opportunity_data=opportunity,
                    action_id=action_id,
                )
            except Exception as e:
                logger.warning(f"Failed to mark opportunity as {status_to_mark}: {e}")

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

    async def _escalate_opportunity(self, opportunity, fp_info, stable_key: str):
        """Create an escalation action for a human."""
        history = await self._fetch_history(stable_key)
        summary = history.get("summary", {})
        attempts = history.get("attempts", [])

        recurrence = fp_info.get("recurrence_count", 1)
        title = opportunity.get("title", "Unknown recurring issue")

        # Build description
        first_seen = summary.get("first_seen", "unknown")
        total = summary.get("total_attempts", recurrence)
        successful = summary.get("successful", 0)
        failed = summary.get("failed", 0)
        rejection_reasons = summary.get("rejection_reasons", [])

        description = (
            f"This issue has occurred {total} times since {first_seen}. "
            f"Previous attempts: {successful} successful, {failed} failed. "
        )
        if rejection_reasons:
            description += f"Human rejection reasons: {', '.join(rejection_reasons)}. "
        description += (
            "The agent has exhausted its standard approaches. "
            "Human investigation needed to identify the root cause."
        )

        # Priority based on recurrence
        priority = min(5, max(3, recurrence // 2))

        payload = {
            "stable_key": stable_key,
            "recurrence_count": total,
            "first_seen": first_seen,
            "prior_attempts": attempts[-5:],  # last 5 attempts
            "rejection_reasons": rejection_reasons,
            "expected_decision": "investigate_root_cause",
        }

        # Send to Laravel
        try:
            result = await self.client.create_pending_action(
                self.brand_id,
                {
                    "name": "escalate_recurring_issue",
                    "target": stable_key,
                    "payload": payload,
                    "title": f"🚨 Recurring: {title} (×{total})",
                    "category": "escalation",
                    "description": description,
                    "priority": priority,
                },
                "Autonomous execution — recurring issue",
            )

            logger.info(
                f"   ✅ Escalation created for {stable_key} (recurrence #{total})"
            )

            return {
                "success": True,
                "escalated": True,
                "stable_key": stable_key,
                "recurrence_count": total,
                "result": result,
            }
        except Exception as e:
            logger.error(f"   ❌ Failed to escalate: {e}")
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

        # ✅ ADD THIS LINE
        verification_result = None
        
        # Reason (specialist.reason is async). This already calls
        # self.memory.analyze_patterns() internally.
        decision = await specialist.reason(opportunity, evidence, self.context)

        # ✅ NEW: Calibrate confidence against measured accuracy
        stated = decision.get("confidence", 0.5)
        opp_type = opportunity.get("type", "unknown")
        action_name = decision.get("action", {}).get("name")

        adjusted_confidence, calibration_note = await self.calibration.adjust(
            stated_confidence=stated,
            opportunity_type=opp_type,
            action_name=action_name,
        )

        if adjusted_confidence != stated:
            logger.info(
                f"   📊 Confidence: {stated:.2f} → {adjusted_confidence:.2f} ({calibration_note})"
            )

        decision["stated_confidence"] = stated
        decision["confidence"] = adjusted_confidence
        decision["calibration_note"] = calibration_note

                # ✅ Record calibration data
        if verification_result and decision.get("stated_confidence") is not None:
            try:
                await self.client.record_calibration(
                    brand_id=self.brand_id,
                    stated_confidence=decision["stated_confidence"],
                    opportunity_type=opp_type,
                    action_name=action_name,
                    was_successful=verification_result.get("was_successful", False),
                )
            except Exception as e:
                logger.warning(f"Failed to record calibration: {e}")

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

        # Register multi-phase verification
        if execution_result.get("status") == "executed":
            verification_result = await self.verifier.verify_immediate(
                execution_result, self.brand_id
            )

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

    def _should_escalate(self, fp_info: dict, opportunity: dict) -> bool:
        """Decide if this recurrence should escalate to human."""
        recurrence = fp_info.get("recurrence_count", 1)
        severity = (opportunity.get("severity") or "medium").lower()

        if severity == "critical" and recurrence >= CRITICAL_ESCALATION_THRESHOLD:
            return True
        return recurrence >= ESCALATION_THRESHOLD

    async def _fetch_history(self, stable_key: str) -> dict:
        """Fetch prior attempts + any human escalation response."""
        try:
            history = await self.client.get_opportunity_history(self.brand_id, stable_key)

            # Fetch any escalation response for this stable_key
            try:
                esc_resp = await self.client._request(
                    "GET", f"/agent/escalations/{self.brand_id}"
                )
                # (Skip for now — future improvement)
            except Exception:
                pass

            return history
        except Exception as e:
            logger.warning(f"Failed to fetch history for {stable_key}: {e}")
            return {"attempts": [], "summary": {"total_attempts": 0}}

    async def _handle_escalation_response(self, outcome: dict):
        """Human responded to an escalation — act on it."""
        action_id = outcome.get("action_id")
        response = outcome.get("human_response")
        notes = outcome.get("human_response_notes") or ""
        stable_key = outcome.get("opportunity_stable_key")

        logger.info(f"   📬 Escalation {action_id} → {response}")

        if response == "resolve":
            # Mark all tracking rows for this stable_key as resolved
            logger.info(f"   ✅ Human resolved {stable_key}. No further retries.")
            # (Optional: emit a Laravel call to mark tracking as resolved)

        elif response == "snooze":
            logger.info(f"   ⏸  Snoozed until {outcome.get('snooze_until')}")

        elif response == "retry":
            logger.info(f"   🔄 Human wants retry for {stable_key}. Guidance: {notes}")
            # The next cycle's opportunity will include this guidance via
            # the recurrence history and the human_response_notes field

        elif response == "investigate":
            logger.info(f"   🔍 Human wants deeper investigation for {stable_key}")
            # Future: agent runs additional diagnostics