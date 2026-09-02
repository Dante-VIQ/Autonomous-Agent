# src/main.py

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from .config import Config
from .orchestrator import Orchestrator
from .utils.logger import setup_logger

logger = setup_logger(__name__, Config.LOG_LEVEL)

async def run_cycle() -> Dict[str, Any]:
    """Run a single agent cycle using the Orchestrator."""
    logger.info("🔄 Starting agent cycle...")
    orchestrator = Orchestrator(Config.BRAND_ID)
    result = await orchestrator.run_cycle()
    logger.info("✅ Cycle completed")
    return result

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
    
    await run_cycle()
    
    while not stop_event.is_set():
        try:
            await asyncio.sleep(Config.AGENT_INTERVAL)
            if stop_event.is_set():
                break
            await run_cycle()
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