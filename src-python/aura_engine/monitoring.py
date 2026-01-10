"""
Aura Activity Monitor - Input & Immersive Mode Detection

This module implements FR-01.1, FR-01.2, and FR-01.3:
- Activity Tracking: Mouse movement and keyboard events
- Idle Detection: Pause timer when user is away
- Immersive Detection: Detect fullscreen and blocklisted apps

CRITICAL: No keystroke content logging. Only metadata (frequency, velocity).
"""

import time
import threading
import platform
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Cross-platform imports
try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Platform-specific imports for fullscreen detection
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

if IS_WINDOWS:
    try:
        import ctypes
        from ctypes import wintypes
        CTYPES_AVAILABLE = True
    except ImportError:
        CTYPES_AVAILABLE = False
else:
    CTYPES_AVAILABLE = False


class ActivityState(Enum):
    """User activity state."""
    ACTIVE = "active"
    IDLE = "idle"
    IMMERSIVE = "immersive"  # Fullscreen or blocklisted app


@dataclass
class ActivityMetrics:
    """Current activity metrics snapshot."""
    mouse_velocity: float = 0.0
    keys_per_min: int = 0
    active_time_seconds: int = 0
    idle_time_seconds: int = 0
    state: ActivityState = ActivityState.IDLE
    active_process: str = ""
    is_fullscreen: bool = False
    last_activity_time: float = field(default_factory=time.time)


