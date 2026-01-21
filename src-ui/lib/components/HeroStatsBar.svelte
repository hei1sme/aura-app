<!--
  HeroStatsBar.svelte - Quick Stats Overview Bar
  
  Compact horizontal bar showing key metrics at a glance
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    nextBreak,
    isPaused,
    hydrationPercent,
    activityMetrics,
    schedulerStatus,
  } from "$lib/stores";
  import { breakStats, breaksToday } from "$lib/stores/analytics";

  // Local countdown that ticks every second
  let displaySeconds = 0;
  let tickInterval: ReturnType<typeof setInterval> | null = null;

  // Format seconds as MM:SS
  function formatTime(totalSeconds: number): string {
    if (totalSeconds <= 0) return "00:00";
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  // Format active time
  function formatActiveTime(totalSecs: number): string {
    const hours = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  }

  // Sync with backend
  $: if ($nextBreak) {
    const backendSeconds = $nextBreak.remaining_seconds;
    const diff = Math.abs(displaySeconds - backendSeconds);
    if (diff > 2 || displaySeconds === 0) {
      displaySeconds = backendSeconds;
    }
  }

  // Calculate today's break count
  $: todayBreakCount = $breaksToday.filter((b) => b.completed).length;

  // Calculate wellness score
  $: breakProgress = $schedulerStatus?.breaks?.micro?.progress ?? 0;
  $: wellnessScore = Math.round(
    $hydrationPercent * 0.4 + (1 - breakProgress) * 100 * 0.6,
  );

  $: wellnessColor =
    wellnessScore >= 70
      ? "var(--aura-eye-care)"
      : wellnessScore >= 40
        ? "var(--aura-stretch)"
        : "var(--color-error)";

  onMount(() => {
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
</script>

<div class="hero-stats-bar">
  <!-- Next Break -->
  <div class="stat-pill" class:paused={$isPaused}>
    <span class="stat-value text-lg font-light tabular-nums">
      {#if $isPaused}
        ⏸️
      {:else}
        {formatTime(displaySeconds)}
      {/if}
    </span>
    <span class="stat-label">Next Break</span>
  </div>

  <!-- Hydration -->
  <div class="stat-pill">
    <span class="stat-value text-lg font-light text-info"
      >{$hydrationPercent}%</span
    >
    <span class="stat-label">💧 Hydration</span>
  </div>

  <!-- Breaks Today -->
  <div class="stat-pill">
    <span class="stat-value text-lg font-light text-success"
      >{todayBreakCount}</span
    >
    <span class="stat-label">✅ Breaks</span>
  </div>

  <!-- Active Time -->
  <div class="stat-pill">
    <span class="stat-value text-lg font-light text-warning">
      {formatActiveTime($activityMetrics.active_time_seconds)}
    </span>
    <span class="stat-label">⚡ Active</span>
  </div>

  <!-- Wellness Progress -->
  <div class="stat-pill wellness-pill flex-1">
    <div class="wellness-bar-container">
      <div class="flex justify-between items-center mb-1">
        <span class="stat-label">Daily Wellness</span>
        <span class="text-sm font-medium" style="color: {wellnessColor}"
          >{wellnessScore}%</span
        >
      </div>
      <div class="wellness-bar">
        <div
          class="wellness-bar-fill"
          style="width: {wellnessScore}%; background: {wellnessColor}"
        ></div>
      </div>
    </div>
  </div>
</div>

<style>
  .hero-stats-bar {
    display: flex;
    gap: 0.75rem;
    padding: 1rem;
    background: linear-gradient(
      135deg,
      rgba(139, 92, 246, 0.12),
      rgba(59, 130, 246, 0.08)
    );
    border-radius: 1rem;
    border: 1px solid rgba(139, 92, 246, 0.2);
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.15);
  }

  .stat-pill {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.25rem;
    background: rgba(139, 92, 246, 0.08);
    border-radius: 0.75rem;
    min-width: 85px;
    border: 1px solid rgba(139, 92, 246, 0.15);
    transition: all 0.2s ease;
    position: relative;
  }

  .stat-pill:hover {
    background: rgba(139, 92, 246, 0.15);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
  }

  .stat-pill.paused {
    opacity: 0.6;
  }

  .stat-value {
    font-variant-numeric: tabular-nums;
  }

  .stat-label {
    font-size: 0.7rem;
    opacity: 0.6;
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .wellness-pill {
    min-width: 180px;
    align-items: stretch;
    padding: 0.75rem 1rem;
  }

  .wellness-bar-container {
    width: 100%;
  }

  .wellness-bar {
    height: 6px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 9999px;
    overflow: hidden;
  }

  .wellness-bar-fill {
    height: 100%;
    border-radius: 9999px;
    transition:
      width 0.5s ease,
      background 0.3s ease;
    box-shadow: 0 0 10px currentColor;
  }

  @media (max-width: 768px) {
    .hero-stats-bar {
      gap: 0.5rem;
    }

    .stat-pill {
      min-width: 70px;
      padding: 0.5rem 0.75rem;
    }

    .wellness-pill {
      width: 100%;
      order: -1;
    }
  }
</style>
