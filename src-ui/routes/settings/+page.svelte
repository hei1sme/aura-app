<!--
  Settings Page - Aura Preferences
  
  Implements FR-04.2 from PRD:
  - Break interval settings
  - Hydration goal
  - Immersive mode toggles
  - App behavior settings
  
  FIX: Uses loading state to prevent "flash of default values"
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { page } from "$app/stores";
  import {
    pauseReminders,
    resumeReminders,
    getSettings,
    updateSetting,
    exportData,
    onSettings,
    onSettingUpdated,
    onDataExported,
    enableAutostart,
    disableAutostart,
    isAutostartEnabled,
    getScheduleRules,
    addScheduleRule,
    updateScheduleRule,
    deleteScheduleRule,
    onScheduleRules,
    onScheduleRuleAdded,
    onScheduleRuleUpdated,
    onScheduleRuleDeleted,
    type ScheduleRule,
  } from "$lib/ipc";
  import { sidecarConnected, isPaused, pauseUntil } from "$lib/stores";
  import type { UnlistenFn } from "@tauri-apps/api/event";

  // Settings state - DO NOT set defaults here, they will be loaded from backend
  // Using `null` to indicate "not yet loaded" state
  let settings: {
    microBreakInterval: number | null;
    macroBreakInterval: number | null;
    hydrationInterval: number | null;
    microBreakDuration: number | null;
    macroBreakDuration: number | null;
    dailyWaterGoal: number | null;
    autoStart: boolean;
    closeToTray: boolean;
    soundEnabled: boolean;
    autoDetectFullscreen: boolean;
    blockedApps: string[];
    timerMode: "active" | "wall-clock"; // NEW: Timer counting mode
  } = {
    // Break intervals (in minutes) - null until loaded
    microBreakInterval: null,
    macroBreakInterval: null,
    hydrationInterval: null,

    // Durations (in seconds) - null until loaded
    microBreakDuration: null,
    macroBreakDuration: null,

    // Goals - null until loaded
    dailyWaterGoal: null,

    // Behavior - safe defaults for booleans
    autoStart: false,
    closeToTray: true,
    soundEnabled: true,

    // Immersive mode
    autoDetectFullscreen: true,
    blockedApps: [],

    // Timer mode (NEW)
    timerMode: "active",
  };

  let newBlockedApp = "";
  let isSaving = false;
  let isLoading = true;
  let saveSuccess = false;
  let exportMessage = "";
  let unlisteners: UnlistenFn[] = [];

  // Work Schedule state
  let scheduleRules: ScheduleRule[] = [];
  let scheduleMode: "same_every_day" | "weekday_weekend" | "custom" =
    "same_every_day";
  let newRuleTitle = "";
  let newRuleTime = "09:00";
  let newRuleAction:
    | "pause"
    | "resume"
    | "reset"
    | "start_session"
    | "end_session" = "pause";
  let newRuleDays: string[] = ["mon", "tue", "wed", "thu", "fri"];

  const DAY_LABELS: Record<string, string> = {
    mon: "Mon",
    tue: "Tue",
    wed: "Wed",
    thu: "Thu",
    fri: "Fri",
    sat: "Sat",
    sun: "Sun",
  };
  const ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const ACTION_LABELS: Record<string, string> = {
    pause: "⏸️ Pause",
    resume: "▶️ Resume",
    reset: "🔄 Reset",
    start_session: "🚀 Start",
    end_session: "🛑 End",
  };

  // Determine back link based on query param
  $: backLink =
    $page.url.searchParams.get("from") === "session" ? "/session" : "/";

  // Check if critical settings are loaded (the numeric ones that could flash)
  $: isSettingsLoaded =
    settings.microBreakInterval !== null &&
    settings.macroBreakInterval !== null &&
    settings.hydrationInterval !== null;

  onMount(async () => {
    // Setup event listeners
    unlisteners = await Promise.all([
      onSettings((loadedSettings) => {
        console.log("[Settings] Loaded settings:", loadedSettings);
        // Map backend settings to UI settings
        if (loadedSettings.micro_break_interval) {
          settings.microBreakInterval = Math.round(
            parseInt(loadedSettings.micro_break_interval) / 60,
          );
        }
        if (loadedSettings.macro_break_interval) {
          settings.macroBreakInterval = Math.round(
            parseInt(loadedSettings.macro_break_interval) / 60,
          );
        }
        if (loadedSettings.hydration_interval) {
          settings.hydrationInterval = Math.round(
            parseInt(loadedSettings.hydration_interval) / 60,
          );
        }
        if (loadedSettings.micro_break_duration) {
          settings.microBreakDuration = parseInt(
            loadedSettings.micro_break_duration,
          );
        }
        if (loadedSettings.macro_break_duration) {
          settings.macroBreakDuration = parseInt(
            loadedSettings.macro_break_duration,
          );
        }
        if (loadedSettings.water_goal) {
          settings.dailyWaterGoal = parseInt(loadedSettings.water_goal);
        }
        if (loadedSettings.auto_start) {
          settings.autoStart = loadedSettings.auto_start === "true";
        }
        if (loadedSettings.close_to_tray) {
          settings.closeToTray = loadedSettings.close_to_tray === "true";
        }
        if (loadedSettings.sound_enabled) {
          settings.soundEnabled = loadedSettings.sound_enabled === "true";
        }
        if (loadedSettings.auto_detect_fullscreen) {
          settings.autoDetectFullscreen =
            loadedSettings.auto_detect_fullscreen === "true";
        }
        if (loadedSettings.blocklist_processes) {
          try {
            settings.blockedApps = JSON.parse(
              loadedSettings.blocklist_processes,
            );
          } catch (e) {
            console.error("Failed to parse blocklist:", e);
          }
        }
        if (loadedSettings.timer_mode) {
          settings.timerMode = loadedSettings.timer_mode as
            | "active"
            | "wall-clock";
        }
        isLoading = false;
      }),
      onSettingUpdated((data) => {
        console.log("[Settings] Setting updated:", data);
      }),
      onDataExported((data) => {
        exportMessage = `Exported ${data.records} records to ${data.path}`;
        setTimeout(() => (exportMessage = ""), 5000);
      }),
      // Schedule rules listeners
      onScheduleRules((data) => {
        console.log("[WorkSchedule] Received schedule_rules event:", data);
        scheduleRules = data.rules;
      }),
      onScheduleRuleAdded((data) => {
        console.log("[WorkSchedule] Received schedule_rule_added event:", data);
        scheduleRules = data.rules;
      }),
      onScheduleRuleUpdated((data) => {
        console.log(
          "[WorkSchedule] Received schedule_rule_updated event:",
          data,
        );
        scheduleRules = data.rules;
      }),
      onScheduleRuleDeleted((data) => {
        console.log(
          "[WorkSchedule] Received schedule_rule_deleted event:",
          data,
        );
        scheduleRules = data.rules;
      }),
    ]);

    // Request current settings from backend
    try {
      await getSettings();
      await getScheduleRules(); // Load schedule rules
      // Also check actual autostart state from OS
      const autostartEnabled = await isAutostartEnabled();
      settings.autoStart = autostartEnabled;
    } catch (error) {
      console.error("Failed to load settings:", error);
      isLoading = false;
    }
  });

  onDestroy(() => {
    unlisteners.forEach((unlisten) => unlisten());
  });

  // Work Schedule functions
  function toggleDay(day: string) {
    if (newRuleDays.includes(day)) {
      newRuleDays = newRuleDays.filter((d) => d !== day);
    } else {
      newRuleDays = [...newRuleDays, day];
    }
  }

  async function handleAddRule() {
    if (newRuleDays.length === 0) return;
    try {
      await addScheduleRule(
        newRuleTime,
        newRuleAction,
        newRuleDays,
        newRuleTitle,
      );
    } catch (e) {
      console.error("Failed to add rule:", e);
    }
  }

  async function handleDeleteRule(id: number) {
    try {
      await deleteScheduleRule(id);
    } catch (e) {
      console.error("Failed to delete rule:", e);
    }
  }

  async function handleToggleRule(rule: ScheduleRule) {
    try {
      await updateScheduleRule(
        rule.id,
        rule.time,
        rule.action,
        rule.days,
        !rule.enabled,
        rule.title,
      );
    } catch (e) {
      console.error("Failed to toggle rule:", e);
    }
  }

  function formatDays(days: string[]): string {
    if (days.length === 7) return "Every day";
    if (
      days.length === 5 &&
      ["mon", "tue", "wed", "thu", "fri"].every((d) => days.includes(d))
    )
      return "Weekdays";
    if (days.length === 2 && days.includes("sat") && days.includes("sun"))
      return "Weekends";
    return days.map((d) => DAY_LABELS[d]).join(", ");
  }

  async function handlePause(minutes: number) {
    try {
      await pauseReminders(minutes);
      isPaused.set(true);
      const until = Date.now() + minutes * 60 * 1000;
      pauseUntil.set(until);
    } catch (error) {
      console.error("Failed to pause:", error);
    }
  }

  async function handleResume() {
    try {
      await resumeReminders();
      isPaused.set(false);
      pauseUntil.set(null);
    } catch (error) {
      console.error("Failed to resume:", error);
    }
  }

  function addBlockedApp() {
    if (newBlockedApp && !settings.blockedApps.includes(newBlockedApp)) {
      settings.blockedApps = [...settings.blockedApps, newBlockedApp];
      newBlockedApp = "";
    }
  }

  function removeBlockedApp(app: string) {
    settings.blockedApps = settings.blockedApps.filter((a) => a !== app);
  }

  async function saveSettings() {
    isSaving = true;
    saveSuccess = false;

    // Ensure settings are loaded before saving
    if (
      settings.microBreakInterval === null ||
      settings.macroBreakInterval === null ||
      settings.hydrationInterval === null
    ) {
      console.error("Cannot save: settings not fully loaded");
      isSaving = false;
      return;
    }

    try {
      // Save all settings to backend (convert to backend format)
      await updateSetting(
        "micro_break_interval",
        String(settings.microBreakInterval * 60),
      );
      await updateSetting(
        "macro_break_interval",
        String(settings.macroBreakInterval * 60),
      );
      await updateSetting(
        "hydration_interval",
        String(settings.hydrationInterval * 60),
      );
      await updateSetting(
        "micro_break_duration",
        String(settings.microBreakDuration),
      );
      await updateSetting(
        "macro_break_duration",
        String(settings.macroBreakDuration),
      );
      await updateSetting("water_goal", String(settings.dailyWaterGoal));
      await updateSetting("auto_start", String(settings.autoStart));
      await updateSetting("close_to_tray", String(settings.closeToTray));
      await updateSetting("sound_enabled", String(settings.soundEnabled));
      await updateSetting(
        "auto_detect_fullscreen",
        String(settings.autoDetectFullscreen),
      );
      await updateSetting(
        "blocklist_processes",
        JSON.stringify(settings.blockedApps),
      );
      await updateSetting("timer_mode", settings.timerMode);

      // Handle Windows autostart registration
      if (settings.autoStart) {
        await enableAutostart();
      } else {
        await disableAutostart();
      }

      saveSuccess = true;
      setTimeout(() => (saveSuccess = false), 3000);
    } catch (error) {
      console.error("Failed to save settings:", error);
    } finally {
      isSaving = false;
    }
  }

  async function handleExportData() {
    try {
      await exportData("aura_training_data.csv");
    } catch (error) {
      console.error("Failed to export data:", error);
    }
  }

  function formatPauseTime(until: number | null): string {
    if (!until) return "";
    const remaining = Math.max(0, until - Date.now());
    const mins = Math.ceil(remaining / 60000);
    return `${mins} min remaining`;
  }
