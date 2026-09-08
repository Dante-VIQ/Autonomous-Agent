# src/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ============ Laravel API ============
    LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://localhost:8000/api")
    LARAVEL_API_KEY = os.getenv("LARAVEL_API_KEY", "")
    
    # ============ Brand ============
    BRAND_ID = int(os.getenv("BRAND_ID", "1"))
    
    # ============ AI Models ============
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.1.5:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # ============ Agent ============
    AGENT_INTERVAL = int(os.getenv("AGENT_INTERVAL", "900"))
    AUTONOMOUS_THRESHOLD = float(os.getenv("AUTONOMOUS_THRESHOLD", "0.8"))
    MAX_ACTIONS_PER_CYCLE = int(os.getenv("MAX_ACTIONS_PER_CYCLE", "10"))
    
    # ============ Logging ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        if not cls.LARAVEL_API_KEY:
            raise ValueError("LARAVEL_API_KEY is required")
        if not cls.GEMINI_API_KEY and not cls.OLLAMA_HOST:
            raise ValueError("Either GEMINI_API_KEY or OLLAMA_HOST must be set")