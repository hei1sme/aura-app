<!--
  Session Hub - The central control panel for Aura work sessions
  
  This compact window shows based on session state:
  - IDLE: "Start Working" button
  - ACTIVE: Next break countdown + Pause button
  - PAUSED: Resume + End Session buttons
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { slide } from "svelte/transition";
  import {
    sessionState,
    nextBreak,
    sidecarConnected,
    sidecarVersion,
    updateFromStatus,
    updateMetrics,
  } from "$lib/stores";
  import {
    startSession,
    pauseSession,
    resumeSession,
    endSession,
    getStatus,
    onStatus,
    onReady,
    onMetrics,
    onScheduleWarning,
    onScheduleActionExecuted,
  } from "$lib/ipc";
  import type { UnlistenFn } from "@tauri-apps/api/event";
  import { WebviewWindow } from "@tauri-apps/api/webviewWindow";

  let unlisteners: UnlistenFn[] = [];

  // Warning Toast State
  let showWarning = false;
  let warningTitle = "";
  let warningSeconds = 0;
  let warningTimer: any = null;

  onMount(async () => {
    // Setup event listeners
    unlisteners = await Promise.all([
      onReady((data) => {
        sidecarConnected.set(true);
        sidecarVersion.set(data.version);
      }),
      onStatus((status) => {
        sidecarConnected.set(true);
        updateFromStatus(status);
      }),
      onMetrics((metrics) => {
        updateMetrics(metrics);
      }),
      onScheduleActionExecuted(() => {
        showWarning = false;
        if (warningTimer) clearInterval(warningTimer);
      }),
      onScheduleWarning((data) => {
        console.log("Schedule warning:", data);
        showWarning = true;
        warningTitle = data.title;
        warningSeconds = data.seconds_remaining;

        if (warningTimer) clearInterval(warningTimer);
        warningTimer = setInterval(() => {
          if (warningSeconds > 0) warningSeconds--;
        }, 1000);
      }),
    ]);

    // Also listen for session state change events directly
    const { listen } = await import("@tauri-apps/api/event");
    console.log("Setting up session event listeners...");

    const sessionStarted = await listen("sidecar-session_started", (event) => {
      console.log("Received sidecar-session_started event:", event);
      sessionState.set("active");
    });
    const sessionPaused = await listen("sidecar-session_paused", () => {
      console.log("Received sidecar-session_paused event");
      sessionState.set("paused");
    });
    const sessionResumed = await listen("sidecar-session_resumed", () => {
      console.log("Received sidecar-session_resumed event");
      sessionState.set("active");
    });
    const sessionEnded = await listen("sidecar-session_ended", () => {
      console.log("Received sidecar-session_ended event");
      sessionState.set("idle");
    });
    unlisteners.push(
      sessionStarted,
      sessionPaused,
      sessionResumed,
      sessionEnded,
    );

    // Request initial status
    try {
      console.log("Requesting initial status...");
      await getStatus();
    } catch (error) {
      console.error("Failed to get status:", error);
    }
  });

  onDestroy(() => {
    unlisteners.forEach((unlisten) => unlisten());
    if (warningTimer) clearInterval(warningTimer);
  });

  // Action handlers
  async function handleStartSession() {
    console.log("Start Working button clicked");
    try {
      console.log("Calling startSession IPC...");
      await startSession();
      console.log("startSession IPC returned");
    } catch (error) {
      console.error("Failed to start session:", error);
    }
  }

  async function handlePauseSession() {
    try {
      await pauseSession();
    } catch (error) {
      console.error("Failed to pause session:", error);
    }
  }

  async function handleResumeSession() {
    try {
      await resumeSession();
    } catch (error) {
      console.error("Failed to resume session:", error);
    }
  }

  async function handleEndSession() {
    try {
      await endSession();
    } catch (error) {
      console.error("Failed to end session:", error);
    }
  }

  async function openFullDashboard() {
    console.log("Attempting to open full dashboard...");
    try {
      const mainWindow = await WebviewWindow.getByLabel("main");
      console.log("Main window reference:", mainWindow);

      if (mainWindow) {
        console.log("Showing main window...");
        await mainWindow.show();
        await mainWindow.setFocus();
        console.log("Main window shown.");

        // Hide the session window
        const sessionWindow = await WebviewWindow.getByLabel("session");
        console.log("Session window reference:", sessionWindow);
        if (sessionWindow) {
          console.log("Hiding session window...");
          await sessionWindow.hide();
        }
      } else {
        console.error("Main window not found!");
      }
    } catch (error) {
      console.error("Failed to open dashboard:", error);
    }
  }

  // Format time as MM:SS
  function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  // Reactive values
  $: breakType = $nextBreak?.type ?? "micro";
  $: breakEmoji =
    breakType === "micro" ? "👁️" : breakType === "macro" ? "🧘" : "💧";
  $: remainingSeconds = $nextBreak?.remaining_seconds ?? 0;
  $: progress =
    remainingSeconds > 0 && $nextBreak
      ? Math.min(
          100,
          (remainingSeconds / ($nextBreak.duration_seconds || 1200)) * 100,
        )
      : 0;
