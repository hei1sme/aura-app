<!--
  +page.svelte - Aura Dashboard (Analytics-Focused Layout)
  
  Main dashboard view with wellness analytics and quick controls
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    HeroStatsBar,
    BreakComplianceCard,
    HydrationTrendsCard,
    TodaysTimelineCard,
    FocusDistributionCard,
    ActivityHeatmapCard,
  } from "$lib/components";
  import {
    sidecarConnected,
    sidecarVersion,
    updateFromStatus,
    updateMetrics,
    setBreakDue,
    updateHydration,
    trainingStats,
    notifications,
    removeNotification,
    isPaused,
    pauseUntil,
  } from "$lib/stores";
  import {
    updateBreakStats,
    updateBreaksToday,
    updateBreakHistory,
    updateHydrationHistory,
    updateFocusStats,
    updateActivityHeatmap,
  } from "$lib/stores/analytics";
  import {
    onReady,
    onStatus,
    onMetrics,
    onBreakDue,
    onHydrationLogged,
    onTrainingStats,
    onError,
    onBreakStats,
    onBreaksToday,
    onBreakHistory,
    onHydrationHistory,
    onFocusStats,
    onActivityHeatmap,
    onBreakCompleted,
    onBreakSnoozed,
    onBreakSkipped,
    getStatus,
    getBreakStats,
    getBreaksToday,
    getBreakHistory,
    getHydrationHistory,
    getFocusStats,
    getActivityHeatmap,
    pauseReminders,
    resumeReminders,
  } from "$lib/ipc";
  import type { UnlistenFn } from "@tauri-apps/api/event";
  import { listen } from "@tauri-apps/api/event";

  let unlisteners: UnlistenFn[] = [];

  // DEFAULT_PAUSE_DURATION in minutes
  const DEFAULT_PAUSE_DURATION = 30;

  // One-click pause/resume toggle
  async function togglePauseResume() {
    try {
      if ($isPaused) {
        await resumeReminders();
        isPaused.set(false);
        pauseUntil.set(null);
      } else {
        await pauseReminders(DEFAULT_PAUSE_DURATION);
        isPaused.set(true);
        const until = Date.now() + DEFAULT_PAUSE_DURATION * 60 * 1000;
        pauseUntil.set(until);
      }
    } catch (error) {
      console.error("Failed to toggle pause:", error);
    }
  }

  function formatPauseRemaining(until: number | null): string {
    if (!until) return "";
    const remaining = Math.max(0, until - Date.now());
    const mins = Math.ceil(remaining / 60000);
    if (mins >= 60) {
      const hrs = Math.floor(mins / 60);
      const m = mins % 60;
      return `${hrs}h ${m}m`;
    }
    return `${mins}m`;
  }

  onMount(async () => {
    console.log("[Page] Setting up event listeners...");
    // Setup event listeners
    unlisteners = await Promise.all([
      onReady((data) => {
        console.log("[Page] onReady callback triggered with:", data);
        sidecarConnected.set(true);
        sidecarVersion.set(data.version);
        console.log("Aura Engine ready:", data);
      }),

      onStatus((status) => {
        console.log("[Page] onStatus callback triggered");
        sidecarConnected.set(true);
        updateFromStatus(status);
      }),

      onMetrics((metrics) => {
        console.log("[Page] onMetrics callback triggered");
        sidecarConnected.set(true);
        updateMetrics(metrics);
      }),

      onBreakDue((breakEvent) => {
        setBreakDue(breakEvent);
      }),

      onHydrationLogged((data) => {
        updateHydration(data);
        // Refresh analytics after hydration log
        getBreaksToday();
      }),

      onTrainingStats((stats) => {
        trainingStats.set(stats);
      }),

      onBreakStats((stats) => {
        updateBreakStats(stats);
      }),

      onBreaksToday((breaks) => {
        updateBreaksToday(breaks);
      }),

      onBreakHistory((history) => {
        updateBreakHistory(history);
      }),

      onHydrationHistory((history) => {
        updateHydrationHistory(history);
      }),

      onFocusStats((stats) => {
        updateFocusStats(stats);
      }),

      onActivityHeatmap((heatmap) => {
        updateActivityHeatmap(heatmap);
      }),

      // Real-time updates for break actions
      onBreakCompleted(() => {
        getBreaksToday();
        getBreakStats(7);
        getBreakHistory(7);
      }),

      onBreakSnoozed(() => {
        getBreaksToday();
        getBreakStats(7);
        getBreakHistory(7);
      }),

      onBreakSkipped(() => {
        getBreaksToday();
        getBreakStats(7);
        getBreakHistory(7);
      }),

      onError((error) => {
        console.error("Sidecar error:", error.message);
        notifications.update((n) => [
          ...n,
          {
            id: Math.random().toString(36).substring(7),
            type: "error",
            message: error.message,
          },
        ]);
      }),

      // Listen for pause/resume events from system tray
      listen("sidecar-paused", (event) => {
        const data = event.payload as { minutes: number };
        console.log("[Page] Paused from tray:", data.minutes, "minutes");
        isPaused.set(true);
        const until = Date.now() + data.minutes * 60 * 1000;
        pauseUntil.set(until);
      }),

      listen("sidecar-resumed", () => {
        console.log("[Page] Resumed from tray");
        isPaused.set(false);
        pauseUntil.set(null);
      }),
    ]);

    // Request initial data with retry for analytics
    // Delay ensures sidecar event loop is ready after page navigation
    const fetchAnalyticsData = async () => {
      try {
        await Promise.all([
          getBreakStats(7),
          getBreaksToday(),
          getBreakHistory(7),
          getHydrationHistory(7),
          getFocusStats(7),
          getActivityHeatmap(7),
        ]);
      } catch (error) {
        console.error("Failed to get analytics data:", error);
      }
    };

    try {
      // Wait for event listeners to be fully established
      // This delay is CRITICAL for production builds where timing is tighter
      await new Promise((resolve) => setTimeout(resolve, 300));

      // Fetch status first
      await getStatus();

      // Fetch analytics data
      await fetchAnalyticsData();

      // Progressive retry strategy for production timing issues
      // First retry: 800ms after initial load
      setTimeout(() => {
        fetchAnalyticsData();
      }, 800);

      // Second retry: 1500ms as final fallback
      setTimeout(() => {
        fetchAnalyticsData();
      }, 1500);
    } catch (error) {
      console.error("Failed to get initial data:", error);
    }
  });

  onDestroy(() => {
    // Cleanup event listeners
    unlisteners.forEach((unlisten) => unlisten());
  });
