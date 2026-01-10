"""
Aura Break Scheduler - Rule-Based Break Logic

This module implements FR-01.2 (Dynamic Timer Logic):
- Reminders based on cumulative active time
- Timer pauses when user is idle
- Different break types (micro, macro, hydration)
"""

import math
import time
import json
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from threading import Lock

from .database import get_database


class BreakType(Enum):
    """Types of breaks supported by Aura."""
    MICRO = "micro"      # Eye rest - every ~20 mins, 20 seconds
    MACRO = "macro"      # Stretch break - every ~45-60 mins, 2-3 mins
    HYDRATION = "hydration"  # Water reminder - periodic


class SessionState(Enum):
    """Work session states for the Session Hub."""
    IDLE = "idle"        # Not tracking, waiting to start
    ACTIVE = "active"    # Session running, timers counting
    PAUSED = "paused"    # Session paused (lunch break, etc.)


@dataclass
class BreakConfig:
    """Configuration for a break type."""
    break_type: BreakType
    interval_seconds: int  # Time between breaks
    duration_seconds: int  # How long the break lasts
    theme_color: str       # UI theme color


class BreakScheduler:
    """
    Manages break scheduling based on user activity.
    
    The scheduler tracks cumulative active time and triggers
    break reminders when thresholds are reached.
    """
    
    # Default break configurations
    DEFAULT_CONFIGS = {
        BreakType.MICRO: BreakConfig(
            break_type=BreakType.MICRO,
            interval_seconds=1200,  # 20 minutes
            duration_seconds=20,    # 20 seconds
            theme_color="#10B981"   # Emerald
        ),
        BreakType.MACRO: BreakConfig(
            break_type=BreakType.MACRO,
            interval_seconds=2700,  # 45 minutes
            duration_seconds=180,   # 3 minutes
            theme_color="#F59E0B"   # Amber/Orange
        ),
        BreakType.HYDRATION: BreakConfig(
            break_type=BreakType.HYDRATION,
            interval_seconds=1800,  # 30 minutes
            duration_seconds=0,     # No timer, just a nudge
            theme_color="#3B82F6"   # Blue
        ),
    }
    
    def __init__(
        self,
        on_break_due: Optional[Callable[[BreakType, BreakConfig], None]] = None
    ):
        """
        Initialize the break scheduler.
        
        Args:
            on_break_due: Callback when a break is due
        """
        self.on_break_due = on_break_due
        self._lock = Lock()
        
        # Load configurations from database or use defaults
        self._configs = dict(self.DEFAULT_CONFIGS)
        self._load_settings()
        
        # Track time since last break for each type
        self._last_break_time: Dict[BreakType, float] = {
            bt: time.time() for bt in BreakType
        }
        
        # Track cumulative active time
        self._active_time_seconds = 0
        self._last_update_time = time.time()
        
        # Pause state
        self._paused = False
        self._pause_until: Optional[float] = None
        
        # Pending break (waiting for user response)
        self._pending_break: Optional[BreakType] = None
        
        # Timer mode: 'active' (only counts active time) or 'wall-clock' (counts real time)
        self._timer_mode = 'active'
        self._load_timer_mode()
        
        # Track ACTIVE seconds since last break (cumulative, pauses when idle)
        self._active_seconds_since_break: Dict[BreakType, float] = {
            bt: 0 for bt in BreakType
        }
        
        # Session state: controls whether timers run
        # Starts in IDLE - user must explicitly start session
        self._session_state = SessionState.IDLE
        self._load_session_state()
    
    def _load_settings(self) -> None:
        """Load break settings from database."""
        try:
            db = get_database()
            
            # Load micro break interval
            micro_interval = db.get_setting("micro_break_interval")
            if micro_interval:
                self._configs[BreakType.MICRO].interval_seconds = int(micro_interval)
            
            micro_duration = db.get_setting("micro_break_duration")
            if micro_duration:
                self._configs[BreakType.MICRO].duration_seconds = int(micro_duration)
            
            # Load macro break interval
            macro_interval = db.get_setting("macro_break_interval")
            if macro_interval:
                self._configs[BreakType.MACRO].interval_seconds = int(macro_interval)
            
            macro_duration = db.get_setting("macro_break_duration")
            if macro_duration:
                self._configs[BreakType.MACRO].duration_seconds = int(macro_duration)
            
            # Load hydration interval
            hydration_interval = db.get_setting("hydration_interval")
            if hydration_interval:
                self._configs[BreakType.HYDRATION].interval_seconds = int(hydration_interval)
        except Exception:
            # Use defaults if database not available
            pass
    
    def _load_timer_mode(self) -> None:
        """Load timer mode setting from database."""
        try:
            db = get_database()
            timer_mode = db.get_setting("timer_mode")
            if timer_mode and timer_mode in ('active', 'wall-clock'):
                self._timer_mode = timer_mode
        except Exception:
            pass  # Keep default timer mode
    
    def _load_session_state(self) -> None:
        """Load session state from database (for persistence across restarts)."""
        try:
            db = get_database()
            session_state = db.get_setting("session_state")
            if session_state and session_state in ('idle', 'active', 'paused'):
                self._session_state = SessionState(session_state)
        except Exception:
            pass  # Keep default IDLE state
    
    def _save_session_state(self) -> None:
        """Persist session state to database."""
        try:
            db = get_database()
            db.set_setting("session_state", self._session_state.value)
        except Exception:
            pass
    
    def reload_settings(self) -> None:
        """
        Reload settings from database (call after settings change).
        
        This method reloads all break interval/duration settings from the
        database. Call this whenever a break-related setting is modified
        to ensure the scheduler uses the latest values.
        """
        with self._lock:
            # Store old values for comparison (debugging)
            old_micro = self._configs[BreakType.MICRO].interval_seconds
            old_macro = self._configs[BreakType.MACRO].interval_seconds
            old_hydration = self._configs[BreakType.HYDRATION].interval_seconds
            old_timer_mode = self._timer_mode
            
            # Reload from database
            self._load_settings()
            self._load_timer_mode()
            
            # Log if values changed (helps with debugging)
            new_micro = self._configs[BreakType.MICRO].interval_seconds
            new_macro = self._configs[BreakType.MACRO].interval_seconds
            new_hydration = self._configs[BreakType.HYDRATION].interval_seconds
            
            if old_micro != new_micro or old_macro != new_macro or old_hydration != new_hydration:
                import sys
                print(f"[Scheduler] Settings reloaded: micro={new_micro}s, macro={new_macro}s, hydration={new_hydration}s", 
                      file=sys.stderr, flush=True)
            
            if old_timer_mode != self._timer_mode:
                import sys
                print(f"[Scheduler] Timer mode changed: {old_timer_mode} -> {self._timer_mode}", 
                      file=sys.stderr, flush=True)
    
    def reload_and_reset(self, break_type: BreakType) -> None:
        """
        Atomically reload settings and SMARTLY recalculate the timer.
        
        SMART RECALCULATION (not dumb reset):
        - If user worked 15 min and changes interval from 20→40 min:
          - Old remaining was 5 min
          - New remaining = 40 - 15 = 25 min (NOT reset to 40!)
        - The active time accumulated is preserved
        - Only the interval target changes
        
        This provides intuitive UX: if you've worked 15 min and change
        the interval, you don't "lose" that 15 min of progress.
        
        Args:
            break_type: The break type whose interval changed
        """
        with self._lock:
            # Get current active time BEFORE reloading
            current_active_time = self._active_seconds_since_break[break_type]
            old_interval = self._configs[break_type].interval_seconds
            
            # Reload all settings from database
            self._load_settings()
            
            new_interval = self._configs[break_type].interval_seconds
            
            # SMART RECALCULATION:
            # Keep the accumulated active time, just apply new interval
            # If active_time > new_interval, a break will be triggered on next update
            # (which is the correct behavior)
            
            # Calculate new remaining time for logging
            new_remaining = max(0, new_interval - current_active_time)
            
            import sys
            print(f"[Scheduler] SMART RECALC: {break_type.value}", file=sys.stderr, flush=True)
            print(f"  Old interval: {old_interval}s ({old_interval // 60}min)", file=sys.stderr, flush=True)
            print(f"  New interval: {new_interval}s ({new_interval // 60}min)", file=sys.stderr, flush=True)
            print(f"  Active time:  {int(current_active_time)}s ({int(current_active_time) // 60}min)", file=sys.stderr, flush=True)
            print(f"  New remaining: {int(new_remaining)}s ({int(new_remaining) // 60}min)", file=sys.stderr, flush=True)
    
    def reload_and_hard_reset(self, break_type: BreakType) -> None:
        """
        Atomically reload settings AND hard-reset the timer to 0.
        
        Use this only when you want to completely restart the timer,
        e.g., after completing a break. For interval changes, use
        reload_and_reset() which preserves accumulated active time.
        
        Args:
            break_type: The break type whose timer should be hard reset
        """
        with self._lock:
            # Reload all settings
            self._load_settings()
            
            # Hard reset the specific break timer
            self._active_seconds_since_break[break_type] = 0
            self._last_break_time[break_type] = time.time()
            
            import sys
            new_interval = self._configs[break_type].interval_seconds
            print(f"[Scheduler] {break_type.value} HARD RESET. Interval: {new_interval}s ({new_interval // 60}min)", 
                  file=sys.stderr, flush=True)
    
    def reset_break_timer(self, break_type: BreakType) -> None:
        """Reset the timer for a specific break type (starts countdown from now)."""
        with self._lock:
            self._active_seconds_since_break[break_type] = 0
            self._last_break_time[break_type] = time.time()
    
    def update(self, is_active: bool, delta_seconds: float, is_immersive: bool = False) -> Optional[BreakType]:
        """
        Update the scheduler with current activity state.
        
        Args:
            is_active: Whether the user is currently active
            delta_seconds: Time since last update
            is_immersive: Whether user is in fullscreen/immersive mode
            
        Returns:
            BreakType if a break is due, None otherwise
        """
        with self._lock:
            # Check if paused (legacy pause for timed pauses)
            if self._is_paused():
                return None
            
            # SESSION STATE CHECK: Only run timers when session is ACTIVE
            # IDLE = waiting to start, PAUSED = user took a break
            if self._session_state != SessionState.ACTIVE:
                return None  # All timers frozen until session is active
            
            # IMPORTANT: If a break is pending (waiting for user response),
            # pause ALL timers. This prevents a cascade of breaks piling up
            # if the user is away from the computer.
            if self._pending_break is not None:
                return None  # All timers frozen until user handles pending break
            
            # Timer mode determines when to accumulate time:
            # - 'active': Only count when user is active (idle = pause)
            # - 'wall-clock': ALWAYS count real time (NEVER pause, even when idle/immersive)
            # 
            # CRITICAL: Wall-clock mode must count continuously, regardless of:
            # - Activity state (active/idle)
            # - Immersive mode (fullscreen apps)
            # This is the defining feature of wall-clock vs active-time mode.
            
            if self._timer_mode == 'wall-clock':
                # Wall-clock: unconditionally accumulate time
                should_accumulate = True
            else:
                # Active-time: only accumulate when user has activity
                should_accumulate = is_active
            
            if should_accumulate:
                self._active_time_seconds += delta_seconds
                # Also accumulate for each break type
                for bt in BreakType:
                    self._active_seconds_since_break[bt] += delta_seconds
            
            # IMMERSIVE MODE HANDLING:
            # - Wall-clock mode: NEVER suppress breaks (timer runs AND breaks trigger)
            # - Active-time mode: Suppress break popups during immersive mode
            #
            # The user chose Wall Clock mode specifically because they want
            # consistent break reminders regardless of what app they're using.
            if is_immersive and self._timer_mode != 'wall-clock':
                return None
            
            due_break = self._check_breaks_due()
            
            if due_break is not None:
                self._pending_break = due_break
                if self.on_break_due:
                    self.on_break_due(due_break, self._configs[due_break])
            
            return due_break
    
    def _is_paused(self) -> bool:
        """Check if scheduler is paused."""
        if not self._paused:
            return False
        
        if self._pause_until is not None and time.time() >= self._pause_until:
            self._paused = False
            self._pause_until = None
            return False
        
        return True
    
    def _check_breaks_due(self) -> Optional[BreakType]:
        """
        Check if any break is due based on CUMULATIVE ACTIVE TIME.
        
        Per PRD FR-01.2: Reminders trigger based on cumulative active time,
        not wall-clock time. Timer pauses when user is idle.
        
        Priority: MACRO > MICRO > HYDRATION
        """
        # Check macro break first (higher priority)
        if self._active_seconds_since_break[BreakType.MACRO] >= self._configs[BreakType.MACRO].interval_seconds:
            return BreakType.MACRO
        
        # Check micro break
        if self._active_seconds_since_break[BreakType.MICRO] >= self._configs[BreakType.MICRO].interval_seconds:
            return BreakType.MICRO
        
        # Check hydration
        if self._active_seconds_since_break[BreakType.HYDRATION] >= self._configs[BreakType.HYDRATION].interval_seconds:
            return BreakType.HYDRATION
        
        return None
    
    def complete_break(self, break_type: Optional[BreakType] = None) -> None:
        """
        Mark a break as completed.
        
        This resets the active time counter for the break type.
        
        Args:
            break_type: The type of break completed. Uses pending if not specified.
        """
        bt = break_type or self._pending_break
        
        if bt is None:
            return
        
        with self._lock:
            # Reset active time counter for this break type
            self._active_seconds_since_break[bt] = 0
            self._last_break_time[bt] = time.time()
            
            # Macro break also resets micro break timer
            if bt == BreakType.MACRO:
                self._active_seconds_since_break[BreakType.MICRO] = 0
                self._last_break_time[BreakType.MICRO] = time.time()
            
            # Reset overall active time counter
            self._active_time_seconds = 0
            
            self._pending_break = None
    
    def snooze_break(self, minutes: int = 5) -> None:
        """
        Snooze the current pending break.
        
        Args:
            minutes: How long to snooze (default 5 minutes)
        """
        with self._lock:
            if self._pending_break is not None:
                # Subtract snooze time from accumulated active seconds
                # This effectively delays the next break by snooze duration of ACTIVE time
                snooze_seconds = minutes * 60
                self._active_seconds_since_break[self._pending_break] = max(
                    0, 
                    self._configs[self._pending_break].interval_seconds - snooze_seconds
                )
            
            self._pending_break = None
    
    def skip_break(self) -> None:
        """Skip the current pending break and reset timer to wait for next full interval."""
        with self._lock:
            if self._pending_break is not None:
                # Reset timer to 0 - user will wait a full interval for the next break
                # This is the same as complete_break() but without the positive ML label
                self._active_seconds_since_break[self._pending_break] = 0
                self._last_break_time[self._pending_break] = time.time()
            self._pending_break = None
    
    def pause(self, minutes: Optional[int] = None) -> None:
        """
        Pause all break reminders.
        
        Args:
            minutes: Optional duration. If None, pause indefinitely.
        """
        with self._lock:
            self._paused = True
            if minutes is not None:
                self._pause_until = time.time() + (minutes * 60)
            else:
                self._pause_until = None
    
    def resume(self) -> None:
        """Resume break reminders."""
        with self._lock:
            self._paused = False
            self._pause_until = None
    
    # ===== SESSION CONTROL METHODS =====
    
    def start_session(self) -> None:
        """
        Start a work session. Timers begin counting.
        
        Transitions: IDLE -> ACTIVE, PAUSED -> ACTIVE
        """
        with self._lock:
            if self._session_state == SessionState.IDLE:
                # Fresh start - reset all timers
                for bt in BreakType:
                    self._active_seconds_since_break[bt] = 0
                    self._last_break_time[bt] = time.time()
                self._active_time_seconds = 0
            # If resuming from PAUSED, timers continue from where they were
            self._session_state = SessionState.ACTIVE
            self._save_session_state()
            
            # import sys
            # print("[Scheduler] Session started - timers running", file=sys.stderr, flush=True)
    
    def pause_session(self) -> None:
        """
        Pause the work session. Timers freeze, can resume later.
        
        Use for: lunch break, meeting, short away time
        Transitions: ACTIVE -> PAUSED
        """
        with self._lock:
            if self._session_state == SessionState.ACTIVE:
                self._session_state = SessionState.PAUSED
                self._save_session_state()
                
                import sys
                # print("[Scheduler] Session paused - timers frozen", file=sys.stderr, flush=True)
    
    def resume_session(self) -> None:
        """
        Resume a paused work session. Timers continue from where they left off.
        
        Transitions: PAUSED -> ACTIVE
        """
        with self._lock:
            if self._session_state == SessionState.PAUSED:
                self._session_state = SessionState.ACTIVE
                self._save_session_state()
                
                import sys
                print("[Scheduler] Session resumed - timers running", file=sys.stderr, flush=True)
    
    def end_session(self) -> None:
        """
        End the work session. Resets all timers to 0.
        
        Use for: end of workday, long break, switching tasks
        Transitions: ACTIVE -> IDLE, PAUSED -> IDLE
        """
        with self._lock:
            # Reset all timers
            for bt in BreakType:
                self._active_seconds_since_break[bt] = 0
                self._last_break_time[bt] = time.time()
            self._active_time_seconds = 0
            self._pending_break = None
            
            self._session_state = SessionState.IDLE
            self._save_session_state()
            
            import sys
            print("[Scheduler] Session ended - all timers reset", file=sys.stderr, flush=True)
    
    def get_session_state(self) -> str:
        """Get the current session state as a string."""
        return self._session_state.value
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status.
        
        Returns:
            Dictionary with scheduler state
        """
        with self._lock:
            status = {
                "session_state": self._session_state.value,
                "paused": self._is_paused(),
                "pause_until": self._pause_until,
                "active_time_seconds": int(self._active_time_seconds),
                "pending_break": self._pending_break.value if self._pending_break else None,
                "breaks": {}
            }
            
            for bt, config in self._configs.items():
                active_elapsed = self._active_seconds_since_break[bt]
                # Use floor() for remaining to ensure monotonic decrement (no oscillation)
                # e.g., 1180.9 -> 1180, 1180.1 -> 1180, 1179.9 -> 1179 (always decreasing)
                remaining = max(0, config.interval_seconds - active_elapsed)
                
                status["breaks"][bt.value] = {
                    "interval_seconds": config.interval_seconds,
                    "duration_seconds": config.duration_seconds,
                    "elapsed_seconds": int(active_elapsed),
                    "remaining_seconds": math.floor(remaining),
                    "progress": min(1.0, active_elapsed / config.interval_seconds),
                    "theme_color": config.theme_color
                }
            
            return status
    
    def get_next_break(self) -> Dict[str, Any]:
        """
        Get information about the next upcoming break based on cumulative active time.
        
        Returns:
            Dictionary with next break info
        """
        with self._lock:
            next_break = None
            min_remaining = float('inf')
            
            for bt, config in self._configs.items():
                active_elapsed = self._active_seconds_since_break[bt]
                remaining = config.interval_seconds - active_elapsed
                
                if remaining < min_remaining:
                    min_remaining = remaining
                    next_break = bt
            
            if next_break is None:
                return {"type": None, "remaining_seconds": 0, "timer_mode": self._timer_mode}
            
            # Use floor() for remaining to ensure monotonic decrement (no oscillation)
            return {
                "type": next_break.value,
                "remaining_seconds": math.floor(max(0, min_remaining)),
                "duration_seconds": self._configs[next_break].duration_seconds,
                "theme_color": self._configs[next_break].theme_color,
                "timer_mode": self._timer_mode
            }
    
    def update_config(self, break_type: BreakType, interval: Optional[int] = None, 
                      duration: Optional[int] = None) -> None:
        """
        Update break configuration.
        
        Args:
            break_type: The break type to update
            interval: New interval in seconds
            duration: New duration in seconds
        """
        with self._lock:
            if interval is not None:
                self._configs[break_type].interval_seconds = interval
            if duration is not None:
                self._configs[break_type].duration_seconds = duration
        
        # Persist to database
        try:
            db = get_database()
            if break_type == BreakType.MICRO:
                if interval is not None:
                    db.set_setting("micro_break_interval", str(interval))
                if duration is not None:
                    db.set_setting("micro_break_duration", str(duration))
            elif break_type == BreakType.MACRO:
                if interval is not None:
                    db.set_setting("macro_break_interval", str(interval))
                if duration is not None:
                    db.set_setting("macro_break_duration", str(duration))
        except Exception:
            pass


if __name__ == "__main__":
    # Test the scheduler
    def on_break_due(break_type: BreakType, config: BreakConfig):
        print(f"\n🔔 BREAK DUE: {break_type.value}")
        print(f"   Duration: {config.duration_seconds}s")
        print(f"   Theme: {config.theme_color}")
    
    scheduler = BreakScheduler(on_break_due=on_break_due)
    
    # Override intervals for testing
    scheduler.update_config(BreakType.MICRO, interval=10, duration=5)
    scheduler.update_config(BreakType.HYDRATION, interval=15)
    
    print("Testing scheduler... (Ctrl+C to stop)")
    print("Simulating active user...")
    
    last_time = time.time()
    
    try:
        while True:
            time.sleep(1)
            
            now = time.time()
            delta = now - last_time
            last_time = now
            
            # Simulate active user
            result = scheduler.update(is_active=True, delta_seconds=delta)
            
            if result:
                print(f"\n   Simulating 'Complete' action...")
                time.sleep(2)
                scheduler.complete_break()
            
            status = scheduler.get_status()
            next_break = scheduler.get_next_break()
            
            print(f"\rNext: {next_break['type']} in {next_break['remaining_seconds']}s | "
                  f"Active: {status['active_time_seconds']}s", end="", flush=True)
    
    except KeyboardInterrupt:
        print("\nDone.")
