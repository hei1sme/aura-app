"""
Aura Engine - The Intelligent Wellness Companion Backend
"""

__version__ = "1.0.0"
__author__ = "Aura Team"

from .database import DatabaseManager
from .monitoring import ActivityMonitor
from .scheduler import BreakScheduler

__all__ = [
    "DatabaseManager",
    "ActivityMonitor", 
    "BreakScheduler",
]
