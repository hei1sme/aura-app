<!--
  HydrationCard.svelte - Water Intake Tracker
  
  Bento Grid Component for tracking daily hydration
-->
<script lang="ts">
  import ProgressRing from './ProgressRing.svelte';
  import { hydrationStatus, hydrationPercent } from '$lib/stores';
  import { logHydration } from '$lib/ipc';
  
  const quickAmounts = [
    { amount: 100, label: '100ml', emoji: '💧' },
    { amount: 250, label: '250ml', emoji: '🥤' },
    { amount: 500, label: '500ml', emoji: '🍶' }
  ];
  
  let isLogging = false;
  
  async function addWater(amount: number) {
    if (isLogging) return;
    isLogging = true;
    try {
      await logHydration(amount);
    } catch (error) {
      console.error('Failed to log hydration:', error);
    } finally {
      isLogging = false;
    }
  }
</script>

<div class="hydration-card bento-item span-2 theme-hydration">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-label flex items-center gap-2">
      <span class="text-base">💧</span>
      Hydration
    </h3>
    <div class="text-right">
      <span class="text-sm font-light text-info">{$hydrationStatus.total_today_ml}ml</span>
      <span class="text-xs opacity-50"> / {$hydrationStatus.goal_ml}ml</span>
    </div>
  </div>
  
  <div class="flex items-center gap-6">
    <div class="ring-wrapper">
      <ProgressRing 
        progress={$hydrationPercent} 
        size={100}
        strokeWidth={6}
        color="var(--aura-hydration)"
      >
        <div class="text-center">
          <span class="text-2xl font-light text-info">{$hydrationPercent}</span>
          <span class="text-xs opacity-60">%</span>
        </div>
      </ProgressRing>
    </div>
    
    <div class="flex-1">
      <p class="text-xs opacity-50 mb-3">Quick Add</p>
      <div class="grid grid-cols-3 gap-2">
        {#each quickAmounts as item}
          <button 
            class="quick-btn"
            class:loading={isLogging}
            on:click={() => addWater(item.amount)}
            disabled={isLogging}
          >
            <span class="text-lg">{item.emoji}</span>
            <span class="text-xs opacity-70">{item.label}</span>
          </button>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .hydration-card {
    min-height: 140px;
  }
  
  .ring-wrapper {
    flex-shrink: 0;
  }
  
  .quick-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    padding: 0.75rem 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    transition: all 0.2s ease;
    cursor: pointer;
  }
  
  .quick-btn:hover {
    background: rgba(59, 130, 246, 0.2);
    border-color: var(--aura-hydration);
    transform: translateY(-2px);
  }
  
  .quick-btn:active {
    transform: translateY(0);
  }
  
  .quick-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
