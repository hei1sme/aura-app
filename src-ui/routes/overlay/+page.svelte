<!--
  Overlay Page - Floating Break Reminder Card
  
  This is a SEPARATE WINDOW that appears as a floating card on top of other apps.
  Shows break type, duration, and action buttons.
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { 
    currentBreak, 
    setBreakDue, 
    clearBreak,
    breakCountdown
  } from '$lib/stores';
  import { 
    onBreakDue, 
    completeBreak, 
    snoozeBreak, 
    skipBreak,
    formatTime,
    getPendingBreak,
    clearPendingBreak,
    hideOverlay,
    logHydration,
    getSettings,
    onSettings
  } from '$lib/ipc';
  import { playBreakSound, playCompletionSound } from '$lib/sounds';
  import type { UnlistenFn } from '@tauri-apps/api/event';
  import { listen } from '@tauri-apps/api/event';
  import { getCurrentWindow } from '@tauri-apps/api/window';
  
  let unlistenBreak: UnlistenFn | null = null;
  let unlistenFocus: UnlistenFn | null = null;
  let unlistenShowBreak: UnlistenFn | null = null;
  let unlistenSettings: UnlistenFn | null = null;
  let state: 'nudge' | 'action' | 'complete' | 'hydration-select' = 'nudge';
  let countdownInterval: ReturnType<typeof setInterval> | null = null;
  
  // Sound settings
  let soundEnabled = true;
  
  // Track last break that triggered sound to prevent duplicates
  let lastSoundBreakId: number | null = null;
  
  // Function to play notification sound if enabled (with deduplication)
  function playNotificationIfEnabled(breakType: string, recordId: number) {
    if (soundEnabled && lastSoundBreakId !== recordId) {
      lastSoundBreakId = recordId;
      playBreakSound(breakType);
    }
  }
  
  // Function to play completion sound if enabled
  function playCompletionIfEnabled() {
    if (soundEnabled) {
      playCompletionSound();
    }
  }
  
  // Hydration amount options
  const hydrationOptions = [
    { ml: 100, label: '100ml', icon: '🥤' },
    { ml: 250, label: '250ml', icon: '🥛' },
    { ml: 500, label: '500ml', icon: '🍶' },
  ];
  
  // Break content by type
  const breakContent: Record<string, { title: string; instruction: string; emoji: string }> = {
    micro: {
      title: 'Eye Rest',
      instruction: 'Look at something 20 feet away',
      emoji: '👁️'
    },
    macro: {
      title: 'Stretch Break',
      instruction: 'Stand up and stretch your body',
      emoji: '🧘'
    },
    hydration: {
      title: 'Hydration',
      instruction: 'Time to drink some water',
      emoji: '💧'
    }
  };
  
  $: content = $currentBreak ? (breakContent[$currentBreak.break_type] || breakContent.micro) : breakContent.micro;
  $: themeColor = $currentBreak?.theme_color ?? '#8B5CF6';
  $: duration = $currentBreak?.duration_seconds ?? 20;
  $: isHydration = $currentBreak?.break_type === 'hydration';
  $: durationDisplay = duration >= 60 ? `${Math.floor(duration / 60)}m` : `${duration}s`;
  
  // Function to fetch pending break data
  async function fetchPendingBreak() {
    console.log('[Overlay] Fetching pending break...');
    try {
      const pendingBreak = await getPendingBreak();
      console.log('[Overlay] Pending break:', pendingBreak);
      if (pendingBreak) {
        setBreakDue(pendingBreak);
        state = 'nudge';
      }
    } catch (error) {
      console.error('[Overlay] Failed to get pending break:', error);
    }
  }
  
  onMount(async () => {
    console.log('[Overlay] Window mounted');
    
    // Listen for settings updates FIRST (before fetching)
    unlistenSettings = await onSettings((settingsData) => {
      if (settingsData.sound_enabled !== undefined) {
        soundEnabled = settingsData.sound_enabled === 'true';
        console.log('[Overlay] Sound enabled:', soundEnabled);
      }
    });
    
    // Now fetch settings - the listener above will catch the response
    try {
      await getSettings();
    } catch (error) {
      console.warn('[Overlay] Failed to fetch settings:', error);
    }
    
    // Fetch on initial mount
    await fetchPendingBreak();
    
    // Listen for show-break event from Rust (most reliable)
    unlistenShowBreak = await listen('show-break', (event) => {
      console.log('[Overlay] show-break event received:', event.payload);
      const breakData = event.payload as { break_type: 'micro' | 'macro' | 'hydration'; duration_seconds: number; theme_color: string; record_id: number };
      if (breakData) {
        setBreakDue(breakData);
        state = 'nudge';
        // Play notification sound (deduplicated by record_id)
        playNotificationIfEnabled(breakData.break_type, breakData.record_id);
      }
    });
    
    // Listen for window focus - backup method
    const appWindow = getCurrentWindow();
    unlistenFocus = await appWindow.onFocusChanged(({ payload: focused }) => {
      console.log('[Overlay] Focus changed:', focused);
      if (focused) {
        // Window just became visible/focused, fetch break data
        fetchPendingBreak();
      }
    });
    
    // Also listen for future break events (for real breaks from sidecar)
    unlistenBreak = await onBreakDue((breakEvent) => {
      console.log('[Overlay] Break event received:', breakEvent);
      setBreakDue(breakEvent);
      state = 'nudge';
      // Play notification sound (deduplicated by record_id)
      playNotificationIfEnabled(breakEvent.break_type, breakEvent.record_id);
    });
  });
  
  onDestroy(() => {
    if (unlistenBreak) unlistenBreak();
    if (unlistenFocus) unlistenFocus();
    if (unlistenShowBreak) unlistenShowBreak();
    if (unlistenSettings) unlistenSettings();
    if (countdownInterval) clearInterval(countdownInterval);
  });
  
  function startBreak() {
    // For hydration, show selection options instead of countdown
    if (isHydration) {
      state = 'hydration-select';
      return;
    }
    
    state = 'action';
    breakCountdown.set(duration);
    
    countdownInterval = setInterval(() => {
      breakCountdown.update(n => {
        if (n <= 1) {
          if (countdownInterval) clearInterval(countdownInterval);
          state = 'complete';
          // Play completion sound
          playCompletionIfEnabled();
          return 0;
        }
        return n - 1;
      });
    }, 1000);
  }
  
  async function handleHydrationSelect(amountMl: number) {
    try {
      await logHydration(amountMl);
      await completeBreak();
      await cleanup();
    } catch (error) {
      console.error('Failed to log hydration:', error);
    }
  }
  
  async function handleComplete() {
    try {
      await completeBreak();
      await cleanup();
    } catch (error) {
      console.error('Failed to complete break:', error);
    }
  }
  
  async function handleSnooze() {
    try {
      await snoozeBreak(5);
      await cleanup();
    } catch (error) {
      console.error('Failed to snooze:', error);
    }
  }
  
  async function handleSkip() {
    try {
      await skipBreak();
      await cleanup();
    } catch (error) {
      console.error('Failed to skip:', error);
    }
  }
  
  async function cleanup() {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
    clearBreak();
    clearPendingBreak(); // Also clear from Rust state
    state = 'nudge';
    lastSoundBreakId = null; // Reset so next break can play sound
    // Hide the overlay window
    try {
      await hideOverlay();
    } catch (error) {
      console.error('Failed to hide overlay:', error);
    }
  }