</script>

<svelte:head>
  <title>Aura - Session Hub</title>
</svelte:head>

<main class="session-hub">
  {#if showWarning}
    <div class="warning-toast" transition:slide={{ axis: "y", duration: 300 }}>
      <div class="warning-content">
        <span class="warning-icon">⏱️</span>
        <div class="warning-text">
          <span class="warning-title">{warningTitle}</span>
          <span class="warning-meta">in {warningSeconds}s</span>
        </div>
      </div>
      <button class="warning-close" on:click={() => (showWarning = false)}
        >✕</button
      >
    </div>
  {/if}
  <!-- Header -->
  <header class="hub-header">
    <div class="logo">
      <img src="/logo.png" alt="Aura" class="logo-icon" />
      <span class="title">Aura</span>
    </div>
    <a href="/settings?from=session" class="settings-btn" aria-label="Settings">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="icon"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
          clip-rule="evenodd"
        />
      </svg>
    </a>
  </header>

  <!-- Content based on session state -->
  <div class="hub-content">
    {#if $sessionState === "idle"}
      <!-- IDLE STATE -->
      <div class="state-idle animate-fade-in">
        <div class="welcome-visual">
          <div class="pulse-ring"></div>
          <span class="welcome-emoji">✨</span>
        </div>

        <h2 class="welcome-title">Ready to Focus?</h2>
        <p class="welcome-subtitle">Start your session to track mindfulness</p>

        <button
          class="btn-primary btn-large btn-glow"
          on:click={handleStartSession}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="btn-icon"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
              clip-rule="evenodd"
            />
          </svg>
          Start Session
        </button>

        <div class="secondary-actions">
          <button class="btn-ghost" on:click={openFullDashboard}>
            <span style="opacity: 0.7; margin-right: 4px">📊</span> View Dashboard
          </button>
        </div>
      </div>
    {:else if $sessionState === "active"}
      <!-- ACTIVE STATE -->
      <div class="state-active animate-fade-in">
        <!-- Circular Timer Container -->
        <div class="relative flex items-center justify-center mb-6">
          <!-- SVG Ring -->
          <svg class="w-52 h-52 transform -rotate-90" viewBox="0 0 288 288">
            <!-- Background Ring -->
            <circle
              cx="144"
              cy="144"
              r="135"
              stroke="rgba(255, 255, 255, 0.05)"
              stroke-width="8"
              fill="none"
            />
            <!-- Progress Ring -->
            <circle
              cx="144"
              cy="144"
              r="135"
              stroke={$nextBreak?.theme_color || "#8B5CF6"}
              stroke-width="8"
              fill="none"
              stroke-linecap="round"
              stroke-dasharray="848"
              stroke-dashoffset={848 * (1 - progress / 100)}
              class="transition-all duration-1000 ease-linear shadow-glow"
              style="filter: drop-shadow(0 0 8px {$nextBreak?.theme_color ||
                '#8B5CF6'}80)"
            />
          </svg>

          <!-- Centered Timer Content -->
          <div
            class="absolute inset-0 flex flex-col items-center justify-center"
          >
            <!-- Badge Inside -->
            <div class="focus-badge-minimal mb-2">
              <span class="pulse-dot-small"></span> Focusing
            </div>

            <span class="countdown-time" style="margin-bottom: 0;"
              >{formatTime(remainingSeconds)}</span
            >

            <div class="next-break-info" style="margin-top: 0.2rem;">
              <span class="break-icon" style="font-size: 0.85em"
                >{breakEmoji}</span
              >
              <span style="font-size: 0.85em">Next break</span>
            </div>
          </div>
        </div>

        <div class="controls-grid">
          <button
            class="btn-control btn-pause"
            on:click={handlePauseSession}
            title="Pause Session"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-6 h-6"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>
            <span>Pause</span>
          </button>

          <button
            class="btn-control btn-reset"
            on:click={handleEndSession}
            title="End Session"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="w-6 h-6"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z"
                clip-rule="evenodd"
              />
            </svg>
            <span>End</span>
          </button>
        </div>

        <button class="btn-link" on:click={openFullDashboard}>
          View Full Dashboard
        </button>
      </div>
    {:else if $sessionState === "paused"}
      <!-- PAUSED STATE -->
      <div class="state-paused animate-fade-in">
        <div class="paused-visual">
          <span class="paused-icon-large">⏸️</span>
        </div>

        <h2 class="paused-title">Session Paused</h2>
        <p class="paused-subtitle">Timers paused. Take a breath.</p>

        <button
          class="btn-primary btn-large btn-resume"
          on:click={handleResumeSession}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="btn-icon"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
              clip-rule="evenodd"
            />
          </svg>
          Resume Focus
        </button>

        <button class="btn-text-danger" on:click={handleEndSession}>
          End Session
        </button>
      </div>
    {/if}
  </div>
