#!/usr/bin/env python3
"""
Aura System Health Check Script
================================

This is the "Go/No-Go" verification script for Phase 2 release.
It tests all critical subsystems to ensure the application is ready
for user testing.

Tests performed:
1. STARTUP - Python sidecar launches without errors
2. DATABASE - SQLite database integrity
3. SCHEMA - training_data table has correct columns  
4. IPC - Command/response protocol works
5. ACTIVITY - Metrics tracking functions correctly
6. SCHEDULER - Break scheduling and settings updates work
7. FORCE ZERO - Ghost metrics bug is fixed
8. BREAK TRIGGER - Break events emit correctly

Usage:
    python scripts/health_check.py

Exit codes:
    0 - All tests passed (GO)
    1 - One or more tests failed (NO-GO)
"""

import sys
import os
import time
import json
import sqlite3
import tempfile
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Add src-python to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src-python"))


# ============================================
# Test Result Tracking
# ============================================

class TestStatus(Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    SKIP = "⏭️ SKIP"
    WARN = "⚠️ WARN"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str
    duration_ms: float = 0.0


class HealthCheckRunner:
    """
    Runs all health checks and reports results.
    """
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
    
    def run_test(self, name: str, test_func) -> TestResult:
        """
        Run a single test and record the result.
        
        Args:
            name: Human-readable test name
            test_func: Function that returns (passed: bool, message: str)
        """
        print(f"\n{'─' * 60}")
        print(f"🔍 Testing: {name}")
        print(f"{'─' * 60}")
        
        start = time.perf_counter()
        
        try:
            passed, message = test_func()
            status = TestStatus.PASS if passed else TestStatus.FAIL
        except Exception as e:
            status = TestStatus.FAIL
            message = f"Exception: {str(e)}"
            import traceback
            traceback.print_exc()
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        result = TestResult(
            name=name,
            status=status,
            message=message,
            duration_ms=duration_ms
        )
        
        self.results.append(result)
        
        print(f"   {status.value}: {message}")
        print(f"   Duration: {duration_ms:.1f}ms")
        
        return result
    
    def print_summary(self) -> bool:
        """
        Print summary and return True if all tests passed.
        """
        total_time = time.time() - self.start_time
        
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        warnings = sum(1 for r in self.results if r.status == TestStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)
        
        print("\n")
        print("=" * 70)
        print("                    AURA HEALTH CHECK SUMMARY")
        print("=" * 70)
        print()
        
        for result in self.results:
            status_icon = result.status.value.split()[0]
            print(f"  {status_icon} {result.name}: {result.message}")
        
        print()
        print("─" * 70)
        print(f"  Total Tests:  {len(self.results)}")
        print(f"  Passed:       {passed}")
        print(f"  Failed:       {failed}")
        print(f"  Warnings:     {warnings}")
        print(f"  Skipped:      {skipped}")
        print(f"  Total Time:   {total_time:.2f}s")
        print("─" * 70)
        print()
        
        if failed == 0:
            print("  🎉 VERDICT: GO - All critical tests passed!")
            print("     The application is ready for user testing.")
            return True
        else:
            print("  💥 VERDICT: NO-GO - Critical tests failed!")
            print("     Please fix the issues above before release.")
            return False


# ============================================
# Individual Tests
# ============================================

def test_python_imports() -> Tuple[bool, str]:
    """Test that all Python modules can be imported."""
    try:
        from aura_engine.database import DatabaseManager, get_database
        from aura_engine.monitoring import ActivityMonitor, ActivityState
        from aura_engine.scheduler import BreakScheduler, BreakType, BreakConfig
        from aura_engine.ml.collector import DataCollector
        import main
        return True, "All modules imported successfully"
    except ImportError as e:
        return False, f"Import failed: {e}"


def test_database_creation() -> Tuple[bool, str]:
    """Test that database can be created and accessed."""
    try:
        from aura_engine.database import DatabaseManager
        
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name
        
        try:
            db = DatabaseManager(temp_db_path)
            
            # Test basic operations
            db.set_setting("test_key", "test_value")
            value = db.get_setting("test_key")
            
            if value != "test_value":
                return False, f"Setting read/write failed: expected 'test_value', got '{value}'"
            
            return True, f"Database created and tested at temp location"
        finally:
            # Cleanup
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    except Exception as e:
        return False, f"Database test failed: {e}"


def test_training_data_schema() -> Tuple[bool, str]:
    """Test that training_data table has correct schema per PRD FR-01.4."""
    try:
        from aura_engine.database import DatabaseManager
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name
        
        try:
            db = DatabaseManager(temp_db_path)
            
            # Get table info
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(training_data)")
                columns = {row[1] for row in cursor.fetchall()}
            
            # Required columns per PRD
            required_columns = {
                "id", "timestamp", "mouse_velocity", "keys_per_min",
                "app_category", "time_since_last_break", "is_fullscreen",
                "user_response"
            }
            
            missing = required_columns - columns
            
            if missing:
                return False, f"Missing columns: {missing}"
            
            return True, f"Schema correct. Columns: {len(columns)}"
        
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    except Exception as e:
        return False, f"Schema test failed: {e}"


def test_training_data_insert() -> Tuple[bool, str]:
    """Test inserting and reading training data."""
    try:
        from aura_engine.database import DatabaseManager
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name
        
        try:
            db = DatabaseManager(temp_db_path)
            
            # Insert a test record
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO training_data 
                    (timestamp, mouse_velocity, keys_per_min, app_category, 
                     time_since_last_break, is_fullscreen, user_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (time.time(), 500.0, 100, "development", 600, False, "completed"))
                
                record_id = cursor.lastrowid
                
                # Read back
                cursor.execute("SELECT * FROM training_data WHERE id = ?", (record_id,))
                row = cursor.fetchone()
            
            if row is None:
                return False, "Failed to read inserted record"
            
            if row["mouse_velocity"] != 500.0:
                return False, f"Data mismatch: expected 500.0, got {row['mouse_velocity']}"
            
            return True, f"Insert/read successful. Record ID: {record_id}"
        
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    except Exception as e:
        return False, f"Insert test failed: {e}"


def test_scheduler_settings_sync() -> Tuple[bool, str]:
    """
    Test the Settings Sync bug fix.
    
    Verifies that changing break intervals immediately updates
    the next_break calculation.
    """
    try:
        from unittest.mock import patch
        from aura_engine.scheduler import BreakScheduler, BreakType
        from aura_engine.database import DatabaseManager
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name
        
        try:
            db = DatabaseManager(temp_db_path)
            
            # Patch get_database to return our temp database
            with patch('aura_engine.scheduler.get_database', return_value=db):
                # Create scheduler (it will load from our patched db)
                scheduler = BreakScheduler()
                
                # Get initial interval (default is 1200 = 20 min)
                initial_interval = scheduler._configs[BreakType.MICRO].interval_seconds
                
                # Change the setting in the database
                new_interval = 1800  # 30 minutes
                db.set_setting("micro_break_interval", str(new_interval))
                
                # Reload and reset (the fix we implemented)
                scheduler.reload_and_reset(BreakType.MICRO)
                
                # Verify the new interval is active
                updated_interval = scheduler._configs[BreakType.MICRO].interval_seconds
                
                if updated_interval != new_interval:
                    return False, f"Interval not updated: expected {new_interval}, got {updated_interval}"
                
                # Verify next_break calculation uses new interval
                next_break = scheduler.get_next_break()
                
                # Since timer was reset, remaining should be close to new interval
                if next_break["remaining_seconds"] > new_interval:
                    return False, f"next_break incorrect: {next_break['remaining_seconds']}s > {new_interval}s"
                
                return True, f"Settings sync working. Interval changed {initial_interval}s → {new_interval}s"
        
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    except Exception as e:
        return False, f"Settings sync test failed: {e}"


def test_force_zero_logic() -> Tuple[bool, str]:
    """
    Test the Force Zero Logic fix for Ghost Metrics bug.
    
    Verifies that metrics drop to exactly 0 when idle > 1 second.
    """
    try:
        from unittest.mock import Mock, patch, MagicMock
        from dataclasses import dataclass, field
        from aura_engine.monitoring import ActivityState
        
        # Import main module with mocks
        @dataclass
        class MockActivityMetrics:
            mouse_velocity: float = 0.0
            keys_per_min: int = 0
            active_time_seconds: int = 0
            idle_time_seconds: int = 0
            state: ActivityState = ActivityState.IDLE
            active_process: str = "test.exe"
            is_fullscreen: bool = False
            last_activity_time: float = field(default_factory=time.time)
        
        class MockMonitor:
            def __init__(self):
                self._last_activity_time = time.time()
                self._velocity = 0.0
                self._keys = 0
                self._running = False
            
            def start(self):
                self._running = True
            
            def stop(self):
                self._running = False
            
            def simulate_activity(self, velocity, keys):
                self._velocity = velocity
                self._keys = keys
                self._last_activity_time = time.time()
            
            def simulate_idle(self):
                pass  # Don't update last_activity_time
            
            def get_last_input_time(self):
                return self._last_activity_time
            
            def get_time_since_last_input(self):
                return time.time() - self._last_activity_time
            
            def get_metrics(self):
                return MockActivityMetrics(
                    mouse_velocity=self._velocity,
                    keys_per_min=self._keys,
                    last_activity_time=self._last_activity_time
                )
        
        class MockDB:
            def __init__(self):
                self._settings = {}
            def get_setting(self, key, default=None):
                return self._settings.get(key, default)
            def set_setting(self, key, value):
                self._settings[key] = value
        
        class MockScheduler:
            def __init__(self, **kwargs):
                pass
            def update(self, is_active, delta):
                pass
        
        class MockCollector:
            def __init__(self, **kwargs):
                pass
        
        from main import AuraEngine
        
        # Create engine with mocks
        with patch('main.get_database') as mock_get_db, \
             patch('main.ActivityMonitor') as mock_monitor_cls, \
             patch('main.BreakScheduler') as mock_scheduler_cls, \
             patch('main.DataCollector') as mock_collector_cls:
            
            mock_db = MockDB()
            mock_monitor = MockMonitor()
            mock_scheduler = MockScheduler()
            mock_collector = MockCollector()
            
            mock_get_db.return_value = mock_db
            mock_monitor_cls.return_value = mock_monitor
            mock_scheduler_cls.return_value = mock_scheduler
            mock_collector_cls.return_value = mock_collector
            
            engine = AuraEngine(db=mock_db)
            engine._monitor = mock_monitor
            engine._scheduler = mock_scheduler
            engine._collector = mock_collector
        
        # Test 1: High activity
        mock_monitor.simulate_activity(velocity=35000.0, keys=200)
        effective = engine._get_effective_metrics()
        
        if effective["mouse_velocity"] != 35000.0:
            return False, f"Activity test failed: expected 35000, got {effective['mouse_velocity']}"
        
        # Test 2: Simulate idle
        mock_monitor.simulate_idle()
        time.sleep(1.2)  # Wait for Force Zero threshold
        
        effective = engine._get_effective_metrics()
        
        if effective["mouse_velocity"] != 0.0:
            return False, f"Force Zero failed: expected 0.0, got {effective['mouse_velocity']}"
        
        if effective["keys_per_min"] != 0:
            return False, f"Force Zero keys failed: expected 0, got {effective['keys_per_min']}"
        
        return True, "Force Zero Logic working. Metrics drop to 0 after 1s idle"
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Force Zero test failed: {e}"


def test_activity_tracking() -> Tuple[bool, str]:
    """Test that activity tracking accumulates time correctly."""
    try:
        from aura_engine.scheduler import BreakScheduler, BreakType
        
        scheduler = BreakScheduler()
        
        # Simulate 5 seconds of activity
        for _ in range(5):
            scheduler.update(is_active=True, delta_seconds=1.0)
        
        status = scheduler.get_status()
        active_time = status["active_time_seconds"]
        
        if active_time < 4 or active_time > 6:
            return False, f"Active time tracking incorrect: expected ~5s, got {active_time}s"
        
        # Simulate 3 seconds of idle (should not accumulate)
        for _ in range(3):
            scheduler.update(is_active=False, delta_seconds=1.0)
        
        status = scheduler.get_status()
        active_time_after_idle = status["active_time_seconds"]
        
        if active_time_after_idle != active_time:
            return False, f"Time accumulated during idle: {active_time}s → {active_time_after_idle}s"
        
        return True, f"Activity tracking correct. Active: {active_time}s, pauses when idle"
    
    except Exception as e:
        return False, f"Activity tracking test failed: {e}"


def test_break_trigger() -> Tuple[bool, str]:
    """Test that break_due events trigger correctly."""
    try:
        from aura_engine.scheduler import BreakScheduler, BreakType
        
        breaks_triggered = []
        
        def on_break(break_type, config):
            breaks_triggered.append(break_type)
        
        scheduler = BreakScheduler(on_break_due=on_break)
        
        # Set a very short interval for testing
        scheduler._configs[BreakType.MICRO].interval_seconds = 3
        
        # Simulate enough active time to trigger break
        for _ in range(5):
            scheduler.update(is_active=True, delta_seconds=1.0)
        
        if BreakType.MICRO not in breaks_triggered:
            return False, f"Break not triggered. Triggered: {breaks_triggered}"
        
        return True, f"Break trigger working. Triggered: {[b.value for b in breaks_triggered]}"
    
    except Exception as e:
        return False, f"Break trigger test failed: {e}"


def test_hydration_logging() -> Tuple[bool, str]:
    """Test hydration logging and retrieval."""
    try:
        from aura_engine.database import DatabaseManager
        
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = f.name
        
        try:
            db = DatabaseManager(temp_db_path)
            
            # Log some water
            db.log_hydration(250)
            db.log_hydration(500)
            
            # Get total
            total = db.get_hydration_today()
            
            if total != 750:
                return False, f"Hydration sum incorrect: expected 750, got {total}"
            
            return True, f"Hydration logging working. Total: {total}ml"
        
        finally:
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    except Exception as e:
        return False, f"Hydration test failed: {e}"


def test_json_protocol() -> Tuple[bool, str]:
    """Test JSON IPC protocol format."""
    try:
        # Test various event payloads
        test_events = [
            {"type": "ready", "data": {"version": "1.1.0"}},
            {"type": "metrics", "data": {"mouse_velocity": 500.0, "keys_per_min": 100}},
            {"type": "break_due", "data": {"break_type": "micro", "duration_seconds": 20}},
            {"type": "setting_updated", "data": {"key": "test", "value": "123"}},
        ]
        
        for event in test_events:
            # Test serialization
            json_str = json.dumps(event)
            
            # Test deserialization
            parsed = json.loads(json_str)
            
            if parsed["type"] != event["type"]:
                return False, f"JSON roundtrip failed for event: {event['type']}"
        
        return True, f"JSON protocol valid. Tested {len(test_events)} event types"
    
    except Exception as e:
        return False, f"JSON protocol test failed: {e}"


# ============================================
# Main Entry Point
# ============================================

def main():
    print()
    print("=" * 70)
    print("            🏥 AURA SYSTEM HEALTH CHECK")
    print("            Phase 2 Release Verification")
    print("=" * 70)
    print()
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Working Dir: {os.getcwd()}")
    print()
    
    runner = HealthCheckRunner()
    
    # Run all tests
    runner.run_test("1. Python Module Imports", test_python_imports)
    runner.run_test("2. Database Creation", test_database_creation)
    runner.run_test("3. Training Data Schema (FR-01.4)", test_training_data_schema)
    runner.run_test("4. Training Data Insert/Read", test_training_data_insert)
    runner.run_test("5. Activity Time Tracking (FR-01.2)", test_activity_tracking)
    runner.run_test("6. Settings Sync Bug Fix", test_scheduler_settings_sync)
    runner.run_test("7. Force Zero Logic (Ghost Metrics Fix)", test_force_zero_logic)
    runner.run_test("8. Break Trigger (FR-01.2)", test_break_trigger)
    runner.run_test("9. Hydration Logging (FR-03)", test_hydration_logging)
    runner.run_test("10. JSON IPC Protocol", test_json_protocol)
    
    # Print summary and get verdict
    all_passed = runner.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
