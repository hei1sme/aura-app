<script lang="ts">
    import { updateSetting } from "$lib/ipc";

    export let settings: any;

    let newBlockedApp = "";

    async function toggleAutoDetect() {
        settings.autoDetectFullscreen = !settings.autoDetectFullscreen;
        await updateSetting(
            "auto_detect_fullscreen",
            String(settings.autoDetectFullscreen),
        );
    }

    async function updateBlocklist() {
        await updateSetting(
            "blocklist_processes",
            JSON.stringify(settings.blockedApps),
        );
    }

    function addBlockedApp() {
        if (newBlockedApp && !settings.blockedApps.includes(newBlockedApp)) {
            settings.blockedApps = [...settings.blockedApps, newBlockedApp];
            newBlockedApp = "";
            updateBlocklist();
        }
    }

    function removeBlockedApp(app: string) {
        settings.blockedApps = settings.blockedApps.filter(
            (a: string) => a !== app,
        );
        updateBlocklist();
    }
</script>

<div class="space-y-6 animate-fade-in">
    <div class="mb-4">
        <h2 class="text-2xl font-light mb-1">Immersive Mode</h2>
        <p class="text-sm opacity-60">
            Suppress breaks during focus time or gaming
        </p>
    </div>

    <div class="glass-card p-0 overflow-hidden">
        <!-- Auto Detect -->
        <div
            class="p-4 border-b border-white/5 flex items-center justify-between"
        >
            <div>
                <div class="font-medium">Auto-detect fullscreen</div>
                <div class="text-xs opacity-60 mt-0.5">
                    Pause reminders when using fullscreen apps
                </div>
            </div>
            <input
                type="checkbox"
                checked={settings.autoDetectFullscreen}
                on:change={toggleAutoDetect}
                class="toggle toggle-primary"
            />
        </div>

        <!-- Timer Mode -->
        <div class="p-4 border-b border-white/5">
            <div class="font-medium mb-3">Timer Mode</div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <!-- Wall Clock (Default) -->
                <label
                    class="cursor-pointer flex items-center gap-3 p-3 rounded-lg border border-white/10 hover:bg-white/5 transition-all"
                    class:bg-primary={settings.timerMode === "wall-clock"}
                    class:bg-opacity-10={settings.timerMode === "wall-clock"}
                    class:border-primary={settings.timerMode === "wall-clock"}
                >
                    <input
                        type="radio"
                        name="timerMode"
                        value="wall-clock"
                        bind:group={settings.timerMode}
                        on:change={() =>
                            updateSetting("timer_mode", "wall-clock")}
                        class="radio radio-primary radio-sm"
                    />
                    <div>
                        <div
                            class="font-medium text-sm flex items-center gap-2"
                        >
                            Wall Clock
                            <span class="badge badge-xs badge-success"
                                >Recommended</span
                            >
                        </div>
                        <div class="text-xs opacity-60">
                            Simple & consistent timing
                        </div>
                    </div>
                </label>

                <!-- Active Time (Advanced) -->
                <label
                    class="cursor-pointer flex items-center gap-3 p-3 rounded-lg border border-white/10 hover:bg-white/5 transition-all"
                    class:bg-primary={settings.timerMode === "active"}
                    class:bg-opacity-10={settings.timerMode === "active"}
                    class:border-primary={settings.timerMode === "active"}
                >
                    <input
                        type="radio"
                        name="timerMode"
                        value="active"
                        bind:group={settings.timerMode}
                        on:change={() => updateSetting("timer_mode", "active")}
                        class="radio radio-primary radio-sm"
                    />
                    <div>
                        <div class="font-medium text-sm">Active Time</div>
                        <div class="text-xs opacity-60">
                            Only counts when typing/clicking
                        </div>
                    </div>
                </label>
            </div>
        </div>
    </div>

    <!-- Blocked Apps -->
    <div class="glass-card p-6">
        <h3 class="font-medium mb-2">Blocked Applications</h3>
        <p class="text-xs opacity-60 mb-4">
            Prevent breaks when these apps are running (e.g., "game.exe")
        </p>

        <div class="flex gap-2 mb-4">
            <input
                type="text"
                placeholder="Process name (e.g. photoshop.exe)"
                bind:value={newBlockedApp}
                class="input input-bordered input-sm flex-1"
                on:keydown={(e) => e.key === "Enter" && addBlockedApp()}
            />
            <button class="btn btn-sm btn-primary" on:click={addBlockedApp}
                >Add</button
            >
        </div>

        <div class="flex flex-wrap gap-2">
            {#each settings.blockedApps as app}
                <span class="badge badge-lg gap-2 py-3 pl-3 pr-1">
                    {app}
                    <button
                        class="btn btn-ghost btn-xs btn-circle h-6 w-6 min-h-0"
                        on:click={() => removeBlockedApp(app)}>✕</button
                    >
                </span>
            {/each}
            {#if settings.blockedApps.length === 0}
                <span class="text-sm opacity-40 italic">No apps blocked</span>
            {/if}
        </div>
    </div>
</div>
