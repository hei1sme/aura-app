<!--
  +page.svelte - Aura Dashboard (Bento Grid Layout)
  
  Main dashboard view with wellness components
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    HydrationCard,
    NextBreakCard,
    ActivityCard,
    FocusRingCard,
    TrainingDataCard
  } from '$lib/components';
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
    pauseUntil
  } from '$lib/stores';
  import {
    onReady,
    onStatus,
    onMetrics,
    onBreakDue,
    onHydrationLogged,
    onTrainingStats,
    onError,
    getStatus,
    triggerTestBreak,
    pauseReminders,
    resumeReminders
  } from '$lib/ipc';
  import type { UnlistenFn } from '@tauri-apps/api/event';
  import { listen } from '@tauri-apps/api/event';
  
  let unlisteners: UnlistenFn[] = [];
  
  // Quick pause functionality
  async function handleQuickPause(minutes: number) {
    try {
      await pauseReminders(minutes);
      isPaused.set(true);
      const until = Date.now() + minutes * 60 * 1000;
      pauseUntil.set(until);
      // Dropdown will auto-close when clicking menu item (DaisyUI behavior)
    } catch (error) {
      console.error('Failed to pause:', error);
    }
  }
  
  async function handleResume() {
    try {
      await resumeReminders();
      isPaused.set(false);
      pauseUntil.set(null);
    } catch (error) {
      console.error('Failed to resume:', error);
    }
  }
  
  function formatPauseRemaining(until: number | null): string {
    if (!until) return '';
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
    console.log('[Page] Setting up event listeners...');
    // Setup event listeners
    unlisteners = await Promise.all([
      onReady((data) => {
        console.log('[Page] onReady callback triggered with:', data);
        sidecarConnected.set(true);
        sidecarVersion.set(data.version);
        console.log('Aura Engine ready:', data);
      }),
      
      onStatus((status) => {
        console.log('[Page] onStatus callback triggered');
        sidecarConnected.set(true); // Mark as connected when we receive status
        updateFromStatus(status);
      }),
      
      onMetrics((metrics) => {
        console.log('[Page] onMetrics callback triggered');
        sidecarConnected.set(true); // Mark as connected when we receive metrics
        updateMetrics(metrics);
      }),
      
      onBreakDue((breakEvent) => {
        setBreakDue(breakEvent);
      }),
      
      onHydrationLogged((data) => {
        updateHydration(data);
      }),
      
      onTrainingStats((stats) => {
        trainingStats.set(stats);
      }),
      
      onError((error) => {
        console.error('Sidecar error:', error.message);
        notifications.update(n => [...n, {
          id: Math.random().toString(36).substring(7),
          type: 'error',
          message: error.message
        }]);
      }),
      
      // Listen for pause/resume events from system tray
      listen('sidecar-paused', (event) => {
        const data = event.payload as { minutes: number };
        console.log('[Page] Paused from tray:', data.minutes, 'minutes');
        isPaused.set(true);
        const until = Date.now() + data.minutes * 60 * 1000;
        pauseUntil.set(until);
      }),
      
      listen('sidecar-resumed', () => {
        console.log('[Page] Resumed from tray');
        isPaused.set(false);
        pauseUntil.set(null);
      })
    ]);
    
    // Request initial status
    try {
      await getStatus();
    } catch (error) {
      console.error('Failed to get initial status:', error);
    }
  });
  
  onDestroy(() => {
    // Cleanup event listeners
    unlisteners.forEach(unlisten => unlisten());
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
          on:click={() => removeNotification(notification.id)}
        >✕</button>
      </div>
    {/each}
  </div>
{/if}

<!-- Main Dashboard -->
<main class="min-h-screen p-6 max-w-6xl mx-auto">
  <!-- Header -->
  <header class="flex items-center justify-between mb-8 animate-fade-in">
    <div>
      <h1 class="text-3xl font-light tracking-tight flex items-center gap-3">
        <span class="text-4xl">🌟</span>
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
      <!-- Quick Pause/Resume Button -->
      <div class="relative">
        {#if $isPaused}
          <button 
            class="btn btn-sm btn-success gap-2"
            on:click={handleResume}
            title="Resume reminders"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
            Resume ({formatPauseRemaining($pauseUntil)})
          </button>
        {:else}
          <div class="dropdown dropdown-end">
            <button 
              tabindex="0"
              class="btn btn-sm btn-ghost gap-2"
              title="Pause reminders"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Pause
            </button>
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow-xl bg-base-200 rounded-box w-52 border border-white/10">
              <li><button on:click={() => handleQuickPause(30)}>⏸️ 30 minutes</button></li>
              <li><button on:click={() => handleQuickPause(60)}>⏸️ 1 hour</button></li>
              <li><button on:click={() => handleQuickPause(120)}>⏸️ 2 hours</button></li>
              <li class="menu-title"><span class="text-xs opacity-50">Extended</span></li>
              <li><button on:click={() => handleQuickPause(480)} class="text-warning">🎬 Movie mode (8h)</button></li>
            </ul>
          </div>
        {/if}
      </div>
      
      <a 
        href="/settings" 
        class="btn btn-ghost btn-circle hover:bg-white/10 transition-all"
        aria-label="Settings"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
        </svg>
      </a>
    </div>
  </header>
  
  <!-- DEV: Test Overlay Button -->
  <div class="mb-4 p-3 glass-card border-dashed border-warning/50">
    <div class="flex items-center justify-between">
      <div>
        <span class="badge badge-warning badge-sm mr-2">DEV</span>
        <span class="text-sm opacity-70">Test break overlay</span>
      </div>
      <div class="flex gap-2">
        <button 
          class="btn btn-sm btn-outline btn-success"
          on:click={() => triggerTestBreak('micro', 20, '#10B981')}
        >
          👁️ Eye Rest
        </button>
        <button 
          class="btn btn-sm btn-outline btn-warning"
          on:click={() => triggerTestBreak('macro', 180, '#F59E0B')}
        >
          🧘 Stretch
        </button>
        <button 
          class="btn btn-sm btn-outline btn-info"
          on:click={() => triggerTestBreak('hydration', 0, '#3B82F6')}
        >
          💧 Hydration
        </button>
      </div>
    </div>
  </div>
  
  <!-- Bento Grid Dashboard -->
  <div class="bento-grid">
    <!-- Row 1: Next Break (span 2) + Focus Ring (span 2, row 2) -->
    <NextBreakCard />
    <div class="bento-item span-2 row-2">
      <FocusRingCard />
    </div>
    
    <!-- Row 2: Hydration (span 2) -->
    <HydrationCard />
    
    <!-- Row 3: Activity + Training Data -->
    <ActivityCard />
    <TrainingDataCard />
  </div>
  
  <!-- Footer -->
  <footer class="mt-10 pt-6 border-t border-white/5 text-center text-xs opacity-40">
    <p>Aura v1.2.0 • Your Intelligent Wellness Companion</p>
    <p class="mt-1">All data stays local. Privacy first. Always.</p>
  </footer>
</main>

<style>
  /* Override bento grid for specific layout */
  .bento-grid {
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: auto;
    gap: 1rem;
  }
  
  /* Focus ring card takes right 2 columns and spans 2 rows */
  .bento-grid > :global(.bento-item.row-2) {
    grid-row: span 2;
  }
  
  @media (max-width: 1024px) {
    .bento-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  
  @media (max-width: 640px) {
    .bento-grid {
      grid-template-columns: 1fr;
    }
    
    .bento-grid > :global(.bento-item.row-2) {
      grid-row: span 1;
    }
  }
</style>
