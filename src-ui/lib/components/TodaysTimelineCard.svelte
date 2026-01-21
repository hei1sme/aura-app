<!--
  TodaysTimelineCard.svelte - Today's Wellness Timeline
  
  Chronological view of breaks and hydration logs
-->
<script lang="ts">
    import { breaksToday } from "$lib/stores/analytics";

    // Format timestamp to time string
    function formatTime(timestamp: number): string {
        const date = new Date(timestamp * 1000);
        return date.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
        });
    }

    // Get icon and color for event type
    function getEventStyle(log: {
        break_type: string;
        completed: boolean;
        skipped: boolean;
        snoozed: boolean;
    }) {
        if (log.completed) {
            return {
                icon: "✅",
                color: "var(--aura-eye-care)",
                label: "Completed",
            };
        } else if (log.skipped) {
            return {
                icon: "⏭️",
                color: "var(--color-error)",
                label: "Skipped",
            };
        } else if (log.snoozed) {
            return {
                icon: "⏰",
                color: "var(--aura-stretch)",
                label: "Snoozed",
            };
        }
        return {
            icon: "⚪",
            color: "rgba(255,255,255,0.5)",
            label: "Pending",
        };
    }

    // Get break type display name
    function getBreakTypeName(type: string): string {
        const names: Record<string, string> = {
            micro: "Eye Rest",
            macro: "Stretch Break",
            hydration: "Hydration",
        };
        return names[type] || type;
    }

    // Sort by timestamp descending (most recent first)
    $: sortedBreaks = [...$breaksToday].sort(
        (a, b) => b.timestamp - a.timestamp,
    );
</script>

<div class="bento-item timeline-card">
    <div class="flex items-center justify-between mb-4">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">📅</span>
            Today's Timeline
        </h3>
        <span class="text-xs opacity-50">{$breaksToday.length} events</span>
    </div>

    <div class="timeline-scroll">
        {#if sortedBreaks.length === 0}
            <div class="empty-state">
                <span class="text-2xl mb-2">🌅</span>
                <p class="text-sm opacity-60">No breaks yet today</p>
                <p class="text-xs opacity-40">
                    Your wellness journey starts here
                </p>
            </div>
        {:else}
            <div class="timeline">
                {#each sortedBreaks as log, i}
                    {@const style = getEventStyle(log)}
                    <div
                        class="timeline-item"
                        style="--accent-color: {style.color}"
                    >
                        <div class="timeline-dot"></div>
                        {#if i < sortedBreaks.length - 1}
                            <div class="timeline-line"></div>
                        {/if}
                        <div class="timeline-content">
                            <div class="flex items-center gap-2">
                                <span class="text-sm">{style.icon}</span>
                                <span class="font-medium text-sm"
                                    >{getBreakTypeName(log.break_type)}</span
                                >
                            </div>
                            <div class="flex items-center gap-2 mt-0.5">
                                <span class="text-xs opacity-50"
                                    >{formatTime(log.timestamp)}</span
                                >
                                <span class="text-xs opacity-40">•</span>
                                <span
                                    class="text-xs opacity-60"
                                    style="color: {style.color}"
                                    >{style.label}</span
                                >
                            </div>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>

<style>
    .timeline-card {
        min-height: 180px;
        display: flex;
        flex-direction: column;
    }

    .timeline-scroll {
        flex: 1;
        overflow-y: auto;
        max-height: 200px;
        padding-right: 0.5rem;
    }

    .timeline-scroll::-webkit-scrollbar {
        width: 4px;
    }

    .timeline-scroll::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 4px;
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 120px;
        text-align: center;
    }

    .timeline {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .timeline-item {
        display: flex;
        gap: 0.75rem;
        position: relative;
        padding-left: 1rem;
    }

    .timeline-dot {
        position: absolute;
        left: 0;
        top: 0.5rem;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--accent-color);
        box-shadow: 0 0 8px var(--accent-color);
    }

    .timeline-line {
        position: absolute;
        left: 3px;
        top: 1rem;
        bottom: -0.75rem;
        width: 2px;
        background: linear-gradient(
            to bottom,
            var(--accent-color) 0%,
            rgba(255, 255, 255, 0.1) 100%
        );
    }

    .timeline-content {
        flex: 1;
        padding: 0.5rem 0.75rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.2s ease;
    }

    .timeline-content:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: var(--accent-color);
    }
</style>
