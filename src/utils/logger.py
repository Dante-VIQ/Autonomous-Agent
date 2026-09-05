# src/utils/logger.py

import logging
import sys
from datetime import datetime

# ============ OLD SETUP LOGGER (for backward compatibility) ============

def setup_logger(name: str = "vumbi_agent", level: str = "INFO") -> logging.Logger:
    """Setup a logger with consistent formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger

# Default logger instance (for old code)
logger = setup_logger()

# ============ NEW STRUCTURED LOGGER (for enhanced logging) ============

class StructuredLogger:
    """Structured logger with agent-specific formatting."""
    
    def __init__(self, name: str = "vumbi_agent", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def cycle_start(self, brand_id: int, cycle_id: str):
        self.logger.info("━" * 50)
        self.logger.info(f"🔄 AGENT CYCLE — Brand {brand_id}")
        self.logger.info(f"   Cycle: {cycle_id}")
        self.logger.info("━" * 50)
    
    def discovery(self, count: int):
        self.logger.info(f"📡 DISCOVERY — {count} opportunities found")
    
    def evidence(self, items: dict):
        self.logger.info(f"📊 EVIDENCE — {items}")
    
    def reasoning(self, opp_id: str, specialist: str, confidence: float):
        self.logger.info(f"🧠 REASONING — Opp: {opp_id} | Specialist: {specialist} | Confidence: {confidence:.2f}")
    
    def policy(self, action: str, result: str):
        self.logger.info(f"🛡️ POLICY — {action} → {result}")
    
    def execution(self, action: str, status: str):
        self.logger.info(f"⚡ EXECUTION — {action} → {status}")
    
    def verification(self, action: str, success: bool):
        self.logger.info(f"✅ VERIFICATION — {action} → {'SUCCESS' if success else 'FAILURE'}")
    
    def learning(self, experience_id: str):
        self.logger.info(f"📖 LEARNING — Recorded experience: {experience_id}")
    
    def cycle_end(self, status: str):
        self.logger.info("━" * 50)
        self.logger.info(f"🏁 CYCLE {status.upper()}")
        self.logger.info("━" * 50)

# Create a default instance
structured_logger = StructuredLogger()