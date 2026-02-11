import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CTRK_FILE = path.resolve(__dirname, '../../input/20000101-010216.CTRK');

test.describe('Chart X-axis Alignment', () => {
  test('analog and boolean chart X axes are pixel-aligned', async ({ page }) => {
    await page.goto('/');

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.chart-analog canvas')).toBeVisible({ timeout: 10000 });

    // Enable the electronics group to get the boolean chart
    await page.locator('.selector-toggle').click();
    await expect(page.locator('#channel-selector-panel')).toBeVisible();
    const electronicsCheckbox = page
      .locator('.group-label', { hasText: 'Electronics' })
      .locator('..')
      .locator('input[type="checkbox"]');
    await electronicsCheckbox.check();

    // Wait for both charts to render
    await expect(page.locator('.chart-boolean canvas')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);

    // Read chart area left positions from data attributes set by TelemetryChart.vue
    const analogChartAreaLeft = await page
      .locator('.chart-analog')
      .getAttribute('data-chart-area-left');
    const booleanChartAreaLeft = await page
      .locator('.chart-boolean')
      .getAttribute('data-chart-area-left');

    expect(analogChartAreaLeft).not.toBeNull();
    expect(booleanChartAreaLeft).not.toBeNull();

    const analogLeft = parseInt(analogChartAreaLeft!, 10);
    const booleanLeft = parseInt(booleanChartAreaLeft!, 10);

    console.log(
      `Chart area left: analog=${analogLeft}px, boolean=${booleanLeft}px, diff=${Math.abs(analogLeft - booleanLeft)}px`
    );

    // Both chart areas must start at the same pixel position (1px tolerance for rounding)
    expect(Math.abs(analogLeft - booleanLeft)).toBeLessThanOrEqual(1);
  });
});
