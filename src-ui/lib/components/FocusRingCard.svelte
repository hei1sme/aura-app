<!--
  FocusRingCard.svelte - Daily Focus Progress
  
  Central visual indicator of daily wellness progress
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import ProgressRing from './ProgressRing.svelte';
  import { schedulerStatus, hydrationPercent, activityMetrics } from '$lib/stores';
  
  // Local active time that ticks every second
  let displayActiveSeconds = 0;
  let tickInterval: ReturnType<typeof setInterval> | null = null;
  
  // Format seconds as MM:SS or HH:MM:SS
  function formatActiveTime(totalSecs: number): string {
    const hours = Math.floor(totalSecs / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);
    const secs = totalSecs % 60;
    
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  
  // Sync with store updates
  $: if ($activityMetrics.active_time_seconds !== undefined) {
    displayActiveSeconds = $activityMetrics.active_time_seconds;
  }
  
  onMount(() => {
    // Tick every second when active
    tickInterval = setInterval(() => {
      if ($activityMetrics.state === 'active' || $activityMetrics.state === 'immersive') {
        displayActiveSeconds += 1;
      }
    }, 1000);
  });
  
  onDestroy(() => {
    if (tickInterval) {
      clearInterval(tickInterval);
    }
  });
  
  // Calculate overall wellness score based on multiple factors
  $: breakProgress = $schedulerStatus?.breaks?.micro?.progress ?? 0;
  $: hydrationScore = $hydrationPercent;
  
  // Combined wellness score (simplified for Phase 1)
  $: wellnessScore = Math.round(
    (hydrationScore * 0.4) + // 40% hydration
    ((1 - breakProgress) * 100 * 0.6) // 60% break compliance (inverse of progress to next break)
  );
  
  $: scoreColor = wellnessScore >= 70 ? 'var(--aura-eye-care)' : 
                  wellnessScore >= 40 ? 'var(--aura-stretch)' : 
                  'var(--color-error)';
  
  $: scoreLabel = wellnessScore >= 80 ? 'Excellent' :
                  wellnessScore >= 60 ? 'Good' :
                  wellnessScore >= 40 ? 'Fair' :
                  'Needs Attention';
  
  $: stateEmoji = $activityMetrics.state === 'immersive' ? '🎮' :
                  $activityMetrics.state === 'active' ? '⚡' :
                  '😴';
</script>

<div class="focus-card bento-item row-2 flex flex-col items-center justify-center text-center">
  <h3 class="text-label mb-2">Daily Focus</h3>
  <span class="text-xs opacity-40 mb-4">{stateEmoji} {$activityMetrics.state}</span>
  
  <div class="ring-container">
    <ProgressRing 
      progress={wellnessScore}
      size={180}
      strokeWidth={8}
      color={scoreColor}
    >
      <div class="flex flex-col items-center">
        <span class="text-5xl font-thin tracking-tight" style="color: {scoreColor}">
          {wellnessScore}
        </span>
        <span class="text-xs opacity-60 mt-1">{scoreLabel}</span>
      </div>
    </ProgressRing>
    
    <!-- Decorative outer glow -->
    <div 
      class="absolute inset-0 rounded-full opacity-20 blur-xl"
      style="background: radial-gradient(circle, {scoreColor} 0%, transparent 70%)"
    ></div>
  </div>
  
  <div class="mt-6 grid grid-cols-3 gap-3 w-full text-sm">
    <div class="stat-box">
      <div class="text-lg font-light text-info">{$hydrationPercent}%</div>
      <div class="text-xs opacity-50">Hydration</div>
    </div>
    <div class="stat-box">
      <div class="text-lg font-light text-success">
        {Math.round((1 - breakProgress) * 100)}%
      </div>
      <div class="text-xs opacity-50">Break Ready</div>
    </div>
    <div class="stat-box">
      <div class="text-lg font-light text-warning">{formatActiveTime(displayActiveSeconds)}</div>
      <div class="text-xs opacity-50">Active</div>
    </div>
  </div>
</div>

<style>
  .focus-card {
    background: linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.08) 0%,
      rgba(255, 255, 255, 0.03) 100%
    );
  }
  
  .ring-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .stat-box {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0.75rem;
    padding: 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
</style>
