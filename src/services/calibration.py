# src/services/calibration.py

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CalibrationService:
    """Adjusts LLM confidence based on measured historical accuracy."""

    MIN_SAMPLES = 10          # Require this many samples before adjusting
    MAX_ADJUSTMENT = 0.30     # Never shift confidence more than this

    def __init__(self, api_client, brand_id: int):
        self.client = api_client
        self.brand_id = brand_id
        self._cache: Dict[str, dict] = {}

    async def adjust(
        self,
        stated_confidence: float,
        opportunity_type: str,
        action_name: Optional[str] = None,
    ) -> tuple[float, str]:
        """
        Returns (adjusted_confidence, reasoning).
        """
        try:
            data = await self._fetch_calibration(opportunity_type)
        except Exception as e:
            logger.warning(f"Calibration fetch failed: {e}")
            return stated_confidence, "no calibration data available"

        bucket = min(10, max(0, int(stated_confidence * 10)))

        # Find matching bucket
        matching = next(
            (b for b in data.get("buckets", []) if b["confidence_bucket"] == bucket),
            None,
        )

        if not matching:
            return stated_confidence, "no matching bucket"

        if not matching.get("sample_sufficient"):
            return stated_confidence, f"insufficient samples ({matching['total_predictions']})"

        actual = matching["actual_accuracy"]
        drift = actual - (bucket / 10)

        # Cap the adjustment
        adjustment = max(-self.MAX_ADJUSTMENT, min(self.MAX_ADJUSTMENT, drift))
        adjusted = max(0.0, min(1.0, stated_confidence + adjustment))

        reasoning = (
            f"stated={stated_confidence:.2f}, bucket={bucket/10:.1f}, "
            f"measured={actual:.2f}, drift={drift:+.2f}, "
            f"adjusted={adjusted:.2f}"
        )

        if abs(adjustment) >= 0.05:
            logger.info(f"📊 Calibration applied: {reasoning}")

        return adjusted, reasoning

    async def _fetch_calibration(self, opportunity_type: str) -> dict:
        if opportunity_type in self._cache:
            return self._cache[opportunity_type]

        data = await self.client.get_calibration(
            self.brand_id, opportunity_type=opportunity_type
        )
        self._cache[opportunity_type] = data
        return data