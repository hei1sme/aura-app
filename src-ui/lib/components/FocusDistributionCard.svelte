<!--
  FocusDistributionCard.svelte - App Usage Analytics
  
  Visualizes time spent in different app categories (Code, Web, etc)
-->
<script lang="ts">
    import { focusStats } from "$lib/stores/analytics";
    import { getFocusStats } from "$lib/ipc";
    import { onMount } from "svelte";

    onMount(() => {
        getFocusStats(7); // Last 7 days
    });

    $: total = Object.values($focusStats).reduce((a, b) => a + b, 0);

    $: categories = Object.entries($focusStats)
        .sort(([, a], [, b]) => b - a) // Sort by count desc
        .map(([name, count], index) => {
            const percentage = total > 0 ? (count / total) * 100 : 0;
            return {
                name,
                count,
                percentage,
                color: getColorForCategory(name, index),
            };
        });

    // Top 4 + "Other" if needed
    $: displayCategories = categories.slice(0, 4);
    $: otherPercentage = categories
        .slice(4)
        .reduce((acc, c) => acc + c.percentage, 0);

    function getColorForCategory(name: string, index: number): string {
        // Aura Brand Colors
        const colors = [
            "var(--aura-eye-care)", // Green
            "var(--aura-stretch)", // Orange
            "var(--aura-accent)", // Blue/Purple
            "#e0e0e0", // White-ish
            "#666666", // Grey
        ];
        // Specific mapping if desired
        if (name === "Code") return "var(--aura-eye-care)";
        if (name === "Web") return "var(--aura-accent)";
        if (name === "Game") return "var(--aura-stretch)";

        return colors[index % colors.length];
    }

    // Pre-calculate segments for SVG rendering
    $: chartData = (() => {
        let accumulatedPercentage = 0;
        return categories.map((cat) => {
            const { percentage } = cat;
            // Start offset
            const offset = accumulatedPercentage;
            accumulatedPercentage += percentage;

            return {
                ...cat,
                strokeDasharray: calculateStrokeDashArray(percentage, 40),
                strokeDashoffset: calculateStrokeDashoffset(offset, 40),
            };
        });
    })();

    function calculateStrokeDashArray(
        percentage: number,
        radius: number,
    ): string {
        const circumference = 2 * Math.PI * radius;
        // Length of the arc
        const arcLength = (percentage / 100) * circumference;
        // Gap is the rest of circle (or small gap for style?)
        // Here we use standard dasharray: arcLength gapLength
        // To leave small gaps between segments, we can subtract a bit from arcLength
        const gap = 2;
        const adjustedArc = Math.max(0, arcLength - gap);
        return `${adjustedArc} ${circumference}`;
    }

    function calculateStrokeDashoffset(
        percentageOffset: number,
        radius: number,
    ): number {
        const circumference = 2 * Math.PI * radius;
        // Negative offset to move clockwise from top (due to -90deg rotate)
        return -((percentageOffset / 100) * circumference);
    }
</script>

<div class="stats-card bento-item">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">🎯</span>
            Focus Distribution
        </h3>
        <span class="badge badge-sm badge-ghost opacity-60">Last 7 Days</span>
    </div>

    {#if total > 0}
        <div class="flex items-center gap-6">
            <!-- Donut Chart -->
            <div class="relative w-32 h-32 flex-shrink-0">
                <svg
                    viewBox="0 0 100 100"
                    class="w-full h-full transform -rotate-90"
                >
                    {#each chartData as segment}
                        <circle
                            cx="50"
                            cy="50"
                            r="40"
                            fill="transparent"
                            stroke={segment.color}
                            stroke-width="12"
                            stroke-dasharray={segment.strokeDasharray}
                            stroke-dashoffset={segment.strokeDashoffset}
                            stroke-linecap="round"
                            class="transition-all duration-1000 ease-out"
                            opacity="0.9"
                        />
                    {/each}

                    <!-- Hole (Background ring for decoration) -->
                    <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="rgba(255,255,255,0.05)"
                        stroke-width="12"
                    />
                </svg>

                <!-- Center Text -->
                <div
                    class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
                >
                    <span class="text-2xl font-light"
                        >{categories[0]?.name.slice(0, 1) || "?"}</span
                    >
                </div>
            </div>

            <!-- Legend -->
            <div class="flex-1 space-y-2">
                {#each displayCategories as cat}
                    <div class="flex items-center justify-between text-sm">
                        <div class="flex items-center gap-2">
                            <span
                                class="w-2 h-2 rounded-full"
                                style="background: {cat.color}"
                            ></span>
                            <span class="opacity-80">{cat.name}</span>
                        </div>
                        <span class="font-mono opacity-60"
                            >{Math.round(cat.percentage)}%</span
                        >
                    </div>
                {/each}
                {#if otherPercentage > 1}
                    <div class="flex items-center justify-between text-sm">
                        <div class="flex items-center gap-2">
                            <span
                                class="w-2 h-2 rounded-full"
                                style="background: #666"
                            ></span>
                            <span class="opacity-80">Other</span>
                        </div>
                        <span class="font-mono opacity-60"
                            >{Math.round(otherPercentage)}%</span
                        >
                    </div>
                {/if}
            </div>
        </div>
    {:else}
        <div class="flex flex-col items-center justify-center h-32 opacity-40">
            <span class="text-3xl mb-2">📊</span>
            <span class="text-xs">No activity data yet</span>
        </div>
    {/if}
</div>

<style>
    .stats-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 1rem;
        padding: 1.25rem;
    }
</style>
