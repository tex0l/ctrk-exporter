import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import ctrk from '@ctrk-exporter/astro-integration';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  integrations: [
    vue(),
    ctrk()
  ],
  vite: {
    optimizeDeps: {
      include: ['@ctrk/parser']
    },
    worker: {
      format: 'es'
    }
  }
});
