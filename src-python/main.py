#!/usr/bin/env python3
"""
Aura Engine - Main Entry Point (Sidecar)

This is the main process that runs as a Tauri sidecar.
It communicates with the Rust/Svelte frontend via JSON over stdout.

Communication Protocol:
- Input: JSON commands from stdin (from Tauri)
- Output: JSON events to stdout (to Tauri)

Event Types (stdout):
- {"type": "ready"} - Engine initialized
- {"type": "metrics", "data": {...}} - Activity metrics update
- {"type": "break_due", "data": {...}} - Break reminder triggered
- {"type": "status", "data": {...}} - Status update
- {"type": "error", "data": {...}} - Error occurred

Command Types (stdin):
- {"cmd": "complete_break"} - User completed break
- {"cmd": "snooze_break", "minutes": 5} - User snoozed break
- {"cmd": "skip_break"} - User skipped break
- {"cmd": "pause", "minutes": 60} - Pause reminders
- {"cmd": "resume"} - Resume reminders
- {"cmd": "log_hydration", "amount_ml": 250} - Log water intake
- {"cmd": "get_status"} - Request full status
- {"cmd": "get_training_stats"} - Get ML data stats
- {"cmd": "export_data", "path": "..."} - Export training data
- {"cmd": "shutdown"} - Graceful shutdown

REFACTORED v1.1.0:
- Switched from time.sleep() to time.perf_counter() for precise timing
- Added Force Zero Logic: metrics explicitly set to 0 when idle > 1s
- Non-blocking loop with busy-wait prevention
"""

import sys
import json
import time
import threading
import signal
from typing import Optional, Dict, Any
from queue import Queue, Empty

# Add parent directory to path for imports
sys.path.insert(0, str(__file__).rsplit("src-python", 1)[0] + "src-python")

from aura_engine.database import get_database, DatabaseManager
from aura_engine.monitoring import ActivityMonitor, ActivityState
from aura_engine.scheduler import BreakScheduler, BreakType, BreakConfig
from aura_engine.ml.collector import DataCollector
from aura_engine.work_schedule import WorkScheduleManager


