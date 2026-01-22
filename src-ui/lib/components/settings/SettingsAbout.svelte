<script lang="ts">
    import { sidecarVersion } from "$lib/stores";
    import { check } from "@tauri-apps/plugin-updater";
    import { relaunch } from "@tauri-apps/plugin-process";
    import { onMount } from "svelte";

    // Updater State
    let updateStatus: "idle" | "checking" | "available" | "uptodate" | "error" =
        "idle";
    let updateError = "";
    let updateManifest: any = null;
    let downloadProgress: number | null = null;
    let isDownloading = false;
    let isInstalling = false;
    let installComplete = false;

    async function checkForUpdates() {
        if (isDownloading || isInstalling) return;

        updateStatus = "checking";
        updateError = "";

        try {
            const update = await check();

            if (update?.available) {
                updateStatus = "available";
                updateManifest = update;
                console.log("Update available:", update);
            } else {
                updateStatus = "uptodate";
                // Reset to idle after 3 seconds
                setTimeout(() => {
                    if (updateStatus === "uptodate") updateStatus = "idle";
                }, 3000);
            }
        } catch (error: any) {
            console.error("Update check failed:", error);
            updateStatus = "error";
            updateError = error.message || "Failed to check for updates";
        }
    }

    async function downloadAndInstall() {
        if (!updateManifest) return;

        isDownloading = true;
        downloadProgress = 0;

        try {
            await updateManifest.downloadAndInstall((event: any) => {
                const { event: status, data } = event;

                if (status === "Started") {
                    downloadProgress = 0;
                } else if (status === "Progress") {
                    let total = data.total || 0;
                    let current = data.chunkLength || 0; // Note: this might need adjustment based on library version, simpler to just show spinner
                    // For simply showing progress, we might need cumulative total.
                    // If library doesn't provide easy percentage, we can just show "Downloading..."
                    console.log(`Downloaded ${data.chunkLength} bytes`);
                } else if (status === "Finished") {
                    downloadProgress = 100;
                    isDownloading = false;
                    isInstalling = true;
                }
            });

            isInstalling = false;
            installComplete = true;
        } catch (error: any) {
            console.error("Update failed:", error);
            isDownloading = false;
            isInstalling = false;
            updateStatus = "error";
            updateError = error.message || "Failed to install update";
        }
    }

    async function handleRestart() {
        await relaunch();
    }

    let appVersion = "";
    onMount(() => {
        // If sidecarVersion is available, use it, otherwise fallback (or get app version via tauri api)
        const unsubscribe = sidecarVersion.subscribe((v) => {
            appVersion = v;
        });

        return () => {
            unsubscribe();
        };
    });
</script>

