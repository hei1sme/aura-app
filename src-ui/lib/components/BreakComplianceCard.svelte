<script lang="ts">
    import {
        breakStats,
        breaksToday,
        breakHistory,
        type DailyBreakStats,
        getComplianceRate,
    } from "$lib/stores/analytics";

    // Calculate overall compliance rate from stats (aggregated)
    $: totalStats = (() => {
        let completed = 0;
        let skipped = 0;
        let snoozed = 0;
        let total = 0;

        for (const [key, stats] of Object.entries($breakStats)) {
            if (stats) {
                completed += stats.completed;
                skipped += stats.skipped;
                snoozed += stats.snoozed;
                total += stats.total;
            }
        }

        return { completed, skipped, snoozed, total };
    })();

    $: complianceRate =
        totalStats.total > 0
            ? Math.round((totalStats.completed / totalStats.total) * 100)
            : 100;

    // Today's count
    $: todayCompleted = $breaksToday.filter((b) => b.completed).length;
    $: todaySkipped = $breaksToday.filter((b) => b.skipped).length;
    $: todaySnoozed = $breaksToday.filter((b) => b.snoozed).length;
    $: todayTotal = $breaksToday.length;

    // Helper to format YYYY-MM-DD
    function formatDateKey(date: Date): string {
        return date.toISOString().split("T")[0];
    }

    function getDayLabel(date: Date): string {
        return date.toLocaleDateString("en-US", { weekday: "short" });
    }

    $: chartData = Array.from({ length: 7 }).map((_, i) => {
        const daysAgo = 6 - i;
        const d = new Date();
        d.setDate(d.getDate() - daysAgo);

        const dateKey = formatDateKey(d);
        const label = i === 6 ? "TODAY" : getDayLabel(d);

        // If it's today (last item), use real reactive data from breaksToday store
        // This ensures instant updates when a break is taken/skipped
        if (i === 6) {
            return {
                day: label,
                completed: todayCompleted,
                skipped: todaySkipped,
                snoozed: todaySnoozed,
                total: todayTotal || 1, // Avoid div by zero visual
            };
        }

        // For past days, look up in breakHistory
        const daysStats = $breakHistory[dateKey];

        let completed = 0;
        let skipped = 0;
        let snoozed = 0;
        let total = 0;

        if (daysStats) {
            // Sum up across all break types (micro, macro, hydration) for that day
            for (const stats of Object.values(daysStats)) {
                completed += stats.completed;
                skipped += stats.skipped;
                snoozed += stats.snoozed;
                total += stats.total;
            }
        }

        // Fallback for empty history: effectively 0 height bars
        if (total === 0) total = 0.1; // tiny value to keep layout but show empty

        return {
            day: label,
            completed,
            skipped,
            snoozed,
            total,
        };
    });

    $: maxTotal = Math.max(...chartData.map((d) => d.total), 1);
</script>

<div class="bento-item compliance-card">
    <div class="flex items-center justify-between mb-2">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">📊</span>
            Break Compliance
        </h3>
        <div class="text-right">
            <span
                class="text-2xl font-light"
                class:text-success={complianceRate >= 70}
                class:text-warning={complianceRate >= 40 && complianceRate < 70}
                class:text-error={complianceRate < 40}>{complianceRate}%</span
            >
            <span class="text-xs opacity-50 block -mt-1">Overall Score</span>
        </div>
    </div>

    <!-- 7-Day Bar Chart -->
    <div class="chart-area">
        {#each chartData as d}
            <div class="bar-group">
                <div class="bars">
                    <!-- Completed Bar (Green) -->
                    <div
                        class="bar bar-completed"
                        style="height: {(d.completed / maxTotal) * 100}%"
                        title="{d.completed} Completed"
                    ></div>

                    <!-- Snoozed Bar (Amber - pushed up by completed) -->
                    <div
                        class="bar bar-snoozed"
                        style="height: {(d.snoozed / maxTotal) *
                            100}%; bottom: {(d.completed / maxTotal) * 100}%"
                        title="{d.snoozed} Snoozed"
                    ></div>

                    <!-- Skipped Bar (Red - pushed up by others) -->
                    <div
                        class="bar bar-skipped"
                        style="height: {(d.skipped / maxTotal) *
                            100}%; bottom: {((d.completed + d.snoozed) /
                            maxTotal) *
                            100}%"
                        title="{d.skipped} Skipped"
                    ></div>
                </div>
                <span class="day-label">{d.day}</span>
            </div>
        {/each}
    </div>

    <!-- Legend -->
    <div class="flex items-center justify-center gap-4 mt-3 text-xs opacity-70">
        <div class="flex items-center gap-1">
            <div class="w-2 h-2 rounded-sm bg-success"></div>
            <span>Completed</span>
        </div>
        <div class="flex items-center gap-1">
            <div class="w-2 h-2 rounded-sm bg-warning"></div>
            <span>Snoozed</span>
        </div>
        <div class="flex items-center gap-1">
            <div class="w-2 h-2 rounded-sm bg-error"></div>
            <span>Skipped</span>
        </div>
    </div>
</div>

<style>
    .compliance-card {
        min-height: 220px; /* Slight increase for chart */
        display: flex;
        flex-direction: column;
    }

    .chart-area {
        flex: 1;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 0.5rem;
        padding-top: 1rem;
        padding-bottom: 0.5rem;
        /* Optional rule line */
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        background: rgba(0, 0, 0, 0.15);
        border-radius: 0.5rem;
        padding: 1rem 0.5rem 0.5rem;
        margin-bottom: 0.5rem;
    }

    .bar-group {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        height: 100%;
        justify-content: flex-end;
    }

    .bars {
        width: 100%;
        max-width: 24px;
        height: 100px; /* Max height for bars */
        position: relative;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        overflow: hidden;
    }

    .bar {
        position: absolute;
        width: 100%;
        bottom: 0;
        left: 0;
        transition:
            height 0.3s ease,
            bottom 0.3s ease;
        border-radius: 2px;
    }

    /* Stacked look touches */
    .bar-completed {
        background: linear-gradient(180deg, #14b8a6, #10b981);
        z-index: 10;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
    }
    .bar-snoozed {
        background: linear-gradient(180deg, #f59e0b, #d97706);
        z-index: 9;
        opacity: 0.85;
        box-shadow: 0 0 6px rgba(245, 158, 11, 0.3);
    }
    .bar-skipped {
        background: linear-gradient(180deg, #ef4444, #dc2626);
        z-index: 8;
        opacity: 0.75;
        box-shadow: 0 0 6px rgba(239, 68, 68, 0.3);
    }

    .day-label {
        font-size: 0.65rem;
        opacity: 0.6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
