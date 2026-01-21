<script lang="ts">
    import { updateSetting, enableAutostart, disableAutostart } from "$lib/ipc";

    export let settings: any;

    async function toggleAutoStart() {
        settings.autoStart = !settings.autoStart;
        try {
            await updateSetting("auto_start", String(settings.autoStart));
            if (settings.autoStart) {
                await enableAutostart();
            } else {
                await disableAutostart();
            }
        } catch (e) {
            console.error("Failed to update auto_start:", e);
            // Revert on failure
            settings.autoStart = !settings.autoStart;
        }
    }

    async function toggleCloseToTray() {
        settings.closeToTray = !settings.closeToTray;
        await updateSetting("close_to_tray", String(settings.closeToTray));
    }

    async function toggleSound() {
        settings.soundEnabled = !settings.soundEnabled;
        await updateSetting("sound_enabled", String(settings.soundEnabled));
    }
</script>

<div class="space-y-6 animate-fade-in">
    <div class="mb-4">
        <h2 class="text-2xl font-light mb-1">General</h2>
        <p class="text-sm opacity-60">
            Application behavior and system integration
        </p>
    </div>

    <div class="glass-card p-0 overflow-hidden">
        <!-- Auto Start -->
        <div
            class="p-4 border-b border-white/5 flex items-center justify-between"
        >
            <div>
                <div class="font-medium">Start with system</div>
                <div class="text-xs opacity-60 mt-0.5">
                    Launch Aura automatically on login
                </div>
            </div>
            <input
                type="checkbox"
                checked={settings.autoStart}
                on:change={toggleAutoStart}
                class="toggle toggle-primary"
            />
        </div>

        <!-- Close to Tray -->
        <div
            class="p-4 border-b border-white/5 flex items-center justify-between"
        >
            <div>
                <div class="font-medium">Close to system tray</div>
                <div class="text-xs opacity-60 mt-0.5">
                    Keep running in background when window is closed
                </div>
            </div>
            <input
                type="checkbox"
                checked={settings.closeToTray}
                on:change={toggleCloseToTray}
                class="toggle toggle-primary"
            />
        </div>

        <!-- Sound -->
        <div class="p-4 flex items-center justify-between">
            <div>
                <div class="font-medium">Sound notifications</div>
                <div class="text-xs opacity-60 mt-0.5">
                    Play a gentle sound for break reminders
                </div>
            </div>
            <input
                type="checkbox"
                checked={settings.soundEnabled}
                on:change={toggleSound}
                class="toggle toggle-primary"
            />
        </div>
    </div>
</div>
