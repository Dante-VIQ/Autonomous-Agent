# src/memory/experience.py

import logging
from typing import Dict, Any, List, Optional
from ..utils.api_client import LaravelApiClient

logger = logging.getLogger(__name__)

class ExperienceMemory:
    """Real experience memory using Laravel backend."""
    
    def __init__(self):
        self.client = LaravelApiClient()
    
    async def find_similar(self, opportunity: Dict[str, Any], brand_id: int) -> List[Dict]:
        """Find similar experiences from real data."""
        if brand_id is None:
            logger.warning("find_similar called with brand_id=None, defaulting to 1")
            brand_id = 1
        
        try:
            result = await self.client.get_similar_experiences(
                brand_id,
                opportunity.get("type"),
                opportunity.get("severity")
            )
            return result.get("experiences", [])
        except Exception as e:
            logger.warning(f"Failed to fetch similar experiences: {e}")
            return []
    
    async def analyze_patterns(self, opportunity: Dict[str, Any], brand_id: int) -> Dict[str, Any]:
        """Analyze patterns from similar experiences."""
        experiences = await self.find_similar(opportunity, brand_id)
        
        if not experiences:
            return {
                "success_rate": 0,
                "avg_improvement": 0,
                "confidence_boost": 0,
                "recommended_action": "investigate",
                "similar_count": 0,
                "insights": ["No similar experiences found. Proceed with caution."],
                "cautionary_notes": ["This is a new type of opportunity for this brand."]
            }
        
        successful = [e for e in experiences if e.get("was_successful", False)]
        success_rate = (len(successful) / len(experiences)) * 100 if experiences else 0
        avg_improvement = sum(e.get("improvement_percentage", 0) for e in successful) / len(successful) if successful else 0
        
        confidence_boost = (success_rate / 100) * 0.2
        
        insights = []
        if success_rate >= 80 and avg_improvement > 10:
            recommended = "execute"
            insights.append(f"✅ High success rate ({success_rate:.1f}%) with avg {avg_improvement:.1f}% improvement")
        elif success_rate >= 60 and avg_improvement > 0:
            recommended = "execute"
            insights.append(f"👍 Moderate success rate ({success_rate:.1f}%) with positive improvement")
        elif success_rate >= 40:
            recommended = "human_review"
            insights.append(f"⚠️ Mixed results ({success_rate:.1f}% success rate)")
        else:
            recommended = "investigate"
            insights.append(f"🔴 Low success rate ({success_rate:.1f}%)")
        
        if len(experiences) > 10:
            insights.append(f"📊 Based on {len(experiences)} similar experiences")
        elif len(experiences) > 3:
            insights.append(f"📊 Limited data ({len(experiences)} experiences), proceed with caution")
        
        return {
            "success_rate": success_rate,
            "avg_improvement": avg_improvement,
            "confidence_boost": confidence_boost,
            "recommended_action": recommended,
            "similar_count": len(experiences),
            "insights": insights,
            "cautionary_notes": []
        }
    
    async def record(self, brand_id: int, data: Dict[str, Any]) -> Dict:
        """Record a new experience."""
        try:
            result = await self.client.record_learning(brand_id, data)
            logger.info(f"Recorded learning for brand {brand_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to record learning: {e}")
            return {"success": False, "error": str(e)}