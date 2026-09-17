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
        """Immediate verification after action execution."""
        action = execution_result.get("action", {}) or {}
        action_name = action.get("name", "unknown")
        action_id = execution_result.get("action_id")

        if not action_id:
            logger.warning("No action_id in execution result — skipping verification")
            return {"success": False, "reason": "no action_id"}

        # Register verification schedule in Laravel
        try:
            schedule = await self.client.register_verification(
                brand_id=brand_id,
                action_id=action_id,
                action_name=action_name,
                metrics=execution_result.get("before_metrics"),
            )
            logger.info(f"📅 Verification scheduled for action {action_id}")
            return {"success": True, "schedule": schedule}
        except Exception as e:
            logger.warning(f"Failed to register verification: {e}")
            return {"success": False, "reason": str(e)}

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
            metrics_after = await self._fetch_current_metrics(brand_id, item)
        except Exception as e:
            logger.warning(f"Failed to fetch metrics for action {action_id}: {e}")
            return False

        deltas = self._compute_deltas(metrics_before, metrics_after)
        improvement = self._score_improvement(deltas)
        was_successful = improvement >= 0.05  # 5% threshold

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
            )
            logger.info(
                f"✅ Verified action {action_id} ({phase}): "
                f"{'success' if was_successful else 'failure'} (score: {improvement:.2%})"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to record verification: {e}")
            return False

    async def _fetch_current_metrics(self, brand_id: int, item: dict) -> Dict:
        """Fetch metrics appropriate for the action type."""
        try:
            analytics = await self.client.get_analytics(brand_id)
            return {
                "impressions": analytics.get("pageViews", 0),
                "clicks": analytics.get("visitors", 0),
                "conversion_rate": analytics.get("conversions", 0),
                "spend": analytics.get("revenue", 0),
                "roi": analytics.get("revenue", 0),
                "indexed_pages": analytics.get("pageViews", 0),
                "ranking_position": 0,
                "reply_rate": 0,
                "engagement": analytics.get("visitors", 0),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch metrics: {e}")
            return {}

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