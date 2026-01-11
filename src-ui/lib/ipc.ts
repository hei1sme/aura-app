/**
 * Aura IPC Bridge - Python Sidecar Communication
 * 
 * This module provides TypeScript interfaces for communicating
 * with the Python sidecar process through Tauri.
 */

import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';

// ===== Types =====

export interface ActivityMetrics {
  mouse_velocity: number;
  keys_per_min: number;
  active_time_seconds: number;
  idle_time_seconds?: number;
  state: 'active' | 'idle' | 'immersive';
  active_process: string;
  is_fullscreen: boolean;
}

export interface BreakInfo {
  type: string;
  remaining_seconds: number;
  duration_seconds: number;
  theme_color: string;
}

export interface BreakStatus {
  interval_seconds: number;
  duration_seconds: number;
  elapsed_seconds: number;
  remaining_seconds: number;
  progress: number;
  theme_color: string;
}

export interface SchedulerStatus {
  session_state: 'idle' | 'active' | 'paused';
  paused: boolean;
  pause_until: number | null;
  active_time_seconds: number;
  pending_break: string | null;
  breaks: {
    micro: BreakStatus;
    macro: BreakStatus;
    hydration: BreakStatus;
  };
}

export interface HydrationStatus {
  total_today_ml: number;
  goal_ml: number;
  progress: number;
}

export interface AuraStatus {
  metrics: ActivityMetrics;
  scheduler: SchedulerStatus;
  next_break: BreakInfo;
  hydration: HydrationStatus;
}

export interface BreakDueEvent {
  break_type: 'micro' | 'macro' | 'hydration';
  duration_seconds: number;
  theme_color: string;
  record_id: number;
}

export interface TrainingStats {
  total_samples: number;
  positive_samples?: number;
  negative_samples?: number;
  positive_rate: number;
  ready_for_training: boolean;
  message: string;
}

export interface SidecarEvent<T = unknown> {
  type: string;
  data?: T;
}

// ===== Commands =====

/**
 * Send a raw command to the Python sidecar
 */
export async function sendToSidecar(command: Record<string, unknown>): Promise<void> {
  return invoke('send_to_sidecar', { command });
}

/**
 * Check if the sidecar is running
 */
export async function isSidecarRunning(): Promise<boolean> {
  return invoke('is_sidecar_running');
}

/**
 * Log water intake
 */
export async function logHydration(amountMl: number): Promise<void> {
  return invoke('log_hydration', { amountMl });
}

/**
 * Mark a break as completed
 */
export async function completeBreak(): Promise<void> {
  return invoke('complete_break');
}

/**
 * Snooze the current break
 */
export async function snoozeBreak(minutes: number = 5): Promise<void> {
  return invoke('snooze_break', { minutes });
}

/**
 * Skip the current break
 */
export async function skipBreak(): Promise<void> {
  return invoke('skip_break');
}

/**
 * Pause all reminders
 */
export async function pauseReminders(minutes?: number): Promise<void> {
  return invoke('pause_reminders', { minutes });
}

/**
 * Resume reminders
 */
export async function resumeReminders(): Promise<void> {
  return invoke('resume_reminders');
}

/**
 * Request full status update
 */
export async function getStatus(): Promise<void> {
  return invoke('get_status');
}

/**
 * Get ML training data statistics
 */
export async function getTrainingStats(): Promise<void> {
  return invoke('get_training_stats');
}

/**
 * Get all settings from the backend
 */
export async function getSettings(): Promise<void> {
  return invoke('get_settings');
}

/**
 * Update a single setting
 */
export async function updateSetting(key: string, value: string): Promise<void> {
  return invoke('update_setting', { key, value });
}

/**
 * Export training data to CSV
 */
export async function exportData(path: string): Promise<void> {
  return invoke('export_data', { path });
}

// ===== SESSION CONTROL =====

/**
 * Start a work session - timers begin counting
 */
export async function startSession(): Promise<void> {
  return invoke('start_session');
}

/**
 * Pause the work session - timers freeze
 */
export async function pauseSession(): Promise<void> {
  return invoke('pause_session');
}

/**
 * Resume a paused work session
 */
export async function resumeSession(): Promise<void> {
  return invoke('resume_session');
}

/**
 * End the work session - resets all timers
 */
export async function endSession(): Promise<void> {
  return invoke('end_session');
}

// ===== SCHEDULE RULES =====

