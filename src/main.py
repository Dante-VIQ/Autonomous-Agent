# src/main.py

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from .config import Config
from .orchestrator import Orchestrator
from .utils.logger import setup_logger
from .utils.lock import cycle_lock

logger = setup_logger(__name__, Config.LOG_LEVEL)

async def run_cycle(brand_id: int = None) -> Dict[str, Any]:
    """Run a single agent cycle using the Orchestrator."""
    from .config import Config
    Config.validate()
    brand_id = brand_id if brand_id is not None else Config.BRAND_ID
    logger.info(f"🔄 Starting agent cycle for brand {brand_id}...")
    with cycle_lock(brand_id) as acquired:
        if not acquired:
            logger.warning(
                f"⏭️  Another cycle is already running for brand {brand_id}; skipping"
            )
            return {"status": "skipped", "reason": "cycle_already_running"}
        orchestrator = Orchestrator(brand_id)
        result = await orchestrator.run_cycle()
    logger.info("✅ Cycle completed")
    return result

async def resolve_brand_ids() -> list:
    """Brands to run: AGENT_BRANDS=all | 1,2,3 | unset (-> BRAND_ID)."""
    spec = (Config.AGENT_BRANDS or "").strip().lower()
    if not spec:
        return [Config.BRAND_ID]
    if spec == "all":
        from .utils.api_client import LaravelApiClient
        client = LaravelApiClient()
        try:
            brands = await client.list_brands()
        finally:
            await client.close()
        ids = [b["id"] for b in brands if b.get("is_active", True) and "id" in b]
        return ids or [Config.BRAND_ID]
    return [int(x) for x in spec.split(",") if x.strip()]


async def run_cycles() -> Dict[str, Any]:
    """Run one cycle per configured brand, sequentially, isolating failures."""
    Config.validate()
    results: Dict[str, Any] = {}
    for brand_id in await resolve_brand_ids():
        try:
            results[str(brand_id)] = await run_cycle(brand_id)
        except Exception as e:
            logger.error(f"❌ Brand {brand_id} cycle crashed: {e}", exc_info=True)
            results[str(brand_id)] = {"status": "failed", "error": str(e)}
    return results


async def run_forever():
    """Run the agent in an infinite loop."""
    logger.info("🚀 Starting Vumbi Python Agent (continuous mode)")
    
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("🛑 Received shutdown signal")
        stop_event.set()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    await run_cycles()
    
    while not stop_event.is_set():
        try:
            await asyncio.sleep(Config.AGENT_INTERVAL)
            if stop_event.is_set():
                break
            await run_cycles()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}")
            await asyncio.sleep(60)
    
    logger.info("🛑 Agent stopped gracefully")

if __name__ == "__main__":
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        logger.info("🛑 Agent stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)