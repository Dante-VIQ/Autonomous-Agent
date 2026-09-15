# src/utils/fingerprints.py

import hashlib
from datetime import date
from typing import Dict, Any


def stable_key(opportunity: Dict[str, Any], brand_id: int) -> str:
    """
    A stable identifier for the underlying business problem.
    Same problem = same stable_key, regardless of the day it appears.
    """
    opp_type = opportunity.get("type", "unknown")
    payload = opportunity.get("payload", {}) or {}

    if opp_type == "seo_issue":
        parts = [
            str(payload.get("page", "")),
            str(payload.get("issue_type", "")),
        ]
    elif opp_type == "content_generation":
        parts = [str(payload.get("topic", ""))]
    elif opp_type == "leads_pending":
        parts = [str(payload.get("lead_id", ""))]
    elif opp_type == "analytics_alert":
        parts = [str(opportunity.get("title", "alert"))]
    else:
        parts = [str(sorted(payload.items()))]

    raw = f"{brand_id}:{opp_type}:" + ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def fingerprint(opportunity: Dict[str, Any], brand_id: int, day: str = None) -> str:
    """
    Day-scoped fingerprint.
    Same problem on different days = different fingerprints.
    """
    if day is None:
        day = date.today().isoformat()

    sk = stable_key(opportunity, brand_id)
    raw = f"{sk}:{day}"
    return hashlib.sha256(raw.encode()).hexdigest()