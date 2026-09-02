# src/utils/api_client.py

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
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an async request to the Laravel API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = await self.client.request(method, url, json=data)
            response.raise_for_status()
            if not response.text:
                return {"success": True}
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"API request failed: {e}")
            if e.response:
                logger.error(f"Response body: {e.response.text}")
            raise
    
    async def close(self):
        """Close the client session."""
        await self.client.aclose()
    
    # ============ All methods become async ============
    
    async def get_opportunities(self, brand_id: int) -> List[Dict]:
        return (await self._request("GET", f"/agent/opportunities/{brand_id}")).get("opportunities", [])

        
    
    async def get_analytics(self, brand_id: int) -> Dict:
        return await self._request("GET", f"/agent/analytics/{brand_id}")
    
    
    # ============ SEO ============
    
    def get_seo_issues(self, brand_id: int) -> List[Dict]:
        """Fetch SEO issues for a brand."""
        return self._request("GET", f"/agent/seo/issues/{brand_id}").get("issues", [])
    
    def get_seo_issue(self, brand_id: int, issue_id: str) -> Dict:
        """Fetch a specific SEO issue."""
        return self._request("GET", f"/agent/seo/issue/{brand_id}/{issue_id}")
    
    def analyze_seo_issue(self, brand_id: int, issue_id: str) -> Dict:
        """Analyze an SEO issue and get recommendations."""
        return self._request("POST", f"/agent/seo/analyze/{brand_id}/{issue_id}")
    
    def get_seo_recommendations(self, brand_id: int, issue_id: str) -> Dict:
        """Get SEO recommendations for a specific issue."""
        return self._request("GET", f"/agent/seo/recommendations/{brand_id}/{issue_id}")
    
    def get_keyword_rankings(self, brand_id: int, page_url: str = None) -> Dict:
        """Get keyword rankings for a page or brand."""
        endpoint = f"/agent/seo/rankings/{brand_id}"
        if page_url:
            endpoint += f"?url={page_url}"
        return self._request("GET", endpoint)
    
    # ============ LEADS ============
    
    def get_pending_leads(self, brand_id: int) -> List[Dict]:
        """Fetch pending leads for a brand."""
        return self._request("GET", f"/agent/leads/pending/{brand_id}").get("leads", [])
    
    def get_lead(self, brand_id: int, lead_id: str) -> Dict:
        """Fetch a specific lead."""
        return self._request("GET", f"/agent/lead/{brand_id}/{lead_id}")
    
    def get_lead_engagement(self, brand_id: int, lead_id: str) -> Dict:
        """Fetch lead engagement data."""
        return self._request("GET", f"/agent/lead/engagement/{brand_id}/{lead_id}")
    
    def get_lead_context(self, brand_id: int, lead_id: str) -> Dict:
        """Fetch lead context (notes, history, etc.)."""
        return self._request("GET", f"/agent/lead/context/{brand_id}/{lead_id}")
    
    def generate_follow_up(self, brand_id: int, lead_id: str) -> Dict:
        """Generate a follow-up message for a lead."""
        return self._request("POST", f"/agent/lead/follow-up/{brand_id}", {"lead_id": lead_id})
    
    # ============ CAMPAIGNS ============
    
    def get_campaigns(self, brand_id: int) -> List[Dict]:
        """Fetch campaigns for a brand."""
        return self._request("GET", f"/agent/campaigns/{brand_id}")
    
    def pause_campaign(self, brand_id: int, campaign_id: str, reason: str = None) -> Dict:
        """Pause a campaign."""
        return self._request("POST", "/agent/campaigns/pause", {
            "brandId": brand_id,
            "campaignId": campaign_id,
            "reason": reason
        })
    
    # ============ CONTENT ============
    
    def generate_content(self, brand_id: int, topic: str, template: str = "blog") -> Dict:
        """Generate content for a topic."""
        return self._request("POST", "/agent/content/generate", {
            "brandId": brand_id,
            "topic": topic,
            "template": template
        })
    
    def analyze_content_gap(self, brand_id: int, topic: str) -> Dict:
        """Analyze content gaps for a topic."""
        return self._request("POST", f"/agent/content/gap-analysis/{brand_id}", {"topic": topic})
    
    def generate_outline(self, topic: str, template: str = "blog") -> Dict:
        """Generate a content outline."""
        return self._request("POST", "/agent/content/outline", {
            "topic": topic,
            "template": template
        })
    
    # ============ EXECUTION ============
    
    def create_pending_action(self, brand_id: int, action: Dict, reason: str = None) -> Dict:
        """Create a pending action for human review."""
        return self._request("POST", "/agent/actions/pending", {
            "brandId": brand_id,
            "action": action,
            "reason": reason
        })
    
    def scan(self, brand_id: int) -> Dict:
        """Trigger a full scan."""
        return self._request("POST", f"/agent/scan/{brand_id}")
    
    # ============ VERIFICATION ============
    
    def start_verification(self, brand_id: int, action_name: str, **kwargs) -> Dict:
        """Start verification for an action."""
        data = {"brand_id": brand_id, "action_name": action_name, **kwargs}
        return self._request("POST", f"/agent/verification/start/{brand_id}", data)
    
    def complete_verification(self, brand_id: int, verification_id: int, **kwargs) -> Dict:
        """Complete verification for an action."""
        return self._request("POST", f"/agent/verification/complete/{brand_id}/{verification_id}", kwargs)
    
    def get_verification(self, brand_id: int, verification_id: int) -> Dict:
        """Get verification status."""
        return self._request("GET", f"/agent/verification/{brand_id}/{verification_id}")
    
    # ============ LEARNING ============
    
    def record_learning(self, brand_id: int, data: Dict) -> Dict:
        """Record learning outcomes."""
        return self._request("POST", f"/agent/learn/{brand_id}", data)
    
    def get_similar_experiences(self, brand_id: int, opportunity_type: str = None, severity: str = None) -> Dict:
        """Get similar experiences for pattern analysis."""
        params = []
        if opportunity_type:
            params.append(f"type={opportunity_type}")
        if severity:
            params.append(f"severity={severity}")
        endpoint = f"/agent/experiences/similar/{brand_id}"
        if params:
            endpoint += "?" + "&".join(params)
        return self._request("GET", endpoint)
    
    # ============ ROLLBACK ============
    
    def rollback_action(self, action_id: str, brand_id: int, action_name: str) -> Dict:
        """Rollback an action via Laravel."""
        return self._request("POST", f"/agent/rollback/{brand_id}", {
            "action_id": action_id,
            "action_name": action_name
        })