<!--
  HydrationTrendsCard.svelte - Hydration Tracking with Trends
  
  Shows current hydration + 7-day trend line chart + quick-add buttons
-->
<script lang="ts">
    import ProgressRing from "./ProgressRing.svelte";
    import { hydrationStatus, hydrationPercent } from "$lib/stores";
    import { hydrationHistory } from "$lib/stores/analytics";
    import { logHydration } from "$lib/ipc";

    // Hover state for tooltip
    let hoveredPoint: {
        val: number;
        goal: number;
        day: string;
        x: number;
        y: number;
    } | null = null;

    const quickAmounts = [
        { amount: 100, label: "100ml", emoji: "💧" },
        { amount: 250, label: "250ml", emoji: "🥤" },
        { amount: 500, label: "500ml", emoji: "🍶" },
    ];

    let isLogging = false;

    async function addWater(amount: number) {
        if (isLogging) return;
        isLogging = true;
        try {
            await logHydration(amount);
        } catch (error) {
            console.error("Failed to log hydration:", error);
        } finally {
            isLogging = false;
        }
    }

    // Helper to format YYYY-MM-DD
    function formatDateKey(date: Date): string {
        return date.toISOString().split("T")[0];
    }

    function getDayLabel(date: Date): string {
        return date.toLocaleDateString("en-US", { weekday: "narrow" });
    }

    // Dynamic day labels
    $: dayLabels = Array.from({ length: 7 }).map((_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (6 - i));
        return getDayLabel(d);
    });

    // Generate real week data from store
    $: weekData = Array.from({ length: 7 }).map((_, i) => {
        const isToday = i === 6;
        if (isToday) {
            return {
                val: $hydrationStatus.total_today_ml,
                goal: $hydrationStatus.goal_ml,
            };
        }

        const daysAgo = 6 - i;
        const d = new Date();
        d.setDate(d.getDate() - daysAgo);
        const dateKey = formatDateKey(d);

        // Lookup in history
        const dayRecord = $hydrationHistory.find((h) => h.date === dateKey);

        return {
            val: dayRecord ? dayRecord.amount_ml : 0,
            goal: $hydrationStatus.goal_ml, // Assuming constant goal for simplicity
        };
    });

    // Chart Dimensions
    const height = 80;
    const width = 180;
    const padding = 5;

    $: maxVal = Math.max(
        ...weekData.map((d) => d.val),
        ...weekData.map((d) => d.goal),
        2500,
    );

    // Scale functions
    $: xScale = (index: number) =>
        (index / (weekData.length - 1)) * (width - 2 * padding) + padding;
    $: yScale = (val: number) =>
        height - (val / maxVal) * (height - 2 * padding) - padding;

    // Generate SVG path for the line
    $: pathD = weekData
        .map((d, i) => {
            const x = xScale(i);
            const y = yScale(d.val);
            return `${i === 0 ? "M" : "L"} ${x} ${y}`;
        })
        .join(" ");

    // Area fill path (closes the loop for gradient)
    $: areaD = `${pathD} L ${xScale(weekData.length - 1)} ${height} L ${xScale(0)} ${height} Z`;

    // Goal line path
    $: goalY = yScale(2000); // Assume 2000 is goal for visual simplicity if varying
</script>

