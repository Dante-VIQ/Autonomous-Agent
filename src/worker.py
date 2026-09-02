# src/worker.py

import asyncio
from typing import Dict, Any
from .orchestrator import Orchestrator
import logging

logger = logging.getLogger(__name__)

class WorkerPool:
    """Pool of persistent workers for the agent runtime."""
    
    def __init__(self, brand_id: int, pool_size: int = 5):
        self.brand_id = brand_id
        self.pool_size = pool_size
        self.workers = []
        self.orchestrator = Orchestrator(brand_id)
    
    async def run(self):
        """Run the worker pool."""
        logger.info(f"🚀 Starting worker pool with {self.pool_size} workers")
        
        tasks = []
        for i in range(self.pool_size):
            task = asyncio.create_task(self._worker_loop(i))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _worker_loop(self, worker_id: int):
        """Individual worker loop."""
        logger.info(f"🧵 Worker {worker_id} started")
        
        while True:
            try:
                # Get next task from queue
                # For now, just run the cycle
                await self.orchestrator.run_cycle()
                
                # Sleep before next cycle
                await asyncio.sleep(900)  # 15 minutes
                
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} failed: {e}")
                await asyncio.sleep(60)  # Back off on error