</script>

<svelte:head>
  <title>Settings - Aura</title>
</svelte:head>

<main class="min-h-screen p-6 max-w-3xl mx-auto">
  <!-- Header -->
  <header class="flex items-center gap-4 mb-8">
    <a href={backLink} class="btn btn-ghost btn-circle" aria-label="Go back">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-5 w-5"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
          clip-rule="evenodd"
        />
      </svg>
    </a>
    <div>
      <h1 class="text-2xl font-light">Settings</h1>
      <p class="text-sm opacity-60">Customize your wellness experience</p>
    </div>
  </header>

  <div class="space-y-6">
    <!-- Quick Actions Section -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">⏸️</span>
        Quick Actions
      </h2>

      <div class="flex flex-wrap gap-3">
        {#if $isPaused}
          <button class="btn btn-success" on:click={handleResume}>
            Resume Reminders
          </button>
          <span class="text-sm opacity-60 self-center">
            {formatPauseTime($pauseUntil)}
          </span>
        {:else}
          <button
            class="btn btn-outline btn-sm"
            on:click={() => handlePause(30)}
          >
            Pause 30m
          </button>
          <button
            class="btn btn-outline btn-sm"
            on:click={() => handlePause(60)}
          >
            Pause 1h
          </button>
          <button
            class="btn btn-outline btn-sm"
            on:click={() => handlePause(120)}
          >
            Pause 2h
          </button>
        {/if}
      </div>
    </section>

    <!-- Break Intervals Section -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">⏰</span>
        Break Intervals
      </h2>

      {#if !isSettingsLoaded}
        <!-- Loading skeleton to prevent flash of default values -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {#each [1, 2, 3, 4] as _}
            <div class="form-control">
              <div class="h-4 bg-base-300 rounded w-32 mb-2"></div>
              <div class="h-8 bg-base-300 rounded"></div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Micro Break -->
          <div class="form-control">
            <span class="label">
              <span class="label-text flex items-center gap-2">
                <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
                Eye Rest Interval
              </span>
            </span>
            <div class="flex items-center gap-2">
              <input
                type="range"
                min="10"
                max="40"
                bind:value={settings.microBreakInterval}
                class="range range-success range-sm flex-1"
                aria-label="Eye rest interval in minutes"
              />
              <span class="text-sm font-mono w-16"
                >{settings.microBreakInterval} min</span
              >
            </div>
          </div>

          <!-- Macro Break -->
          <div class="form-control">
            <span class="label">
              <span class="label-text flex items-center gap-2">
                <span class="w-3 h-3 rounded-full bg-amber-500"></span>
                Stretch Break Interval
              </span>
            </span>
            <div class="flex items-center gap-2">
              <input
                type="range"
                min="30"
                max="90"
                step="5"
                bind:value={settings.macroBreakInterval}
                class="range range-warning range-sm flex-1"
                aria-label="Stretch break interval in minutes"
              />
              <span class="text-sm font-mono w-16"
                >{settings.macroBreakInterval} min</span
              >
            </div>
          </div>

          <!-- Hydration -->
          <div class="form-control">
            <span class="label">
              <span class="label-text flex items-center gap-2">
                <span class="w-3 h-3 rounded-full bg-blue-500"></span>
                Hydration Reminder
              </span>
            </span>
            <div class="flex items-center gap-2">
              <input
                type="range"
                min="15"
                max="60"
                step="5"
                bind:value={settings.hydrationInterval}
                class="range range-info range-sm flex-1"
                aria-label="Hydration reminder interval in minutes"
              />
              <span class="text-sm font-mono w-16"
                >{settings.hydrationInterval} min</span
              >
            </div>
          </div>

          <!-- Water Goal -->
          <div class="form-control">
            <span class="label">
              <span class="label-text">Daily Water Goal</span>
            </span>
            <div class="flex items-center gap-2">
              <input
                type="range"
                min="1000"
                max="4000"
                step="250"
                bind:value={settings.dailyWaterGoal}
                class="range range-info range-sm flex-1"
                aria-label="Daily water goal in milliliters"
              />
              <span class="text-sm font-mono w-16"
                >{settings.dailyWaterGoal} ml</span
              >
            </div>
          </div>
        </div>
      {/if}
    </section>

    <!-- Timer Mode Section (NEW) -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">⏱️</span>
        Timer Mode
      </h2>

      <p class="text-sm opacity-60 mb-4">
        Choose how break timers count down. <strong>Active Time</strong> pauses
        when you're away,
        <strong>Wall Clock</strong> counts continuously regardless of activity.
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label
          class="cursor-pointer flex items-start gap-3 p-4 rounded-lg border-2 transition-all hover:bg-white/5"
          class:border-primary={settings.timerMode === "active"}
          class:border-base-300={settings.timerMode !== "active"}
          class:bg-primary={settings.timerMode === "active"}
          class:bg-opacity-10={settings.timerMode === "active"}
        >
          <input
            type="radio"
            name="timerMode"
            value="active"
            bind:group={settings.timerMode}
            class="radio radio-primary mt-1"
          />
          <div class="flex-1">
            <span class="font-medium text-base">Active Time</span>
            <p class="text-xs opacity-60 mt-1">
              Timer pauses when you're idle or away (recommended)
            </p>
          </div>
        </label>

        <label
          class="cursor-pointer flex items-start gap-3 p-4 rounded-lg border-2 transition-all hover:bg-white/5"
          class:border-primary={settings.timerMode === "wall-clock"}
          class:border-base-300={settings.timerMode !== "wall-clock"}
          class:bg-primary={settings.timerMode === "wall-clock"}
          class:bg-opacity-10={settings.timerMode === "wall-clock"}
        >
          <input
            type="radio"
            name="timerMode"
            value="wall-clock"
            bind:group={settings.timerMode}
            class="radio radio-primary mt-1"
          />
          <div class="flex-1">
            <span class="font-medium text-base">Wall Clock</span>
            <p class="text-xs opacity-60 mt-1">
              Timer counts real time, even when not using computer
            </p>
          </div>
        </label>
      </div>
    </section>

    <!-- Work Schedule Section (NEW) -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">📅</span>
        Work Schedule
      </h2>

      <p class="text-sm opacity-60 mb-4">
        Automate your breaks based on your work routine. Rules execute
        automatically at the specified time.
      </p>

      <!-- Schedule Mode Selector -->
      <div class="mb-6">
        <label class="label py-1"
          ><span class="label-text text-sm font-medium">Schedule Mode</span
          ></label
        >
        <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
          <label
            class="cursor-pointer flex items-center gap-3 p-3 rounded-lg border-2 transition-all hover:bg-white/5"
            class:border-primary={scheduleMode === "same_every_day"}
            class:border-base-300={scheduleMode !== "same_every_day"}
            class:bg-primary={scheduleMode === "same_every_day"}
            class:bg-opacity-10={scheduleMode === "same_every_day"}
          >
            <input
              type="radio"
              name="scheduleMode"
              value="same_every_day"
              bind:group={scheduleMode}
              class="radio radio-primary radio-sm"
            />
            <div>
              <span class="font-medium text-sm">Same Every Day</span>
              <p class="text-xs opacity-60">Simple daily schedule</p>
            </div>
          </label>
          <label
            class="cursor-pointer flex items-center gap-3 p-3 rounded-lg border-2 transition-all hover:bg-white/5"
            class:border-primary={scheduleMode === "weekday_weekend"}
            class:border-base-300={scheduleMode !== "weekday_weekend"}
            class:bg-primary={scheduleMode === "weekday_weekend"}
            class:bg-opacity-10={scheduleMode === "weekday_weekend"}
          >
            <input
              type="radio"
              name="scheduleMode"
              value="weekday_weekend"
              bind:group={scheduleMode}
              class="radio radio-primary radio-sm"
            />
            <div>
              <span class="font-medium text-sm">Weekday/Weekend</span>
              <p class="text-xs opacity-60">Different for work days</p>
            </div>
          </label>
          <label
            class="cursor-pointer flex items-center gap-3 p-3 rounded-lg border-2 transition-all hover:bg-white/5"
            class:border-primary={scheduleMode === "custom"}
            class:border-base-300={scheduleMode !== "custom"}
            class:bg-primary={scheduleMode === "custom"}
            class:bg-opacity-10={scheduleMode === "custom"}
          >
            <input
              type="radio"
              name="scheduleMode"
              value="custom"
              bind:group={scheduleMode}
              class="radio radio-primary radio-sm"
            />
            <div>
              <span class="font-medium text-sm">Custom</span>
              <p class="text-xs opacity-60">Full per-day control</p>
            </div>
          </label>
        </div>
      </div>

      <!-- Existing Rules -->
      {#if scheduleRules.length > 0}
        <div class="space-y-2 mb-4">
          {#each scheduleRules as rule}
            <div
              class="flex items-center gap-3 p-3 bg-base-200 rounded-lg"
              class:opacity-50={!rule.enabled}
            >
              <span class="font-mono text-lg font-semibold">{rule.time}</span>
              <span class="badge badge-primary"
                >{ACTION_LABELS[rule.action]}</span
              >
              <span class="text-sm flex-1">
                {rule.title || formatDays(rule.days)}
              </span>
              <input
                type="checkbox"
                checked={rule.enabled}
                on:change={() => handleToggleRule(rule)}
                class="toggle toggle-sm toggle-success"
              />
              <button
                type="button"
                class="btn btn-ghost btn-xs text-error"
                on:click={() => handleDeleteRule(rule.id)}>✕</button
              >
            </div>
          {/each}
        </div>
      {:else}
        <div class="text-center py-4 text-sm opacity-50 mb-4">
          No schedule rules yet. Add one below!
        </div>
      {/if}

      <!-- Add New Rule -->
      <div class="border border-base-300 rounded-lg p-4">
        <h3 class="text-sm font-medium mb-3">Add New Rule</h3>
        <div class="form-control mb-3">
          <label class="label py-1"
            ><span class="label-text text-xs">Title (optional)</span></label
          >
          <input
            type="text"
            bind:value={newRuleTitle}
            placeholder="e.g. Lunch Break, End of Day"
            class="input input-sm input-bordered"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="form-control">
            <label class="label py-1"
              ><span class="label-text text-xs">Time</span></label
            >
            <input
              type="time"
              bind:value={newRuleTime}
              class="input input-sm input-bordered"
            />
          </div>
          <div class="form-control">
            <label class="label py-1"
              ><span class="label-text text-xs">Action</span></label
            >
            <select
              bind:value={newRuleAction}
              class="select select-sm select-bordered"
            >
              <option value="pause">⏸️ Pause</option>
              <option value="resume">▶️ Resume</option>
              <option value="reset">🔄 Reset Timers</option>
              <option value="start_session">🚀 Start Session</option>
              <option value="end_session">🛑 End Session</option>
            </select>
          </div>
        </div>
        <div class="form-control mt-3">
          <label class="label py-1"
            ><span class="label-text text-xs">Days</span></label
          >
          <!-- Different day selectors based on mode -->
          {#if scheduleMode === "same_every_day"}
            <div class="text-sm opacity-70 p-2 bg-base-200 rounded">
              Rule will apply to all 7 days
            </div>
          {:else if scheduleMode === "weekday_weekend"}
            <div class="flex gap-2">
              <button
                type="button"
                class="btn btn-sm flex-1"
                class:btn-primary={newRuleDays.includes("mon")}
                class:btn-outline={!newRuleDays.includes("mon")}
                on:click={() => {
                  newRuleDays = ["mon", "tue", "wed", "thu", "fri"];
                }}>Weekdays (Mon-Fri)</button
              >
              <button
                type="button"
                class="btn btn-sm flex-1"
                class:btn-primary={newRuleDays.includes("sat") &&
                  !newRuleDays.includes("mon")}
                class:btn-outline={!newRuleDays.includes("sat") ||
                  newRuleDays.includes("mon")}
                on:click={() => {
                  newRuleDays = ["sat", "sun"];
                }}>Weekends (Sat-Sun)</button
              >
            </div>
          {:else}
            <div class="flex flex-wrap gap-1">
              {#each ALL_DAYS as day}
                <button
                  type="button"
                  class="btn btn-xs"
                  class:btn-primary={newRuleDays.includes(day)}
                  class:btn-outline={!newRuleDays.includes(day)}
                  on:click={() => toggleDay(day)}>{DAY_LABELS[day]}</button
                >
              {/each}
            </div>
          {/if}
        </div>
        <button
          type="button"
          class="btn btn-primary btn-sm mt-4 w-full"
          on:click={async () => {
            try {
              const daysToUse =
                scheduleMode === "same_every_day" ? ALL_DAYS : newRuleDays;
              console.log("[WorkSchedule] Adding rule with:", {
                time: newRuleTime,
                action: newRuleAction,
                days: daysToUse,
                mode: scheduleMode,
              });
              await addScheduleRule(
                newRuleTime,
                newRuleAction,
                daysToUse,
                newRuleTitle,
              );
              console.log(
                "[WorkSchedule] Rule added successfully, refreshing...",
              );
              // Clear title input after adding
              newRuleTitle = "";
              // Force refresh the rules list in case event wasn't received
              await getScheduleRules();
              console.log("[WorkSchedule] Refresh complete");
            } catch (e) {
              console.error("[WorkSchedule] Failed to add rule:", e);
            }
          }}
          disabled={scheduleMode !== "same_every_day" &&
            newRuleDays.length === 0}>Add Rule</button
        >
      </div>
    </section>

    <!-- Immersive Mode Section -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">🎮</span>
        Immersive Mode (Zen)
      </h2>

      <p class="text-sm opacity-60 mb-4">
        When enabled, Aura will suppress break reminders during fullscreen apps
        or specified programs.
      </p>

      <div class="space-y-4">
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              bind:checked={settings.autoDetectFullscreen}
              class="toggle toggle-primary"
            />
            <span class="label-text">Auto-detect fullscreen apps</span>
          </label>
        </div>

        <div class="form-control">
          <span class="label">
            <span class="label-text">Blocked Applications</span>
          </span>
          <div class="flex gap-2 mb-2">
            <input
              type="text"
              placeholder="e.g., game.exe"
              bind:value={newBlockedApp}
              class="input input-bordered input-sm flex-1"
              on:keydown={(e) => e.key === "Enter" && addBlockedApp()}
              aria-label="Add blocked application"
            />
            <button class="btn btn-sm btn-primary" on:click={addBlockedApp}
              >Add</button
            >
          </div>
          <div class="flex flex-wrap gap-2">
            {#each settings.blockedApps as app}
              <span class="badge badge-lg gap-2">
                {app}
                <button
                  class="btn btn-ghost btn-xs"
                  on:click={() => removeBlockedApp(app)}>✕</button
                >
              </span>
            {/each}
          </div>
        </div>
      </div>
    </section>

    <!-- App Behavior Section -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">⚙️</span>
        App Behavior
      </h2>

      <div class="space-y-3">
        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              bind:checked={settings.autoStart}
              class="toggle toggle-primary"
            />
            <div>
              <span class="label-text">Start with system</span>
              <p class="text-xs opacity-60">
                Launch Aura automatically on login
              </p>
            </div>
          </label>
        </div>

        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              bind:checked={settings.closeToTray}
              class="toggle toggle-primary"
            />
            <div>
              <span class="label-text">Close to system tray</span>
              <p class="text-xs opacity-60">
                Keep running in background when closed
              </p>
            </div>
          </label>
        </div>

        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-4">
            <input
              type="checkbox"
              bind:checked={settings.soundEnabled}
              class="toggle toggle-primary"
            />
            <div>
              <span class="label-text">Sound notifications</span>
              <p class="text-xs opacity-60">
                Play a gentle sound for break reminders
              </p>
            </div>
          </label>
        </div>
      </div>
    </section>

    <!-- Data & Privacy Section -->
    <section class="glass-card">
      <h2 class="text-lg font-medium mb-4 flex items-center gap-2">
        <span class="text-xl">🔒</span>
        Data & Privacy
      </h2>

      <p class="text-sm opacity-60 mb-4">
        All your data is stored locally on your device. Aura never sends data to
        external servers.
      </p>

      <div class="flex flex-wrap gap-3">
        <button class="btn btn-outline btn-sm" on:click={handleExportData}>
          Export Training Data
        </button>
        <button class="btn btn-outline btn-sm btn-error">
          Clear All Data
        </button>
      </div>

      {#if exportMessage}
        <div class="mt-3 text-sm text-success">
          ✓ {exportMessage}
        </div>
      {/if}

      <div class="mt-4 text-xs opacity-40">
        <p>Database location: ~/.aura/aura.db</p>
      </div>
    </section>

    <!-- Save Button -->
    <div class="flex justify-end gap-4 pt-4 items-center">
      {#if saveSuccess}
        <span class="text-sm text-success">✓ Settings saved!</span>
      {/if}
      <button
        class="btn btn-primary btn-lg"
        class:loading={isSaving}
        on:click={saveSettings}
        disabled={isSaving || isLoading}
      >
        {isSaving ? "Saving..." : "Save Settings"}
      </button>
    </div>
  </div>

  <!-- Footer -->
  <footer class="mt-12 text-center text-xs opacity-40">
    <p>Aura v1.2.0 - Phase 2: UI Polish</p>
  </footer>
</main>
