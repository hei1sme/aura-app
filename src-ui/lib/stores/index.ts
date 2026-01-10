/**
 * Aura Svelte Stores - Reactive State Management
 * 
 * These stores maintain the application state and sync with
 * the Python sidecar through the IPC bridge.
 */

import { writable, derived, type Readable } from 'svelte/store';
import type {
  ActivityMetrics,
  AuraStatus,
  BreakDueEvent,
  BreakInfo,
  HydrationStatus,
  SchedulerStatus,
  TrainingStats
} from '$lib/ipc';

// ===== Sidecar Connection State =====
export const sidecarConnected = writable<boolean>(false);
export const sidecarVersion = writable<string>('');

// ===== Activity Metrics =====
export const activityMetrics = writable<ActivityMetrics>({
  mouse_velocity: 0,
  keys_per_min: 0,
  active_time_seconds: 0,
  idle_time_seconds: 0,
  state: 'idle',
  active_process: '',
  is_fullscreen: false
});

// ===== Scheduler State =====
export const schedulerStatus = writable<SchedulerStatus | null>(null);
export const nextBreak = writable<BreakInfo | null>(null);
export const isPaused = writable<boolean>(false);
export const pauseUntil = writable<number | null>(null);

// ===== Session State =====
export type SessionState = 'idle' | 'active' | 'paused';
export const sessionState = writable<SessionState>('idle');

// ===== Current Break (when overlay is shown) =====
export const currentBreak = writable<BreakDueEvent | null>(null);
export const breakCountdown = writable<number>(0);

// ===== Hydration State =====
export const hydrationStatus = writable<HydrationStatus>({
  total_today_ml: 0,
  goal_ml: 2000,
  progress: 0
});

// ===== Training Data Stats =====
export const trainingStats = writable<TrainingStats | null>(null);

// ===== Settings =====
export interface AppSettings {
  waterGoal: number;
  microBreakInterval: number;
  macroBreakInterval: number;
  microBreakDuration: number;
  macroBreakDuration: number;
  idleThreshold: number;
  autoStart: boolean;
  theme: 'dark' | 'light';
}

export const settings = writable<AppSettings>({
  waterGoal: 2000,
  microBreakInterval: 1200,
  macroBreakInterval: 2700,
  microBreakDuration: 20,
  macroBreakDuration: 180,
  idleThreshold: 180,
  autoStart: false,
  theme: 'dark'
});

// ===== Derived Stores =====

/**
 * Whether the user is currently active (not idle or immersive)
 */
export const isActive: Readable<boolean> = derived(
  activityMetrics,
  $metrics => $metrics.state === 'active'
);

/**
 * Whether in immersive mode (fullscreen/gaming)
 */
export const isImmersive: Readable<boolean> = derived(
  activityMetrics,
  $metrics => $metrics.state === 'immersive'
);

/**
 * Hydration progress as percentage (0-100)
 */
export const hydrationPercent: Readable<number> = derived(
  hydrationStatus,
  $h => Math.min(100, Math.round($h.progress * 100))
);

/**
 * Time until next break in MM:SS format
 */
export const nextBreakFormatted: Readable<string> = derived(
  nextBreak,
  $break => {
    if (!$break) return '--:--';
    const mins = Math.floor($break.remaining_seconds / 60);
    const secs = $break.remaining_seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
);

/**
 * Active time formatted as HH:MM:SS
 */
export const activeTimeFormatted: Readable<string> = derived(
  activityMetrics,
  $metrics => {
    const totalSecs = $metrics.active_time_seconds;
    const hours = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;

    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
);

// ===== Store Update Functions =====

/**
 * Update stores from a full status update
 */
export function updateFromStatus(status: AuraStatus): void {
  activityMetrics.set(status.metrics);
  schedulerStatus.set(status.scheduler);
  nextBreak.set(status.next_break);
  hydrationStatus.set(status.hydration);

  // Update session state from scheduler
  if (status.scheduler?.session_state) {
    sessionState.set(status.scheduler.session_state as SessionState);
  }
}

/**
 * Update metrics from a metrics event
 */
export function updateMetrics(metrics: ActivityMetrics & { next_break?: BreakInfo }): void {
  activityMetrics.set(metrics);
  if (metrics.next_break) {
    nextBreak.set(metrics.next_break);
  }
}

/**
 * Set current break when break is due
 */
export function setBreakDue(breakEvent: BreakDueEvent): void {
  currentBreak.set(breakEvent);
  breakCountdown.set(breakEvent.duration_seconds);
}

/**
 * Clear current break (after completion/dismiss)
 */
export function clearBreak(): void {
  currentBreak.set(null);
  breakCountdown.set(0);
}

/**
 * Update hydration after logging water
 */
export function updateHydration(status: HydrationStatus): void {
  hydrationStatus.set(status);
}

// ===== Notification State =====
export interface Notification {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  message: string;
  duration?: number;
}

export const notifications = writable<Notification[]>([]);

export function addNotification(notification: Omit<Notification, 'id'>): void {
  const id = Math.random().toString(36).substring(7);
  notifications.update(n => [...n, { ...notification, id }]);

  // Auto-remove after duration
  const duration = notification.duration ?? 3000;
  setTimeout(() => {
    notifications.update(n => n.filter(item => item.id !== id));
  }, duration);
}

export function removeNotification(id: string): void {
  notifications.update(n => n.filter(item => item.id !== id));
}