class ActivityMonitor:
    """
    Monitors user activity through mouse and keyboard events.
    
    Features:
    - Tracks mouse movement velocity
    - Counts keystrokes per minute (no content logging)
    - Detects idle periods (configurable threshold)
    - Detects fullscreen applications
    - Supports process blocklist for immersive mode
    """
    
    # Default blocklist of processes that trigger immersive mode
    DEFAULT_BLOCKLIST = [
        "league_of_legends.exe",
        "leagueclient.exe",
        "valorant.exe",
        "vlc.exe",
        "obs64.exe",
        "zoom.exe",
        "mpc-hc64.exe",
        "potplayer.exe",
    ]
    
    def __init__(
        self,
        idle_threshold: int = 180,  # 3 minutes default
        blocklist: Optional[List[str]] = None,
        on_state_change: Optional[Callable[[ActivityState], None]] = None,
        auto_detect_fullscreen: bool = True  # Whether to detect fullscreen apps
    ):
        """
        Initialize the activity monitor.
        
        Args:
            idle_threshold: Seconds of inactivity before considered idle
            blocklist: List of process names that trigger immersive mode
            on_state_change: Callback when activity state changes
            auto_detect_fullscreen: If False, disables fullscreen detection (prevents timer flickering)
        """
        self.idle_threshold = idle_threshold
        self.blocklist = [p.lower() for p in (blocklist or self.DEFAULT_BLOCKLIST)]
        self.on_state_change = on_state_change
        self.auto_detect_fullscreen = auto_detect_fullscreen
        
        # State tracking
        self._running = False
        self._lock = threading.Lock()
        self._current_state = ActivityState.IDLE
        
        # Activity metrics
        self._last_mouse_pos: Optional[tuple] = None
        self._last_mouse_time: float = time.time()
        self._last_activity_time: float = time.time()
        self._session_start_time: float = time.time()
        
        # Accumulated metrics for velocity/KPM calculation
        self._mouse_distances: List[tuple] = []  # (timestamp, distance)
        self._key_timestamps: List[float] = []
        self._metrics_window = 60  # seconds
        
        # Active time tracking
        self._active_seconds: int = 0
        self._last_active_check: float = time.time()
        
        # Listeners
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        
    def start(self) -> None:
        """Start monitoring user activity."""
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput is required for activity monitoring")
        
        if self._running:
            return
        
        self._running = True
        self._session_start_time = time.time()
        self._last_activity_time = time.time()
        self._last_active_check = time.time()
        
        # Start mouse listener
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self._mouse_listener.start()
        
        # Start keyboard listener (no content logging!)
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        self._keyboard_listener.start()
    
    def stop(self) -> None:
        """Stop monitoring user activity."""
        self._running = False
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
    
    def _record_activity(self) -> None:
        """Record that user activity occurred."""
        now = time.time()
        with self._lock:
            self._last_activity_time = now
            
            # Update active time counter
            time_since_check = now - self._last_active_check
            if time_since_check >= 1.0:  # Update every second
                if self._current_state == ActivityState.ACTIVE:
                    self._active_seconds += int(time_since_check)
                self._last_active_check = now
    
    def _on_mouse_move(self, x: int, y: int) -> None:
        """Handle mouse movement event."""
        if not self._running:
            return
        
        now = time.time()
        is_significant_move = False
        
        with self._lock:
            if self._last_mouse_pos is not None:
                # Calculate distance moved
                last_x, last_y = self._last_mouse_pos
                distance = ((x - last_x) ** 2 + (y - last_y) ** 2) ** 0.5
                
                # Only record significant movements (filters out micro-jitter)
                # CRITICAL: This threshold determines what counts as "real" activity
                if distance > 5:
                    self._mouse_distances.append((now, distance))
                    self._cleanup_old_metrics()
                    is_significant_move = True
            
            self._last_mouse_pos = (x, y)
            self._last_mouse_time = now
        
        # CRITICAL FIX: Only update last_activity_time for SIGNIFICANT movements
        # This prevents micro-jitter from keeping the activity timer "alive"
        if is_significant_move:
            self._record_activity()
    
    def _on_mouse_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        """Handle mouse click event."""
        if pressed:
            self._record_activity()
    
    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Handle mouse scroll event."""
        self._record_activity()
    
    def _on_key_press(self, key: Any) -> None:
        """
        Handle key press event.
        
        IMPORTANT: We only record the timestamp, NOT the key content.
        This is critical for privacy.
        """
        if not self._running:
            return
        
        now = time.time()
        with self._lock:
            self._key_timestamps.append(now)
            self._cleanup_old_metrics()
        
        self._record_activity()
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than the window."""
        cutoff = time.time() - self._metrics_window
        
        self._mouse_distances = [
            (t, d) for t, d in self._mouse_distances if t >= cutoff
        ]
        self._key_timestamps = [
            t for t in self._key_timestamps if t >= cutoff
        ]
    
    def get_mouse_velocity(self) -> float:
        """
        Calculate average mouse velocity in pixels per second.
        
        Returns:
            Average velocity over the metrics window
        """
        with self._lock:
            if not self._mouse_distances:
                return 0.0
            
            total_distance = sum(d for _, d in self._mouse_distances)
            
            if len(self._mouse_distances) < 2:
                return 0.0
            
            time_span = self._mouse_distances[-1][0] - self._mouse_distances[0][0]
            
            if time_span <= 0:
                return 0.0
            
            return total_distance / time_span
    
    def get_instant_velocity(self, window_seconds: float = 1.0) -> float:
        """
        Calculate instantaneous mouse velocity over a short window.
        
        This provides more responsive velocity reading for real-time display.
        Used when we need quick response rather than smoothed average.
        
        Args:
            window_seconds: Time window to consider (default 1.0s)
            
        Returns:
            Velocity in pixels per second over the short window
        """
        with self._lock:
            if not self._mouse_distances:
                return 0.0
            
            now = time.time()
            cutoff = now - window_seconds
            
            # Get only recent movements
            recent = [(t, d) for t, d in self._mouse_distances if t >= cutoff]
            
            if len(recent) < 2:
                return 0.0
            
            total_distance = sum(d for _, d in recent)
            time_span = recent[-1][0] - recent[0][0]
            
            if time_span <= 0:
                return 0.0
            
            return total_distance / time_span
    
    def get_instant_keys(self, window_seconds: float = 5.0) -> int:
        """
        Calculate instantaneous keystrokes per minute over a short window.
        
        This provides more responsive key rate reading for real-time display.
        
        Args:
            window_seconds: Time window to consider (default 5.0s)
            
        Returns:
            Keys per minute (extrapolated from short window)
        """
        with self._lock:
            if not self._key_timestamps:
                return 0
            
            now = time.time()
            cutoff = now - window_seconds
            
            # Count keys in window
            recent_keys = sum(1 for t in self._key_timestamps if t >= cutoff)
            
            # Extrapolate to per-minute rate
            return int(recent_keys * (60.0 / window_seconds))
    
    def clear_stale_data(self, max_age_seconds: float = 1.0) -> None:
        """
        Aggressively clear all data older than max_age_seconds.
        
        This is used by the Force Zero Logic to ensure that when
        the user stops moving, there's no stale data in the buffers
        that would cause "ghost" readings.
        
        Args:
            max_age_seconds: Maximum age of data to keep (default 1s)
        """
        with self._lock:
            now = time.time()
            cutoff = now - max_age_seconds
            
            # Aggressively purge old mouse data
            self._mouse_distances = [
                (t, d) for t, d in self._mouse_distances if t >= cutoff
            ]
            
            # Aggressively purge old key data
            self._key_timestamps = [
                t for t in self._key_timestamps if t >= cutoff
            ]
    
    def get_fresh_metrics(self, idle_threshold: float = 1.0) -> tuple:
        """
        Get metrics with automatic staleness handling.
        
        If user has been idle for > idle_threshold, returns (0.0, 0).
        Otherwise returns (velocity, keys_per_min) from recent data only.
        
        This is the AUTHORITATIVE method for Force Zero Logic.
        
        Args:
            idle_threshold: Seconds of idle before forcing zero
            
        Returns:
            Tuple of (mouse_velocity: float, keys_per_min: int)
        """
        with self._lock:
            now = time.time()
            time_since_input = now - self._last_activity_time
            
            # FORCE ZERO: User is idle
            if time_since_input > idle_threshold:
                # Also clear stale data from buffers
                cutoff = now - idle_threshold
                self._mouse_distances = [
                    (t, d) for t, d in self._mouse_distances if t >= cutoff
                ]
                self._key_timestamps = [
                    t for t in self._key_timestamps if t >= cutoff
                ]
                return (0.0, 0)
            
            # User is active - get fresh metrics only
            cutoff = now - idle_threshold
            
            # Calculate velocity from recent data only
            recent_moves = [(t, d) for t, d in self._mouse_distances if t >= cutoff]
            if len(recent_moves) >= 2:
                total_distance = sum(d for _, d in recent_moves)
                time_span = recent_moves[-1][0] - recent_moves[0][0]
                velocity = total_distance / time_span if time_span > 0 else 0.0
            else:
                velocity = 0.0
            
            # Calculate keys from recent data only
            recent_keys = sum(1 for t in self._key_timestamps if t >= cutoff)
            # Extrapolate to per-minute (from 1-second window)
            keys_per_min = int(recent_keys * 60)
            
            return (velocity, keys_per_min)
    
    def get_keys_per_minute(self) -> int:
        """
        Calculate keystrokes per minute.
        
        Returns:
            Keystrokes per minute (integer)
        """
        with self._lock:
            if not self._key_timestamps:
                return 0
            
            # Count keys in the last minute
            now = time.time()
            minute_ago = now - 60
            recent_keys = sum(1 for t in self._key_timestamps if t >= minute_ago)
            
            return recent_keys
    
    def get_active_process(self) -> str:
        """
        Get the name of the currently active (foreground) process.
        
        Returns:
            Process name or empty string if unavailable
        """
        if not PSUTIL_AVAILABLE:
            return ""
        
        if IS_WINDOWS and CTYPES_AVAILABLE:
            try:
                # Get foreground window
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                
                # Get process ID
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                # Get process name
                process = psutil.Process(pid.value)
                return process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                return ""
        
        elif IS_MACOS:
            try:
                # On macOS, we use a different approach
                import subprocess
                result = subprocess.run(
                    ["osascript", "-e", 
                     'tell application "System Events" to get name of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=1
                )
                return result.stdout.strip() if result.returncode == 0 else ""
            except Exception:
                return ""
        
        return ""
    
    def is_fullscreen(self) -> bool:
        """
        Check if the foreground window is in fullscreen mode.
        
        Returns:
            True if fullscreen, False otherwise
        """
        if IS_WINDOWS and CTYPES_AVAILABLE:
            try:
                user32 = ctypes.windll.user32
                
                # Get foreground window
                hwnd = user32.GetForegroundWindow()
                
                # Get window rect
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                
                # Get screen dimensions
                screen_width = user32.GetSystemMetrics(0)
                screen_height = user32.GetSystemMetrics(1)
                
                # Check if window covers the entire screen
                window_width = rect.right - rect.left
                window_height = rect.bottom - rect.top
                
                # Allow small tolerance for taskbar/borders
                is_fs = (
                    window_width >= screen_width - 10 and
                    window_height >= screen_height - 50
                )
                
                return is_fs
            except Exception:
                return False
        
        elif IS_MACOS:
            try:
                import subprocess
                result = subprocess.run(
                    ["osascript", "-e",
                     'tell application "System Events" to get value of attribute "AXFullScreen" of first window of first process whose frontmost is true'],
                    capture_output=True, text=True, timeout=1
                )
                return result.stdout.strip().lower() == "true"
            except Exception:
                return False
        
        return False
    
    def is_blocklisted_app(self) -> bool:
        """
        Check if the active process is in the blocklist.
        
        Returns:
            True if blocklisted, False otherwise
        """
        process_name = self.get_active_process().lower()
        return process_name in self.blocklist
    
    def is_immersive_mode(self) -> bool:
        """
        Check if immersive mode should be active.
        
        Immersive mode is triggered by:
        - Fullscreen application (only if auto_detect_fullscreen is True)
        - Blocklisted process
        
        NOTE: When auto_detect_fullscreen is False, only blocklisted apps
        trigger immersive mode. This prevents timer flickering with apps
        like Discord, VSCode, Browser that may be detected as fullscreen.
        
        Returns:
            True if in immersive mode, False otherwise
        """
        # Only check fullscreen if auto_detect_fullscreen is enabled
        if self.auto_detect_fullscreen and self.is_fullscreen():
            return True
        return self.is_blocklisted_app()
    
    def is_idle(self) -> bool:
        """
        Check if the user is currently idle.
        
        Returns:
            True if idle time exceeds threshold, False otherwise
        """
        with self._lock:
            idle_time = time.time() - self._last_activity_time
            return idle_time >= self.idle_threshold
    
    def get_idle_time(self) -> float:
        """
        Get current idle time in seconds.
        
        Returns:
            Seconds since last activity
        """
        with self._lock:
            return time.time() - self._last_activity_time
    
    def get_last_input_time(self) -> float:
        """
        Get the timestamp of the last user input event.
        
        This is used by the main loop for Force Zero Logic:
        If (current_time - last_input_time) > threshold, metrics are forced to 0.
        
        Returns:
            Unix timestamp of last mouse/keyboard activity
        """
        with self._lock:
            return self._last_activity_time
    
    def get_time_since_last_input(self) -> float:
        """
        Get seconds elapsed since the last user input.
        
        This is the primary method for Force Zero Logic checks.
        
        Returns:
            Seconds since last mouse/keyboard activity
        """
        with self._lock:
            return time.time() - self._last_activity_time
    
    def get_active_time(self) -> int:
        """
        Get cumulative active time in seconds.
        
        Active time pauses when user is idle.
        
        Returns:
            Total active seconds in current session
        """
        return self._active_seconds
    
    def reset_active_time(self) -> None:
        """Reset the active time counter (e.g., after a break)."""
        self._active_seconds = 0
    
    def update_state(self) -> ActivityState:
        """
        Update and return the current activity state.
        
        States:
        - IMMERSIVE: Fullscreen or blocklisted app (suppress reminders)
        - IDLE: User inactive beyond threshold (pause timer)
        - ACTIVE: User is actively working
        
        Returns:
            Current activity state
        """
        old_state = self._current_state
        
        if self.is_immersive_mode():
            new_state = ActivityState.IMMERSIVE
        elif self.is_idle():
            new_state = ActivityState.IDLE
        else:
            new_state = ActivityState.ACTIVE
        
        self._current_state = new_state
        
        # Trigger callback on state change
        if old_state != new_state and self.on_state_change:
            self.on_state_change(new_state)
        
        return new_state
    
    def get_metrics(self) -> ActivityMetrics:
        """
        Get current activity metrics snapshot.
        
        Returns:
            ActivityMetrics with all current values
        """
        state = self.update_state()
        
        return ActivityMetrics(
            mouse_velocity=self.get_mouse_velocity(),
            keys_per_min=self.get_keys_per_minute(),
            active_time_seconds=self.get_active_time(),
            idle_time_seconds=int(self.get_idle_time()),
            state=state,
            active_process=self.get_active_process(),
            is_fullscreen=self.is_fullscreen(),
            last_activity_time=self._last_activity_time
        )
    
    def set_blocklist(self, processes: List[str]) -> None:
        """Update the process blocklist."""
        self.blocklist = [p.lower() for p in processes]
    
    def add_to_blocklist(self, process: str) -> None:
        """Add a process to the blocklist."""
        process_lower = process.lower()
        if process_lower not in self.blocklist:
            self.blocklist.append(process_lower)
    
    def remove_from_blocklist(self, process: str) -> None:
        """Remove a process from the blocklist."""
        process_lower = process.lower()
        if process_lower in self.blocklist:
            self.blocklist.remove(process_lower)


if __name__ == "__main__":
    # Test the monitor
    import json
    
    def on_state_change(state: ActivityState):
        print(f"State changed to: {state.value}")
    
    monitor = ActivityMonitor(
        idle_threshold=5,  # 5 seconds for testing
        on_state_change=on_state_change
    )
    
    print("Starting activity monitor...")
    print("Move your mouse and type to test. Press Ctrl+C to stop.")
    
    monitor.start()
    
    try:
        while True:
            time.sleep(2)
            metrics = monitor.get_metrics()
            print(json.dumps({
                "mouse_velocity": round(metrics.mouse_velocity, 2),
                "keys_per_min": metrics.keys_per_min,
                "active_seconds": metrics.active_time_seconds,
                "state": metrics.state.value,
                "process": metrics.active_process,
                "fullscreen": metrics.is_fullscreen
            }, indent=2))
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        monitor.stop()
