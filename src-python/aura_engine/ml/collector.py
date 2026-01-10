"""
Aura Data Collector - ML Training Data Collection Logic

This module implements the DATA-FIRST strategy (FR-01.4):
Collects behavioral metadata for future ML model training.

Features Logged:
- timestamp: Unix timestamp of the event
- mouse_velocity: Average mouse movement speed
- keys_per_min: Keyboard activity rate  
- app_category: Category of active app (Code/Web/Video/Game/Other)
- time_since_last_break: Seconds since last break
- is_fullscreen: Whether app is in fullscreen mode

Labels Logged:
- user_response: 1 = Done/Completed, 0 = Snooze/Dismiss
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

from ..database import get_database, DatabaseManager


class AppCategory(Enum):
    """Application categories for behavioral analysis."""
    CODE = "Code"
    WEB = "Web"
    VIDEO = "Video"
    GAME = "Game"
    PRODUCTIVITY = "Productivity"
    COMMUNICATION = "Communication"
    OTHER = "Other"


class UserResponse(Enum):
    """User response to break reminders."""
    DISMISS = 0
    SNOOZE = 0  # Treated same as dismiss for ML
    COMPLETED = 1


@dataclass
class ActivitySnapshot:
    """
    A snapshot of user activity at a given moment.
    
    This is the feature vector for ML training.
    """
    timestamp: int
    mouse_velocity: float  # pixels per second (average)
    keys_per_min: int  # keystrokes per minute
    app_category: str  # From AppCategory enum
    time_since_last_break: int  # seconds
    is_fullscreen: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return asdict(self)


@dataclass
class LabeledSample:
    """
    A labeled training sample with user response.
    """
    snapshot: ActivitySnapshot
    user_response: int  # 0 or 1
    record_id: Optional[int] = None  # Database record ID


class DataCollector:
    """
    Collects and manages training data for the ML model.
    
    This class is responsible for:
    1. Recording activity snapshots when breaks are triggered
    2. Updating records with user responses
    3. Providing data for model training
    """
    
    # App process name to category mapping
    APP_CATEGORY_MAP = {
        # Code editors & IDEs
        "code.exe": AppCategory.CODE,
        "code": AppCategory.CODE,
        "devenv.exe": AppCategory.CODE,
        "pycharm64.exe": AppCategory.CODE,
        "idea64.exe": AppCategory.CODE,
        "sublime_text.exe": AppCategory.CODE,
        "atom.exe": AppCategory.CODE,
        "notepad++.exe": AppCategory.CODE,
        "cursor.exe": AppCategory.CODE,
        
        # Browsers
        "chrome.exe": AppCategory.WEB,
        "firefox.exe": AppCategory.WEB,
        "msedge.exe": AppCategory.WEB,
        "brave.exe": AppCategory.WEB,
        "opera.exe": AppCategory.WEB,
        "safari": AppCategory.WEB,
        
        # Video players
        "vlc.exe": AppCategory.VIDEO,
        "vlc": AppCategory.VIDEO,
        "mpc-hc64.exe": AppCategory.VIDEO,
        "potplayer.exe": AppCategory.VIDEO,
        "wmplayer.exe": AppCategory.VIDEO,
        
        # Games
        "league of legends.exe": AppCategory.GAME,
        "leagueclient.exe": AppCategory.GAME,
        "valorant.exe": AppCategory.GAME,
        "csgo.exe": AppCategory.GAME,
        "cs2.exe": AppCategory.GAME,
        "dota2.exe": AppCategory.GAME,
        "minecraft.exe": AppCategory.GAME,
        "steam.exe": AppCategory.GAME,
        
        # Productivity
        "winword.exe": AppCategory.PRODUCTIVITY,
        "excel.exe": AppCategory.PRODUCTIVITY,
        "powerpnt.exe": AppCategory.PRODUCTIVITY,
        "notion.exe": AppCategory.PRODUCTIVITY,
        "obsidian.exe": AppCategory.PRODUCTIVITY,
        
        # Communication
        "discord.exe": AppCategory.COMMUNICATION,
        "slack.exe": AppCategory.COMMUNICATION,
        "teams.exe": AppCategory.COMMUNICATION,
        "zoom.exe": AppCategory.COMMUNICATION,
        "telegram.exe": AppCategory.COMMUNICATION,
    }
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Initialize the data collector.
        
        Args:
            db: Optional database manager instance. Uses singleton if not provided.
        """
        self.db = db or get_database()
        self._last_break_time: int = int(time.time())
        self._pending_record_id: Optional[int] = None
    
    def categorize_app(self, process_name: str) -> str:
        """
        Categorize an application by its process name.
        
        Args:
            process_name: The name of the process (e.g., "code.exe")
            
        Returns:
            Category string (Code/Web/Video/Game/Productivity/Communication/Other)
        """
        if not process_name:
            return AppCategory.OTHER.value
        
        process_lower = process_name.lower()
        category = self.APP_CATEGORY_MAP.get(process_lower, AppCategory.OTHER)
        return category.value
    
    def record_activity_snapshot(
        self,
        mouse_velocity: float,
        keys_per_min: int,
        active_process: str,
        is_fullscreen: bool = False
    ) -> int:
        """
        Record an activity snapshot when a break is about to be triggered.
        
        This creates a training sample WITHOUT a label. The label will be
        added when the user responds to the break reminder.
        
        Args:
            mouse_velocity: Average mouse movement speed (pixels/sec)
            keys_per_min: Keyboard activity rate
            active_process: Name of the currently active process
            is_fullscreen: Whether the app is in fullscreen mode
            
        Returns:
            The database record ID for later label update
        """
        app_category = self.categorize_app(active_process)
        time_since_last_break = int(time.time()) - self._last_break_time
        
        record_id = self.db.log_training_data(
            mouse_velocity=mouse_velocity,
            keys_per_min=keys_per_min,
            app_category=app_category,
            time_since_last_break=time_since_last_break,
            is_fullscreen=is_fullscreen,
            user_response=None  # Label pending
        )
        
        self._pending_record_id = record_id
        return record_id
    
    def record_user_response(self, response: int, record_id: Optional[int] = None) -> None:
        """
        Record the user's response to a break reminder.
        
        Args:
            response: 0 = Snooze/Dismiss, 1 = Done/Completed
            record_id: Optional record ID. Uses pending record if not provided.
        """
        rid = record_id or self._pending_record_id
        
        if rid is None:
            return  # No pending record to update
        
        self.db.update_training_response(rid, response)
        
        # If user completed the break, update last break time
        if response == 1:
            self._last_break_time = int(time.time())
        
        self._pending_record_id = None
    
    def mark_break_completed(self, record_id: Optional[int] = None) -> None:
        """Mark a break as completed (positive label)."""
        self.record_user_response(1, record_id)
    
    def mark_break_dismissed(self, record_id: Optional[int] = None) -> None:
        """Mark a break as dismissed/snoozed (negative label)."""
        self.record_user_response(0, record_id)
    
    def get_time_since_last_break(self) -> int:
        """Get seconds since the last completed break."""
        return int(time.time()) - self._last_break_time
    
    def reset_break_timer(self) -> None:
        """Reset the break timer (e.g., when user manually takes a break)."""
        self._last_break_time = int(time.time())
    
    def get_training_stats(self) -> Dict[str, Any]:
        """
        Get statistics about collected training data.
        
        Returns:
            Dictionary with stats about the training dataset
        """
        total_labeled = self.db.get_training_data_count()
        data = self.db.get_training_data(limit=10000)
        
        if not data:
            return {
                "total_samples": 0,
                "positive_rate": 0.0,
                "ready_for_training": False,
                "message": "No training data collected yet"
            }
        
        positive = sum(1 for d in data if d.get("user_response") == 1)
        negative = total_labeled - positive
        
        # We need at least 100 samples for meaningful training
        ready = total_labeled >= 100
        
        return {
            "total_samples": total_labeled,
            "positive_samples": positive,
            "negative_samples": negative,
            "positive_rate": positive / total_labeled if total_labeled > 0 else 0,
            "ready_for_training": ready,
            "message": f"{'Ready for model training!' if ready else f'Need {100 - total_labeled} more samples'}"
        }
    
    def export_dataset(self, filepath: str) -> int:
        """
        Export the training dataset to a CSV file.
        
        Useful for:
        - External analysis in Jupyter notebooks
        - Custom model training
        - Data backup
        
        Args:
            filepath: Path to the output CSV file
            
        Returns:
            Number of records exported
        """
        return self.db.export_training_data_csv(filepath)


