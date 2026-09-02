# src/config.py

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"

if env_file.exists():
    load_dotenv(env_file)
else:
    # Also try loading from current directory for backward compatibility
    load_dotenv()


class Config:
    # ============ API Configuration ============
    LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "").strip()
    LARAVEL_API_KEY = os.getenv("LARAVEL_API_KEY", "").strip()
    BRAND_ID = int(os.getenv("BRAND_ID", "1"))
    
    # ============ Model Configuration ============
    # Primary: Ollama for cost savings
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
    
    # Fallback: Gemini for complex reasoning
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    
    # ============ Agent Settings ============
    AGENT_INTERVAL = int(os.getenv("AGENT_INTERVAL", "900"))  # 15 minutes
    AUTONOMOUS_THRESHOLD = float(os.getenv("AUTONOMOUS_THRESHOLD", "0.8"))
    MAX_ACTIONS_PER_CYCLE = int(os.getenv("MAX_ACTIONS_PER_CYCLE", "10"))
    
    # ============ Logging ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    _validated = False
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration. Fails fast with clear diagnostic messages."""
        if cls._validated:
            return
        
        errors = []
        
        # Check Laravel API URL
        if not cls.LARAVEL_API_URL:
            errors.append(
                "LARAVEL_API_URL is required.\n"
                f"  Set LARAVEL_API_URL in {env_file} or as an environment variable.\n"
                "  Example: LARAVEL_API_URL=http://localhost:8000/api"
            )
        elif "your-hostinger-domain.com" in cls.LARAVEL_API_URL:
            errors.append(
                f"LARAVEL_API_URL is still a placeholder: {cls.LARAVEL_API_URL}\n"
                f"  Update LARAVEL_API_URL in {env_file} to your actual backend URL.\n"
                "  Example: LARAVEL_API_URL=http://localhost:8000/api"
            )
        
        # Check Laravel API Key
        if not cls.LARAVEL_API_KEY:
            errors.append(
                "LARAVEL_API_KEY is required.\n"
                f"  Set LARAVEL_API_KEY in {env_file} or as an environment variable."
            )
        
        # Check at least one AI model is configured
        if not cls.GEMINI_API_KEY and not cls.OLLAMA_HOST:
            errors.append(
                "No AI model configured.\n"
                f"  Set at least one of: GEMINI_API_KEY or OLLAMA_HOST in {env_file}"
            )
        
        if errors:
            error_msg = "❌ Configuration validation failed:\n\n" + "\n\n".join(errors)
            logger = logging.getLogger(__name__)
            logger.critical(error_msg)
            sys.exit(1)
        
        cls._validated = True