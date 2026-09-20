# src/verifier.py

import asyncio
import logging
from typing import Dict, Any, List, Optional
from .utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)


class Verifier:
    """Multi-phase action verification with rollback support."""

    def __init__(self, api_client: LaravelApiClient = None):
        self.client = api_client or LaravelApiClient()

    async def verify_immediate(self, execution_result: Dict, brand_id: int) -> Dict:
        """
        Immediate verification: register the multi-phase schedule and snapshot
        metrics at execution time. This does NOT decide success — that happens
        at hour_1 and day_1. So was_successful is None here, not False.
        """
        action = execution_result.get("action", {}) or {}
        action_name = action.get("name", "unknown")
        action_id = execution_result.get("action_id")

        if not action_id:
            logger.warning("No action_id in execution result — skipping verification")
            return {
                "success": False,
                "was_successful": None,
                "reason": "no action_id",
                "improvement_score": 0.0,
            }

        # Snapshot current metrics — this is what hour_1/day_1 will compare against
        try:
            resp = await self.client.get_action_metrics(brand_id, action_id)
            before_metrics = resp.get("metrics", {})
        except Exception as e:
            logger.warning(f"Could not snapshot metrics for {action_id}: {e}")
            before_metrics = {}

        try:
            schedule = await self.client.register_verification(
                brand_id=brand_id,
                action_id=action_id,
                action_name=action_name,
                metrics=before_metrics,
            )
            logger.info(f"📅 Verification scheduled for action {action_id}")
            return {
                "success": True,
                "was_successful": None,   # unknown until hour_1/day_1
                "scheduled": True,
                "action_id": action_id,
                "action_name": action_name,
                "schedule": schedule,
                "before_metrics": before_metrics,
                "improvement_score": 0.0,
            }
        except Exception as e:
            logger.warning(f"Failed to register verification: {e}")
            return {
                "success": False,
                "was_successful": None,
                "reason": str(e),
                "improvement_score": 0.0,
            }
            
    async def run_due_verifications(self, brand_id: int) -> Dict:
        """Check for and run any due hour_1/day_1 verifications."""
        try:
            due = await self.client.get_due_verifications(brand_id)
        except Exception as e:
            logger.warning(f"Failed to fetch due verifications: {e}")
            return {"hour_1": 0, "day_1": 0}

        hour_1_count = 0
        day_1_count = 0

        # Hour 1
        for item in due.get("hour_1", []):
            if await self._verify_phase(item, "hour_1", brand_id):
                hour_1_count += 1

        # Day 1
        for item in due.get("day_1", []):
            if await self._verify_phase(item, "day_1", brand_id):
                day_1_count += 1

                # Auto-rollback if day_1 failed
                if self._should_rollback(item):
                    await self._trigger_rollback(item, brand_id)

        return {"hour_1": hour_1_count, "day_1": day_1_count}

    async def _verify_phase(self, item: dict, phase: str, brand_id: int) -> bool:
        action_id = item.get("action_id")
        metrics_before = item.get("metrics_before") or {}
        action_name = item.get("action_name", "unknown")

        try:
            resp = await self.client.get_action_metrics(brand_id, action_id)
        except Exception as e:
            logger.warning(f"Failed to fetch metrics for action {action_id}: {e}")
            return False

        metrics_after = resp.get("metrics", {})
        attribution = resp.get("attribution", "unknown")

        deltas = self._compute_deltas(metrics_before, metrics_after)
        improvement = self._score_improvement(deltas)

        # Honest success logic:
        #  - If human did the fix (attribution=human): inconclusive, don't credit agent
        #  - If mixed: also inconclusive
        #  - Only agent or unknown proceeds to success test
        if attribution in ("human", "mixed"):
            was_successful = None
            logger.info(
                f"⚠️  Action {action_id} ({phase}): attribution={attribution}, "
                f"marking inconclusive"
            )
        else:
            was_successful = improvement >= 0.05

        try:
            await self.client.record_verification(
                brand_id=brand_id,
                action_id=action_id,
                phase=phase,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                metric_deltas=deltas,
                was_successful=was_successful,
                improvement_score=improvement,
                attribution=attribution,
            )
            logger.info(
                f"✅ Verified action {action_id} ({phase}): "
                f"{'inconclusive' if was_successful is None else ('success' if was_successful else 'failure')} "
                f"(score: {improvement:.2%}, attribution: {attribution})"
            )

            # Patch 12: record learning after verification
            try:
                await self.client.record_learning(brand_id, {
                    "action_name": action_name,
                    "opportunity_type": item.get("opportunity_type", "unknown"),
                    "severity": "medium",
                    "confidence": item.get("stated_confidence", 0.5),
                    "was_autonomous": True,
                    "was_successful": bool(was_successful) if was_successful is not None else False,
                    "improvement_percentage": improvement * 100,
                    "duration_seconds": 0,
                    "context": {
                        "phase": phase,
                        "action_id": action_id,
                        "attribution": attribution,
                        "metrics_before": metrics_before,
                        "metrics_after": metrics_after,
                        "deltas": deltas,
                    },
                    "learning_type": (
                        "inconclusive" if was_successful is None
                        else "significant_success" if improvement > 0.15
                        else "moderate_success" if improvement > 0.05
                        else "marginal_success" if was_successful
                        else "failure"
                    ),
                })
            except Exception as e:
                logger.warning(f"Failed to record learning after {phase}: {e}")

            return True
        except Exception as e:
            logger.warning(f"Failed to record verification: {e}")
            return False
                     
    def _compute_deltas(self, before: Dict, after: Dict) -> Dict:
        deltas = {}
        for key in set(before.keys()) | set(after.keys()):
            b = before.get(key) or 0
            a = after.get(key) or 0
            try:
                if b == 0 and a == 0:
                    continue
                if b == 0:
                    deltas[key] = {"before": b, "after": a, "pct": None, "abs": a - b}
                else:
                    deltas[key] = {
                        "before": b,
                        "after": a,
                        "pct": (a - b) / b,
                        "abs": a - b,
                    }
            except Exception:
                continue
        return deltas

    def _score_improvement(self, deltas: Dict) -> float:
        scores = []
        for _, d in deltas.items():
            pct = d.get("pct")
            if pct is not None:
                scores.append(max(-1.0, min(1.0, pct)))
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def _should_rollback(self, item: dict) -> bool:
        """Roll back failed day_1 verifications if configured."""
        from .config import Config
        return getattr(Config, "AUTO_ROLLBACK", True)

    async def _trigger_rollback(self, item: dict, brand_id: int):
        action_id = item.get("action_id")
        action_name = item.get("action_name", "unknown")
        reason = f"Day-1 verification failed for {action_name}"

        try:
            await self.client.rollback_action(action_id, reason)
            logger.warning(f"🔄 Rollback triggered for action {action_id}: {reason}")
        except Exception as e:
            logger.error(f"Rollback failed for action {action_id}: {e}")