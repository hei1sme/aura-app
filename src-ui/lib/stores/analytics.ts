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
    goal_ml: number;
}

export const hydrationHistory = writable<DailyHydration[]>([]);

// Update functions
export function updateBreakStats(stats: BreakStats): void {
    breakStats.set(stats);
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
