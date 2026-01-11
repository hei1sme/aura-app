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

  onMount(async () => {
    // Setup global event listeners
    unlisteners = await Promise.all([
      onScheduleActionExecuted((data) => {
        showWarning = false;
        if (warningTimer) clearInterval(warningTimer);
      }),
      onScheduleWarning((data) => {
        // Disabled: Using system notification window instead
        // showWarningToast(data.action, data.time, data.title, data.seconds_remaining); // Assuming these parameters based on the instruction's intent
        console.log("[Layout] Schedule warning received:", data);

        // Toast disabled.
        // showWarning = true;
        // warningTitle = data.title;
      }),
      onStatus((status) => {
        // Just to show we are connected
      }),
    ]);
  });

  onDestroy(() => {
    unlisteners.forEach((unlisten) => unlisten());
    if (warningTimer) clearInterval(warningTimer);
  });
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
</div>

<style>
  .app-container {
    position: relative;
    min-height: 100vh;
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
