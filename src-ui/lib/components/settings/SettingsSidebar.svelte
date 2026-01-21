<script lang="ts">
    import { createEventDispatcher } from "svelte";

    export let activeTab: string = "general";

    const dispatch = createEventDispatcher();

    const tabs = [
        { id: "general", label: "General", icon: "⚙️" },
        { id: "wellness", label: "Wellness", icon: "⏰" },
        { id: "schedule", label: "Schedule", icon: "📅" },
        { id: "immersive", label: "Immersive", icon: "🎮" },
        { id: "data", label: "Data", icon: "🔒" },
    ];

    function selectTab(id: string) {
        dispatch("change", id);
    }
</script>

<div class="flex flex-col gap-2 w-full md:w-64 flex-shrink-0">
    <div class="px-4 py-2 mb-2">
        <h2 class="text-xs font-bold opacity-40 uppercase tracking-widest">
            Settings
        </h2>
    </div>

    {#each tabs as tab}
        <button
            class="flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all duration-200"
            class:bg-white={activeTab === tab.id}
            class:bg-opacity-10={activeTab === tab.id}
            class:text-primary={activeTab === tab.id}
            class:opacity-70={activeTab !== tab.id}
            class:hover:bg-white={activeTab !== tab.id}
            class:hover:bg-opacity-5={activeTab !== tab.id}
            on:click={() => selectTab(tab.id)}
        >
            <span class="text-xl">{tab.icon}</span>
            <span class="font-medium">{tab.label}</span>
            {#if activeTab === tab.id}
                <div class="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />
            {/if}
        </button>
    {/each}
</div>