</script>

<svelte:head>
  <title>Aura - Wellness Companion</title>
</svelte:head>

<!-- Notifications Toast -->
{#if $notifications.length > 0}
  <div class="toast toast-end z-50">
    {#each $notifications as notification (notification.id)}
      <div class="alert alert-{notification.type}">
        <span>{notification.message}</span>
        <button
          class="btn btn-xs btn-ghost"
          on:click={() => removeNotification(notification.id)}>✕</button
        >
      </div>
    {/each}
  </div>
{/if}

<!-- Main Dashboard -->
<main class="min-h-screen p-6 max-w-6xl mx-auto">
  <!-- Header -->
  <header class="flex items-center justify-between mb-6 animate-fade-in">
    <div>
      <h1 class="text-3xl font-light tracking-tight flex items-center gap-3">
        <img src="/logo.png" alt="Aura" class="w-10 h-10 object-contain" />
        Aura
      </h1>
      <p class="text-sm opacity-60 ml-12">
        {#if $sidecarConnected}
          <span class="text-success animate-pulse">●</span> Connected
          <span class="ml-2 opacity-40">v{$sidecarVersion}</span>
        {:else}
          <span class="text-warning">●</span> Connecting...
        {/if}
      </p>
    </div>

    <div class="flex items-center gap-3">
      <!-- One-Click Pause/Resume Toggle -->
      <button
        class="btn btn-sm gap-2 transition-all {$isPaused
          ? 'btn-success hover:shadow-lg hover:shadow-cyan-500/30'
          : 'btn-ghost hover:btn-warning hover:shadow-lg hover:shadow-purple-500/30'}"
        on:click={togglePauseResume}
        title={$isPaused
          ? "Click to resume reminders"
          : "Click to pause for 30 minutes"}
        style={$isPaused ? "" : "border: 1px solid rgba(139, 92, 246, 0.3);"}
      >
        {#if $isPaused}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
              clip-rule="evenodd"
            />
          </svg>
          Resume
          <span class="badge badge-sm badge-ghost"
            >{formatPauseRemaining($pauseUntil)}</span
          >
        {:else}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          Pause
        {/if}
      </button>

      <a
        href="/settings"
        class="btn btn-ghost btn-circle hover:bg-white/10 transition-all"
        aria-label="Settings"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
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
    </div>
  </header>

  <!-- Hero Stats Bar -->
  <HeroStatsBar />

  <!-- Analytics Grid (2x2) -->
  <div class="analytics-grid">
    <!-- Row 1 -->
    <BreakComplianceCard />
    <HydrationTrendsCard />

    <!-- Row 2 -->
    <FocusDistributionCard />
    <ActivityHeatmapCard />

    <!-- Row 3 -->
    <div class="row-span-1 col-span-2">
      <TodaysTimelineCard />
    </div>
  </div>

  <!-- Footer -->
  <footer
    class="mt-10 pt-6 border-t border-white/5 text-center text-xs opacity-40"
  >
    <p>Aura v1.3.0 • Your Intelligent Wellness Companion</p>
    <p class="mt-1">All data stays local. Privacy first. Always.</p>
  </footer>
</main>

<style>
  .analytics-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  @media (max-width: 768px) {
    .analytics-grid {
      grid-template-columns: 1fr;
    }

    .col-span-2 {
      grid-column: span 1 / span 1;
    }
  }
</style>
