import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import ctrk from '@tex0l/ctrk-astro';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  output: 'static',
  integrations: [
    vue(),
    ctrk()
  ],
  vite: {
    plugins: [tailwindcss()]
  }
});
