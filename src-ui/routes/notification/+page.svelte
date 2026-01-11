<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { listen } from "@tauri-apps/api/event";
    import { getCurrentWindow } from "@tauri-apps/api/window";
    import { fade, scale } from "svelte/transition";
    import type { UnlistenFn } from "@tauri-apps/api/event";
    import { invoke } from "@tauri-apps/api/core";

    let title = "Schedule Warning";
    let action = "pause";
    let seconds = 60;
    let timer: any = null;
    let visible = true;
    let unlisten: UnlistenFn | null = null;

    // Format action for display
    $: actionDetails = getActionDetails(action);

    function getActionDetails(act: string) {
        switch (act) {
            case "pause":
                return { icon: "⏸️", label: "Pause Session" };
            case "resume":
                return { icon: "▶️", label: "Resume Session" };
            case "reset":
                return { icon: "🔄", label: "Reset Timers" };
            case "start_session":
                return { icon: "🚀", label: "Start Session" };
            case "end_session":
                return { icon: "🔴", label: "End Session" };
            default:
                return { icon: "⚡", label: "Scheduled Action" };
        }
    }

    // Circular Progress
    $: progress = seconds > 0 ? (seconds / 60) * 100 : 0;
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    $: strokeDashoffset = circumference - (progress / 100) * circumference;

    onMount(async () => {
        const appWindow = getCurrentWindow();

        // Listen for the event from Backend
        unlisten = await listen("show-schedule-warning", (event: any) => {
            console.log("Notification Event Received:", event);
            const data = event.payload;
            title = data.title || "Scheduled Activity";
            action = data.action || "";
            seconds = data.seconds_remaining || 60;
            visible = true;

            // Ensure window is visible (failsafe)
            appWindow.show();

            // Start Countdown
            if (timer) clearInterval(timer);
            timer = setInterval(() => {
                if (seconds > 0) {
                    seconds--;
                } else {
                    clearInterval(timer);
                    dismiss();
                }
            }, 1000);
        });
    });

    onDestroy(() => {
        if (unlisten) unlisten();
        if (timer) clearInterval(timer);
    });

    async function dismiss() {
        // Hiding logic
        try {
            const appWindow = getCurrentWindow();
            // Hide immediately
            await appWindow.hide();
            // Reset state after hide
            visible = false;
        } catch (e) {
            console.error("Failed to hide window:", e);
        }
    }
</script>

{#if visible}
    <div class="card" in:scale={{ duration: 300, start: 0.95 }} out:fade>
        <!-- Header -->
        <div class="header">
            <span class="app-name">AURA</span>
        </div>

        <!-- Content -->
        <div class="body">
            <div class="ring-container">
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <!-- Track -->
                    <circle
                        cx="60"
                        cy="60"
                        r={radius}
                        fill="none"
                        stroke="rgba(255,255,255,0.1)"
                        stroke-width="8"
                    />
                    <!-- Progress -->
                    <circle
                        cx="60"
                        cy="60"
                        r={radius}
                        fill="none"
                        stroke="#F59E0B"
                        stroke-width="8"
                        stroke-linecap="round"
                        stroke-dasharray={circumference}
                        stroke-dashoffset={strokeDashoffset}
                        transform="rotate(-90 60 60)"
                        style="transition: stroke-dashoffset 1s linear;"
                    />
                </svg>
                <div class="timer-value">
                    <span class="seconds">{seconds}</span>
                    <span class="label">sec</span>
                </div>
            </div>

            <div class="text-container">
                <h3 class="event-title">{title}</h3>
                <div class="action-row">
                    <span class="action-icon">{actionDetails.icon}</span>
                    <span class="action-label">{actionDetails.label}</span>
                </div>
            </div>
        </div>

        <!-- Footer Actions -->
        <div class="footer">
            <button class="btn-dismiss" on:click={dismiss}>Dismiss</button>
        </div>
    </div>
{/if}

<style>
    /* Global Overrides */
    :global(body) {
        background: transparent !important;
        margin: 0;
        padding: 0;
        overflow: hidden;
        font-family: "Inter", sans-serif;
        user-select: none;
    }
    :global(.debug-toggle),
    :global(.debug-overlay) {
        display: none !important;
    }
    :global(.app-container) {
        min-height: auto !important;
        background: transparent !important;
    }

    .card {
        width: 100%;
        height: 100vh;
        background: rgba(
            15,
            23,
            42,
            0.95
        ); /* Slightly darker for better contrast */
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        color: white;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
        box-sizing: border-box;
    }

    .header {
        display: flex;
        justify-content: center;
        padding: 14px 0;
        background: linear-gradient(
            to bottom,
            rgba(255, 255, 255, 0.03),
            transparent
        );
    }

    .app-name {
        font-size: 0.7rem;
        font-weight: 700;
        color: rgba(255, 255, 255, 0.3);
        letter-spacing: 2px;
    }

    .body {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px; /* Compact gap */
        padding: 0 16px;
    }

    .ring-container {
        position: relative;
        width: 120px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .timer-value {
        position: absolute;
        display: flex;
        flex-direction: column;
        align-items: center;
        line-height: 1;
    }

    .seconds {
        font-size: 2.75rem; /* Larger */
        font-weight: 700;
        color: #f59e0b;
        font-variant-numeric: tabular-nums;
        text-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
    }

    .label {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
        margin-top: -4px;
    }

    .text-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        width: 100%;
    }

    .event-title {
        margin: 0;
        font-size: 1.25rem; /* Larger Title */
        font-weight: 600;
        text-align: center;
        color: white;
        line-height: 1.2;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .action-row {
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 255, 255, 0.08); /* Authentic pill look */
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .action-icon {
        font-size: 1rem;
    }
    .action-label {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 500;
    }

    .footer {
        padding: 16px 20px 20px;
        display: flex;
        justify-content: center; /* Center the button container */
        align-items: center;
    }

    button {
        width: auto;
        min-width: 140px;
        margin: 0 auto;
        /* Flexbox Centering */
        display: flex;
        justify-content: center;
        align-items: center;

        border: none;
        padding: 10px 24px;
        border-radius: 20px;
        font-size: 0.95rem;
        font-weight: 600;
        text-align: center; /* Ensure text is centered */
        cursor: pointer;
        transition: all 0.2s;
    }
    button:active {
        transform: scale(0.98);
    }

    .btn-dismiss {
        background: #f59e0b;
        color: #1a0f02;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
    }
    .btn-dismiss:hover {
        background: #fbbf24;
        box-shadow: 0 6px 16px rgba(245, 158, 11, 0.3);
    }
</style>
