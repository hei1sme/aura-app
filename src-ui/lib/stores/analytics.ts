/**
 * Analytics Stores - Break stats and history data
 * 
 * These stores hold analytics data fetched from the backend
 * for dashboard visualizations.
 */

import { writable } from 'svelte/store';

// Break statistics for analytics (from get_break_stats)
export interface BreakTypeStats {
    total: number;
    completed: number;
    skipped: number;
    snoozed: number;
}

export interface BreakStats {
    micro?: BreakTypeStats;
    macro?: BreakTypeStats;
    hydration?: BreakTypeStats;
    [key: string]: BreakTypeStats | undefined;
}

export const breakStats = writable<BreakStats>({});

// Daily break history for bar chart (date -> break types -> stats)
export interface DailyBreakStats {
    [breakType: string]: BreakTypeStats;
}

export const breakHistory = writable<Record<string, DailyBreakStats>>({});

// Today's break history (from get_breaks_today)
export interface BreakLog {
    id: number;
    timestamp: number;
    break_type: string;
    duration_seconds: number;
    completed: boolean;
    skipped: boolean;
    snoozed: boolean;
    created_at?: number;
}

export const breaksToday = writable<BreakLog[]>([]);

// Hydration history for trends (last 7 days)
export interface DailyHydration {
    date: string;
    amount_ml: number;
    goal_ml?: number; // Optional, might be inferred from settings
}

export const hydrationHistory = writable<DailyHydration[]>([]);

// Update functions
export function updateBreakStats(stats: BreakStats): void {
    breakStats.set(stats);
}

export function updateBreakHistory(history: Record<string, DailyBreakStats>): void {
    breakHistory.set(history);
}

export function updateBreaksToday(breaks: BreakLog[]): void {
    breaksToday.set(breaks);
}

export function updateHydrationHistory(history: DailyHydration[]): void {
    hydrationHistory.set(history);
}

// Computed helpers
export function getTotalBreaksToday(breaks: BreakLog[]): number {
    return breaks.length;
}

export function getCompletedBreaksToday(breaks: BreakLog[]): number {
    return breaks.filter(b => b.completed).length;
}

export function getSkippedBreaksToday(breaks: BreakLog[]): number {
    return breaks.filter(b => b.skipped).length;
}

export function getComplianceRate(stats: BreakStats): number {
    let total = 0;
    let completed = 0;

    for (const type of Object.values(stats)) {
        if (type) {
            total += type.total;
            completed += type.completed;
        }
    }

    return total > 0 ? Math.round((completed / total) * 100) : 100;
}

// Focus Stats (App Categories)
export type FocusStats = Record<string, number>;
export const focusStats = writable<FocusStats>({});

// Activity Heatmap
export interface ActivityHeatmapInfo {
    date: string;
    hour: number;
    intensity: number;
    details: {
        kpm: number;
        mouse: number;
        samples: number;
    };
}
export const activityHeatmap = writable<ActivityHeatmapInfo[]>([]);

export function updateFocusStats(stats: FocusStats): void {
    focusStats.set(stats);
}

export function updateActivityHeatmap(heatmap: ActivityHeatmapInfo[]): void {
    activityHeatmap.set(heatmap);
}
