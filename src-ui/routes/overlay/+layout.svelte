<!--
  Overlay Layout - Minimal layout for transparent overlay window
  Does NOT import app.css to avoid background styles
-->
<script lang="ts">
  import { onMount } from 'svelte';
</script>

<slot />

<style>
  /* Reset all styles for overlay - must be completely transparent */
  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  
  :global(html) {
    background: transparent !important;
    background-color: transparent !important;
    overflow: hidden !important;
    border: none !important;
    outline: none !important;
  }
  
  :global(body) {
    background: transparent !important;
    background-color: transparent !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    min-height: 100vh;
    border: none !important;
    outline: none !important;
    /* Prevent any scrollbars which can appear as borders */
    scrollbar-width: none;
    -ms-overflow-style: none;
    /* Allow click-through on transparent areas (WebKit) */
    -webkit-app-region: no-drag;
  }
  
  :global(body::-webkit-scrollbar) {
    display: none;
    width: 0;
    height: 0;
  }
</style>