class ActivityAccumulator:
    """
    Accumulates activity metrics over a time window.
    
    Used to calculate average mouse velocity and keys per minute
    between break reminders.
    """
    
    def __init__(self, window_seconds: int = 60):
        """
        Initialize the accumulator.
        
        Args:
            window_seconds: Time window for averaging metrics
        """
        self.window_seconds = window_seconds
        self._mouse_positions: List[tuple] = []  # (timestamp, x, y)
        self._key_events: List[float] = []  # timestamps
        self._start_time: float = time.time()
    
    def add_mouse_position(self, x: int, y: int) -> None:
        """Record a mouse position."""
        now = time.time()
        self._mouse_positions.append((now, x, y))
        self._cleanup_old_data()
    
    def add_key_event(self) -> None:
        """Record a key press event."""
        self._key_events.append(time.time())
        self._cleanup_old_data()
    
    def _cleanup_old_data(self) -> None:
        """Remove data older than the window."""
        cutoff = time.time() - self.window_seconds
        
        self._mouse_positions = [
            p for p in self._mouse_positions if p[0] >= cutoff
        ]
        self._key_events = [t for t in self._key_events if t >= cutoff]
    
    def get_mouse_velocity(self) -> float:
        """
        Calculate average mouse velocity in pixels per second.
        
        Returns:
            Average velocity, or 0 if insufficient data
        """
        if len(self._mouse_positions) < 2:
            return 0.0
        
        total_distance = 0.0
        total_time = 0.0
        
        for i in range(1, len(self._mouse_positions)):
            t1, x1, y1 = self._mouse_positions[i - 1]
            t2, x2, y2 = self._mouse_positions[i]
            
            distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            dt = t2 - t1
            
            if dt > 0:
                total_distance += distance
                total_time += dt
        
        return total_distance / total_time if total_time > 0 else 0.0
    
    def get_keys_per_minute(self) -> int:
        """
        Calculate keystrokes per minute.
        
        Returns:
            Keys per minute (integer)
        """
        if not self._key_events:
            return 0
        
        # Calculate over actual time window
        now = time.time()
        window_start = now - self.window_seconds
        recent_keys = [t for t in self._key_events if t >= window_start]
        
        # Scale to per-minute
        elapsed = min(self.window_seconds, now - self._start_time)
        if elapsed <= 0:
            return 0
        
        kpm = (len(recent_keys) / elapsed) * 60
        return int(kpm)
    
    def reset(self) -> None:
        """Reset all accumulated data."""
        self._mouse_positions = []
        self._key_events = []
        self._start_time = time.time()
    
    def get_snapshot_data(self) -> Dict[str, Any]:
        """
        Get current activity metrics for snapshot creation.
        
        Returns:
            Dictionary with mouse_velocity and keys_per_min
        """
        return {
            "mouse_velocity": self.get_mouse_velocity(),
            "keys_per_min": self.get_keys_per_minute()
        }


if __name__ == "__main__":
    # Test the collector
    collector = DataCollector()
    
    # Simulate recording an activity snapshot
    record_id = collector.record_activity_snapshot(
        mouse_velocity=150.5,
        keys_per_min=45,
        active_process="code.exe",
        is_fullscreen=False
    )
    print(f"Created record: {record_id}")
    
    # Simulate user completing the break
    collector.mark_break_completed(record_id)
    
    # Check stats
    stats = collector.get_training_stats()
    print(f"Training stats: {stats}")
