import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import ctrk from '@tex0l/ctrk-astro';

export default defineConfig({
  output: 'static',
  integrations: [
    vue(),
    ctrk()
  ]
});
