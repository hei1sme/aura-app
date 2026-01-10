<!--
  TrainingDataCard.svelte - ML Data Collection Stats
  
  Shows progress toward training a personalized model
-->
<script lang="ts">
  import { trainingStats } from '$lib/stores';
  import { getTrainingStats } from '$lib/ipc';
  import { onMount } from 'svelte';
  
  onMount(() => {
    getTrainingStats();
  });
  
  $: progress = $trainingStats 
    ? Math.min(100, ($trainingStats.total_samples / 100) * 100)
    : 0;
    
  $: progressColor = progress >= 100 ? 'var(--aura-eye-care)' :
                     progress >= 50 ? 'var(--aura-stretch)' :
                     'var(--aura-accent)';
</script>

<div class="training-card bento-item">
  <div class="flex items-center justify-between mb-3">
    <h3 class="text-label flex items-center gap-2">
      <span class="text-base">🧠</span>
      AI Training
    </h3>
    <span class="badge badge-sm badge-ghost opacity-60">Data Collection</span>
  </div>
  
  {#if $trainingStats}
    <div class="space-y-4">
      <div class="flex items-baseline gap-2">
        <span class="text-3xl font-light" style="color: {progressColor}">
          {$trainingStats.total_samples}
        </span>
        <span class="text-sm opacity-50">/ 100 samples</span>
      </div>
      
      <div class="progress-container">
        <div class="progress-track">
          <div 
            class="progress-fill"
            style="width: {progress}%; background: {progressColor}"
          ></div>
        </div>
        <div class="flex justify-between text-xs opacity-40 mt-1">
          <span>0</span>
          <span>50</span>
          <span>100</span>
        </div>
      </div>
      
      <p class="text-xs opacity-60 leading-relaxed">
        {$trainingStats.message}
      </p>
      
      {#if $trainingStats.ready_for_training}
        <div class="ready-badge">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
          Ready for Phase 3!
        </div>
      {:else}
        <div class="text-xs opacity-40">
          Keep using Aura to collect more training data
        </div>
      {/if}
    </div>
  {:else}
    <div class="flex flex-col items-center justify-center h-24 opacity-50 gap-2">
      <span class="loading loading-dots loading-sm"></span>
      <span class="text-xs">Loading stats...</span>
    </div>
  {/if}
</div>

<style>
  .training-card {
    min-height: 180px;
  }
  
  .progress-container {
    width: 100%;
  }
  
  .progress-track {
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 9999px;
    overflow: hidden;
  }
  
  .progress-fill {
    height: 100%;
    border-radius: 9999px;
    transition: width 0.5s ease;
  }
  
  .ready-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: color-mix(in srgb, var(--aura-eye-care) 20%, transparent);
    color: var(--aura-eye-care);
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }
</style>
