<!--
  NextBreakCard.svelte - Upcoming Break Countdown
  
  Shows time until next break and break type
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { nextBreak, isPaused } from '$lib/stores';
  import { getBreakTypeName, getBreakThemeClass, formatDuration } from '$lib/ipc';
  import { pauseReminders, resumeReminders } from '$lib/ipc';
  
  // Local countdown that ticks every second
  let displaySeconds = 0;
  let tickInterval: ReturnType<typeof setInterval> | null = null;
  let lastSyncedType: string | null = null;
  
  // Format seconds as MM:SS
  function formatTime(totalSeconds: number): string {
    if (totalSeconds <= 0) return '00:00';
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  // FIXED: Only sync with backend when there's a significant difference
  // This prevents flickering caused by timing mismatch between frontend tick and backend emit
  $: if ($nextBreak) {
    const backendSeconds = $nextBreak.remaining_seconds;
    const diff = Math.abs(displaySeconds - backendSeconds);
    
    // Only sync if:
    // 1. Break type changed (different break countdown)
    // 2. Difference is more than 2 seconds (significant drift)
    // 3. Backend is ahead (timer was reset/extended)
    // 4. First time sync (displaySeconds is 0 or lastSyncedType is different)
    const typeChanged = lastSyncedType !== $nextBreak.type;
    const significantDrift = diff > 2;
    const backendAhead = backendSeconds > displaySeconds + 1;
    const firstSync = displaySeconds === 0 || typeChanged;
    
    if (firstSync || significantDrift || backendAhead) {
      displaySeconds = backendSeconds;
      lastSyncedType = $nextBreak.type;
    }
  }
  
  onMount(() => {
    // Tick every second for smooth countdown
    tickInterval = setInterval(() => {
      if (!$isPaused && displaySeconds > 0) {
        displaySeconds -= 1;
      }
    }, 1000);
  });
  
  onDestroy(() => {
    if (tickInterval) {
      clearInterval(tickInterval);
    }
  });
  
  async function togglePause() {
    try {
      if ($isPaused) {
        await resumeReminders();
      } else {
        await pauseReminders(60); // Pause for 1 hour
      }
    } catch (error) {
      console.error('Failed to toggle pause:', error);
    }
  }
</script>

<div class="bento-item span-2 {$nextBreak ? getBreakThemeClass($nextBreak.type) : ''}">
  <div class="flex items-center justify-between mb-2">
    <h3 class="text-label">Next Break</h3>
    <button 
      class="btn btn-xs btn-ghost"
      on:click={togglePause}
    >
      {#if $isPaused}
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
        </svg>
        Resume
      {:else}
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        Pause 1h
      {/if}
    </button>
  </div>
  
  <div class="flex items-baseline gap-4">
    {#if $isPaused}
      <span class="text-display text-base-content/50">PAUSED</span>
    {:else if $nextBreak}
      <span class="text-display">{formatTime(displaySeconds)}</span>
      <div class="flex flex-col">
        <span class="text-lg font-medium" style="color: {$nextBreak.theme_color}">
          {getBreakTypeName($nextBreak.type)}
        </span>
        <span class="text-xs opacity-60">
          {formatDuration($nextBreak.duration_seconds)} break
        </span>
      </div>
    {:else}
      <span class="text-display text-base-content/30">--:--</span>
    {/if}
  </div>
</div>

<style>
  .text-display {
    font-variant-numeric: tabular-nums;
  }
</style>
