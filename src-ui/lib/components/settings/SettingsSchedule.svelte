<script lang="ts">
    import {
        getScheduleRules,
        addScheduleRule,
        deleteScheduleRule,
        updateScheduleRule,
        type ScheduleRule,
    } from "$lib/ipc";
    import { onMount } from "svelte";

    export let scheduleRules: ScheduleRule[] = [];

    let scheduleMode: "same_every_day" | "weekday_weekend" | "custom" =
        "same_every_day";
    let showAddModal = false;

    // Modal State
    let newRuleTitle = "";
    let newRuleTime = "09:00";
    let newRuleAction:
        | "pause"
        | "resume"
        | "reset"
        | "start_session"
        | "end_session" = "start_session";
    let newRuleDays: string[] = []; // Used for Custom mode validation or internal logic

    // Context for "Add Rule" (which bucket are we adding to?)
    let addContext: "all" | "weekday" | "weekend" | "custom" = "all";

    const ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
    const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"];
    const WEEKENDS = ["sat", "sun"];

    const DAY_LABELS: Record<string, string> = {
        mon: "Mon",
        tue: "Tue",
        wed: "Wed",
        thu: "Thu",
        fri: "Fri",
        sat: "Sat",
        sun: "Sun",
    };
    const FULL_DAY_LABELS: Record<string, string> = {
        mon: "Monday",
        tue: "Tuesday",
        wed: "Wednesday",
        thu: "Thursday",
        fri: "Friday",
        sat: "Saturday",
        sun: "Sunday",
    };

    const ACTION_LABELS: Record<string, string> = {
        pause: "⏸️ Pause",
        resume: "▶️ Resume",
        reset: "🔄 Reset",
        start_session: "🚀 Start Session",
        end_session: "🛑 End Session",
    };

    function openAddModal(context: typeof addContext) {
        addContext = context;
        newRuleTitle = "";
        newRuleTime = "09:00";
        newRuleAction = "start_session";

        // Pre-select days based on context
        if (context === "weekday") newRuleDays = [...WEEKDAYS];
        else if (context === "weekend") newRuleDays = [...WEEKENDS];
        else newRuleDays = []; // For custom, user selects

        showAddModal = true;
    }

    async function handleAddRule() {
        let daysToUse: string[] = [];

        if (addContext === "all") daysToUse = ALL_DAYS;
        else if (addContext === "weekday") daysToUse = WEEKDAYS;
        else if (addContext === "weekend") daysToUse = WEEKENDS;
        else daysToUse = newRuleDays; // Custom mode

        if (daysToUse.length === 0) return;

        try {
            await addScheduleRule(
                newRuleTime,
                newRuleAction,
                daysToUse,
                newRuleTitle,
            );
            // We still want to fetch after add because we need the new rule's ID
            // await getScheduleRules(); // Handled by event listener in parent
            showAddModal = false;
        } catch (e) {
            console.error("Failed to add rule:", e);
        }
    }

    async function handleDeleteRule(id: number) {
        // Optimistic update
        const previousRules = [...scheduleRules];
        scheduleRules = scheduleRules.filter((r) => r.id !== id);

        try {
            await deleteScheduleRule(id);
            // Do NOT re-fetch immediately to avoid race condition
        } catch (e) {
            console.error("Failed to delete rule:", e);
            scheduleRules = previousRules;
        }
    }

    async function handleRemoveDayFromRule(rule: ScheduleRule, day: string) {
        if (rule.days.length > 1) {
            const newDays = rule.days.filter((d) => d !== day);

            // Optimistic update: Find the rule and update its days locally
            const previousRules = [...scheduleRules];
            scheduleRules = scheduleRules.map((r) =>
                r.id === rule.id ? { ...r, days: newDays } : r,
            );

            try {
                await updateScheduleRule(
                    rule.id,
                    rule.time,
                    rule.action,
                    newDays,
                    rule.enabled,
                    rule.title,
                );
                // Do NOT re-fetch immediately to avoid race condition
            } catch (e) {
                console.error("Failed to update rule:", e);
                scheduleRules = previousRules;
            }
        } else {
            // If it's the last day, we delete the rule entirely
            await handleDeleteRule(rule.id);
        }
    }

    // Helpers to filter rules for display
    $: globalRules = scheduleRules.filter((r) => r.days.length === 7);
    $: weekdayRules = scheduleRules.filter(
        (r) => r.days.length === 5 && r.days.every((d) => WEEKDAYS.includes(d)),
    );
    $: weekendRules = scheduleRules.filter(
        (r) => r.days.length === 2 && r.days.every((d) => WEEKENDS.includes(d)),
    );

    $: rulesByDay = ALL_DAYS.reduce(
        (acc, day) => {
            acc[day] = scheduleRules.filter((r) => r.days.includes(day));
            return acc;
        },
        {} as Record<string, ScheduleRule[]>,
    );
</script>

