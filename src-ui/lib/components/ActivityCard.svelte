<!--
  ActivityCard.svelte - Current Activity Status
  
  Shows active time, state, and current process
-->
<script lang="ts">
  import { activityMetrics, activeTimeFormatted, isActive, isImmersive } from '$lib/stores';
  
  function getStateIcon(state: string): string {
    switch (state) {
      case 'active': return '⚡';
      case 'idle': return '💤';
      case 'immersive': return '🎮';
      default: return '⚪';
    }
  }
  
  function getStateLabel(state: string): string {
    switch (state) {
      case 'active': return 'Working';
      case 'idle': return 'Taking a break';
      case 'immersive': return 'Focus Mode';
      default: return 'Unknown';
    }
  }
  
  function getStateColor(state: string): string {
    switch (state) {
      case 'active': return 'var(--aura-eye-care)';
      case 'idle': return 'var(--aura-stretch)';
      case 'immersive': return 'var(--aura-immersive)';
      default: return 'var(--aura-accent)';
    }
  }
</script>

<div class="activity-card bento-item" class:theme-immersive={$isImmersive}>
  <div class="flex items-center justify-between mb-3">
    <h3 class="text-label">Activity</h3>
    <div 
      class="flex items-center gap-2 px-2 py-1 rounded-full text-xs"
      style="background: color-mix(in srgb, {getStateColor($activityMetrics.state)} 20%, transparent)"
    >
      <span class="text-base">{getStateIcon($activityMetrics.state)}</span>
      <span style="color: {getStateColor($activityMetrics.state)}">{getStateLabel($activityMetrics.state)}</span>
    </div>
  </div>
  
  <div class="space-y-4">
    <div class="grid grid-cols-2 gap-3">
      <div class="metric-box">
        <div class="metric-value text-success">{$activityMetrics.keys_per_min}</div>
        <div class="metric-label">Keys/min</div>
        <div class="metric-bar">
          <div 
            class="metric-bar-fill bg-success" 
            style="width: {Math.min(100, $activityMetrics.keys_per_min)}%"
          ></div>
        </div>
      </div>
      <div class="metric-box">
        <div class="metric-value text-info">{Math.round($activityMetrics.mouse_velocity)}</div>
        <div class="metric-label">Mouse velocity</div>
        <div class="metric-bar">
          <div 
            class="metric-bar-fill bg-info" 
            style="width: {Math.min(100, $activityMetrics.mouse_velocity / 10)}%"
          ></div>
        </div>
      </div>
    </div>
    
    {#if $activityMetrics.active_process}
      <div class="flex items-center gap-2 text-xs opacity-60 truncate">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M3 5a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2h-2.22l.123.489.804.804A1 1 0 0113 18H7a1 1 0 01-.707-1.707l.804-.804L7.22 15H5a2 2 0 01-2-2V5zm5.771 7H5V5h10v7H8.771z" clip-rule="evenodd" />
        </svg>
        <span class="truncate">{$activityMetrics.active_process}</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .activity-card {
    min-height: 160px;
  }
  
  .metric-box {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0.75rem;
    padding: 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
  
  .metric-value {
    font-size: 1.5rem;
    font-weight: 300;
    font-variant-numeric: tabular-nums;
  }
  
  .metric-label {
    font-size: 0.7rem;
    opacity: 0.5;
    margin-top: 0.125rem;
  }
  
  .metric-bar {
    height: 3px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 9999px;
    margin-top: 0.5rem;
    overflow: hidden;
  }
  
  .metric-bar-fill {
    height: 100%;
    border-radius: 9999px;
    transition: width 0.3s ease;
  }
</style>
