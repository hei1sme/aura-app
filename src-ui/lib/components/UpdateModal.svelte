<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { relaunch } from "@tauri-apps/plugin-process";
    import { fade, scale } from "svelte/transition";

    export let updateData: any = null;

    const dispatch = createEventDispatcher();

    // State
    let downloadProgress: number | null = null;
    let isDownloading = false;
    let isInstalling = false;
    let installComplete = false;
    let error = "";

    async function handleUpdate() {
        if (!updateData) return;

        isDownloading = true;
        downloadProgress = 0;
        error = "";

        try {
            await updateData.downloadAndInstall((event: any) => {
                const { event: status, data } = event;

                if (status === "Started") {
                    downloadProgress = 0;
                } else if (status === "Progress") {
                    // Tauri updater provides chunk info
                    console.log(`Downloaded ${data.chunkLength} bytes`);
                } else if (status === "Finished") {
                    downloadProgress = 100;
                    isDownloading = false;
                    isInstalling = true;
                }
            });

            isInstalling = false;
            installComplete = true;
        } catch (e: any) {
            console.error("Update failed:", e);
            isDownloading = false;
            isInstalling = false;
            error = e.message || "Failed to install update";
        }
    }

    async function handleRestart() {
        await relaunch();
    }

    function handleLater() {
        dispatch("later");
    }

    function handleSkip() {
        // Save skipped version to localStorage
        if (updateData?.version) {
            localStorage.setItem("aura_skip_version", updateData.version);
        }
        dispatch("skip");
    }

    function handleClose() {
        if (!isDownloading && !isInstalling) {
            dispatch("close");
        }
    }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
    class="modal-backdrop"
    transition:fade={{ duration: 200 }}
    on:click={handleClose}
>
    <div
        class="modal-container"
        transition:scale={{ duration: 250, start: 0.95 }}
        on:click|stopPropagation
    >
        <!-- Header -->
        <div class="modal-header">
            <div class="header-icon">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"
                    />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
            </div>
            <div class="header-text">
                <h2>Update Available</h2>
                <p class="version-info">
                    Version <span class="version">{updateData?.version}</span> is
                    ready
                </p>
            </div>
        </div>

        <!-- Release Notes -->
        {#if updateData?.body}
            <div class="release-notes">
                <h4>What's New</h4>
                <div class="notes-content">
                    {updateData.body}
                </div>
            </div>
        {/if}

        <!-- Error Message -->
        {#if error}
            <div class="error-message">
                <span class="error-icon">⚠️</span>
                {error}
            </div>
        {/if}

        <!-- Progress -->
        {#if isDownloading || isInstalling}
            <div class="progress-section">
                <div class="progress-text">
                    {isDownloading ? "Downloading..." : "Installing..."}
                </div>
                <div class="progress-bar">
                    <div
                        class="progress-fill"
                        class:indeterminate={isInstalling}
                        style="width: {downloadProgress ?? 0}%"
                    ></div>
                </div>
            </div>
        {/if}

        <!-- Actions -->
        <div class="modal-actions">
            {#if installComplete}
                <button class="btn btn-primary full-width" on:click={handleRestart}>
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        class="btn-icon"
                    >
                        <path d="M23 4v6h-6" />
                        <path
                            d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"
                        />
                    </svg>
                    Restart Now
                </button>
            {:else if isDownloading || isInstalling}
                <div class="status-text">Please wait...</div>
            {:else}
                <button class="btn btn-primary" on:click={handleUpdate}>
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        class="btn-icon"
                    >
                        <path
                            d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"
                        />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    Update Now
                </button>
                <button class="btn btn-ghost" on:click={handleLater}>
                    Remind Me Later
                </button>
                <button class="btn btn-text" on:click={handleSkip}>
                    Skip This Version
                </button>
            {/if}
        </div>
    </div>
</div>

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    }

    .modal-container {
        background: linear-gradient(
            135deg,
            rgba(30, 41, 59, 0.95) 0%,
            rgba(15, 23, 42, 0.98) 100%
        );
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2rem;
        width: 90%;
        max-width: 420px;
        box-shadow:
            0 25px 50px -12px rgba(0, 0, 0, 0.5),
            0 0 0 1px rgba(255, 255, 255, 0.05);
    }

    .modal-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .header-icon {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #06b6d4, #3b82f6);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .header-icon svg {
        width: 24px;
        height: 24px;
        color: white;
    }

    .header-text h2 {
        font-size: 1.25rem;
        font-weight: 600;
        color: white;
        margin: 0 0 0.25rem 0;
    }

    .version-info {
        font-size: 0.875rem;
        color: rgba(255, 255, 255, 0.6);
        margin: 0;
    }

    .version {
        color: #06b6d4;
        font-weight: 600;
        font-family: ui-monospace, monospace;
    }

    .release-notes {
        background: rgba(0, 0, 0, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }

    .release-notes h4 {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: rgba(255, 255, 255, 0.5);
        margin: 0 0 0.75rem 0;
    }

    .notes-content {
        font-size: 0.875rem;
        color: rgba(255, 255, 255, 0.8);
        line-height: 1.6;
        max-height: 150px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: ui-monospace, monospace;
    }

    .error-message {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.875rem;
        color: #fca5a5;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .progress-section {
        margin-bottom: 1.5rem;
    }

    .progress-text {
        font-size: 0.875rem;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 0.5rem;
    }

    .progress-bar {
        height: 6px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #06b6d4, #3b82f6);
        border-radius: 3px;
        transition: width 0.3s ease;
    }

    .progress-fill.indeterminate {
        width: 100% !important;
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0%,
        100% {
            opacity: 0.5;
        }
        50% {
            opacity: 1;
        }
    }

    .modal-actions {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        border: none;
    }

    .btn-icon {
        width: 18px;
        height: 18px;
    }

    .btn-primary {
        background: linear-gradient(135deg, #06b6d4, #3b82f6);
        color: white;
    }

    .btn-primary:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(6, 182, 212, 0.4);
    }

    .btn-ghost {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .btn-ghost:hover {
        background: rgba(255, 255, 255, 0.12);
    }

    .btn-text {
        background: transparent;
        color: rgba(255, 255, 255, 0.5);
        padding: 0.5rem;
    }

    .btn-text:hover {
        color: rgba(255, 255, 255, 0.8);
    }

    .full-width {
        width: 100%;
    }

    .status-text {
        text-align: center;
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.875rem;
        padding: 0.75rem;
    }
</style>
