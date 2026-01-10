#!/usr/bin/env python3
"""
Aura Engine Loop Test Script
=============================

This script tests the refactored AuraEngine to verify:
1. Metrics are non-zero during simulated activity
2. Force Zero Logic: Metrics drop to EXACTLY 0 when idle > 1 second
3. New monitoring methods: get_last_input_time(), get_time_since_last_input()

This is a HEADLESS test that doesn't require the GUI.

CRITICAL BUG BEING TESTED:
"When I move the mouse vigorously for 5s (Velocity ~38000) and then STOP 
completely for 5s, the metric does NOT drop to 0. It slowly decays to ~12000."

EXPECTED BEHAVIOR AFTER FIX:
If the user stops for > 1.0 second, metrics MUST be EXACTLY 0.

Usage:
    python scripts/test_engine_loop.py

Expected Output:
    PASSED - if Force Zero Logic works correctly
    FAILED - if ghost metrics persist after idle period
"""

import sys
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field

# Add src-python to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src-python"))

from aura_engine.monitoring import ActivityState


# ============================================
# Mock Classes for Headless Testing
# ============================================

@dataclass
class MockActivityMetrics:
    """Simulated activity metrics."""
    mouse_velocity: float = 0.0
    keys_per_min: int = 0
    active_time_seconds: int = 0
    idle_time_seconds: int = 0
    state: ActivityState = ActivityState.IDLE
    active_process: str = "test.exe"
    is_fullscreen: bool = False
    last_activity_time: float = field(default_factory=time.time)


class MockActivityMonitor:
    """
    Mock activity monitor that can simulate activity and idle states.
    
    Includes the new methods:
    - get_last_input_time()
    - get_time_since_last_input()
    """
    def __init__(self, **kwargs):
        self.idle_threshold = kwargs.get("idle_threshold", 180)
        self.blocklist = kwargs.get("blocklist", [])
        self.on_state_change = kwargs.get("on_state_change", None)
        
        self._running = False
        self._simulated_velocity = 0.0
        self._simulated_keys = 0
        self._last_activity_time = time.time()
        self._state = ActivityState.IDLE
    
    def start(self):
        self._running = True
        self._last_activity_time = time.time()
    
    def stop(self):
        self._running = False
    
    def simulate_activity(self, velocity: float, keys: int):
        """Simulate user activity with given metrics."""
        self._simulated_velocity = velocity
        self._simulated_keys = keys
        self._last_activity_time = time.time()  # Update last input time
        self._state = ActivityState.ACTIVE
        if self.on_state_change:
            self.on_state_change(self._state)
    
    def simulate_idle(self):
        """
        Simulate user going idle (no activity).
        
        CRITICAL: Do NOT update _last_activity_time.
        This simulates the user stopping all input.
        """
        # Keep velocity/keys at old values to simulate sliding window
        # The Force Zero Logic should override these
        self._state = ActivityState.IDLE
        if self.on_state_change:
            self.on_state_change(self._state)
    
    def get_last_input_time(self) -> float:
        """Return timestamp of last activity."""
        return self._last_activity_time
    
    def get_time_since_last_input(self) -> float:
        """Return seconds since last activity."""
        return time.time() - self._last_activity_time
    
    def get_metrics(self) -> MockActivityMetrics:
        """
        Return current simulated metrics.
        
        NOTE: This returns the RAW metrics from the sliding window.
        The Force Zero Logic in main.py should override these when idle.
        """
        return MockActivityMetrics(
            # These values simulate "ghost metrics" from sliding window
            mouse_velocity=self._simulated_velocity,
            keys_per_min=self._simulated_keys,
            active_time_seconds=10,
            idle_time_seconds=int(time.time() - self._last_activity_time),
            state=self._state,
            active_process="test.exe",
            is_fullscreen=False,
            last_activity_time=self._last_activity_time
        )


class MockDatabase:
    """Mock database for testing."""
    def __init__(self):
        self.db_path = ":memory:"
        self._settings = {
            "idle_threshold": "180",
            "blocklist_processes": "[]",
            "water_goal": "2000"
        }
    
    def get_setting(self, key: str, default: str = None) -> str:
        return self._settings.get(key, default)
    
    def set_setting(self, key: str, value: str):
        self._settings[key] = value
    
    def get_all_settings(self):
        return self._settings.copy()
    
    def get_hydration_today(self) -> int:
        return 500
    
    def log_break(self, **kwargs):
        pass
    
    def log_hydration(self, amount_ml: int):
        pass