</script>

<svelte:head>
  <title></title>
</svelte:head>

<div class="overlay-card" style="--theme-color: {themeColor}">
  {#if $currentBreak}
    <!-- State 1: Nudge - Show break info and start button -->
    {#if state === 'nudge'}
      <div class="card-content animate-fade-in">
        <div class="emoji">{content.emoji}</div>
        <h2 class="title" style="color: {themeColor}">{content.title}</h2>
        <p class="instruction">{content.instruction}</p>
        
        <button class="btn-start" style="background: {themeColor}" on:click={startBreak}>
          {isHydration ? 'Log Water' : 'Start Break'}
          {#if !isHydration}
            <span class="duration-badge">{durationDisplay}</span>
          {/if}
        </button>
        
        <div class="secondary-actions">
          <button class="btn-secondary" on:click={handleSnooze}>
            ⏰ Snooze 5m
          </button>
          <button class="btn-secondary btn-skip" on:click={handleSkip}>
            Skip
          </button>
        </div>
      </div>
    {/if}
    
    <!-- State 2: Action - Countdown timer (for micro/macro breaks) -->
    {#if state === 'action'}
      <div class="card-content animate-fade-in">
        <div class="countdown-ring" style="--progress: {($breakCountdown / duration) * 100}%">
          <span class="countdown-text" style="color: {themeColor}">{formatTime($breakCountdown)}</span>
        </div>
        <p class="instruction">{content.instruction}</p>
        <button class="btn-secondary" on:click={handleSkip}>Cancel</button>
      </div>
    {/if}
    
    <!-- State: Hydration Select - Show water amount options -->
    {#if state === 'hydration-select'}
      <div class="card-content animate-fade-in">
        <div class="emoji">💧</div>
        <h2 class="title" style="color: {themeColor}">How much did you drink?</h2>
        
        <div class="hydration-options">
          {#each hydrationOptions as option}
            <button 
              class="hydration-btn" 
              style="border-color: {themeColor}"
              on:click={() => handleHydrationSelect(option.ml)}
            >
              <span class="hydration-icon">{option.icon}</span>
              <span class="hydration-label">{option.label}</span>
            </button>
          {/each}
        </div>
        
        <div class="secondary-actions">
          <button class="btn-secondary btn-skip" on:click={handleSkip}>
            Skip
          </button>
        </div>
      </div>
    {/if}
    
    <!-- State 3: Complete -->
    {#if state === 'complete'}
      <div class="card-content animate-fade-in">
        <div class="emoji">✨</div>
        <h2 class="title text-success">Great job!</h2>
        <p class="instruction">Break completed</p>
        <button class="btn-start btn-success" on:click={handleComplete}>Done</button>
      </div>
    {/if}
  {:else}
    <!-- Waiting state (should not be visible normally) -->
    <div class="card-content">
      <div class="emoji opacity-50">⏳</div>
      <p class="instruction opacity-50">Waiting for break...</p>
    </div>
  {/if}
</div>

<style>
  /* 
   * OVERLAY WINDOW STYLES
   * This window must be completely transparent with only the card visible.
   * DO NOT add any background colors here - the layout handles transparency.
   */
  
  .overlay-card {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    /* Fully transparent - only the card-content is visible */
    background: transparent !important;
    margin: 0;
    padding: 0;
  }
  
  .card-content {
    text-align: center;
    /* The actual card with glass effect */
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
    padding: 2.5rem 3rem;
    min-width: 320px;
  }
  
  .emoji {
    font-size: 4rem;
    margin-bottom: 1rem;
    animation: float 3s ease-in-out infinite;
  }
  
  .title {
    font-size: 1.75rem;
    font-weight: 300;
    margin-bottom: 0.5rem;
  }
  
  .instruction {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
  }
  
  .btn-start {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 2rem;
    border: none;
    border-radius: 12px;
    color: white;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  }
  
  .btn-start:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
  }
  
  .btn-success {
    background: #10B981 !important;
  }
  
  .duration-badge {
    background: rgba(255, 255, 255, 0.2);
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    font-size: 0.85rem;
  }
  
  .secondary-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-top: 1rem;
  }
  
  .btn-secondary {
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.85rem;
    cursor: pointer;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    transition: all 0.2s ease;
  }
  
  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.8);
  }
  
  .btn-skip {
    opacity: 0.5;
  }
  
  .btn-skip:hover {
    opacity: 1;
  }
  
  .countdown-ring {
    width: 150px;
    height: 150px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1.5rem;
    background: conic-gradient(
      var(--theme-color) var(--progress),
      rgba(255, 255, 255, 0.1) var(--progress)
    );
    position: relative;
  }
  
  .countdown-ring::before {
    content: '';
    position: absolute;
    inset: 8px;
    background: rgba(15, 23, 42, 0.95);
    border-radius: 50%;
  }
  
  .countdown-text {
    position: relative;
    z-index: 1;
    font-size: 2.5rem;
    font-weight: 300;
  }
  
  /* Hydration selection styles */
  .hydration-options {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-bottom: 1.5rem;
  }
  
  .hydration-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid;
    border-radius: 12px;
    color: white;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  
  .hydration-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: translateY(-2px);
  }
  
  .hydration-icon {
    font-size: 1.5rem;
  }
  
  .hydration-label {
    font-size: 0.9rem;
    font-weight: 500;
  }
  
  .text-success {
    color: #10B981 !important;
  }
  
  .opacity-50 {
    opacity: 0.5;
  }
  
  .animate-fade-in {
    animation: fadeIn 0.3s ease-out;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  }
  
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
  }
</style>