export interface ScheduleRule {
  id: number;
  title: string;      // Optional descriptive title
  time: string;       // "HH:MM" 24-hour format
  action: 'pause' | 'resume' | 'reset' | 'start_session' | 'end_session';
  days: string[];     // ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
  enabled: boolean;
  created_at: number;
}

/**
 * Get all schedule rules
 */
export async function getScheduleRules(): Promise<void> {
  return invoke('get_schedule_rules');
}

/**
 * Add a new schedule rule
 */
export async function addScheduleRule(time: string, action: string, days: string[], title: string = ""): Promise<void> {
  return invoke('add_schedule_rule', { time, action, days, title });
}

/**
 * Update an existing schedule rule
 */
export async function updateScheduleRule(
  id: number,
  time: string,
  action: string,
  days: string[],
  enabled: boolean,
  title: string = ""
): Promise<void> {
  return invoke('update_schedule_rule', { id, time, action, days, enabled, title });
}

/**
 * Delete a schedule rule
 */
export async function deleteScheduleRule(id: number): Promise<void> {
  return invoke('delete_schedule_rule', { id });
}

/**
 * Reset all break timers without changing session state
 */
export async function resetAllTimers(): Promise<void> {
  return invoke('reset_all_timers');
}

/**
 * Show the overlay window (used to manually trigger overlay)
 */
export async function showOverlay(): Promise<void> {
  return invoke('show_overlay');
}

/**
 * Hide the overlay window
 */
export async function hideOverlay(): Promise<void> {
  return invoke('hide_overlay');
}

/**
 * DEV: Trigger a test break - emits the event so overlay window receives it
 */
export async function triggerTestBreak(breakType: string, durationSeconds: number, themeColor: string): Promise<void> {
  return invoke('trigger_test_break', { breakType, durationSeconds, themeColor });
}

/**
 * Get pending break data (called by overlay on mount)
 */
export async function getPendingBreak(): Promise<BreakDueEvent | null> {
  return invoke('get_pending_break');
}

/**
 * Clear pending break data
 */
export async function clearPendingBreak(): Promise<void> {
  return invoke('clear_pending_break');
}

/**
 * Enable autostart (start with Windows)
 */
export async function enableAutostart(): Promise<void> {
  return invoke('enable_autostart');
}

/**
 * Disable autostart
 */
export async function disableAutostart(): Promise<void> {
  return invoke('disable_autostart');
}

/**
 * Check if autostart is enabled
 */
export async function isAutostartEnabled(): Promise<boolean> {
  return invoke('is_autostart_enabled');
}

// ===== Event Listeners =====

type EventCallback<T> = (data: T) => void;

/**
 * Listen to sidecar ready event
 */
export function onReady(callback: EventCallback<{ version: string; db_path: string }>): Promise<UnlistenFn> {
  console.log('[IPC] Setting up sidecar-ready listener');
  return listen('sidecar-ready', (event) => {
    console.log('[IPC] Received sidecar-ready event:', event);
    const sidecarEvent = event.payload as SidecarEvent<{ version: string; db_path: string }>;
    console.log('[IPC] Parsed sidecarEvent:', sidecarEvent);
    if (sidecarEvent.data) {
      callback(sidecarEvent.data);
    } else {
      console.warn('[IPC] sidecarEvent.data is null/undefined');
    }
  });
}

/**
 * Listen to metrics updates
 */
export function onMetrics(callback: EventCallback<ActivityMetrics & { next_break?: BreakInfo }>): Promise<UnlistenFn> {
  console.log('[IPC] Setting up sidecar-metrics listener');
  return listen('sidecar-metrics', (event) => {
    console.log('[IPC] Received sidecar-metrics event:', event.payload);
    const sidecarEvent = event.payload as SidecarEvent<ActivityMetrics & { next_break?: BreakInfo }>;
    if (sidecarEvent.data) {
      callback(sidecarEvent.data);
    }
  });
}

/**
 * Listen to break due events
 */
export function onBreakDue(callback: EventCallback<BreakDueEvent>): Promise<UnlistenFn> {
  return listen('sidecar-break_due', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<BreakDueEvent>;
    if (sidecarEvent.data) {
      callback(sidecarEvent.data);
    }
  });
}

/**
 * Listen to status updates
 */
export function onStatus(callback: EventCallback<AuraStatus>): Promise<UnlistenFn> {
  console.log('[IPC] Setting up sidecar-status listener');
  return listen('sidecar-status', (event) => {
    console.log('[IPC] Received sidecar-status event:', event.payload);
    const sidecarEvent = event.payload as SidecarEvent<AuraStatus>;
    if (sidecarEvent.data) {
      callback(sidecarEvent.data);
    }
  });
}

