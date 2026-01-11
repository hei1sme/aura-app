"""
Work Schedule Manager - Time-Based Automation

This module implements automatic pause/resume/reset of break timers
based on user-defined schedule rules. For example:
- Pause at 12:00 for lunch
- Resume at 13:00 after lunch
- Reset timers after long breaks

The manager runs on a background thread and checks rules every minute.
"""

import sys
import time
import threading
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable

from .database import DatabaseManager, get_database
from .scheduler import BreakScheduler


# Day abbreviations used in schedule rules
DAY_ABBREVS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class WorkScheduleManager:
    """
    Manages automatic execution of schedule rules.

    Runs on a separate thread, checks every minute if any
    rules should trigger based on current time and day.
    """

    def __init__(
        self,
        scheduler: BreakScheduler,
        db: Optional[DatabaseManager] = None,
        on_action: Optional[Callable[[str, str, str], None]] = None,
        on_warning: Optional[Callable[[str, str, int], None]] = None,
    ):
        """
        Initialize the work schedule manager.

        Args:
            scheduler: The break scheduler to control
            db: Optional database manager (uses singleton if not provided)
            on_action: Callback when action executed (action, time, title)
            on_warning: Callback for 1-minute warning (action, time, title, seconds_remaining)
        """
        self._scheduler = scheduler
        self._db = db or get_database()
        self._on_action = on_action
        self._on_warning = on_warning

        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Track executed rules to prevent double-execution in same minute
        # Key: rule_id, Value: last execution time (minute precision)
        self._last_executed: Dict[int, str] = {}

        # Track warned rules to prevent duplicate warnings
        self._last_warned: Dict[int, str] = {}

        # Cache of rules (reloaded when needed)
        self._rules: List[Dict[str, Any]] = []
        self._rules_dirty = True  # Set to True to force reload

    def start(self) -> None:
        """Start the schedule manager background thread."""
        if self._running:
            return

        self._running = True
        self._rules_dirty = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[WorkSchedule] Started", file=sys.stderr, flush=True)

    def stop(self) -> None:
        """Stop the schedule manager."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        print("[WorkSchedule] Stopped", file=sys.stderr, flush=True)

    def reload_rules(self) -> None:
        """Mark rules for reload (called after rules are modified)."""
        self._rules_dirty = True

    def _run_loop(self) -> None:
        """Main loop - checks rules every minute."""
        last_check_minute = ""

        while self._running:
            now = datetime.now()
            current_minute = now.strftime("%H:%M")

            # Only check once per minute
            if current_minute != last_check_minute:
                last_check_minute = current_minute
                self._check_and_execute(now)

            # Sleep for a short interval to allow shutdown
            time.sleep(5)  # Check every 5 seconds for responsiveness

    def _check_and_execute(self, now: datetime) -> None:
        """Check all rules and execute matching ones, also check for 1-minute warnings."""
        # Reload rules if marked dirty
        if self._rules_dirty:
            try:
                self._rules = self._db.get_enabled_schedule_rules()
                self._rules_dirty = False
            except Exception as e:
                print(
                    f"[WorkSchedule] Failed to load rules: {e}",
                    file=sys.stderr,
                    flush=True,
                )
                return

        current_time = now.strftime("%H:%M")
        current_day = DAY_ABBREVS[now.weekday()]  # 0=Monday -> "mon"

        # Calculate next minute for warnings
        next_minute = (now.minute + 1) % 60
        next_hour = now.hour if next_minute > 0 else (now.hour + 1) % 24
        next_time = f"{next_hour:02d}:{next_minute:02d}"

        for rule in self._rules:
            rule_id = rule["id"]
            rule_time = rule["time"]
            rule_days = rule["days"]
            rule_action = rule["action"]
            rule_title = rule.get("title", "")

            # Skip if not for today
            if current_day not in rule_days:
                continue

            # Check for 1-minute warning
            if rule_time == next_time and self._on_warning:
                warn_key = f"{rule_id}:{next_time}"
                if self._last_warned.get(rule_id) != warn_key:
                    display_title = (
                        rule_title or f"{rule_action.title()} at {rule_time}"
                    )
                    self._on_warning(rule_action, rule_time, display_title, 60)
                    self._last_warned[rule_id] = warn_key
                    print(
                        f"[WorkSchedule] Warning: {display_title} in 1 min",
                        file=sys.stderr,
                        flush=True,
                    )

            # Check if rule matches current time
            if rule_time != current_time:
                continue

            # Check if already executed this minute
            execution_key = f"{rule_id}:{current_time}"
            if self._last_executed.get(rule_id) == execution_key:
                continue

            # Execute the action
            self._execute_action(rule_action)
            self._last_executed[rule_id] = execution_key

            display_title = rule_title or f"{rule_action.title()} at {current_time}"
            print(
                f"[WorkSchedule] Executed: {display_title}", file=sys.stderr, flush=True
            )

            if self._on_action:
                self._on_action(rule_action, current_time, rule_title)

    def _execute_action(self, action: str) -> None:
        """Execute a schedule action on the scheduler."""
        if action == "pause":
            self._scheduler.pause_session()
        elif action == "resume":
            self._scheduler.resume_session()
        elif action == "reset":
            self._scheduler.reset_all_timers()
        elif action == "start_session":
            self._scheduler.start_session()
        elif action == "end_session":
            self._scheduler.end_session()
        else:
            print(
                f"[WorkSchedule] Unknown action: {action}", file=sys.stderr, flush=True
            )

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all schedule rules (for IPC)."""
        return self._db.get_schedule_rules()

    def add_rule(self, time: str, action: str, days: List[str], title: str = "") -> int:
        """Add a new schedule rule."""
        rule_id = self._db.add_schedule_rule(time, action, days, title)
        self._rules_dirty = True
        return rule_id

    def update_rule(
        self,
        rule_id: int,
        time: str,
        action: str,
        days: List[str],
        enabled: bool,
        title: str = "",
    ) -> None:
        """Update an existing schedule rule."""
        self._db.update_schedule_rule(rule_id, time, action, days, enabled, title)
        self._rules_dirty = True

    def delete_rule(self, rule_id: int) -> None:
        """Delete a schedule rule."""
        self._db.delete_schedule_rule(rule_id)
        self._rules_dirty = True
        # Clear from last_executed cache
        if rule_id in self._last_executed:
            del self._last_executed[rule_id]


if __name__ == "__main__":
    # Test the work schedule manager
    print("Testing WorkScheduleManager...")

    from .scheduler import BreakScheduler

    scheduler = BreakScheduler()
    manager = WorkScheduleManager(
        scheduler, on_action=lambda action, time: print(f"ACTION: {action} at {time}")
    )

    # Add test rule for current minute + 1
    now = datetime.now()
    test_time = f"{now.hour:02d}:{(now.minute + 1) % 60:02d}"
    test_day = DAY_ABBREVS[now.weekday()]

    print(f"Adding test rule: pause at {test_time} on {test_day}")
    rule_id = manager.add_rule(test_time, "pause", [test_day])
    print(f"Added rule ID: {rule_id}")

    print("Starting manager...")
    manager.start()

    try:
        print("Waiting 2 minutes for rule to trigger...")
        time.sleep(120)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        manager.delete_rule(rule_id)
        print("Test complete.")
