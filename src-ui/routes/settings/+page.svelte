<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { page } from "$app/stores";
  import {
    getSettings,
    onSettings,
    getScheduleRules,
    onScheduleRules,
    onScheduleRuleAdded,
    onScheduleRuleUpdated,
    onScheduleRuleDeleted,
    isAutostartEnabled,
    type ScheduleRule,
  } from "$lib/ipc";
  import type { UnlistenFn } from "@tauri-apps/api/event";

  // Components
  import SettingsSidebar from "$lib/components/settings/SettingsSidebar.svelte";
  import SettingsGeneral from "$lib/components/settings/SettingsGeneral.svelte";
  import SettingsWellness from "$lib/components/settings/SettingsWellness.svelte";
  import SettingsSchedule from "$lib/components/settings/SettingsSchedule.svelte";
  import SettingsImmersive from "$lib/components/settings/SettingsImmersive.svelte";
  import SettingsData from "$lib/components/settings/SettingsData.svelte";
  import SettingsAbout from "$lib/components/settings/SettingsAbout.svelte";

  // State
  let activeTab = "general";
  let isLoading = true;
  let unlisteners: UnlistenFn[] = [];

  // Determine back link based on query param
  $: backLink =
    $page.url.searchParams.get("from") === "session" ? "/session" : "/";

  // Shared Settings Object
  let settings = {
    microBreakInterval: 20,
    macroBreakInterval: 45,
    hydrationInterval: 30,
    microBreakDuration: 20,
    macroBreakDuration: 300,
    dailyWaterGoal: 2000,
    autoStart: false,
    closeToTray: true,
    soundEnabled: true,
    autoDetectFullscreen: true,
    blockedApps: [] as string[],
    timerMode: "active" as "active" | "wall-clock",
  };

  let scheduleRules: ScheduleRule[] = [];

  onMount(async () => {
    // Setup listeners
    unlisteners = await Promise.all([
      onSettings((loaded) => {
        if (loaded.micro_break_interval)
          settings.microBreakInterval = Math.round(
            parseInt(loaded.micro_break_interval) / 60,
          );
        if (loaded.macro_break_interval)
          settings.macroBreakInterval = Math.round(
            parseInt(loaded.macro_break_interval) / 60,
          );
        if (loaded.hydration_interval)
          settings.hydrationInterval = Math.round(
            parseInt(loaded.hydration_interval) / 60,
          );
        if (loaded.micro_break_duration)
          settings.microBreakDuration = parseInt(loaded.micro_break_duration);
        if (loaded.macro_break_duration)
          settings.macroBreakDuration = parseInt(loaded.macro_break_duration);
        if (loaded.water_goal)
          settings.dailyWaterGoal = parseInt(loaded.water_goal);
        if (loaded.auto_start)
          settings.autoStart = loaded.auto_start === "true";
        if (loaded.close_to_tray)
          settings.closeToTray = loaded.close_to_tray === "true";
        if (loaded.sound_enabled)
          settings.soundEnabled = loaded.sound_enabled === "true";
        if (loaded.auto_detect_fullscreen)
          settings.autoDetectFullscreen =
            loaded.auto_detect_fullscreen === "true";
        if (loaded.timer_mode)
          settings.timerMode = loaded.timer_mode as "active" | "wall-clock";
        if (loaded.blocklist_processes) {
          try {
            settings.blockedApps = JSON.parse(loaded.blocklist_processes);
          } catch (e) {}
        }
        isLoading = false;
      }),
      onScheduleRules((data) => {
        scheduleRules = data.rules;
      }),
      onScheduleRuleAdded((data) => {
        scheduleRules = data.rules;
      }),
      onScheduleRuleUpdated((data) => {
        scheduleRules = data.rules;
      }),
      onScheduleRuleDeleted((data) => {
        scheduleRules = data.rules;
      }),
    ]);

    // Load initial data
    try {
      await getSettings();
      await getScheduleRules();
      settings.autoStart = await isAutostartEnabled();
    } catch (e) {
      console.error("Failed to load settings:", e);
    }

    // Check URL params for initial tab
    const tabParam = $page.url.searchParams.get("tab");
    if (
      tabParam &&
      [
        "general",
        "wellness",
        "schedule",
        "immersive",
        "data",
        "about",
      ].includes(tabParam)
    ) {
      activeTab = tabParam;
    }
  });

  onDestroy(() => {
    unlisteners.forEach((u) => u());
  });
</script>

<svelte:head>
  <title>Settings - Aura</title>
</svelte:head>

<main class="min-h-screen bg-base-100 flex flex-col">
  <!-- Header -->
  <header
    class="h-16 border-b border-white/5 flex items-center px-6 gap-4 bg-base-100 z-10 sticky top-0"
  >
    <a
      href={backLink}
      class="btn btn-ghost btn-square btn-sm"
      aria-label="Go back"
    >
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
    <h1 class="text-xl font-light">Settings</h1>
  </header>

  <div class="flex-1 flex overflow-hidden">
    <!-- Sidebar -->
    <aside
      class="w-64 border-r border-white/5 bg-base-100 hidden md:block pt-6"
    >
      <SettingsSidebar {activeTab} on:change={(e) => (activeTab = e.detail)} />
    </aside>

    <!-- Main Content -->
    <div class="flex-1 overflow-y-auto p-6 md:p-12 relative">
      {#if isLoading}
        <div class="absolute inset-0 flex items-center justify-center">
          <span class="loading loading-spinner loading-lg opacity-20"></span>
        </div>
      {:else}
        <div class="max-w-2xl mx-auto">
          {#if activeTab === "general"}
            <SettingsGeneral {settings} />
          {:else if activeTab === "wellness"}
            <SettingsWellness {settings} />
          {:else if activeTab === "schedule"}
            <SettingsSchedule bind:scheduleRules />
          {:else if activeTab === "immersive"}
            <SettingsImmersive {settings} />
          {:else if activeTab === "data"}
            <SettingsData />
          {:else if activeTab === "about"}
            <SettingsAbout />
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <!-- Mobile Tab Bar (visible only on small screens) -->
  <div class="md:hidden btm-nav btm-nav-sm border-t border-white/5 z-20">
    <button
      class:active={activeTab === "general"}
      on:click={() => (activeTab = "general")}
    >
      <span class="text-xl">⚙️</span>
    </button>
    <button
      class:active={activeTab === "wellness"}
      on:click={() => (activeTab = "wellness")}
    >
      <span class="text-xl">⏰</span>
    </button>
    <button
      class:active={activeTab === "schedule"}
      on:click={() => (activeTab = "schedule")}
    >
      <span class="text-xl">📅</span>
    </button>
    <button
      class:active={activeTab === "immersive"}
      on:click={() => (activeTab = "immersive")}
    >
      <span class="text-xl">🎮</span>
    </button>
  </div>
</main>
