"""
Aura Database Manager - SQLite Handler

Handles all database operations including:
- Schema initialization
- Settings management
- Break logs storage
- Training data collection for ML
"""

import sqlite3
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
import json


class DatabaseManager:
    """
    SQLite Database Manager for Aura.
    
    Database location: ~/.aura/aura.db
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database manager.
        
        Args:
            db_path: Optional custom path for the database file.
                    Defaults to ~/.aura/aura.db
        """
        if db_path is None:
            aura_dir = Path.home() / ".aura"
            aura_dir.mkdir(exist_ok=True)
            self.db_path = str(aura_dir / "aura.db")
        else:
            self.db_path = db_path
            
        self._init_schema()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize the database schema as per PRD Section 6.2."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Settings table: key-value store for app configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Logs table: History of breaks taken (for Dashboard)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    break_type TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT 0,
                    skipped BOOLEAN NOT NULL DEFAULT 0,
                    snoozed BOOLEAN NOT NULL DEFAULT 0,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Hydration logs: Track water intake
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hydration_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    amount_ml INTEGER NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Training data table: ML feature collection (FR-01.4)
            # This is the DATA-FIRST architecture - collect from Day 1
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    mouse_velocity REAL NOT NULL,
                    keys_per_min INTEGER NOT NULL,
                    app_category TEXT NOT NULL,
                    time_since_last_break INTEGER NOT NULL,
                    is_fullscreen BOOLEAN NOT NULL DEFAULT 0,
                    user_response INTEGER DEFAULT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
                ON logs(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_training_timestamp 
                ON training_data(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hydration_timestamp 
                ON hydration_logs(timestamp)
            """)
            
            # Insert default settings if not exist
            self._init_default_settings(cursor)
    
    def _init_default_settings(self, cursor: sqlite3.Cursor):
        """Initialize default application settings."""
        defaults = {
            "water_goal": "2000",  # ml per day
            "micro_break_interval": "1200",  # 20 minutes in seconds
            "macro_break_interval": "2700",  # 45 minutes in seconds
            "hydration_interval": "1800",  # 30 minutes in seconds
            "micro_break_duration": "20",  # seconds
            "macro_break_duration": "180",  # 3 minutes in seconds
            "idle_threshold": "180",  # 3 minutes in seconds
            "immersive_mode_enabled": "false",
            "auto_start": "false",
            "close_to_tray": "true",
            "sound_enabled": "true",
            "auto_detect_fullscreen": "true",
            "theme": "dark",
            "blocklist_processes": json.dumps([
                "league_of_legends.exe",
                "vlc.exe", 
                "obs64.exe",
                "zoom.exe",
                "discord.exe"
            ])
        }
        
        for key, value in defaults.items():
            cursor.execute("""
                INSERT OR IGNORE INTO settings (key, value) 
                VALUES (?, ?)
            """, (key, value))
    
    # ==================== Settings Methods ====================
    
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
    
    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (key, value, updated_at) 
                VALUES (?, ?, strftime('%s', 'now'))
                ON CONFLICT(key) DO UPDATE SET 
                    value = excluded.value,
                    updated_at = strftime('%s', 'now')
            """, (key, value))
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as a dictionary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
    
    # ==================== Break Log Methods ====================
    
    def log_break(
        self, 
        break_type: str, 
        duration_seconds: int,
        completed: bool = False,
        skipped: bool = False,
        snoozed: bool = False
    ) -> int:
        """
        Log a break event.
        
        Args:
            break_type: "micro", "macro", or "hydration"
            duration_seconds: Duration of the break
            completed: Whether the user completed the break
            skipped: Whether the user skipped the break
            snoozed: Whether the user snoozed the break
            
        Returns:
            The ID of the inserted log entry
        """
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs (timestamp, break_type, duration_seconds, 
                                  completed, skipped, snoozed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (int(time.time()), break_type, duration_seconds, 
                  completed, skipped, snoozed))
            return cursor.lastrowid
    
    def get_breaks_today(self) -> List[Dict[str, Any]]:
        """Get all breaks logged today."""
        import time
        today_start = int(time.time()) - (int(time.time()) % 86400)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM logs 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (today_start,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_break_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get break statistics for the last N days."""
        import time
        cutoff = int(time.time()) - (days * 86400)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_breaks,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN skipped = 1 THEN 1 ELSE 0 END) as skipped,
                    SUM(CASE WHEN snoozed = 1 THEN 1 ELSE 0 END) as snoozed,
                    break_type
                FROM logs
                WHERE timestamp >= ?
                GROUP BY break_type
            """, (cutoff,))
            
            stats = {}
            for row in cursor.fetchall():
                stats[row["break_type"]] = {
                    "total": row["total_breaks"],
                    "completed": row["completed"],
                    "skipped": row["skipped"],
                    "snoozed": row["snoozed"]
                }
            return stats
    
    # ==================== Hydration Methods ====================
    
    def log_hydration(self, amount_ml: int) -> int:
        """Log water intake."""
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO hydration_logs (timestamp, amount_ml)
                VALUES (?, ?)
            """, (int(time.time()), amount_ml))
            return cursor.lastrowid
    
    def get_hydration_today(self) -> int:
        """Get total water intake for today in ml."""
        import time
        today_start = int(time.time()) - (int(time.time()) % 86400)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(SUM(amount_ml), 0) as total
                FROM hydration_logs
                WHERE timestamp >= ?
            """, (today_start,))
            return cursor.fetchone()["total"]
    
    # ==================== Training Data Methods ====================
    
    def log_training_data(
        self,
        mouse_velocity: float,
        keys_per_min: int,
        app_category: str,
        time_since_last_break: int,
        is_fullscreen: bool = False,
        user_response: Optional[int] = None
    ) -> int:
        """
        Log training data for ML model (FR-01.4 Data Collection Engine).
        
        Args:
            mouse_velocity: Average mouse movement speed
            keys_per_min: Keyboard activity rate
            app_category: Category of active app (Code/Web/Video/Game/Other)
            time_since_last_break: Seconds since last break
            is_fullscreen: Whether app is in fullscreen mode
            user_response: 1 = Done/Completed, 0 = Snooze/Dismiss, None = pending
            
        Returns:
            The ID of the inserted training record
        """
        import time
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO training_data 
                (timestamp, mouse_velocity, keys_per_min, app_category,
                 time_since_last_break, is_fullscreen, user_response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (int(time.time()), mouse_velocity, keys_per_min, 
                  app_category, time_since_last_break, is_fullscreen, 
                  user_response))
            return cursor.lastrowid
    
    def update_training_response(self, record_id: int, user_response: int) -> None:
        """Update the user response for a training data record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE training_data 
                SET user_response = ?
                WHERE id = ?
            """, (user_response, record_id))
    
    def get_training_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get training data for ML model training.
        
        Returns only records where user_response is not null.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM training_data
                WHERE user_response IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_training_data_count(self) -> int:
        """Get count of labeled training data records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM training_data
                WHERE user_response IS NOT NULL
            """)
            return cursor.fetchone()["count"]
    
    def export_training_data_csv(self, filepath: str) -> int:
        """
        Export training data to CSV for external analysis.
        
        Returns:
            Number of records exported
        """
        import csv
        
        data = self.get_training_data(limit=100000)
        
        if not data:
            return 0
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        return len(data)


# Singleton instance for easy access
_db_instance: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


if __name__ == "__main__":
    # Test the database
    db = DatabaseManager()
    print(f"Database initialized at: {db.db_path}")
    print(f"Settings: {db.get_all_settings()}")
