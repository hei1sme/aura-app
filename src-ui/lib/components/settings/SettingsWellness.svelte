<script lang="ts">
    import { updateSetting } from "$lib/ipc";

    export let settings: any;

    let isSaving = false;
    let saveMessage = "";

    // Helper to format duration display
    function formatDuration(seconds: number): string {
        if (seconds >= 60) {
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
        }
        return `${seconds}s`;
    }

    async function saveWellnessSettings() {
        isSaving = true;
        try {
            await updateSetting(
                "micro_break_interval",
                String(settings.microBreakInterval * 60),
            );
            await updateSetting(
                "macro_break_interval",
                String(settings.macroBreakInterval * 60),
            );
            await updateSetting(
                "macro_break_duration",
                String(settings.macroBreakDuration),
            );
            await updateSetting(
                "hydration_interval",
                String(settings.hydrationInterval * 60),
            );
            await updateSetting("water_goal", String(settings.dailyWaterGoal));

            saveMessage = "Saved!";
            setTimeout(() => (saveMessage = ""), 2000);
        } catch (e) {
            console.error("Failed to save wellness settings:", e);
        } finally {
            isSaving = false;
        }
    }
</script>

<div class="space-y-6 animate-fade-in">
    <div class="mb-4">
        <h2 class="text-2xl font-light mb-1">Wellness</h2>
        <p class="text-sm opacity-60">
            Configure your break intervals and hydration goals
        </p>
    </div>

    <div class="glass-card space-y-8 p-6">
        <!-- Micro Break -->
        <div>
            <div class="flex justify-between items-center mb-2">
                <label class="label-text flex items-center gap-2 font-medium">
                    <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
                    Eye Rest Interval
                </label>
                <span class="font-mono text-sm bg-base-300 px-2 py-1 rounded">
                    {settings.microBreakInterval} min
                </span>
            </div>
            <input
                type="range"
                min="10"
                max="40"
                bind:value={settings.microBreakInterval}
                class="range range-success range-sm"
            />
            <div class="text-xs opacity-50 mt-1">
                Short 20s breaks to rest your eyes
            </div>
        </div>

        <!-- Macro Break -->
        <div>
            <div class="flex justify-between items-center mb-2">
                <label class="label-text flex items-center gap-2 font-medium">
                    <span class="w-3 h-3 rounded-full bg-amber-500"></span>
                    Stretch Break Interval
                </label>
                <span class="font-mono text-sm bg-base-300 px-2 py-1 rounded">
                    {settings.macroBreakInterval} min
                </span>
            </div>
            <input
                type="range"
                min="30"
                max="90"
                step="5"
                bind:value={settings.macroBreakInterval}
                class="range range-warning range-sm"
            />
            <div class="text-xs opacity-50 mt-1">
                How often you'll be reminded to stretch
            </div>
        </div>

        <!-- Stretch Break Duration -->
        <div>
            <div class="flex justify-between items-center mb-2">
                <label class="label-text flex items-center gap-2 font-medium">
                    <span class="w-3 h-3 rounded-full bg-amber-500/50"></span>
                    Stretch Break Duration
                </label>
                <span class="font-mono text-sm bg-base-300 px-2 py-1 rounded">
                    {formatDuration(settings.macroBreakDuration)}
                </span>
            </div>
            <input
                type="range"
                min="30"
                max="300"
                step="30"
                bind:value={settings.macroBreakDuration}
                class="range range-warning range-sm opacity-70"
            />
            <div class="text-xs opacity-50 mt-1">
                How long the stretch break countdown lasts (30s - 5min)
            </div>
        </div>

        <!-- Hydration -->
        <div>
            <div class="flex justify-between items-center mb-2">
                <label class="label-text flex items-center gap-2 font-medium">
                    <span class="w-3 h-3 rounded-full bg-blue-500"></span>
                    Hydration Reminder
                </label>
                <span class="font-mono text-sm bg-base-300 px-2 py-1 rounded">
                    {settings.hydrationInterval} min
                </span>
            </div>
            <input
                type="range"
                min="15"
                max="60"
                step="5"
                bind:value={settings.hydrationInterval}
                class="range range-info range-sm"
            />
        </div>

        <!-- Water Goal -->
        <div>
            <div class="flex justify-between items-center mb-2">
                <label class="label-text font-medium">Daily Water Goal</label>
                <span class="font-mono text-sm bg-base-300 px-2 py-1 rounded">
                    {settings.dailyWaterGoal} ml
                </span>
            </div>
            <input
                type="range"
                min="1000"
                max="4000"
                step="250"
                bind:value={settings.dailyWaterGoal}
                class="range range-info range-sm"
            />
        </div>
    </div>

    <div class="flex justify-end items-center gap-3">
        {#if saveMessage}
            <span class="text-sm text-success animate-fade-in"
                >{saveMessage}</span
            >
        {/if}
        <button
            class="btn btn-primary"
            class:loading={isSaving}
            on:click={saveWellnessSettings}
        >
            Save Changes
        </button>
    </div>
</div>
