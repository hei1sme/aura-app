<!--
  HydrationTrendsCard.svelte - Hydration Tracking with Trends
  
  Shows current hydration + 7-day trend chart + quick-add buttons
-->
<script lang="ts">
    import ProgressRing from "./ProgressRing.svelte";
    import { hydrationStatus, hydrationPercent } from "$lib/stores";
    import { hydrationHistory } from "$lib/stores/analytics";
    import { logHydration } from "$lib/ipc";

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

    // Day labels for the chart
    const dayLabels = ["M", "T", "W", "T", "F", "S", "S"];

    // Generate mock week data if no history (will be replaced by real data)
    $: weekData =
        $hydrationHistory.length > 0
            ? $hydrationHistory.slice(-7)
            : Array(7)
                  .fill(null)
                  .map((_, i) => ({
                      date: "",
                      amount_ml: i === 6 ? $hydrationStatus.total_today_ml : 0,
                      goal_ml: $hydrationStatus.goal_ml,
                  }));

    // Calculate bar heights
    $: maxAmount = Math.max(...weekData.map((d) => d.goal_ml), 2000);
</script>

<div class="bento-item hydration-card theme-hydration">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">💧</span>
            Hydration
        </h3>
        <div class="text-right">
            <span class="text-sm font-light text-info"
                >{$hydrationStatus.total_today_ml}ml</span
            >
            <span class="text-xs opacity-50">
                / {$hydrationStatus.goal_ml}ml</span
            >
        </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
        <!-- Left: Progress ring + Quick add -->
        <div class="flex flex-col items-center gap-3">
            <div class="ring-wrapper">
                <ProgressRing
                    progress={$hydrationPercent}
                    size={80}
                    strokeWidth={6}
                    color="var(--aura-hydration)"
                >
                    <div class="text-center">
                        <span class="text-xl font-light text-info"
                            >{$hydrationPercent}</span
                        >
                        <span class="text-xs opacity-60">%</span>
                    </div>
                </ProgressRing>
            </div>

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
        </div>

        <!-- Right: Weekly trend chart -->
        <div class="trend-chart">
            <div class="text-xs opacity-50 mb-2 text-center">This Week</div>
            <div class="chart-bars">
                {#each weekData as day, i}
                    {@const heightPercent =
                        maxAmount > 0 ? (day.amount_ml / maxAmount) * 100 : 0}
                    {@const isToday = i === 6}
                    {@const reachedGoal = day.amount_ml >= day.goal_ml}
                    <div class="bar-column">
                        <div class="bar-wrapper">
                            <div
                                class="bar"
                                class:today={isToday}
                                class:reached={reachedGoal}
                                style="height: {Math.max(heightPercent, 4)}%"
                            ></div>
                            <!-- Goal line -->
                            <div
                                class="goal-line"
                                style="bottom: {(day.goal_ml / maxAmount) *
                                    100}%"
                            ></div>
                        </div>
                        <span class="day-label" class:today={isToday}
                            >{dayLabels[i]}</span
                        >
                    </div>
                {/each}
            </div>
        </div>
    </div>
</div>

<style>
    .hydration-card {
        min-height: 180px;
    }

    .ring-wrapper {
        flex-shrink: 0;
    }

    .quick-add-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.35rem;
    }

    .quick-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.125rem;
        padding: 0.4rem 0.3rem;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 0.5rem;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    .quick-btn:hover {
        background: rgba(59, 130, 246, 0.2);
        border-color: var(--aura-hydration);
        transform: translateY(-1px);
    }

    .quick-btn:active {
        transform: translateY(0);
    }

    .quick-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .trend-chart {
        display: flex;
        flex-direction: column;
    }

    .chart-bars {
        display: flex;
        gap: 0.25rem;
        align-items: flex-end;
        flex: 1;
        min-height: 80px;
    }

    .bar-column {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
    }

    .bar-wrapper {
        width: 100%;
        height: 70px;
        position: relative;
        display: flex;
        align-items: flex-end;
        justify-content: center;
    }

    .bar {
        width: 80%;
        background: rgba(59, 130, 246, 0.3);
        border-radius: 2px 2px 0 0;
        transition:
            height 0.3s ease,
            background 0.3s ease;
        min-height: 2px;
    }

    .bar.today {
        background: var(--aura-hydration);
    }

    .bar.reached {
        background: var(--aura-eye-care);
    }

    .goal-line {
        position: absolute;
        left: 0;
        right: 0;
        height: 1px;
        background: rgba(255, 255, 255, 0.2);
        border-style: dashed;
    }

    .day-label {
        font-size: 0.6rem;
        opacity: 0.5;
        text-transform: uppercase;
    }

    .day-label.today {
        opacity: 1;
        color: var(--aura-hydration);
        font-weight: 500;
    }
</style>
