/**
 * Astro integration for CTRK telemetry parser
 *
 * This integration sets up Vue.js support and provides configuration
 * for the CTRK parser components.
 */

import type { AstroIntegration } from 'astro';

export interface CTRKIntegrationOptions {}

/**
 * Astro integration for CTRK telemetry parser
 *
 * @param options - Integration configuration options
 * @returns Astro integration configuration
 *
 * @example
 * ```js
 * // astro.config.mjs
 * import { defineConfig } from 'astro/config';
 * import vue from '@astrojs/vue';
 * import ctrk from '@ctrk-exporter/astro-integration';
 *
 * export default defineConfig({
 *   integrations: [
 *     vue(),
 *     ctrk()
 *   ]
 * });
 * ```
 */
export default function createIntegration(
  _options: CTRKIntegrationOptions = {}
): AstroIntegration {
  return {
    name: '@ctrk-exporter/astro-integration',
    hooks: {
      'astro:config:setup': ({ updateConfig }) => {
        updateConfig({
          vite: {
            optimizeDeps: {
              include: ['@ctrk/parser'],
            },
          },
        });
      },
    },
  };
}
