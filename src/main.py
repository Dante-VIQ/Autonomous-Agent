# src/main.py

# src/main.py – add at the very top
import os
import subprocess
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_candidates = [
    os.path.join(project_root, "venv", "bin", "python"),
    os.path.join(project_root, ".venv", "bin", "python"),
]
venv_python = next((path for path in venv_candidates if os.path.exists(path)), venv_candidates[-1])


def ensure_runtime_environment() -> None:
    """Re-exec through the project venv when launched with the system Python."""
    if os.path.exists(venv_python) and os.path.realpath(sys.executable) != os.path.realpath(venv_python):
        try:
            import strands  # noqa: F401
            import google.genai  # noqa: F401
        except ModuleNotFoundError:
            requirements_file = os.path.join(project_root, "requirements.txt")
            if os.path.exists(requirements_file):
                subprocess.run([venv_python, "-m", "pip", "install", "-r", requirements_file], cwd=project_root, check=False)
            os.execv(venv_python, [venv_python, "-m", "src.main"] + sys.argv[1:])


ensure_runtime_environment()

# Ensure the project root is in the path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging
import time
import json
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config

# Validate configuration early so the app fails with clear diagnostics
Config.validate()

from src.utils.api_client import LaravelApiClient
from src.tools.monitor import monitor_opportunities
from src.tools.decision import intelligent_decision
from src.tools.execute import execute_action
from src.tools.verify import verify_action
from src.tools.learn import record_learning
from src.specialists.seo import SeoSpecialist
from src.specialists.lead import LeadSpecialist
from src.specialists.content import ContentSpecialist

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_cycle():
    """Run a full agent cycle with real data."""
    logger.info("🔄 Starting agent cycle...")
    
    try:
        # 1. Monitor – Get real opportunities
        logger.info("📡 Monitoring opportunities...")
        opportunities = monitor_opportunities(Config.BRAND_ID)
        opp_data = json.loads(opportunities)
        
        if not opp_data.get("opportunities"):
            logger.info("No opportunities found, skipping cycle.")
            return
        
        # 2. Delegate to specialists
        for opp in opp_data["opportunities"]:
            opp_type = opp.get("type")
            logger.info(f"🎯 Processing {opp_type} opportunity: {opp.get('title')}")
            
            # Route to appropriate specialist
            if opp_type == "seo_issue":
                specialist = SeoSpecialist()
            elif opp_type == "leads_pending":
                specialist = LeadSpecialist()
            elif opp_type == "content_generation":
                specialist = ContentSpecialist()
            else:
                logger.warning(f"Unknown opportunity type: {opp_type}, skipping.")
                continue
            
            # 3. Execute with safety
            result = specialist.execute_with_safety(opp, Config.BRAND_ID)
            
            if result.get("requires_approval"):
                logger.info(f"⏳ Action requires approval: {opp.get('title')}")
            else:
                logger.info(f"✅ Action executed: {opp.get('title')}")
        
        logger.info("✅ Cycle completed.")
        
    except Exception as e:
        logger.error(f"❌ Cycle failed: {e}")

if __name__ == "__main__":
    logger.info(f"🚀 Starting Vumbi Python Agent")
    logger.info(f"   Brand ID: {Config.BRAND_ID}")
    logger.info(f"   Interval: {Config.AGENT_INTERVAL}s")
    logger.info(f"   Model: {Config.OLLAMA_MODEL} (Ollama) / {Config.GEMINI_MODEL} (fallback)")
    
    # Run first cycle immediately
    run_cycle()
    
    # Then run on schedule
    while True:
        time.sleep(Config.AGENT_INTERVAL)
        run_cycle()