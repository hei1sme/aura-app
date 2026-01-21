<!--
  ActivityHeatmapCard.svelte - Activity Intensity Heatmap
  
  Visualizes activity intensity over time (Day x Hour grid)
-->
<script lang="ts">
    import { activityHeatmap } from "$lib/stores/analytics";
    import { getActivityHeatmap } from "$lib/ipc";
    import { onMount } from "svelte";

    onMount(() => {
        getActivityHeatmap(7);
    });

    // Helper to format date label
    function getDayLabel(dateStr: string): string {
        const d = new Date(dateStr);
        return d.toLocaleDateString("en-US", { weekday: "short" }); // Mon, Tue...
    }

    // Prepare grid data: 7 rows (days) x 24 cols (hours)
    // We need to map the flat list from store to this grid
    $: grid = (() => {
        if (!$activityHeatmap || $activityHeatmap.length === 0) return [];

        // Group by Date
        const days: Record<string, typeof $activityHeatmap> = {};
        const dates: string[] = [];

        $activityHeatmap.forEach((item) => {
            if (!days[item.date]) {
                days[item.date] = [];
                dates.push(item.date);
            }
            days[item.date].push(item);
        });

        // Sort dates (latest at bottom)
        dates.sort();

        return dates.map((date) => {
            // Create array of 24 hours
            const hours = Array(24)
                .fill(null)
                .map((_, h) => {
                    const found = days[date].find((i) => i.hour === h);
                    return found ? found : { intensity: 0, details: null };
                });
            return {
                date,
                label: getDayLabel(date),
                hours,
            };
        });
    })();

    function getIntensityColor(intensity: number): string {
        if (intensity === 0) return "rgba(255,255,255,0.05)";
        // Scale 0-1 to opacity of theme color
        // Determine color based on intensity level?
        // Low = Blue, Med = Green, High = Orange? Or just opacity of 'eye-care'
        // Let's use opacity of var(--aura-eye-care)
        const opacity = Math.min(1, Math.max(0.1, intensity * 0.8 + 0.1));
        return `rgba(74, 222, 128, ${opacity})`; // aura-eye-care is rgb(74, 222, 128)
    }
</script>

<div class="stats-card bento-item">
    <div class="flex items-center justify-between mb-2">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">⚡</span>
            Activity Intensity
        </h3>
        <span class="badge badge-sm badge-ghost opacity-60">Last 7 Days</span>
    </div>

    {#if grid.length > 0}
        <div class="heatmap-container mt-2">
            <!-- Hours Label (Top) -->
            <div
                class="flex ml-8 mb-1 text-[10px] opacity-40 justify-between px-1"
            >
                <span>12am</span>
                <span>6am</span>
                <span>12pm</span>
                <span>6pm</span>
            </div>

            <!-- Grid -->
            <div class="space-y-1">
                {#each grid as day}
                    <div class="flex items-center gap-2">
                        <!-- Day Label -->
                        <span class="text-[10px] w-6 opacity-50 text-right"
                            >{day.label}</span
                        >

                        <!-- Hours Grid -->
                        <div class="flex-1 grid grid-cols-24 gap-px h-6">
                            {#each day.hours as hourData, h}
                                <div
                                    class="rounded-sm transition-all hover:ring-1 hover:ring-white/50 relative group"
                                    style="background: {getIntensityColor(
                                        hourData.intensity,
                                    )}"
                                >
                                    <!-- Tooltip -->
                                    <div
                                        class="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 rounded text-xs whitespace-nowrap z-10 border border-white/10 pointer-events-none"
                                    >
                                        {h}:00 - Intensity: {Math.round(
                                            hourData.intensity * 100,
                                        )}%
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    {:else}
        <div class="flex flex-col items-center justify-center h-40 opacity-40">
            <span class="text-3xl mb-2">📉</span>
            <span class="text-xs">No intensity metrics yet</span>
        </div>
    {/if}
</div>

<style>
    .stats-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 1rem;
        padding: 1.25rem;
        min-height: 200px;
    }

    .grid-cols-24 {
        display: grid;
        grid-template-columns: repeat(24, minmax(0, 1fr));
    }
</style>
