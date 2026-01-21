<script lang="ts">
    import { exportData } from "$lib/ipc";

    let exportMessage = "";

    async function handleExportData() {
        try {
            const result = await exportData("aura_training_data.csv");
            // @ts-ignore - result type might vary based on IPC imp
            exportMessage = `Exported to ${result.path || "file"}`;
            setTimeout(() => (exportMessage = ""), 5000);
        } catch (error) {
            console.error("Failed to export data:", error);
        }
    }
</script>

<div class="space-y-6 animate-fade-in">
    <div class="mb-4">
        <h2 class="text-2xl font-light mb-1">Data & Privacy</h2>
        <p class="text-sm opacity-60">Manage your local data</p>
    </div>

    <div class="glass-card p-6">
        <div class="flex items-start gap-4 mb-6">
            <div class="p-3 bg-primary/10 rounded-full text-2xl">🔒</div>
            <div>
                <h3 class="font-medium text-lg">Local First</h3>
                <p class="text-sm opacity-70 mt-1">
                    Your data is stored locally on your device in <code
                        class="bg-base-300 px-1 rounded">~/.aura/aura.db</code
                    >. Aura never sends your activity data to external servers.
                </p>
            </div>
        </div>

        <div class="divider opacity-10"></div>

        <h3 class="font-medium mb-3">Data Management</h3>
        <div class="flex flex-wrap gap-3">
            <button class="btn btn-outline" on:click={handleExportData}>
                Export Activity Data (CSV)
            </button>
            <button class="btn btn-outline btn-error"> Clear All Data </button>
        </div>

        {#if exportMessage}
            <div
                class="mt-4 p-3 bg-success/10 text-success rounded-lg text-sm flex items-center gap-2"
            >
                <span>✓</span>
                {exportMessage}
            </div>
        {/if}
    </div>
</div>
