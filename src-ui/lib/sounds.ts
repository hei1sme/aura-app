/**
 * Sound utilities for Aura notifications
 * 
 * Uses Web Audio API to generate gentle notification sounds
 * without requiring external audio files.
 * 
 * FIXED v1.2.3: Added debounce to prevent duplicate sounds
 */

let audioContext: AudioContext | null = null;

// Debounce tracking to prevent duplicate sounds
let lastNotificationTime = 0;
let lastCompletionTime = 0;
let lastHydrationTime = 0;
const SOUND_DEBOUNCE_MS = 500; // Minimum 500ms between same sound type

/**
 * Get or create the AudioContext (lazy initialization)
 * Also resumes context if suspended (browser autoplay policy)
 */
function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  // Resume if suspended (required by browser autoplay policies)
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }
  return audioContext;
}

/**
 * Play a gentle chime notification sound
 * 
 * Creates a pleasant two-tone chime using sine waves.
 * Duration: ~400ms, Volume: 30%
 * 
 * DEBOUNCED: Will not play if called within 500ms of last play
 */
export function playNotificationChime(): void {
  // Debounce check
  const now = Date.now();
  if (now - lastNotificationTime < SOUND_DEBOUNCE_MS) {
    console.log('[Sound] Notification chime debounced');
    return;
  }
  lastNotificationTime = now;
  
  try {
    const ctx = getAudioContext();
    const ctxTime = ctx.currentTime;
    
    // Create gain node for volume control
    const gainNode = ctx.createGain();
    gainNode.connect(ctx.destination);
    gainNode.gain.setValueAtTime(0.3, ctxTime); // 30% volume
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctxTime + 0.4);
    
    // First tone (higher pitch)
    const osc1 = ctx.createOscillator();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(880, ctxTime); // A5
    osc1.connect(gainNode);
    osc1.start(ctxTime);
    osc1.stop(ctxTime + 0.15);
    
    // Second tone (lower, slightly delayed)
    const osc2 = ctx.createOscillator();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(659.25, ctxTime + 0.15); // E5
    osc2.connect(gainNode);
    osc2.start(ctxTime + 0.15);
    osc2.stop(ctxTime + 0.4);
    
  } catch (error) {
    console.warn('[Sound] Failed to play notification chime:', error);
  }
}

/**
 * Play a soft water droplet sound for hydration reminders
 * 
 * DEBOUNCED: Will not play if called within 500ms of last play
 */
export function playHydrationSound(): void {
  // Debounce check
  const now = Date.now();
  if (now - lastHydrationTime < SOUND_DEBOUNCE_MS) {
    console.log('[Sound] Hydration sound debounced');
    return;
  }
  lastHydrationTime = now;
  
  try {
    const ctx = getAudioContext();
    const ctxTime = ctx.currentTime;
    
    // Create gain node
    const gainNode = ctx.createGain();
    gainNode.connect(ctx.destination);
    gainNode.gain.setValueAtTime(0.25, ctxTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctxTime + 0.3);
    
    // Droplet effect - frequency slides down
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(1200, ctxTime);
    osc.frequency.exponentialRampToValueAtTime(400, ctxTime + 0.2);
    osc.connect(gainNode);
    osc.start(ctxTime);
    osc.stop(ctxTime + 0.3);
    
  } catch (error) {
    console.warn('[Sound] Failed to play hydration sound:', error);
  }
}

/**
 * Play a completion sound (positive feedback)
 * 
 * DEBOUNCED: Will not play if called within 500ms of last play
 */
export function playCompletionSound(): void {
  // Debounce check
  const now = Date.now();
  if (now - lastCompletionTime < SOUND_DEBOUNCE_MS) {
    console.log('[Sound] Completion sound debounced');
    return;
  }
  lastCompletionTime = now;
  
  try {
    const ctx = getAudioContext();
    const ctxTime = ctx.currentTime;
    
    const gainNode = ctx.createGain();
    gainNode.connect(ctx.destination);
    gainNode.gain.setValueAtTime(0.2, ctxTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctxTime + 0.5);
    
    // Rising arpeggio (C5 -> E5 -> G5)
    const frequencies = [523.25, 659.25, 783.99];
    frequencies.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctxTime + i * 0.1);
      osc.connect(gainNode);
      osc.start(ctxTime + i * 0.1);
      osc.stop(ctxTime + i * 0.1 + 0.15);
    });
    
  } catch (error) {
    console.warn('[Sound] Failed to play completion sound:', error);
  }
}

/**
 * Play the appropriate sound for a break type
 */
export function playBreakSound(breakType: string): void {
  if (breakType === 'hydration') {
    playHydrationSound();
  } else {
    playNotificationChime();
  }
}