<div class="space-y-8 animate-fade-in">
    <!-- App Header -->
    <div class="flex flex-col items-center justify-center py-8 text-center">
        <div class="relative w-24 h-24 mb-4">
            <div
                class="absolute inset-0 bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 rounded-xl blur-xl"
            ></div>
            <img
                src="/logo.png"
                alt="Aura Logo"
                class="relative w-full h-full object-contain drop-shadow-lg"
            />
        </div>
        <h2 class="text-3xl font-light mb-1 tracking-tight">Aura</h2>
        <p class="text-white/40 font-mono text-sm">v{appVersion || "1.4.0"}</p>
    </div>

    <!-- Update Section -->
    <div
        class="bg-white/5 rounded-2xl p-6 border border-white/5 backdrop-blur-sm"
    >
        <h3 class="text-lg font-medium mb-4 flex items-center gap-2">
            <span class="text-cyan-400">⚡</span> Software Update
        </h3>

        <div class="flex flex-col gap-4">
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-sm font-medium">Current Version</p>
                    <p class="text-xs text-white/50">{appVersion || "1.4.0"}</p>
                </div>

                {#if updateStatus === "idle" || updateStatus === "uptodate" || updateStatus === "error"}
                    <button
                        class="btn btn-sm btn-ghost border border-white/10 hover:bg-white/5"
                        on:click={checkForUpdates}
                        disabled={updateStatus === "checking"}
                    >
                        {#if updateStatus === "checking"}
                            <span class="loading loading-spinner loading-xs"
                            ></span>
                        {/if}
                        Check for Updates
                    </button>
                {/if}
            </div>

            <!-- Status Messages -->
            {#if updateStatus === "checking"}
                <div
                    class="p-3 rounded-lg bg-base-100/50 border border-white/5 text-center text-sm"
                >
                    <span class="loading loading-dots loading-xs mr-2"></span>
                    Checking for updates...
                </div>
            {:else if updateStatus === "uptodate"}
                <div
                    class="p-3 rounded-lg bg-success/10 border border-success/20 text-success text-sm flex items-center justify-center gap-2"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-4 w-4"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                    >
                        <path
                            fill-rule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clip-rule="evenodd"
                        />
                    </svg>
                    Aura is up to date
                </div>
            {:else if updateStatus === "error"}
                <div
                    class="p-3 rounded-lg bg-error/10 border border-error/20 text-error text-sm"
                >
                    <p class="font-bold flex items-center gap-2">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            class="h-4 w-4"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                        >
                            <path
                                fill-rule="evenodd"
                                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                                clip-rule="evenodd"
                            />
                        </svg>
                        Update Check Failed
                    </p>
                    <p class="mt-1 opacity-80">{updateError}</p>
                </div>
            {:else if updateStatus === "available"}
                <div
                    class="bg-cyan-500/10 border border-cyan-500/20 rounded-xl p-4 animate-in fade-in slide-in-from-top-2"
                >
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <h4 class="font-bold text-cyan-400">
                                New Version Available
                            </h4>
                            <p class="text-sm font-mono mt-1">
                                v{updateManifest?.version}
                            </p>
                            <div class="text-xs text-white/50 mt-1">
                                {updateManifest?.date ||
                                    new Date().toLocaleDateString()}
                            </div>
                        </div>
                        <span class="badge badge-accent">New</span>
                    </div>

                    {#if updateManifest?.body}
                        <div
                            class="bg-black/20 rounded p-3 text-xs text-white/70 max-h-32 overflow-y-auto mb-4 whitespace-pre-wrap font-mono"
                        >
                            {updateManifest.body}
                        </div>
                    {/if}

                    {#if installComplete}
                        <div
                            class="bg-success/20 p-4 rounded-lg text-center mb-2"
                        >
                            <h3 class="font-bold text-success mb-2">
                                Update Installed!
                            </h3>
                            <button
                                class="btn btn-success btn-sm w-full"
                                on:click={handleRestart}
                            >
                                Restart Now
                            </button>
                        </div>
                    {:else if isDownloading || isInstalling}
                        <div class="space-y-2">
                            <div
                                class="flex justify-between text-xs opacity-70"
                            >
                                <span
                                    >{isDownloading
                                        ? "Downloading..."
                                        : "Installing..."}</span
                                >
                                {#if downloadProgress !== null}
                                    <span>{Math.round(downloadProgress)}%</span>
                                {/if}
                            </div>
                            <progress
                                class="progress progress-cyan w-full"
                                value={downloadProgress}
                                max="100"
                            ></progress>
                        </div>
                    {:else}
                        <button
                            class="btn btn-primary btn-sm w-full gap-2"
                            on:click={downloadAndInstall}
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                class="h-4 w-4"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                            Download & Install
                        </button>
                    {/if}
                </div>
            {/if}
        </div>
    </div>

    <!-- About Content -->
    <div class="space-y-4">
        <div class="bg-white/5 rounded-xl p-4 border border-white/5">
            <h4 class="text-sm font-medium mb-2 text-white/70">Description</h4>
            <p class="text-sm text-white/50 leading-relaxed">
                Aura is your intelligent wellness companion designed to keep you
                healthy, productive, and focused. It seamlessly integrates into
                your workflow, managing breaks, hydration, and environmental
                awareness to prevent burnout.
            </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <a
                href="https://github.com/hei1sme/aura-app"
                target="_blank"
                rel="noreferrer"
                class="bg-white/5 hover:bg-white/10 transition-colors p-4 rounded-xl border border-white/5 flex flex-col items-center justify-center gap-2 group"
            >
                <svg
                    viewBox="0 0 24 24"
                    class="h-6 w-6 fill-current text-white/70 group-hover:text-white transition-colors"
                >
                    <path
                        d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                    />
                </svg>
                <span
                    class="text-xs font-medium text-white/70 group-hover:text-white"
                    >GitHub</span
                >
            </a>

            <a
                href="https://aura-wellness.app"
                target="_blank"
                rel="noreferrer"
                class="bg-white/5 hover:bg-white/10 transition-colors p-4 rounded-xl border border-white/5 flex flex-col items-center justify-center gap-2 group"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-6 w-6 text-white/70 group-hover:text-white transition-colors"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                    />
                </svg>
                <span
                    class="text-xs font-medium text-white/70 group-hover:text-white"
                    >Website</span
                >
            </a>
        </div>
    </div>

    <!-- Footer Info -->
    <div class="text-center text-xs text-white/20 pt-8 pb-4">
        <p>
            &copy; {new Date().getFullYear()} Aura Wellness. All rights reserved.
        </p>
        <p class="mt-1">Designed with ❤️ for a balanced digital life.</p>
    </div>
</div>
