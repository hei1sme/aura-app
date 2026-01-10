<!--
  ProgressRing.svelte - Circular Progress Indicator
  
  Used for:
  - Hydration progress
  - Break countdown
  - Daily focus ring
-->
<script lang="ts">
  export let progress: number = 0; // 0-100
  export let size: number = 120;
  export let strokeWidth: number = 8;
  export let color: string = 'var(--aura-accent)';
  export let trackColor: string = 'rgba(255, 255, 255, 0.1)';
  export let showPercentage: boolean = false;
  
  $: radius = (size - strokeWidth) / 2;
  $: circumference = 2 * Math.PI * radius;
  $: dashOffset = circumference - (progress / 100) * circumference;
</script>

<div class="progress-ring" style="width: {size}px; height: {size}px;">
  <svg width={size} height={size}>
    <!-- Track -->
    <circle
      class="track"
      cx={size / 2}
      cy={size / 2}
      r={radius}
      fill="none"
      stroke={trackColor}
      stroke-width={strokeWidth}
    />
    <!-- Progress -->
    <circle
      class="progress"
      cx={size / 2}
      cy={size / 2}
      r={radius}
      fill="none"
      stroke={color}
      stroke-width={strokeWidth}
      stroke-linecap="round"
      stroke-dasharray={circumference}
      stroke-dashoffset={dashOffset}
    />
  </svg>
  
  <div class="absolute inset-0 flex items-center justify-center">
    {#if showPercentage}
      <span class="text-2xl font-light">{Math.round(progress)}%</span>
    {:else}
      <slot />
    {/if}
  </div>
</div>

<style>
  .progress-ring {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  
  .progress-ring svg {
    transform: rotate(-90deg);
  }
  
  .progress {
    transition: stroke-dashoffset 0.5s ease;
  }
</style>