<div class="space-y-6 animate-fade-in relative">
    <div class="mb-4">
        <h2 class="text-2xl font-light mb-1">Work Schedule</h2>
        <p class="text-sm opacity-60">
            Automate your breaks based on your routine
        </p>
    </div>

    <!-- Mode Selector -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-2 mb-6">
        <button
            class="p-3 rounded-lg border text-left transition-all hover:bg-white/5"
            class:border-primary={scheduleMode === "same_every_day"}
            class:bg-primary={scheduleMode === "same_every_day"}
            class:bg-opacity-10={scheduleMode === "same_every_day"}
            class:border-white={scheduleMode !== "same_every_day"}
            class:border-opacity-10={scheduleMode !== "same_every_day"}
            on:click={() => (scheduleMode = "same_every_day")}
        >
            <div class="font-medium text-sm">Same Every Day</div>
            <div class="text-xs opacity-60">Simple daily routine</div>
        </button>
        <button
            class="p-3 rounded-lg border text-left transition-all hover:bg-white/5"
            class:border-primary={scheduleMode === "weekday_weekend"}
            class:bg-primary={scheduleMode === "weekday_weekend"}
            class:bg-opacity-10={scheduleMode === "weekday_weekend"}
            class:border-white={scheduleMode !== "weekday_weekend"}
            class:border-opacity-10={scheduleMode !== "weekday_weekend"}
            on:click={() => (scheduleMode = "weekday_weekend")}
        >
            <div class="font-medium text-sm">Weekday / Weekend</div>
            <div class="text-xs opacity-60">Different on weekends</div>
        </button>
        <button
            class="p-3 rounded-lg border text-left transition-all hover:bg-white/5"
            class:border-primary={scheduleMode === "custom"}
            class:bg-primary={scheduleMode === "custom"}
            class:bg-opacity-10={scheduleMode === "custom"}
            class:border-white={scheduleMode !== "custom"}
            class:border-opacity-10={scheduleMode !== "custom"}
            on:click={() => (scheduleMode = "custom")}
        >
            <div class="font-medium text-sm">Custom</div>
            <div class="text-xs opacity-60">Full control</div>
        </button>
    </div>

    <!-- MODE 1: SAME EVERY DAY -->
    {#if scheduleMode === "same_every_day"}
        <div class="glass-card">
            <div class="flex justify-between items-center mb-4">
                <h3 class="font-medium">Daily Timeline</h3>
                <button
                    class="btn btn-sm btn-primary"
                    on:click={() => openAddModal("all")}
                >
                    + Add Event
                </button>
            </div>

            {#if globalRules.length === 0}
                <div class="text-center py-8 opacity-40 text-sm">
                    No automated rules set.
                </div>
            {:else}
                <div class="space-y-2">
                    {#each globalRules.sort( (a, b) => a.time.localeCompare(b.time), ) as rule (rule.id)}
                        <div
                            class="flex items-center gap-4 p-3 bg-base-300/30 rounded-lg group"
                        >
                            <div class="font-mono text-lg font-bold">
                                {rule.time}
                            </div>
                            <div class="flex-1">
                                <span
                                    class="badge badge-primary badge-outline mr-2"
                                    >{ACTION_LABELS[rule.action]}</span
                                >
                                <span class="text-sm opacity-70"
                                    >{rule.title}</span
                                >
                            </div>
                            <button
                                class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity"
                                on:click={() => handleDeleteRule(rule.id)}
                            >
                                Delete
                            </button>
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}

    <!-- MODE 2: WEEKDAY / WEEKEND -->
    {#if scheduleMode === "weekday_weekend"}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Weekdays -->
            <div class="glass-card">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="font-medium">Weekdays (Mon-Fri)</h3>
                    <button
                        class="btn btn-xs btn-primary"
                        on:click={() => openAddModal("weekday")}
                    >
                        + Add
                    </button>
                </div>
                {#if weekdayRules.length === 0}
                    <div class="text-center py-4 opacity-40 text-xs">
                        No weekday rules.
                    </div>
                {:else}
                    <div class="space-y-2">
                        {#each weekdayRules.sort( (a, b) => a.time.localeCompare(b.time), ) as rule (rule.id)}
                            <div
                                class="flex items-center gap-2 p-2 bg-base-300/30 rounded text-sm group"
                            >
                                <span class="font-mono font-bold"
                                    >{rule.time}</span
                                >
                                <span class="text-xs opacity-70 flex-1 truncate"
                                    >{ACTION_LABELS[rule.action]}</span
                                >
                                <button
                                    class="text-error opacity-0 group-hover:opacity-100 px-2"
                                    on:click={() => handleDeleteRule(rule.id)}
                                    >✕</button
                                >
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>

            <!-- Weekends -->
            <div class="glass-card">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="font-medium">Weekends (Sat-Sun)</h3>
                    <button
                        class="btn btn-xs btn-primary"
                        on:click={() => openAddModal("weekend")}
                    >
                        + Add
                    </button>
                </div>
                {#if weekendRules.length === 0}
                    <div class="text-center py-4 opacity-40 text-xs">
                        No weekend rules.
                    </div>
                {:else}
                    <div class="space-y-2">
                        {#each weekendRules.sort( (a, b) => a.time.localeCompare(b.time), ) as rule (rule.id)}
                            <div
                                class="flex items-center gap-2 p-2 bg-base-300/30 rounded text-sm group"
                            >
                                <span class="font-mono font-bold"
                                    >{rule.time}</span
                                >
                                <span class="text-xs opacity-70 flex-1 truncate"
                                    >{ACTION_LABELS[rule.action]}</span
                                >
                                <button
                                    class="text-error opacity-0 group-hover:opacity-100 px-2"
                                    on:click={() => handleDeleteRule(rule.id)}
                                    >✕</button
                                >
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    {/if}

    <!-- MODE 3: CUSTOM -->
    {#if scheduleMode === "custom"}
        <div class="space-y-2">
            {#each ALL_DAYS as day}
                <div
                    class="collapse collapse-arrow bg-base-200/30 border border-white/5 rounded-lg"
                >
                    <input type="checkbox" />
                    <div
                        class="collapse-title flex justify-between items-center pr-12"
                    >
                        <span class="font-medium">{FULL_DAY_LABELS[day]}</span>
                        <span class="text-xs opacity-50"
                            >{(rulesByDay[day] || []).length} rules</span
                        >
                    </div>
                    <div class="collapse-content">
                        <div class="pt-2 pb-4 space-y-2">
                            <button
                                class="btn btn-xs btn-ghost w-full border border-dashed border-white/20 mb-2"
                                on:click={() => {
                                    newRuleDays = [day];
                                    openAddModal("custom");
                                }}
                            >
                                + Add Rule for {DAY_LABELS[day]}
                            </button>

                            {#each (rulesByDay[day] || []).sort( (a, b) => a.time.localeCompare(b.time), ) as rule (rule.id)}
                                <div
                                    class="flex items-center gap-3 p-2 bg-black/20 rounded text-sm group"
                                >
                                    <span class="font-mono">{rule.time}</span>
                                    <span class="flex-1 opacity-80"
                                        >{ACTION_LABELS[rule.action]}</span
                                    >
                                    <button
                                        class="text-error opacity-0 group-hover:opacity-100"
                                        on:click={() =>
                                            handleRemoveDayFromRule(rule, day)}
                                        >Delete</button
                                    >
                                </div>
                            {/each}
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}

    <!-- Add Rule Modal -->
    {#if showAddModal}
        <div
            class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        >
            <div
                class="bg-base-100 border border-white/10 rounded-xl p-6 w-full max-w-sm shadow-2xl animate-scale-in"
            >
                <h3 class="text-lg font-bold mb-4">Add Schedule Rule</h3>

                <div class="space-y-4">
                    <!-- Time -->
                    <div class="form-control">
                        <label class="label-text text-xs mb-1">Time</label>
                        <input
                            type="time"
                            bind:value={newRuleTime}
                            class="input input-bordered w-full"
                        />
                    </div>

                    <!-- Action -->
                    <div class="form-control">
                        <label class="label-text text-xs mb-1">Action</label>
                        <select
                            bind:value={newRuleAction}
                            class="select select-bordered w-full"
                        >
                            {#each Object.entries(ACTION_LABELS) as [val, label]}
                                <option value={val}>{label}</option>
                            {/each}
                        </select>
                    </div>

                    <!-- Title -->
                    <div class="form-control">
                        <label class="label-text text-xs mb-1"
                            >Label (Optional)</label
                        >
                        <input
                            type="text"
                            bind:value={newRuleTitle}
                            placeholder="e.g. Lunch"
                            class="input input-bordered w-full"
                        />
                    </div>

                    <!-- Days (Only if Custom) -->
                    {#if addContext === "custom"}
                        <div class="form-control">
                            <label class="label-text text-xs mb-1"
                                >Apply to</label
                            >
                            <div class="flex flex-wrap gap-1">
                                {#each ALL_DAYS as day}
                                    <button
                                        class="btn btn-xs {newRuleDays.includes(
                                            day,
                                        )
                                            ? 'btn-primary'
                                            : 'btn-outline'}"
                                        on:click={() => {
                                            if (newRuleDays.includes(day))
                                                newRuleDays =
                                                    newRuleDays.filter(
                                                        (d) => d !== day,
                                                    );
                                            else
                                                newRuleDays = [
                                                    ...newRuleDays,
                                                    day,
                                                ];
                                        }}
                                    >
                                        {DAY_LABELS[day]}
                                    </button>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <div class="flex gap-2 mt-6">
                        <button
                            class="btn flex-1"
                            on:click={() => (showAddModal = false)}
                            >Cancel</button
                        >
                        <button
                            class="btn btn-primary flex-1"
                            on:click={handleAddRule}>Add Rule</button
                        >
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    @keyframes scale-in {
        from {
            transform: scale(0.95);
            opacity: 0;
        }
        to {
            transform: scale(1);
            opacity: 1;
        }
    }
    .animate-scale-in {
        animation: scale-in 0.15s ease-out;
    }
</style>