class MockScheduler:
    """Mock scheduler for testing."""
    def __init__(self, **kwargs):
        self.on_break_due = kwargs.get("on_break_due", None)
    
    def update(self, is_active: bool, delta: float):
        pass
    
    def get_status(self):
        return {"paused": False, "active_time_seconds": 0}
    
    def get_next_break(self):
        return {"type": "micro", "remaining_seconds": 600}
    
    def reload_settings(self):
        pass


class MockDataCollector:
    """Mock data collector for testing."""
    def __init__(self, **kwargs):
        pass
    
    def record_activity_snapshot(self, **kwargs):
        return 1
    
    def mark_break_completed(self, record_id):
        pass
    
    def mark_break_dismissed(self, record_id):
        pass
    
    def get_training_stats(self):
        return {"total_samples": 0}


# ============================================
# Test Harness
# ============================================

class EngineTestHarness:
    """
    Test harness that runs AuraEngine with mocked dependencies.
    """
    
    def __init__(self):
        self.captured_events = []
        self.mock_monitor = MockActivityMonitor()
        self.mock_db = MockDatabase()
        self.mock_scheduler = MockScheduler()
        self.mock_collector = MockDataCollector()
    
    def capture_emit(self, event_type: str, data=None):
        """Capture emitted events for assertion."""
        self.captured_events.append({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })
    
    def get_last_metrics(self):
        """Get the last emitted metrics event."""
        for event in reversed(self.captured_events):
            if event["type"] == "metrics":
                return event["data"]
        return None
    
    def run_test(self) -> bool:
        """
        Run the Force Zero Logic test.
        
        This test verifies the critical bug fix:
        "If I stop the mouse for 1.1 seconds, the Dashboard MUST show exactly 0"
        
        Returns:
            True if test PASSED, False if FAILED
        """
        print("=" * 70)
        print("AURA ENGINE FORCE ZERO LOGIC TEST")
        print("=" * 70)
        print()
        print("BUG BEING TESTED:")
        print("  'When mouse velocity is ~38000 and user STOPS, the metric should")
        print("   drop to EXACTLY 0, not slowly decay to ~12000.'")
        print()
        
        # Import and patch AuraEngine
        from main import AuraEngine
        
        # Create engine with mocks
        with patch('main.get_database', return_value=self.mock_db), \
             patch('main.ActivityMonitor', return_value=self.mock_monitor), \
             patch('main.BreakScheduler', return_value=self.mock_scheduler), \
             patch('main.DataCollector', return_value=self.mock_collector):
            
            engine = AuraEngine(db=self.mock_db)
            engine._monitor = self.mock_monitor
            engine._scheduler = self.mock_scheduler
            engine._collector = self.mock_collector
            engine._emit = self.capture_emit
        
        # ============================================
        # TEST PHASE 1: Simulate HIGH Activity
        # ============================================
        print("-" * 70)
        print("[PHASE 1] Simulating HIGH USER ACTIVITY (like the bug report)")
        print("-" * 70)
        print("  • Setting mouse_velocity=38000.0 (vigorous movement)")
        print("  • Setting keys_per_min=200")
        
        # Simulate high activity (matches bug report)
        self.mock_monitor.simulate_activity(velocity=38000.0, keys=200)
        
        # Run engine's metrics getter
        effective = engine._get_effective_metrics()
        
        print(f"  • Effective mouse_velocity: {effective['mouse_velocity']}")
        print(f"  • Effective keys_per_min: {effective['keys_per_min']}")
        print(f"  • time_since_input: {effective.get('time_since_input', 'N/A')}s")
        
        phase1_passed = (
            effective["mouse_velocity"] == 38000.0 and
            effective["keys_per_min"] == 200
        )
        
        if phase1_passed:
            print("  ✅ PHASE 1 PASSED: High metrics correctly reported")
        else:
            print("  ❌ PHASE 1 FAILED: Metrics should match simulated values")
            return False
        
        print()
        
        # ============================================
        # TEST PHASE 2: Simulate STOP (Force Zero)
        # ============================================
        print("-" * 70)
        print("[PHASE 2] Simulating USER STOPS (Force Zero Logic)")
        print("-" * 70)
        print("  • User has STOPPED all input")
        print("  • Sliding window still has old high-velocity data (38000)")
        print("  • EXPECTED: Force Zero should override to 0")
        
        # Simulate idle - don't update activity time
        self.mock_monitor.simulate_idle()
        
        # Wait > IDLE_ZERO_THRESHOLD (1.0s)
        print("  • Waiting 1.5 seconds for Force Zero Logic to trigger...")
        time.sleep(1.5)
        
        # Now get metrics - Force Zero should apply
        effective = engine._get_effective_metrics()
        
        print(f"  • time_since_input: {effective.get('time_since_input', 'N/A')}s")
        print(f"  • RAW velocity in sliding window: 38000 (still there!)")
        print(f"  • Effective mouse_velocity: {effective['mouse_velocity']}")
        print(f"  • Effective keys_per_min: {effective['keys_per_min']}")
        
        phase2_passed = (
            effective["mouse_velocity"] == 0.0 and
            effective["keys_per_min"] == 0
        )
        
        if phase2_passed:
            print("  ✅ PHASE 2 PASSED: Force Zero correctly applied!")
            print("     Dashboard will show 0 (not decaying 12000)")
        else:
            print("  ❌ PHASE 2 FAILED: GHOST METRICS DETECTED!")
            print(f"     Expected: velocity=0.0, keys=0")
            print(f"     Got: velocity={effective['mouse_velocity']}, keys={effective['keys_per_min']}")
            print("     BUG NOT FIXED - sliding window values are leaking through")
            return False
        
        print()
        
        # ============================================
        # TEST PHASE 3: Resume Activity
        # ============================================
        print("-" * 70)
        print("[PHASE 3] Resuming ACTIVITY after idle period")
        print("-" * 70)
        print("  • Setting mouse_velocity=500.0")
        print("  • Setting keys_per_min=100")
        
        self.mock_monitor.simulate_activity(velocity=500.0, keys=100)
        
        effective = engine._get_effective_metrics()
        
        print(f"  • Effective mouse_velocity: {effective['mouse_velocity']}")
        print(f"  • Effective keys_per_min: {effective['keys_per_min']}")
        print(f"  • time_since_input: {effective.get('time_since_input', 'N/A')}s")
        
        phase3_passed = (
            effective["mouse_velocity"] == 500.0 and
            effective["keys_per_min"] == 100
        )
        
        if phase3_passed:
            print("  ✅ PHASE 3 PASSED: Metrics correctly resume after new activity")
        else:
            print("  ❌ PHASE 3 FAILED: Metrics should recover after new activity")
            return False
        
        print()
        
        # ============================================
        # TEST PHASE 4: Quick Stop Test (Edge Case)
        # ============================================
        print("-" * 70)
        print("[PHASE 4] Edge Case: Stop for EXACTLY 1.1 seconds")
        print("-" * 70)
        print("  • Verifying threshold boundary (IDLE_ZERO_THRESHOLD = 1.0s)")
        
        self.mock_monitor.simulate_activity(velocity=1000.0, keys=50)
        self.mock_monitor.simulate_idle()
        
        # Wait just over threshold
        print("  • Waiting 1.1 seconds (just over threshold)...")
        time.sleep(1.1)
        
        effective = engine._get_effective_metrics()
        
        print(f"  • time_since_input: {effective.get('time_since_input', 'N/A')}s")
        print(f"  • Effective mouse_velocity: {effective['mouse_velocity']}")
        
        phase4_passed = effective["mouse_velocity"] == 0.0
        
        if phase4_passed:
            print("  ✅ PHASE 4 PASSED: Threshold boundary works correctly")
        else:
            print("  ❌ PHASE 4 FAILED: Metrics should be 0 at 1.1s idle")
            return False
        
        print()
        
        return True


# ============================================
# Main Entry Point
# ============================================

def main():
    print()
    harness = EngineTestHarness()
    
    try:
        result = harness.run_test()
    except Exception as e:
        print(f"❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        result = False
    
    print("=" * 70)
    if result:
        print("🎉 ALL TESTS PASSED")
        print()
        print("Force Zero Logic is working correctly!")
        print("  • Ghost metrics will no longer appear after idle periods")
        print("  • If you stop for >1 second, Dashboard shows EXACTLY 0")
        print("  • No more slow decay from 38000 -> 12000 -> 5000")
    else:
        print("💥 TEST FAILED")
        print()
        print("Force Zero Logic is NOT working as expected.")
        print("Review the _get_effective_metrics() implementation in main.py")
    print("=" * 70)
    print()
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
