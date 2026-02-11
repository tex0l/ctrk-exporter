<template>
  <header class="app-header" role="banner">
    <div class="header-content">
      <div class="header-brand">
        <h1 class="brand-title">CTRK Exporter</h1>
        <p class="brand-subtitle">Yamaha Y-Trac Telemetry Analysis</p>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  padding: 1rem 2rem;
  margin-bottom: 2rem;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
}

.header-brand {
  flex: 1;
}

.brand-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-accent);
}

.brand-subtitle {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

/* Mobile: < 640px */
@media (max-width: 639px) {
  .app-header {
    padding: 0.875rem 1rem;
    margin-bottom: 1rem;
  }

  .brand-title {
    font-size: 1.25rem;
  }

  .brand-subtitle {
    font-size: 0.75rem;
  }
}

/* Tablet: 640px - 1023px */
@media (min-width: 640px) and (max-width: 1023px) {
  .app-header {
    padding: 1rem 1.5rem;
  }
}

/* Desktop: >= 1024px */
@media (min-width: 1024px) {
  .app-header {
    padding: 1rem 2rem;
  }
}
</style>