</main>

<style>
  .session-hub {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    padding: 1.5rem;
    background: linear-gradient(
      135deg,
      rgba(15, 23, 42, 0.98),
      rgba(30, 41, 59, 0.98)
    );
  }

  .hub-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .logo .logo-icon {
    width: 32px;
    height: 32px;
    object-fit: contain;
  }

  .logo .title {
    font-size: 1.25rem;
    font-weight: 300;
    color: white;
  }

  .settings-btn {
    padding: 0.5rem;
    border-radius: 50%;
    color: rgba(255, 255, 255, 0.6);
    transition: all 0.2s;
  }

  .settings-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  .settings-btn .icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  .hub-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .subtitle {
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
  }

  /* Buttons */
  .btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 2rem;
    background: linear-gradient(135deg, #00ffa3, #00d2ff);
    border: none;
    border-radius: 12px;
    color: #0a0a1f;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 4px 15px rgba(0, 255, 163, 0.3);
  }

  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 255, 163, 0.5);
  }

  .btn-primary.btn-large {
    padding: 1.25rem 2.5rem;
    font-size: 1.1rem;
  }

  .btn-primary.btn-success {
    background: linear-gradient(135deg, #10b981, #059669);
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
  }

  .btn-primary.btn-success:hover {
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4);
  }

  .btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.875rem 1.5rem;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    color: white;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 1rem;
  }

  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  .btn-ghost {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.85rem;
    cursor: pointer;
    padding: 0.5rem 1rem;
    transition: all 0.2s;
  }

  .btn-ghost:hover {
    color: white;
  }

  .btn-ghost.btn-danger:hover {
    color: #f87171;
  }

  .btn-icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  .secondary-actions {
    display: flex;
    gap: 1rem;
    margin-top: 1.5rem;
    justify-content: center;
  }

  /* Active state styles */
  .break-label {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
  }

  .countdown-display {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .countdown-time {
    font-size: 3rem;
    font-weight: 200;
    color: white;
    font-variant-numeric: tabular-nums;
  }

  .countdown-emoji {
    font-size: 1.5rem;
  }

  .progress-bar {
    width: 100%;
    max-width: 250px;
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    margin-bottom: 1.5rem;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #00ffa3, #00d2ff);
    border-radius: 2px;
    transition: width 1s linear;
  }

  /* Paused state styles */
  .paused-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .paused-icon {
    font-size: 1.5rem;
  }

  .paused-text {
    font-size: 1.25rem;
    font-weight: 300;
    color: #fbbf24;
  }

  /* Animations */
  .animate-fade-in {
    animation: fadeIn 0.3s ease-out;
  }

  /* Welcome/Idle State Styles */
  .welcome-visual {
    position: relative;
    width: 80px;
    height: 80px;
    margin: 0 auto 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 50%;
  }

  .welcome-emoji {
    font-size: 2.5rem;
    position: relative;
    z-index: 2;
  }

  .pulse-ring {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: 50%;
    border: 2px solid rgba(0, 255, 163, 0.5);
    animation: pulse 2s infinite;
  }

  .welcome-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: white;
    margin: 0 0 0.5rem;
    background: linear-gradient(to right, #fff, #a5b4fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .welcome-subtitle {
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.6);
    margin: 0 0 2rem;
  }

  .btn-glow {
    box-shadow: 0 0 20px rgba(0, 255, 163, 0.4);
    animation: glow-pulse 3s infinite;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 0.5;
    }
    70% {
      transform: scale(1.3);
      opacity: 0;
    }
    100% {
      transform: scale(1);
      opacity: 0;
    }
  }

  @keyframes glow-pulse {
    0% {
      box-shadow: 0 0 20px rgba(0, 255, 163, 0.4);
    }
    50% {
      box-shadow: 0 0 30px rgba(0, 255, 163, 0.7);
    }
    100% {
      box-shadow: 0 0 20px rgba(0, 255, 163, 0.4);
    }
  }

  /* Active State Styles */
  /* Active State Styles */

  @keyframes breathe {
    0% {
      transform: scale(1);
      box-shadow: 0 0 0 rgba(255, 255, 255, 0);
    }
    50% {
      transform: scale(1.05);
      box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
    }
    100% {
      transform: scale(1);
      box-shadow: 0 0 0 rgba(255, 255, 255, 0);
    }
  }

  .focus-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 1rem;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 500;
    color: #c4b5fd;
    margin-bottom: 2rem;
    animation: breathe 4s infinite ease-in-out;
  }

  .pulse-dot {
    width: 6px;
    height: 6px;
    background-color: #a78bfa;
    border-radius: 50%;
    animation: pulse-simple 2s infinite;
    box-shadow: 0 0 5px #a78bfa;
  }

  .focus-badge-minimal {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.2rem 0.6rem;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    color: #c4b5fd;
    animation: breathe 4s infinite ease-in-out;
  }

  .pulse-dot-small {
    width: 4px;
    height: 4px;
    background-color: #a78bfa;
    border-radius: 50%;
    animation: pulse-simple 2s infinite;
    box-shadow: 0 0 4px #a78bfa;
  }

  .timer-container {
    margin-bottom: 2.5rem;
  }

  .countdown-time {
    display: block;
    font-size: 3rem;
    font-weight: 300;
    line-height: 1;
    margin-bottom: 0.25rem;
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
    text-shadow: 0 0 20px rgba(0, 255, 163, 0.2);
    letter-spacing: -1px;
    z-index: 10;
  }

  .next-break-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.7);
    font-weight: 400;
    z-index: 10;
  }

  .state-active,
  .state-paused {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
  }

  .controls-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1rem;
    width: 100%;
    margin-top: 0.5rem;
  }

  .btn-control {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    color: white;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .btn-control:hover {
    background: rgba(255, 255, 255, 0.08);
    transform: translateY(-2px);
    box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .btn-reset:hover {
    background: rgba(239, 68, 68, 0.15);
    border-color: rgba(239, 68, 68, 0.3);
    color: #fca5a5;
  }

  .btn-link {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    font-size: 0.8rem;
    cursor: pointer;
    text-decoration: underline;
    transition: color 0.2s;
    margin: 0 auto;
    display: block;
  }

  .btn-link:hover {
    color: rgba(255, 255, 255, 0.8);
  }

  /* Paused State */
  .paused-visual {
    width: 64px;
    height: 64px;
    margin: 0 auto 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(251, 191, 36, 0.2);
    border-radius: 50%;
  }

  .paused-icon-large {
    font-size: 2rem;
  }

  .paused-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: #fbbf24;
    text-align: center;
  }

  .paused-subtitle {
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 2rem;
    text-align: center;
  }

  .btn-text-danger {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.9rem;
    margin-top: 1rem;
    cursor: pointer;
    transition: color 0.2s;
    display: block;
    margin-left: auto;
    margin-right: auto;
  }

  .btn-text-danger:hover {
    color: #ef4444;
  }

  @keyframes pulse-simple {
    0% {
      opacity: 0.5;
    }
    50% {
      opacity: 1;
    }
    100% {
      opacity: 0.5;
    }
  }

  /* Animations */
  .animate-fade-in {
    animation: fadeIn 0.3s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  /* Warning Toast */
  .warning-toast {
    position: absolute;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15, 23, 42, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(12px);
    padding: 0.75rem 1rem;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 50;
    width: 90%;
    max-width: 320px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  .warning-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
  }

  .warning-icon {
    font-size: 1.25rem;
  }

  .warning-text {
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .warning-title {
    font-weight: 600;
    font-size: 0.9rem;
    color: white;
  }

  .warning-meta {
    font-size: 0.75rem;
    color: #a78bfa;
  }

  .warning-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    cursor: pointer;
    font-size: 1rem;
    padding: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s;
  }

  .warning-close:hover {
    color: white;
  }
</style>
