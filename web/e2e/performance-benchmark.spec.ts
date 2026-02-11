import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CTRK_FILE = path.resolve(__dirname, '../../input/20000101-010216.CTRK');

test.describe('Performance Benchmark', () => {
  test('measure key interaction timings', async ({ page }) => {
    // Inject performance measurement helpers
    await page.goto('/');

    // 1. Measure file upload → analysis visible
    const uploadStart = Date.now();
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 30000 });
    const uploadEnd = Date.now();
    const uploadTime = uploadEnd - uploadStart;

    // 2. Wait for charts to render
    await expect(page.locator('.chart-analog canvas')).toBeVisible({ timeout: 15000 });
    const chartsRenderedTime = Date.now() - uploadStart;

    // 3. Measure lap selection change
    const lapSelect = page.locator('#lap-select');
    const options = lapSelect.locator('option');
    const optionCount = await options.count();

    let lapChangeTime = 0;
    if (optionCount > 1) {
      const lapStart = Date.now();
      await lapSelect.selectOption({ index: 1 });
      // Wait for chart to re-render (canvas gets replaced)
      await page.waitForTimeout(100);
      await expect(page.locator('.chart-analog canvas')).toBeVisible({ timeout: 10000 });
      lapChangeTime = Date.now() - lapStart;
    }

    // 4. Measure channel toggle
    await page.locator('.selector-toggle').click();
    await expect(page.locator('#channel-selector-panel')).toBeVisible();
    const expandButton = page.locator('.expand-button').first();
    await expandButton.click();
    await expect(page.locator('.channel-item').first()).toBeVisible();

    const channelStart = Date.now();
    const firstCheckbox = page.locator('.channel-item input[type="checkbox"]').first();
    await firstCheckbox.click();
    await page.waitForTimeout(100);
    await expect(page.locator('.chart-analog canvas')).toBeVisible({ timeout: 10000 });
    const channelToggleTime = Date.now() - channelStart;

    // 5. Measure scroll performance (frame drops)
    // Go back to all laps for more data
    await lapSelect.selectOption({ value: 'all' });
    await page.waitForTimeout(500);

    const scrollMetrics = await page.evaluate(async () => {
      const frames: number[] = [];
      let lastFrameTime = performance.now();

      return new Promise<{ avgFps: number; minFps: number; frameTimes: number[] }>((resolve) => {
        let count = 0;

        function measureFrame(now: number) {
          const delta = now - lastFrameTime;
          if (delta > 0) {
            frames.push(delta);
          }
          lastFrameTime = now;
          count++;

          if (count < 60) {
            requestAnimationFrame(measureFrame);
          } else {
            const avgFrameTime = frames.reduce((a, b) => a + b, 0) / frames.length;
            const maxFrameTime = Math.max(...frames);
            resolve({
              avgFps: Math.round(1000 / avgFrameTime),
              minFps: Math.round(1000 / maxFrameTime),
              frameTimes: frames.map((f) => Math.round(f)),
            });
          }
        }

        // Start scroll to trigger repaints
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setTimeout(() => {
          window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
          requestAnimationFrame(measureFrame);
        }, 100);
      });
    });

    // 6. Measure hover/mousemove over chart (tooltip performance)
    const chartElement = page.locator('.chart-analog');
    const chartBox = await chartElement.boundingBox();
    let hoverFps = { avgFps: 0, minFps: 0 };

    if (chartBox) {
      // Start frame measurement, then move mouse across chart
      hoverFps = await page.evaluate(async (box) => {
        const frames: number[] = [];
        let lastFrameTime = performance.now();
        let measuring = true;

        function measureFrame(now: number) {
          const delta = now - lastFrameTime;
          if (delta > 0) frames.push(delta);
          lastFrameTime = now;
          if (measuring) requestAnimationFrame(measureFrame);
        }

        requestAnimationFrame(measureFrame);

        // Simulate mouse moves across the chart area
        const steps = 30;
        for (let i = 0; i < steps; i++) {
          const x = box.x + (box.width * i) / steps;
          const y = box.y + box.height / 2;
          const evt = new MouseEvent('mousemove', {
            clientX: x,
            clientY: y,
            bubbles: true,
          });
          document.elementFromPoint(x, y)?.dispatchEvent(evt);
          await new Promise((r) => setTimeout(r, 16)); // ~60fps tick
        }

        measuring = false;
        await new Promise((r) => setTimeout(r, 50));

        const avgFrameTime = frames.reduce((a, b) => a + b, 0) / frames.length;
        const maxFrameTime = Math.max(...frames);
        return {
          avgFps: Math.round(1000 / avgFrameTime),
          minFps: Math.round(1000 / maxFrameTime),
        };
      }, chartBox);
    }

    // Print results
    console.log('\n=== PERFORMANCE BENCHMARK RESULTS ===');
    console.log(`Upload → Analysis visible: ${uploadTime}ms`);
    console.log(`Upload → Charts rendered: ${chartsRenderedTime}ms`);
    console.log(`Lap selection change: ${lapChangeTime}ms`);
    console.log(`Channel toggle: ${channelToggleTime}ms`);
    console.log(`Scroll FPS (avg): ${scrollMetrics.avgFps}`);
    console.log(`Scroll FPS (min): ${scrollMetrics.minFps}`);
    console.log(`Hover FPS (avg): ${hoverFps.avgFps}`);
    console.log(`Hover FPS (min): ${hoverFps.minFps}`);
    console.log('=====================================\n');

    // Basic assertions (benchmarks, not hard failures)
    expect(uploadTime).toBeLessThan(15000);
  });
});
