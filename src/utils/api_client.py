# src/utils/api_client.py

import asyncio
import httpx
import logging
from typing import Dict, Any, Optional, List
from ..config import Config

logger = logging.getLogger(__name__)


class LaravelApiClient:
    """Async API client for Vumbi Ventures Laravel backend."""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.api_key = (api_key or Config.LARAVEL_API_KEY).strip()
        self.base_url = (base_url or Config.LARAVEL_API_URL).rstrip('/')
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # 120s timeout for long-running content generation
        self.client = httpx.AsyncClient(headers=self.headers, timeout=120.0)

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make an async request with automatic 429 retry."""
        url = f"{self.base_url}{endpoint}"
        attempt = 0

        while attempt <= max_retries:
            try:
                response = await self.client.request(method, url, json=data)
                response.raise_for_status()
                if not response.text:
                    return {"success": True}
                return response.json()

            except httpx.HTTPStatusError as e:
                # 429 – rate limited: wait and retry
                if e.response.status_code == 429:
                    retry_after = int(
                        e.response.headers.get("Retry-After", 5)
                    )
                    attempt += 1

                    if attempt > max_retries:
                        logger.error(
                            f"🚫 Rate limited {max_retries} times on {endpoint}. Giving up."
                        )
                        raise

                    wait = min(retry_after, 30)  # cap at 30s
                    logger.warning(
                        f"⏳ Rate limited on {endpoint}. "
                        f"Retry {attempt}/{max_retries} in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                    continue

                # Other HTTP errors – log and re-raise
                logger.error(f"API request failed: {e}")
                if e.response is not None:
                    logger.error(f"Response body: {e.response.text}")
                raise

            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                # Network errors – retry once
                attempt += 1
                if attempt > max_retries:
                    raise
                logger.warning(f"⚠️  Network error on {endpoint}: {e}. Retrying...")
                await asyncio.sleep(2)
                continue

        # Should never reach here
        raise RuntimeError(f"Request to {endpoint} failed after {max_retries} retries.")

    async def close(self):
        await self.client.aclose()
    
        # ============ FRESHNESS / REFRESH ============

    async def check_data_status(self, brand_id: int) -> Dict:
        """Ask Laravel: is today's data fresh?"""
        return await self._request("GET", f"/agent/data-status/{brand_id}")

    async def refresh_data(self, brand_id: int) -> Dict:
        """Ask Laravel to collect fresh data."""
        return await self._request("POST", f"/agent/refresh-data/{brand_id}")

    # ============ OPPORTUNITY TRACKING ============

    async def check_opportunities(self, brand_id: int, opportunities: list) -> Dict:
        """Ask Laravel which fingerprints are new / recurring / already processed today."""
        return await self._request("POST", "/agent/opportunities/check", {
            "brand_id": brand_id,
            "opportunities": opportunities,
        })

    async def mark_opportunity(self, **data) -> Dict:
        """Mark an opportunity as processing / processed / failed."""
        return await self._request("POST", "/agent/opportunities/mark", data)
        
    # ============ All methods are async ============
    
    async def get_opportunities(self, brand_id: int) -> List[Dict]:
        """Fetch all opportunities for a brand."""
        result = await self._request("GET", f"/agent/opportunities/{brand_id}")
        return result.get("opportunities", [])

    # ============ ANALYTICS ============

    async def get_analytics(self, brand_id: int) -> Dict:
        return await self._request("GET", f"/agent/analytics/{brand_id}")

    # ============ HUMAN OUTCOMES ============

    async def get_pending_outcomes(self, brand_id: int) -> Dict:
        """Fetch human decisions on actions the agent hasn't seen yet."""
        return await self._request("GET", f"/agent/actions/outcomes/{brand_id}")

    async def acknowledge_outcomes(self, brand_id: int, action_ids: list) -> Dict:
        """Acknowledge to Laravel that the agent has processed these outcomes."""
        return await self._request("POST", "/agent/actions/acknowledge", {
            "brand_id": brand_id,
            "action_ids": action_ids,
        })

    async def authorize_retry(
        self,
        action_id: int,
        approach: str = None,
        hold: bool = False,
    ) -> Dict:
        """Authorize a retry for a rejected action."""
        return await self._request("POST", f"/agent/actions/{action_id}/authorize-retry", {
            "expected_retry_approach": approach,
            "hold": hold,
        })
        
    # ============ SEO ============

    async def get_seo_issues(self, brand_id: int) -> List[Dict]:
        result = await self._request("GET", f"/agent/seo/issues/{brand_id}")
        return result.get("issues", [])

    async def get_seo_issue(self, brand_id: int, issue_id: str) -> Dict:
        return await self._request("GET", f"/agent/seo/issue/{brand_id}/{issue_id}")

    async def analyze_seo_issue(self, brand_id: int, issue_id: str) -> Dict:
        return await self._request("POST", f"/agent/seo/analyze/{brand_id}/{issue_id}")

    async def get_seo_recommendations(self, brand_id: int, issue_id: str) -> Dict:
        return await self._request("GET", f"/agent/seo/recommendations/{brand_id}/{issue_id}")

    async def get_keyword_rankings(self, brand_id: int, page_url: str = None) -> Dict:
        endpoint = f"/agent/seo/rankings/{brand_id}"
        if page_url:
            endpoint += f"?url={page_url}"
        return await self._request("GET", endpoint)

    # ============ LEADS ============

    async def get_pending_leads(self, brand_id: int) -> List[Dict]:
        result = await self._request("GET", f"/agent/leads/pending/{brand_id}")
        return result.get("leads", [])

    async def get_lead(self, brand_id: int, lead_id: str) -> Dict:
        return await self._request("GET", f"/agent/lead/{brand_id}/{lead_id}")

    async def get_lead_engagement(self, brand_id: int, lead_id: str) -> Dict:
        return await self._request("GET", f"/agent/lead/engagement/{brand_id}/{lead_id}")

    async def get_lead_context(self, brand_id: int, lead_id: str) -> Dict:
        return await self._request("GET", f"/agent/lead/context/{brand_id}/{lead_id}")

    async def generate_follow_up(self, brand_id: int, lead_id: str) -> Dict:
        return await self._request("POST", f"/agent/lead/follow-up/{brand_id}", {"lead_id": lead_id})

    # ============ CAMPAIGNS ============

    async def get_campaigns(self, brand_id: int) -> List[Dict]:
        return await self._request("GET", f"/agent/campaigns/{brand_id}")

    async def pause_campaign(self, brand_id: int, campaign_id: str, reason: str = None) -> Dict:
        return await self._request("POST", "/agent/campaigns/pause", {
            "brandId": brand_id,
            "campaignId": campaign_id,
            "reason": reason,
        })

    # ============ CONTENT ============

    async def generate_content(self, brand_id: int, topic: str, template: str = "blog") -> Dict:
        return await self._request("POST", "/agent/content/generate", {
            "brandId": brand_id,
            "topic": topic,
            "template": template,
        })

    async def analyze_content_gap(self, brand_id: int, topic: str) -> Dict:
        return await self._request("POST", f"/agent/content/gap-analysis/{brand_id}", {"topic": topic})

    async def generate_outline(self, topic: str, template: str = "blog") -> Dict:
        return await self._request("POST", "/agent/content/outline", {
            "topic": topic,
            "template": template,
        })

    # ============ EXECUTION ============

    async def create_pending_action(self, brand_id: int, action: Dict, reason: str = None) -> Dict:
        return await self._request("POST", "/agent/actions/pending", {
            "brandId": brand_id,
            "action": action,
            "reason": reason,
        })

    async def scan(self, brand_id: int) -> Dict:
        return await self._request("POST", f"/agent/scan/{brand_id}")

    # ============ VERIFICATION ============

    async def start_verification(self, brand_id: int, action_name: str, **kwargs) -> Dict:
        data = {"brand_id": brand_id, "action_name": action_name, **kwargs}
        return await self._request("POST", f"/agent/verification/start/{brand_id}", data)

    async def complete_verification(self, brand_id: int, verification_id: int, **kwargs) -> Dict:
        return await self._request("POST", f"/agent/verification/complete/{brand_id}/{verification_id}", kwargs)

    async def get_verification(self, brand_id: int, verification_id: int) -> Dict:
        return await self._request("GET", f"/agent/verification/{brand_id}/{verification_id}")

    # ============ LEARNING ============

    async def record_learning(self, brand_id: int, data: Dict) -> Dict:
        return await self._request("POST", f"/agent/learn/{brand_id}", data)

    async def get_similar_experiences(
        self, brand_id: int, opportunity_type: str = None, severity: str = None
    ) -> Dict:
        params = []
        if opportunity_type:
            params.append(f"type={opportunity_type}")
        if severity:
            params.append(f"severity={severity}")
        endpoint = f"/agent/experiences/similar/{brand_id}"
        if params:
            endpoint += "?" + "&".join(params)
        return await self._request("GET", endpoint)
    


async def rollback_action(self, action_id: str, brand_id: int, action_name: str) -> Dict:
    return await self._request("POST", f"/agent/rollback/log", {
        "action_id": action_id,
        "action_name": action_name,
        "brand_id": brand_id
    })