/**
 * Listen to hydration logged events
 */
export function onHydrationLogged(callback: EventCallback<HydrationStatus & { amount_ml: number }>): Promise<UnlistenFn> {
  return listen('sidecar-hydration_logged', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<HydrationStatus & { amount_ml: number }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to training stats updates
 */
export function onTrainingStats(callback: EventCallback<TrainingStats>): Promise<UnlistenFn> {
  return listen('sidecar-training_stats', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<TrainingStats>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to activity state changes
 */
export function onStateChange(callback: EventCallback<{ state: string }>): Promise<UnlistenFn> {
  return listen('sidecar-state_change', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ state: string }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to break completed events
 */
export function onBreakCompleted(callback: EventCallback<void>): Promise<UnlistenFn> {
  return listen('sidecar-break_completed', () => {
    callback();
  });
}

/**
 * Listen to errors from sidecar
 */
export function onError(callback: EventCallback<{ message: string }>): Promise<UnlistenFn> {
  return listen('sidecar-error', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ message: string }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to settings loaded event
 */
export function onSettings(callback: EventCallback<Record<string, string>>): Promise<UnlistenFn> {
  return listen('sidecar-settings', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<Record<string, string>>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to setting updated event
 */
export function onSettingUpdated(callback: EventCallback<{ key: string; value: string }>): Promise<UnlistenFn> {
  return listen('sidecar-setting_updated', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ key: string; value: string }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to data exported event
 */
export function onDataExported(callback: EventCallback<{ path: string; records: number }>): Promise<UnlistenFn> {
  return listen('sidecar-data_exported', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ path: string; records: number }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to schedule rules updates
 */
export function onScheduleRules(callback: EventCallback<{ rules: ScheduleRule[] }>): Promise<UnlistenFn> {
  return listen('sidecar-schedule_rules', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ rules: ScheduleRule[] }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to schedule rule added event
 */
export function onScheduleRuleAdded(callback: EventCallback<{ id: number; rules: ScheduleRule[] }>): Promise<UnlistenFn> {
  return listen('sidecar-schedule_rule_added', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ id: number; rules: ScheduleRule[] }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to schedule rule updated event
 */
export function onScheduleRuleUpdated(callback: EventCallback<{ id: number; rules: ScheduleRule[] }>): Promise<UnlistenFn> {
  return listen('sidecar-schedule_rule_updated', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ id: number; rules: ScheduleRule[] }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to schedule rule deleted event
 */
export function onScheduleRuleDeleted(callback: EventCallback<{ id: number; rules: ScheduleRule[] }>): Promise<UnlistenFn> {
  return listen('sidecar-schedule_rule_deleted', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ id: number; rules: ScheduleRule[] }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to schedule action executed events (when a rule triggers)
 */
export function onScheduleActionExecuted(callback: EventCallback<{ action: string; time: string; title: string }>): Promise<UnlistenFn> {
  return listen('sidecar-schedule_action_executed', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ action: string; time: string; title: string }>;
    callback(sidecarEvent.data!);
  });
}

/**
 * Listen to schedule warning events (1 minute before rule triggers)
 */
export function onScheduleWarning(callback: EventCallback<{ action: string; time: string; title: string; seconds_remaining: number }>): Promise<UnlistenFn> {
  return listen('sidecar-schedule_warning', (event) => {
    const sidecarEvent = event.payload as SidecarEvent<{ action: string; time: string; title: string; seconds_remaining: number }>;
    callback(sidecarEvent.data!);
  });
}

// ===== Utility Functions =====

/**
 * Format seconds to MM:SS display
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format seconds to human-readable duration
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const mins = Math.floor(seconds / 60);
  if (mins < 60) {
    return `${mins}m`;
  }
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
}

/**
 * Get break type display name
 */
export function getBreakTypeName(type: string): string {
  const names: Record<string, string> = {
    micro: 'Eye Rest',
    macro: 'Stretch Break',
    hydration: 'Hydration'
  };
  return names[type] || type;
}

/**
 * Get break type theme class
 */
export function getBreakThemeClass(type: string): string {
  const themes: Record<string, string> = {
    micro: 'theme-eye-care',
    macro: 'theme-stretch',
    hydration: 'theme-hydration'
  };
  return themes[type] || '';
}
