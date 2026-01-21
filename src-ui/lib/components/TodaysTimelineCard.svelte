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
            icon: "❌",
            color: "rgba(255,255,255,0.3)",
            label: "Missed",
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
    <div class="flex items-center justify-between mb-2">
        <h3 class="text-label flex items-center gap-2">
            <span class="text-base">📅</span>
            Today's Timeline
        </h3>
        <span class="text-xs opacity-50"
            >{$breaksToday.length} events • Recent First</span
        >
    </div>

    <div class="timeline-scroll">
        {#if sortedBreaks.length === 0}
            <div class="empty-state">
                <span class="text-2xl">🌅</span>
                <div>
                    <p class="text-sm font-medium">No breaks yet</p>
                    <p class="text-xs">Your timeline will appear here</p>
                </div>
            </div>
        {:else}
            <div class="timeline">
                {#each sortedBreaks as log, i}
                    {@const style = getEventStyle(log)}
                    <div
                        class="timeline-item"
                        style="--accent-color: {style.color}"
                    >
                        <!-- Connecting Line (except for last item) -->
                        {#if i < sortedBreaks.length - 1}
                            <div class="timeline-connector"></div>
                        {/if}

                        <div class="timeline-dot"></div>

                        <div class="timeline-content">
                            <span
                                class="text-xs font-mono opacity-60 mb-1 block"
                                >{formatTime(log.timestamp)}</span
                            >
                            <div
                                class="flex items-center gap-1.5 justify-center"
                            >
                                <span class="text-sm">{style.icon}</span>
                                <span
                                    class="font-medium text-xs truncate max-w-[90px]"
                                    title={getBreakTypeName(log.break_type)}
                                >
                                    {getBreakTypeName(log.break_type)}
                                </span>
                            </div>
                            <span
                                class="text-[10px] uppercase tracking-wider opacity-50 mt-1"
                                style="color: {style.color}"
                            >
                                {style.label}
                            </span>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>
</div>

<style>
    .timeline-card {
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .timeline-scroll {
        flex: 1;
        overflow-x: auto;
        overflow-y: hidden;
        padding-bottom: 0.5rem;
        /* Hide scrollbar but keep functionality */
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
    }

    .timeline-scroll::-webkit-scrollbar {
        height: 6px;
    }

    .timeline-scroll::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 4px;
    }

    .empty-state {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        height: 80px;
        text-align: center;
        opacity: 0.4;
    }

    .timeline {
        display: flex;
        flex-direction: row; /* Horizontal */
        align-items: center; /* Center items vertically */
        gap: 0; /* Connected via lines */
        padding: 0 1rem;
        min-width: min-content;
    }

    .timeline-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        min-width: 140px;
        padding-top: 1rem;
    }

    /* Connecting Line */
    .timeline-connector {
        position: absolute;
        top: 1.5rem; /* Match dot center */
        left: 50%;
        width: 100%;
        height: 2px;
        background: rgba(255, 255, 255, 0.1);
        z-index: 0;
    }

    .timeline-dot {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: var(--accent-color);
        box-shadow: 0 0 10px var(--accent-color);
        border: 2px solid rgba(0, 0, 0, 0.5);
        z-index: 1;
        margin-bottom: 0.75rem;
    }

    .timeline-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 0.5rem;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.2s ease;
        width: 130px;
    }

    .timeline-content:hover {
        background: rgba(255, 255, 255, 0.08);
        border-color: var(--accent-color);
        transform: translateY(-2px);
    }
</style>