class AuraEngine:
    """
    Main Aura Engine controller.

    Coordinates all components:
    - Activity monitoring
    - Break scheduling
    - Data collection
    - IPC communication

    REFACTORED v1.3.0:
    - Uses time.perf_counter() for precise delta timing
    - Force Zero Logic via get_fresh_metrics() (authoritative source)
    - Interruptible sleep for clean shutdown (no STATUS_CONTROL_C_EXIT)
    """

    VERSION = "1.4.0"
    TARGET_FRAME_TIME = 0.1  # 100ms tick rate for responsive loop
    METRICS_BROADCAST_INTERVAL = 1.0  # seconds
    IDLE_ZERO_THRESHOLD = 1.0  # Force zero after 1 second of no input
    SHUTDOWN_CHECK_INTERVAL = 0.05  # 50ms granularity for shutdown checks

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Initialize the Aura engine.

        Args:
            db: Optional database manager for testing. Uses singleton if not provided.
        """
        self._running = False
        self._command_queue: Queue = Queue()

        # Initialize database (allow injection for testing)
        self._db = db or get_database()

        # Load settings
        idle_threshold = int(self._db.get_setting("idle_threshold", "180"))
        blocklist_json = self._db.get_setting("blocklist_processes", "[]")
        blocklist = json.loads(blocklist_json)
        auto_detect_fullscreen = (
            self._db.get_setting("auto_detect_fullscreen", "true") == "true"
        )

        # Initialize components
        self._monitor = ActivityMonitor(
            idle_threshold=idle_threshold,
            blocklist=blocklist,
            on_state_change=self._on_activity_state_change,
            auto_detect_fullscreen=auto_detect_fullscreen,
        )

        self._scheduler = BreakScheduler(on_break_due=self._on_break_due)

        # Force reload settings to ensure timer_mode is correctly loaded from DB
        # (scheduler constructor may initialize before DB singleton is ready)
        self._scheduler.reload_settings()

        self._collector = DataCollector(db=self._db)

        # Initialize work schedule manager for time-based automation
        self._work_schedule = WorkScheduleManager(
            scheduler=self._scheduler,
            db=self._db,
            on_action=self._on_schedule_action,
            on_warning=self._on_schedule_warning,
        )

        # Precision timing state (using perf_counter)
        self._last_metrics_broadcast = time.perf_counter()
        self._last_update_time = time.perf_counter()
        self._pending_record_id: Optional[int] = None
        self._pending_log_id: Optional[int] = None

        # Force Zero tracking
        self._last_input_time = time.perf_counter()
        self._forced_zero_velocity: float = 0.0
        self._forced_zero_keys: int = 0

    def _emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit a JSON event to stdout for Tauri to receive.

        Args:
            event_type: Type of event (ready, metrics, break_due, etc.)
            data: Optional event data
        """
        event = {"type": event_type}
        if data is not None:
            event["data"] = data

        # Print JSON to stdout (Tauri reads this)
        print(json.dumps(event), flush=True)

    def _get_effective_metrics(self) -> Dict[str, Any]:
        """
        Get metrics with Force Zero Logic applied.

        CRITICAL FIX for "Ghost Metrics" Bug (v1.2.0):
        Uses get_fresh_metrics() which:
        1. Checks if user is idle > IDLE_ZERO_THRESHOLD
        2. If idle: clears stale data AND returns (0.0, 0)
        3. If active: returns metrics from ONLY the last 1 second

        This GUARANTEES that when user stops moving, the next poll
        returns mouse_velocity=0.0 and keys_per_min=0.

        Returns:
            Dictionary with effective metrics (Force Zero applied)
        """
        raw_metrics = self._monitor.get_metrics()

        # FORCE ZERO via get_fresh_metrics() - the authoritative source
        # This method clears stale data AND returns 0 when idle
        mouse_velocity, keys_per_min = self._monitor.get_fresh_metrics(
            idle_threshold=self.IDLE_ZERO_THRESHOLD
        )

        time_since_input = self._monitor.get_time_since_last_input()

        return {
            "mouse_velocity": round(mouse_velocity, 2),
            "keys_per_min": keys_per_min,
            "active_time_seconds": raw_metrics.active_time_seconds,
            "idle_time_seconds": raw_metrics.idle_time_seconds,
            "state": raw_metrics.state.value,
            "active_process": raw_metrics.active_process,
            "is_fullscreen": raw_metrics.is_fullscreen,
            "time_since_input": round(time_since_input, 2),
            "_raw": raw_metrics,  # Keep raw for internal use
        }

    def _on_activity_state_change(self, state: ActivityState) -> None:
        """Handle activity state changes."""
        self._emit("state_change", {"state": state.value})

    def _on_break_due(self, break_type: BreakType, config: BreakConfig) -> None:
        """
        Handle break due events from scheduler.

        This is where we implement the DATA-FIRST strategy:
        Record activity snapshot before showing break reminder.
        
        NOTE: This is called both for new breaks AND snooze re-triggers.
        We only create a new log entry for the FIRST trigger (when _pending_log_id is None).
        Snooze re-triggers reuse the existing log to prevent duplicate entries.
        """
        metrics = self._monitor.get_metrics()

        # Record training data BEFORE showing break
        # (This is OK to do on every trigger - it's separate from break logs)
        self._pending_record_id = self._collector.record_activity_snapshot(
            mouse_velocity=metrics.mouse_velocity,
            keys_per_min=metrics.keys_per_min,
            active_process=metrics.active_process,
            is_fullscreen=metrics.is_fullscreen,
        )

        # Emit break_due event to frontend
        self._emit(
            "break_due",
            {
                "break_type": break_type.value,
                "duration_seconds": config.duration_seconds,
                "theme_color": config.theme_color,
                "record_id": self._pending_record_id,
            },
        )

        # Only create NEW log entry if this is a fresh break trigger (not a snooze re-trigger)
        # When snooze expires and re-triggers, _pending_log_id is still set from the original trigger
        if self._pending_log_id is None:
            self._pending_log_id = self._db.log_break(
                break_type=break_type.value,
                duration_seconds=config.duration_seconds,
                completed=False,
                skipped=False,
                snoozed=False,
            )

    def _on_schedule_action(self, action: str, time: str, title: str) -> None:
        """Handle work schedule actions (emit event to frontend)."""
        self._emit(
            "schedule_action_executed", {"action": action, "time": time, "title": title}
        )
        # Broadcast updated status so UI reflects changes
        self._broadcast_status()

    def _on_schedule_warning(
        self, action: str, time: str, title: str, seconds: int
    ) -> None:
        """Handle work schedule warnings (1 minute before action)."""
        self._emit(
            "schedule_warning",
            {
                "action": action,
                "time": time,
                "title": title,
                "seconds_remaining": seconds,
            },
        )

    def _handle_command(self, cmd: Dict[str, Any]) -> None:
        """
        Handle a command from the frontend.

        Args:
            cmd: Command dictionary from stdin
        """
        command = cmd.get("cmd", "")

        if command == "complete_break":
            # User completed the break - positive label
            self._scheduler.complete_break()
            if self._pending_record_id:
                self._collector.mark_break_completed(self._pending_record_id)
                self._pending_record_id = None
            
            # Update log status
            if self._pending_log_id:
                self._db.update_break_log(self._pending_log_id, completed=True)
                self._pending_log_id = None
                
            self._emit("break_completed")

        elif command == "snooze_break":
            minutes = cmd.get("minutes", 5)
            self._scheduler.snooze_break(minutes)
            if self._pending_record_id:
                self._collector.mark_break_dismissed(self._pending_record_id)
                self._pending_record_id = None
                
            # Update log status to snoozed
            # IMPORTANT: Do NOT clear _pending_log_id here!
            # When snooze expires and _on_break_due is called again,
            # we need the ID to prevent creating a duplicate log entry.
            if self._pending_log_id:
                self._db.update_break_log(self._pending_log_id, snoozed=True)
                # Keep _pending_log_id set - it will be cleared when user finally
                # completes or skips the break after snooze
                
            self._emit("break_snoozed", {"minutes": minutes})

        elif command == "skip_break":
            self._scheduler.skip_break()
            if self._pending_record_id:
                self._collector.mark_break_dismissed(self._pending_record_id)
                self._pending_record_id = None
                
            # Update log status
            if self._pending_log_id:
                self._db.update_break_log(self._pending_log_id, skipped=True)
                self._pending_log_id = None
                
            self._emit("break_skipped")

        elif command == "pause":
            minutes = cmd.get("minutes")
            self._scheduler.pause(minutes)
            self._emit("paused", {"minutes": minutes})

        elif command == "resume":
            self._scheduler.resume()
            self._emit("resumed")

        elif command == "log_hydration":
            amount_ml = cmd.get("amount_ml", 250)
            self._db.log_hydration(amount_ml)
            total_today = self._db.get_hydration_today()
            goal = int(self._db.get_setting("water_goal", "2000"))
            self._emit(
                "hydration_logged",
                {
                    "amount_ml": amount_ml,
                    "total_today_ml": total_today,
                    "goal_ml": goal,
                    "progress": min(1.0, total_today / goal),
                },
            )

        elif command == "get_status":
            self._broadcast_status()

        elif command == "get_metrics":
            effective = self._get_effective_metrics()
            self._emit(
                "metrics",
                {
                    "mouse_velocity": effective["mouse_velocity"],
                    "keys_per_min": effective["keys_per_min"],
                    "active_time_seconds": effective["active_time_seconds"],
                    "idle_time_seconds": effective["idle_time_seconds"],
                    "state": effective["state"],
                    "active_process": effective["active_process"],
                    "is_fullscreen": effective["is_fullscreen"],
                },
            )

        elif command == "get_training_stats":
            stats = self._collector.get_training_stats()
            self._emit("training_stats", stats)

        elif command == "export_data":
            path = cmd.get("path", "aura_training_data.csv")
            count = self._collector.export_dataset(path)
            self._emit("data_exported", {"path": path, "records": count})

        elif command == "get_hydration":
            total = self._db.get_hydration_today()
            goal = int(self._db.get_setting("water_goal", "2000"))
            self._emit(
                "hydration_status",
                {
                    "total_today_ml": total,
                    "goal_ml": goal,
                    "progress": min(1.0, total / goal),
                },
            )

        elif command == "update_setting":
            key = cmd.get("key")
            value = cmd.get("value")
            if key and value is not None:
                self._db.set_setting(key, str(value))
                self._emit("setting_updated", {"key": key, "value": value})

                # Reload scheduler settings if break-related setting changed
                # Use atomic reload_and_reset() to ensure consistency
                if key in ["micro_break_interval", "micro_break_duration"]:
                    self._scheduler.reload_and_reset(BreakType.MICRO)
                    self._broadcast_status()
                elif key in ["macro_break_interval", "macro_break_duration"]:
                    self._scheduler.reload_and_reset(BreakType.MACRO)
                    self._broadcast_status()
                elif key == "hydration_interval":
                    self._scheduler.reload_and_reset(BreakType.HYDRATION)
                    self._broadcast_status()
                elif key == "timer_mode":
                    # Reload timer mode setting
                    self._scheduler.reload_settings()
                    self._broadcast_status()
                elif key == "auto_detect_fullscreen":
                    # Update monitor's fullscreen detection setting
                    self._monitor.auto_detect_fullscreen = value == "true"
                    import sys

                    print(
                        f"[Engine] auto_detect_fullscreen set to: {self._monitor.auto_detect_fullscreen}",
                        file=sys.stderr,
                        flush=True,
                    )
                elif key == "blocklist_processes":
                    # Update monitor's blocklist
                    try:
                        blocklist = json.loads(value)
                        self._monitor.set_blocklist(blocklist)
                    except json.JSONDecodeError:
                        pass

        elif command == "get_settings":
            settings = self._db.get_all_settings()
            self._emit("settings", settings)

        # ===== SESSION CONTROL COMMANDS =====
        elif command == "start_session":
            self._scheduler.start_session()
            self._emit("session_started")
            self._broadcast_status()

        elif command == "pause_session":
            self._scheduler.pause_session()
            self._emit("session_paused")
            self._broadcast_status()

        elif command == "resume_session":
            self._scheduler.resume_session()
            self._emit("session_resumed")
            self._broadcast_status()

        elif command == "end_session":
            self._scheduler.end_session()
            self._emit("session_ended")
            self._broadcast_status()

        elif command == "get_session_state":
            state = self._scheduler.get_session_state()
            self._emit("session_state", {"state": state})

        # ===== SCHEDULE RULES COMMANDS =====
        elif command == "get_schedule_rules":
            rules = self._work_schedule.get_rules()
            self._emit("schedule_rules", {"rules": rules})

        elif command == "add_schedule_rule":
            time_str = cmd.get("time")
            action = cmd.get("action")
            days = cmd.get("days", [])
            title = cmd.get("title", "")
            if time_str and action:
                rule_id = self._work_schedule.add_rule(time_str, action, days, title)
                rules = self._work_schedule.get_rules()
                self._emit("schedule_rule_added", {"id": rule_id, "rules": rules})

        elif command == "update_schedule_rule":
            rule_id = cmd.get("id")
            time_str = cmd.get("time")
            action = cmd.get("action")
            days = cmd.get("days", [])
            enabled = cmd.get("enabled", True)
            title = cmd.get("title", "")
            if rule_id is not None and time_str and action:
                self._work_schedule.update_rule(
                    rule_id, time_str, action, days, enabled, title
                )
                rules = self._work_schedule.get_rules()
                self._emit("schedule_rule_updated", {"id": rule_id, "rules": rules})

        elif command == "delete_schedule_rule":
            rule_id = cmd.get("id")
            if rule_id is not None:
                self._work_schedule.delete_rule(rule_id)
                rules = self._work_schedule.get_rules()
                self._emit("schedule_rule_deleted", {"id": rule_id, "rules": rules})

        elif command == "reset_all_timers":
            self._scheduler.reset_all_timers()
            self._emit("timers_reset")
            self._broadcast_status()

        # ===== ANALYTICS COMMANDS =====
        elif command == "get_break_stats":
            days = cmd.get("days", 7)
            stats = self._db.get_break_stats(days)
            self._emit("break_stats", stats)

        elif command == "get_breaks_today":
            breaks = self._db.get_breaks_today()
            self._emit("breaks_today", breaks)

        elif command == "get_break_history":
            days = cmd.get("days", 7)
            history = self._db.get_break_history(days)
            self._emit("break_history", history)

        elif command == "get_hydration_history":
            days = cmd.get("days", 7)
            history = self._db.get_hydration_history(days)
            self._emit("hydration_history", history)

        elif command == "get_focus_stats":
            days = cmd.get("days", 7)
            stats = self._db.get_focus_stats(days)
            self._emit("focus_stats", stats)

        elif command == "get_activity_heatmap":
            days = cmd.get("days", 7)
            heatmap = self._db.get_activity_heatmap(days)
            self._emit("activity_heatmap", heatmap)

        elif command == "shutdown":
            self._running = False
            self._emit("shutdown_ack")

        else:
            self._emit("error", {"message": f"Unknown command: {command}"})

    def _broadcast_status(self) -> None:
        """Broadcast full status to frontend with Force Zero applied."""
        effective = self._get_effective_metrics()
        scheduler_status = self._scheduler.get_status()
        next_break = self._scheduler.get_next_break()
        hydration_today = self._db.get_hydration_today()
        water_goal = int(self._db.get_setting("water_goal", "2000"))

        self._emit(
            "status",
            {
                "metrics": {
                    "mouse_velocity": effective["mouse_velocity"],
                    "keys_per_min": effective["keys_per_min"],
                    "active_time_seconds": effective["active_time_seconds"],
                    "state": effective["state"],
                    "active_process": effective["active_process"],
                    "is_fullscreen": effective["is_fullscreen"],
                },
                "scheduler": scheduler_status,
                "next_break": next_break,
                "hydration": {
                    "total_today_ml": hydration_today,
                    "goal_ml": water_goal,
                    "progress": min(1.0, hydration_today / water_goal),
                },
            },
        )

    def _broadcast_metrics(self) -> None:
        """Periodically broadcast metrics to frontend with Force Zero applied."""
        now = time.perf_counter()

        if now - self._last_metrics_broadcast >= self.METRICS_BROADCAST_INTERVAL:
            effective = self._get_effective_metrics()
            next_break = self._scheduler.get_next_break()

            self._emit(
                "metrics",
                {
                    "mouse_velocity": effective["mouse_velocity"],
                    "keys_per_min": effective["keys_per_min"],
                    "active_time_seconds": effective["active_time_seconds"],
                    "state": effective["state"],
                    "next_break": next_break,
                },
            )

            self._last_metrics_broadcast = now

    def _input_reader(self) -> None:
        """
        Read commands from stdin in a separate thread.

        Tauri sends JSON commands through stdin.
        """
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    continue

                line = line.strip()
                if not line:
                    continue

                try:
                    cmd = json.loads(line)
                    self._command_queue.put(cmd)
                except json.JSONDecodeError:
                    self._emit("error", {"message": f"Invalid JSON: {line}"})

            except Exception as e:
                if self._running:
                    self._emit("error", {"message": f"Input error: {str(e)}"})

    def run(self) -> None:
        """
        Main run loop.

        This is the heart of the Aura engine.

        REFACTORED v1.2.0:
        - Uses time.perf_counter() for precise delta timing
        - Interruptible sleep via _sleep_interruptible() for clean shutdown
        - Force Zero Logic applied via get_fresh_metrics()
        """
        self._running = True

        # Start activity monitoring
        self._monitor.start()

        # Start work schedule manager for time-based automation
        self._work_schedule.start()

        # Start input reader thread
        input_thread = threading.Thread(target=self._input_reader, daemon=True)
        input_thread.start()

        # Emit ready event
        self._emit("ready", {"version": self.VERSION, "db_path": self._db.db_path})

        # Broadcast initial status
        self._broadcast_status()

        # Initialize precision timing
        self._last_update_time = time.perf_counter()
        frame_accumulator = 0.0

        try:
            while self._running:
                # PRECISION TIMING: Use perf_counter for accurate delta
                now = time.perf_counter()
                delta = now - self._last_update_time
                self._last_update_time = now
                frame_accumulator += delta

                # Process any pending commands (non-blocking)
                try:
                    while True:
                        cmd = self._command_queue.get_nowait()
                        self._handle_command(cmd)
                except Empty:
                    pass

                # Only update scheduler every ~1 second (accumulated)
                if frame_accumulator >= 1.0:
                    # Get effective metrics (with Force Zero applied)
                    effective = self._get_effective_metrics()
                    raw_metrics = effective["_raw"]

                    # Determine if user has REAL activity (keyboard/mouse input)
                    # This is independent of immersive/fullscreen state!
                    # - If user is typing in Discord (fullscreen), that's still ACTIVE work
                    # - Only consider IDLE if there's no input for idle_threshold seconds
                    has_real_activity = raw_metrics.state != ActivityState.IDLE

                    # For active-time mode: count time if user has any activity
                    # (including activity during fullscreen apps like Discord)
                    is_active = has_real_activity
                    is_immersive = raw_metrics.state == ActivityState.IMMERSIVE

                    # Update scheduler with immersive state info
                    # - is_active: True if user has keyboard/mouse activity (even in fullscreen)
                    # - is_immersive: True if fullscreen (suppresses break popups only)
                    self._scheduler.update(
                        is_active, frame_accumulator, is_immersive=is_immersive
                    )

                    # Reset accumulator
                    frame_accumulator = 0.0

                # Broadcast metrics periodically (uses its own timer)
                self._broadcast_metrics()

                # INTERRUPTIBLE SLEEP: Check _running flag frequently
                # This allows clean shutdown without STATUS_CONTROL_C_EXIT
                elapsed = time.perf_counter() - now
                remaining_sleep = max(0.01, self.TARGET_FRAME_TIME - elapsed)
                self._sleep_interruptible(remaining_sleep)

        except KeyboardInterrupt:
            pass

        finally:
            self._running = False
            self._work_schedule.stop()
            self._monitor.stop()
            self._emit("shutdown")

    def _sleep_interruptible(self, duration: float) -> None:
        """
        Sleep for duration, but check _running flag every SHUTDOWN_CHECK_INTERVAL.

        This prevents the STATUS_CONTROL_C_EXIT crash by allowing the loop
        to exit cleanly when shutdown is requested, rather than being stuck
        in a long sleep.

        Args:
            duration: Total time to sleep in seconds
        """
        elapsed = 0.0
        while elapsed < duration and self._running:
            sleep_chunk = min(self.SHUTDOWN_CHECK_INTERVAL, duration - elapsed)
            time.sleep(sleep_chunk)
            elapsed += sleep_chunk

    def shutdown(self) -> None:
        """
        Gracefully shutdown the engine.

        This sets _running=False which will be detected by _sleep_interruptible()
        within 50ms, allowing clean exit.
        """
        self._running = False


def main():
    """Entry point for the Aura sidecar."""
    engine = None

    # Handle SIGTERM and SIGINT gracefully
    def signal_handler(signum, frame):
        if engine:
            engine.shutdown()
        # Give a moment for shutdown to complete
        time.sleep(0.1)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        engine = AuraEngine()
        engine.run()
    except Exception as e:
        # Emit error as JSON so Tauri can handle it
        error_event = {"type": "fatal_error", "data": {"message": str(e)}}
        print(json.dumps(error_event), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
