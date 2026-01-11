<script lang="ts">
  import "../app.css";
  import { onMount, onDestroy } from "svelte";
  import { slide } from "svelte/transition";
  import {
    onScheduleWarning,
    onScheduleActionExecuted,
    onStatus,
  } from "$lib/ipc";
  import type { UnlistenFn } from "@tauri-apps/api/event";
  import { invoke } from "@tauri-apps/api/core";

  let unlisteners: UnlistenFn[] = [];

  // Warning Toast State
  let showWarning = false;
  let warningTitle = "";
  let warningSeconds = 0;
  let warningTimer: any = null;

  // Debug State
  let lastDebugEvent = "Waiting for events...";
  let debugVisible = false;

  onMount(async () => {
    // Setup global event listeners
    unlisteners = await Promise.all([
      onScheduleActionExecuted((data) => {
        lastDebugEvent = `Action: ${data.action} at ${data.time}`;
        showWarning = false;
        if (warningTimer) clearInterval(warningTimer);
      }),
      onScheduleWarning((data) => {
        // Disabled: Using system notification window instead
        // showWarningToast(data.action, data.time, data.title, data.seconds_remaining); // Assuming these parameters based on the instruction's intent
        const msg = `${data.title} in ${data.seconds_remaining}s`;
        lastDebugEvent = `Warning: ${msg}`;
        console.log("[Layout] Schedule warning received:", data);

        // Toast disabled.
        // showWarning = true;
        // warningTitle = data.title;
      }),
      onStatus((status) => {
        // Just to show we are connected
        if (lastDebugEvent === "Waiting for events...") {
          lastDebugEvent = `Connected.`;
        }
      }),
    ]);
  });

  onDestroy(() => {
    unlisteners.forEach((unlisten) => unlisten());
    if (warningTimer) clearInterval(warningTimer);
  });

  async function testToast() {
    // Test In-App
    showWarning = true;
    warningTitle = "Debug Test Rule";
    warningSeconds = 60;

    if (warningTimer) clearInterval(warningTimer);
    warningTimer = setInterval(() => {
      if (warningSeconds > 0) warningSeconds--;
    }, 1000);

    lastDebugEvent = "Test Toast Triggered (Local + Window)";

    try {
      await invoke("debug_notification");
    } catch (e) {
      console.error("Debug Window Error", e);
    }
  }
</script>

<div class="app-container">
  <slot />

  {#if showWarning}
    <div class="warning-toast" transition:slide={{ axis: "y", duration: 300 }}>
      <div class="warning-content">
        <span class="warning-icon">⏱️</span>
        <div class="warning-text">
          <span class="warning-title">{warningTitle}</span>
          <span class="warning-meta">in {warningSeconds}s</span>
        </div>
      </div>
      <button class="warning-close" on:click={() => (showWarning = false)}
        >✕</button
      >
    </div>
  {/if}

  <!-- Debug Overlay -->
  {#if debugVisible}
    <div class="debug-overlay">
      <div class="text-xs font-mono mb-2">Debug Info:</div>
      <div class="text-xs opacity-70 mb-2">{lastDebugEvent}</div>
      <button class="btn btn-xs btn-warning" on:click={testToast}
        >Test Toast</button
      >
      <button
        class="btn btn-xs btn-ghost"
        on:click={() => (debugVisible = false)}>Hide</button
      >
    </div>
  {/if}
  <button class="debug-toggle" on:click={() => (debugVisible = !debugVisible)}
    >🐞</button
  >
</div>

<style>
  .app-container {
    position: relative;
    min-height: 100vh;
  }

  .debug-toggle {
    position: fixed;
    bottom: 0.5rem;
    left: 0.5rem;
    background: rgba(0, 0, 0, 0.5);
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    font-size: 12px;
    cursor: pointer;
    z-index: 10000;
  }

  .debug-overlay {
    position: fixed;
    bottom: 2.5rem;
    left: 0.5rem;
    background: rgba(0, 0, 0, 0.9);
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    z-index: 10000;
    max-width: 300px;
  }

  /* Warning Toast */
  .warning-toast {
    position: fixed;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(139, 92, 246, 0.4);
    backdrop-filter: blur(12px);
    padding: 0.75rem 1rem;
    border-radius: 12px;
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 9999;
    width: 90%;
    max-width: 320px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
    overflow: hidden;
  }

  .warning-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
  }

  .warning-icon {
    font-size: 1.25rem;
  }

  .warning-text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    line-height: normal;
  }

  .warning-title {
    font-weight: 600;
    font-size: 0.9rem;
    color: white;
  }

  .warning-meta {
    font-size: 0.75rem;
    color: #a78bfa;
  }

  .warning-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    cursor: pointer;
    font-size: 1rem;
    padding: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s;
  }

  .warning-close:hover {
    color: white;
  }
</style>
