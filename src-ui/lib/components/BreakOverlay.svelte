<!--
  BreakOverlay.svelte - Break Reminder Modal
  
  Full-screen overlay shown when a break is due.
  Implements FR-02 (The Overlay) from PRD.
-->
<script lang="ts">
  import { currentBreak, breakCountdown, clearBreak } from '$lib/stores';
  import { completeBreak, snoozeBreak, skipBreak, getBreakTypeName, formatTime } from '$lib/ipc';
  import ProgressRing from './ProgressRing.svelte';
  import { onDestroy } from 'svelte';
  
  type OverlayState = 'nudge' | 'action' | 'complete';
  
  let state: OverlayState = 'nudge';
  let countdownInterval: ReturnType<typeof setInterval> | null = null;
  
  $: if ($currentBreak) {
    state = 'nudge';
  }
  
  $: themeColor = $currentBreak?.theme_color ?? 'var(--aura-accent)';
  $: breakType = $currentBreak?.break_type ?? 'micro';
  $: duration = $currentBreak?.duration_seconds ?? 20;
  $: countdownProgress = duration > 0 ? (($breakCountdown / duration) * 100) : 0;
  
  function startBreak() {
    state = 'action';
    breakCountdown.set(duration);
    
    countdownInterval = setInterval(() => {
      breakCountdown.update(n => {
        if (n <= 1) {
          if (countdownInterval) clearInterval(countdownInterval);
          state = 'complete';
          return 0;
        }
        return n - 1;
      });
    }, 1000);
  }
  
  async function handleComplete() {
    try {
      await completeBreak();
      cleanup();
    } catch (error) {
      console.error('Failed to complete break:', error);
    }
  }
  
  async function handleSnooze() {
    try {
      await snoozeBreak(5);
      cleanup();
    } catch (error) {
      console.error('Failed to snooze break:', error);
    }
  }
  
  async function handleSkip() {
    try {
      await skipBreak();
      cleanup();
    } catch (error) {
      console.error('Failed to skip break:', error);
    }
  }
  
  function cleanup() {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
    clearBreak();
    state = 'nudge';
  }
  
  onDestroy(() => {
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
  });
  
  // Break-specific content
  const breakContent = {
    micro: {
      title: 'Eye Rest',
      subtitle: 'Look away from the screen',
      instruction: 'Focus on something 20 feet away',
      emoji: '👁️'
    },
    macro: {
      title: 'Stretch Break',
      subtitle: 'Time to move your body',
      instruction: 'Stand up and stretch',
      emoji: '🧘'
    },
    hydration: {
      title: 'Hydration',
      subtitle: 'Stay hydrated',
      instruction: 'Drink some water',
      emoji: '💧'
    }
  };
  
  $: content = breakContent[breakType] || breakContent.micro;
</script>

{#if $currentBreak}
  <!-- Note: backdrop is provided by the overlay page, not this component -->
  <div class="overlay-container" style="--theme-color: {themeColor}">
    <div class="overlay-card">
      
      <!-- State 1: Nudge -->
      {#if state === 'nudge'}
        <div class="animate-scale-in">
          <div class="emoji-container animate-float">
            <span class="text-7xl">{content.emoji}</span>
          </div>
          <h2 class="text-3xl font-light mb-2 mt-6" style="color: {themeColor}">
            {content.title}
          </h2>
          <p class="text-base opacity-70 mb-8">{content.subtitle}</p>
          
          <div class="flex flex-col gap-4">
            <button 
              class="btn btn-lg btn-wide btn-primary-themed animate-pulse-glow"
              style="--btn-color: {themeColor}"
              on:click={startBreak}
            >
              <span class="text-lg">Start Break</span>
              <span class="badge badge-ghost ml-2">{duration}s</span>
            </button>
            
            <div class="flex gap-3 justify-center mt-2">
              <button 
                class="btn btn-sm btn-ghost gap-2"
                on:click={handleSnooze}
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                </svg>
                Snooze 5m
              </button>
              <button 
                class="btn btn-sm btn-ghost opacity-50 hover:opacity-100"
                on:click={handleSkip}
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      {/if}
      
      <!-- State 2: Action (Countdown) -->
      {#if state === 'action'}
        <div class="animate-scale-in">
          <div class="relative">
            <ProgressRing 
              progress={countdownProgress}
              size={220}
              strokeWidth={6}
              color={themeColor}
            >
              <div class="flex flex-col items-center">
                <span class="text-6xl font-thin tracking-tight" style="color: {themeColor}">
                  {formatTime($breakCountdown)}
                </span>
                <span class="text-sm opacity-50 mt-2">remaining</span>
              </div>
            </ProgressRing>
            
            <!-- Breathing animation ring -->
            <div 
              class="absolute inset-0 rounded-full animate-breathe opacity-20"
              style="border: 2px solid {themeColor}"
            ></div>
          </div>
          
          <p class="text-lg mt-8 opacity-80 font-light">{content.instruction}</p>
          
          {#if breakType === 'micro'}
            <p class="text-sm mt-2 opacity-50">Look at something 20 feet away</p>
          {/if}
          
          <button 
            class="btn btn-sm btn-ghost mt-6 opacity-40 hover:opacity-100"
            on:click={handleSkip}
          >
            Cancel break
          </button>
        </div>
      {/if}
      
      <!-- State 3: Complete -->
      {#if state === 'complete'}
        <div class="animate-scale-in text-center">
          <div class="emoji-container">
            <span class="text-8xl animate-float">✨</span>
          </div>
          <h2 class="text-3xl font-light mb-3 mt-6 text-success">
            Great job!
          </h2>
          <p class="text-base opacity-70 mb-8">
            Break completed. Keep up the good work!
          </p>
          
          <button 
            class="btn btn-lg btn-success btn-wide"
            on:click={handleComplete}
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            Done
          </button>
        </div>
      {/if}
      
    </div>
  </div>
{/if}

<style>
  .overlay-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .overlay-card {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 1.5rem;
    box-shadow: 
      0 25px 50px -12px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.05) inset;
    padding: 3rem;
    max-width: 420px;
    width: calc(100% - 2rem);
    text-align: center;
  }
  
  .emoji-container {
    display: inline-block;
  }
  
  .btn-primary-themed {
    background: linear-gradient(135deg, var(--btn-color) 0%, color-mix(in srgb, var(--btn-color) 70%, black) 100%);
    border: none;
    color: white;
    box-shadow: 
      0 0 30px color-mix(in srgb, var(--btn-color) 40%, transparent),
      0 4px 15px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
  }
  
  .btn-primary-themed:hover {
    transform: translateY(-2px);
    box-shadow: 
      0 0 50px color-mix(in srgb, var(--btn-color) 60%, transparent),
      0 8px 25px rgba(0, 0, 0, 0.4);
  }
  
  .btn-primary-themed:active {
    transform: translateY(0);
  }
</style>
