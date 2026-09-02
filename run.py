#!/usr/bin/env python3
# run.py – Entry point for the Python agent

import sys
import os
import asyncio
import logging

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.main import run_cycle

if __name__ == "__main__":
    try:
        # ✅ Properly await the async function
        asyncio.run(run_cycle())
    except KeyboardInterrupt:
        logging.info("🛑 Agent stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1)