<div class="bento-item hydration-card theme-hydration">
    <div class="flex items-center justify-between mb-2">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">💧</span>
            Hydration
        </h3>
        <div class="text-right">
            <span class="text-2xl font-light text-info"
                >{$hydrationStatus.total_today_ml}</span
            >
            <span class="text-sm font-light text-info opacity-70">ml</span>
            <div class="text-xs opacity-50 -mt-1">
                Goal: <span class="font-medium">{$hydrationStatus.goal_ml}</span
                >
            </div>
        </div>
    </div>

    <div class="flex gap-4">
        <!-- Left: Quick Add Buttons (Stacked) -->
        <div class="flex flex-col gap-2 w-24 flex-shrink-0">
            <div class="quick-add-grid">
                {#each quickAmounts as item}
                    <button
                        class="quick-btn"
                        class:loading={isLogging}
                        on:click={() => addWater(item.amount)}
                        disabled={isLogging}
                        title="Add {item.label}"
                    >
                        <span class="text-sm">{item.emoji}</span>
                        <span class="text-[10px] opacity-70">{item.label}</span>
                    </button>
                {/each}
            </div>

            <!-- Mini Progress Stat -->
            <div class="text-center mt-1">
                <div class="text-xs opacity-60">Daily Progress</div>
                <div class="font-medium text-info">{$hydrationPercent}%</div>
            </div>
        </div>

        <!-- Right: Trend Chart -->
        <div class="trend-chart-container flex-1">
            <div class="chart-header">
                <span class="text-[10px] opacity-40 uppercase tracking-wider"
                    >7-Day Trend</span
                >
            </div>

            <svg
                viewBox="0 0 {width} {height}"
                class="trend-svg"
                preserveAspectRatio="none"
            >
                <defs>
                    <linearGradient
                        id="hydroGradient"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                    >
                        <stop
                            offset="0%"
                            stop-color="var(--aura-hydration)"
                            stop-opacity="0.5"
                        />
                        <stop
                            offset="100%"
                            stop-color="var(--aura-hydration)"
                            stop-opacity="0.05"
                        />
                    </linearGradient>
                </defs>

                <!-- Goal Line (Dashed) -->
                <line
                    x1="0"
                    y1={goalY}
                    x2={width}
                    y2={goalY}
                    stroke="rgba(255,255,255,0.15)"
                    stroke-width="1"
                    stroke-dasharray="3 3"
                />

                <!-- Area Fill -->
                <path d={areaD} fill="url(#hydroGradient)" />

                <!-- Trend Line -->
                <path
                    d={pathD}
                    fill="none"
                    stroke="var(--aura-hydration)"
                    stroke-width="2.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="trend-line"
                />

                <!-- Data Points -->
                {#each weekData as d, i}
                    <circle
                        cx={xScale(i)}
                        cy={yScale(d.val)}
                        r={i === 6 ? 4 : 3}
                        fill={i === 6
                            ? "var(--aura-hydration)"
                            : "rgba(255,255,255,0.8)"}
                        class="data-point cursor-pointer"
                        role="img"
                        aria-label="{dayLabels[i]}: {d.val}ml"
                        on:mouseenter={() => {
                            hoveredPoint = {
                                val: d.val,
                                goal: d.goal,
                                day: dayLabels[i],
                                x: xScale(i),
                                y: yScale(d.val),
                            };
                        }}
                        on:mouseleave={() => (hoveredPoint = null)}
                    />
                {/each}

                <!-- Hover Tooltip -->
                {#if hoveredPoint}
                    <g
                        transform="translate({hoveredPoint.x}, {hoveredPoint.y -
                            10})"
                    >
                        <rect
                            x="-30"
                            y="-32"
                            width="60"
                            height="28"
                            rx="4"
                            fill="rgba(17, 24, 39, 0.95)"
                            stroke="rgba(255,255,255,0.2)"
                            stroke-width="1"
                        />
                        <text
                            x="0"
                            y="-20"
                            text-anchor="middle"
                            fill="var(--aura-hydration)"
                            font-size="10"
                            font-weight="600">{hoveredPoint.val}ml</text
                        >
                        <text
                            x="0"
                            y="-9"
                            text-anchor="middle"
                            fill="rgba(255,255,255,0.6)"
                            font-size="8"
                            >{Math.round(
                                (hoveredPoint.val / hoveredPoint.goal) * 100,
                            )}% of goal</text
                        >
                    </g>
                {/if}
            </svg>

            <!-- X-Axis Labels -->
            <div class="flex justify-between mt-1 px-1">
                {#each dayLabels as day, i}
                    <span
                        class="text-[9px] opacity-40 {i === 6
                            ? 'text-info font-bold opacity-100'
                            : ''}">{day}</span
                    >
                {/each}
            </div>
        </div>
    </div>
</div>

<style>
    .hydration-card {
        min-height: 180px;
        display: flex;
        flex-direction: column;
    }

    .quick-add-grid {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .quick-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.6rem 0.75rem;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 0.75rem;
        transition: all 0.2s ease;
        cursor: pointer;
        width: 100%;
        text-align: left;
        position: relative;
    }

    .quick-btn:hover {
        background: rgba(59, 130, 246, 0.2);
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateX(3px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }

    .quick-btn:active {
        transform: translateX(3px) scale(0.98);
    }

    .trend-chart-container {
        display: flex;
        flex-direction: column;
        background: rgba(0, 0, 0, 0.35);
        border-radius: 0.75rem;
        padding: 0.75rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .chart-header {
        margin-bottom: 0.5rem;
        text-align: right;
    }

    .trend-svg {
        flex: 1;
        width: 100%;
        overflow: visible;
    }

    .trend-line {
        filter: drop-shadow(0 4px 8px rgba(59, 130, 246, 0.4));
        animation: drawLine 1s ease-out forwards;
    }

    @keyframes drawLine {
        from {
            stroke-dasharray: 1000;
            stroke-dashoffset: 1000;
        }
        to {
            stroke-dasharray: 1000;
            stroke-dashoffset: 0;
        }
    }

    .data-point {
        filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.4));
        transition: all 0.2s ease;
    }
</style>
