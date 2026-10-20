<template>
  <div class="app-layout">
    <AppNav />
    <div class="app-body">
      <aside class="app-sidebar">
        <ChatPanel />
      </aside>
      <main class="app-main">
        <ResultPanel />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppNav from '../components/AppNav.vue'
import ChatPanel from '../components/ChatPanel.vue'
import ResultPanel from '../components/ResultPanel.vue'
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.app-sidebar {
  flex-shrink: 0;
  width: 380px;
  border-right: var(--border-light);
  background: var(--color-bg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  min-width: 0;
  padding: 0;
  background: var(--color-bg-page);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
