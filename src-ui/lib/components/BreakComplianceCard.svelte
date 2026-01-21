<!--
  BreakComplianceCard.svelte - Break Compliance Analytics
  
  Visualizes break completion rates with donut chart and stats
-->
<script lang="ts">
    import {
        breakStats,
        breaksToday,
        getComplianceRate,
    } from "$lib/stores/analytics";

    // Calculate totals across all break types
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

    $: completedPercent =
        totalStats.total > 0
            ? Math.round((totalStats.completed / totalStats.total) * 100)
            : 0;
    $: skippedPercent =
        totalStats.total > 0
            ? Math.round((totalStats.skipped / totalStats.total) * 100)
            : 0;
    $: snoozedPercent =
        totalStats.total > 0
            ? Math.round((totalStats.snoozed / totalStats.total) * 100)
            : 0;

    // SVG donut chart calculations
    const size = 120;
    const strokeWidth = 12;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;

    $: completedDash = (completedPercent / 100) * circumference;
    $: skippedDash = (skippedPercent / 100) * circumference;
    $: snoozedDash = (snoozedPercent / 100) * circumference;

    $: completedOffset = 0;
    $: skippedOffset = -completedDash;
    $: snoozedOffset = -(completedDash + skippedDash);

    // Today's count
    $: todayCompleted = $breaksToday.filter((b) => b.completed).length;
    $: todayTotal = $breaksToday.length;
</script>

<div class="bento-item compliance-card">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">📊</span>
            Break Compliance
        </h3>
        <span class="text-xs opacity-50">Last 7 days</span>
    </div>

    <div class="flex items-center gap-6">
        <!-- Donut Chart -->
        <div class="chart-container">
            <svg width={size} height={size} class="donut-chart">
                <!-- Background circle -->
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    fill="none"
                    stroke="rgba(255,255,255,0.1)"
                    stroke-width={strokeWidth}
                />

                <!-- Completed segment (green) -->
                {#if completedPercent > 0}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="var(--aura-eye-care)"
                        stroke-width={strokeWidth}
                        stroke-dasharray="{completedDash} {circumference}"
                        stroke-dashoffset={completedOffset}
                        stroke-linecap="round"
                        class="segment"
                    />
                {/if}

                <!-- Skipped segment (red) -->
                {#if skippedPercent > 0}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="var(--color-error)"
                        stroke-width={strokeWidth}
                        stroke-dasharray="{skippedDash} {circumference}"
                        stroke-dashoffset={skippedOffset}
                        stroke-linecap="round"
                        class="segment"
                    />
                {/if}

                <!-- Snoozed segment (amber) -->
                {#if snoozedPercent > 0}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="var(--aura-stretch)"
                        stroke-width={strokeWidth}
                        stroke-dasharray="{snoozedDash} {circumference}"
                        stroke-dashoffset={snoozedOffset}
                        stroke-linecap="round"
                        class="segment"
                    />
                {/if}
            </svg>

            <!-- Center text -->
            <div class="chart-center">
                <span
                    class="text-2xl font-light"
                    class:text-success={complianceRate >= 70}
                    class:text-warning={complianceRate >= 40 &&
                        complianceRate < 70}
                    class:text-error={complianceRate < 40}
                >
                    {complianceRate}%
                </span>
            </div>
        </div>

        <!-- Stats breakdown -->
        <div class="flex-1 space-y-3">
            <!-- Today's progress bar -->
            <div class="today-progress">
                <div class="flex justify-between text-xs mb-1">
                    <span class="opacity-70">Today</span>
                    <span class="text-success"
                        >{todayCompleted}/{todayTotal}</span
                    >
                </div>
                <div class="progress-bar">
                    <div
                        class="progress-fill bg-success"
                        style="width: {todayTotal > 0
                            ? (todayCompleted / todayTotal) * 100
                            : 0}%"
                    ></div>
                </div>
            </div>

            <!-- Breakdown -->
            <div class="stat-row">
                <div class="stat-indicator bg-success"></div>
                <span class="flex-1">Completed</span>
                <span class="font-medium">{totalStats.completed}</span>
                <span class="opacity-50 text-xs w-10 text-right"
                    >{completedPercent}%</span
                >
            </div>

            <div class="stat-row">
                <div class="stat-indicator bg-error"></div>
                <span class="flex-1">Skipped</span>
                <span class="font-medium">{totalStats.skipped}</span>
                <span class="opacity-50 text-xs w-10 text-right"
                    >{skippedPercent}%</span
                >
            </div>

            <div class="stat-row">
                <div class="stat-indicator bg-warning"></div>
                <span class="flex-1">Snoozed</span>
                <span class="font-medium">{totalStats.snoozed}</span>
                <span class="opacity-50 text-xs w-10 text-right"
                    >{snoozedPercent}%</span
                >
            </div>
        </div>
    </div>
</div>

<style>
    .compliance-card {
        min-height: 180px;
    }

    .chart-container {
        position: relative;
        flex-shrink: 0;
    }

    .donut-chart {
        transform: rotate(-90deg);
    }

    .segment {
        transition:
            stroke-dasharray 0.5s ease,
            stroke-dashoffset 0.5s ease;
    }

    .chart-center {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
    }

    .today-progress {
        padding: 0.5rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 0.5rem;
    }

    .progress-bar {
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 9999px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        border-radius: 9999px;
        transition: width 0.3s ease;
    }

    .stat-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.8rem;
    }

    .stat-indicator {
        width: 8px;
        height: 8px;
        border-radius: 2px;
        flex-shrink: 0;
    }
</style>
