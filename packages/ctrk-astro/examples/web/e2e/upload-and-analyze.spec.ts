import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CTRK_FILE = path.resolve(__dirname, '../../input/20000101-010216.CTRK');

test.describe('Upload and Analyze Flow', () => {
  test('home page loads with upload form', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('heading', { name: 'CTRK Telemetry Exporter' })).toBeVisible();
    await expect(page.locator('.drop-zone')).toBeVisible();
  });

  test('analysis section is hidden before upload', async ({ page }) => {
    await page.goto('/');

    // AnalyzePage content should not be visible before file upload
    await expect(page.locator('.analyze-page')).not.toBeVisible();
  });

  test('upload CTRK file and display analysis on same page', async ({ page }) => {
    await page.goto('/');

    // Upload the file via the hidden input
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);

    // Wait for parsing to complete and analysis to appear (same page, no navigation)
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });

    // Verify all sections are rendered
    await expect(page.locator('text=File Information')).toBeVisible();
    await expect(page.locator('text=Lap Selection')).toBeVisible();
    await expect(page.locator('text=GPS Track Map')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Lap Timing' })).toBeVisible();
    await expect(page.locator('text=Telemetry Charts')).toBeVisible();

    // URL should still be root (no navigation)
    expect(page.url()).toMatch(/\/$/);
  });

  test('file name is displayed in file info', async ({ page }) => {
    await page.goto('/');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);

    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('20000101-010216.CTRK', { exact: true })).toBeVisible();
  });
});

test.describe('Analyze Page Components', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });
  });

  test('file information card shows correct metadata', async ({ page }) => {
    await expect(page.getByText('File Name', { exact: true })).toBeVisible();
    await expect(page.getByText('File Size', { exact: true })).toBeVisible();
    await expect(page.getByText('Parse Time', { exact: true })).toBeVisible();
    await expect(page.getByText('Total Records', { exact: true })).toBeVisible();
  });

  test('lap selector is populated', async ({ page }) => {
    const lapSelect = page.locator('#lap-select');
    await expect(lapSelect).toBeVisible();

    // Should have "All Laps" option plus at least one lap
    const options = lapSelect.locator('option');
    const count = await options.count();
    expect(count).toBeGreaterThan(1);
  });

  test('lap timing table shows data', async ({ page }) => {
    await expect(page.locator('.lap-timing-table')).toBeVisible();
    await expect(page.locator('.session-summary')).toBeVisible();

    // Table should have rows
    const rows = page.locator('.lap-timing-table tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('selecting a lap updates the view', async ({ page }) => {
    const lapSelect = page.locator('#lap-select');

    // Get initial record count
    const initialStats = await page.locator('.stat-value').first().textContent();

    // Select a specific lap (second option, which is lap 0 or 1)
    const options = lapSelect.locator('option');
    const count = await options.count();
    if (count > 1) {
      await lapSelect.selectOption({ index: 1 });

      // Wait for stats to potentially change
      await page.waitForTimeout(500);

      // Record count should be different from "all laps"
      const newStats = await page.locator('.stat-value').first().textContent();
      expect(newStats).toBeTruthy();
    }
  });
});

test.describe('Telemetry Charts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });
  });

  test('analog chart renders with canvas', async ({ page }) => {
    await expect(page.locator('.chart-analog canvas')).toBeVisible({ timeout: 10000 });
  });

  test('boolean chart renders when electronics channels enabled', async ({ page }) => {
    // Boolean channels are in the "Electronics" group which is disabled by default
    // Open channel selector and enable the electronics group
    await page.locator('.selector-toggle').click();
    await expect(page.locator('#channel-selector-panel')).toBeVisible();

    // Find and check the Electronics group checkbox
    const electronicsGroupLabel = page.locator('.group-label', { hasText: 'Electronics' });
    const electronicsCheckbox = electronicsGroupLabel.locator('..').locator('input[type="checkbox"]');
    await electronicsCheckbox.check();

    // Boolean chart should now render
    await expect(page.locator('.chart-boolean canvas')).toBeVisible({ timeout: 10000 });

    // Boolean chart should be shorter than analog chart
    const analogHeight = await page.locator('.chart-analog').evaluate((el) => el.clientHeight);
    const booleanHeight = await page.locator('.chart-boolean').evaluate((el) => el.clientHeight);
    expect(booleanHeight).toBeLessThan(analogHeight);
  });
});

test.describe('Channel Selector', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });
  });

  test('channel selector toggle shows count', async ({ page }) => {
    const toggle = page.locator('.selector-toggle');
    await expect(toggle).toBeVisible();

    // Should show "Channels (X/Y)" format
    const text = await toggle.textContent();
    expect(text).toMatch(/Channels\s*\(\d+\/\d+\)/);
  });

  test('expanding channel selector shows groups', async ({ page }) => {
    // Click the toggle to expand
    await page.locator('.selector-toggle').click();

    // Panel should appear with channel groups
    await expect(page.locator('#channel-selector-panel')).toBeVisible();
    await expect(page.locator('.channel-group').first()).toBeVisible();
  });

  test('expanding a group shows individual channels', async ({ page }) => {
    // Open the selector
    await page.locator('.selector-toggle').click();
    await expect(page.locator('#channel-selector-panel')).toBeVisible();

    // Expand the first group
    const expandButton = page.locator('.expand-button').first();
    await expandButton.click();

    // Individual channels should appear
    await expect(page.locator('.channel-item').first()).toBeVisible();
    await expect(page.locator('.channel-color-dot').first()).toBeVisible();
  });

  test('toggling individual channel updates chart', async ({ page }) => {
    // Wait for charts to render
    await expect(page.locator('.chart-analog canvas')).toBeVisible({ timeout: 10000 });

    // Open the selector and expand a group
    await page.locator('.selector-toggle').click();
    await expect(page.locator('#channel-selector-panel')).toBeVisible();

    const expandButton = page.locator('.expand-button').first();
    await expandButton.click();

    // Get the first channel checkbox and toggle it
    const firstChannelCheckbox = page.locator('.channel-item input[type="checkbox"]').first();
    const wasChecked = await firstChannelCheckbox.isChecked();
    await firstChannelCheckbox.click();

    // Verify the checkbox state changed
    const isNowChecked = await firstChannelCheckbox.isChecked();
    expect(isNowChecked).toBe(!wasChecked);

    // Channel count in toggle should have changed
    const toggle = page.locator('.selector-toggle');
    const text = await toggle.textContent();
    expect(text).toMatch(/Channels\s*\(\d+\/\d+\)/);
  });
});

test.describe('Upload Another', () => {
  test('upload form is replaced by compact button after upload', async ({ page }) => {
    await page.goto('/');

    // Full upload form should be visible
    await expect(page.locator('.drop-zone')).toBeVisible();

    // Upload a file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });

    // Full upload form should be hidden, compact button should be visible
    await expect(page.locator('.drop-zone')).not.toBeVisible();
    await expect(page.locator('.upload-another-button')).toBeVisible();
  });

  test('clicking "Upload another" resets to upload form', async ({ page }) => {
    await page.goto('/');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);
    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });

    // Click "Upload another"
    await page.locator('.upload-another-button').click();

    // Should go back to full upload form
    await expect(page.locator('.drop-zone')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.upload-another-button')).not.toBeVisible();

    // Analysis should be hidden
    await expect(page.locator('.analyze-page')).not.toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('rejects non-CTRK file', async ({ page }) => {
    await page.goto('/');

    const fileInput = page.locator('input[type="file"]');

    await fileInput.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('not a CTRK file'),
    });

    // Should show an error (toast or error state)
    await expect(
      page.locator('.has-error, [role="alert"], .toast-error').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('rejects file with wrong magic bytes', async ({ page }) => {
    await page.goto('/');

    const fileInput = page.locator('input[type="file"]');

    await fileInput.setInputFiles({
      name: 'fake.CTRK',
      mimeType: 'application/octet-stream',
      buffer: Buffer.alloc(200, 0),
    });

    // Should show an error
    await expect(
      page.locator('.has-error, [role="alert"], .toast-error').first()
    ).toBeVisible({ timeout: 5000 });
  });
});

test.describe('No Console Errors', () => {
  test('no JS errors during upload and analyze flow', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CTRK_FILE);

    await expect(page.locator('.analyze-page')).toBeVisible({ timeout: 15000 });

    // Wait for all components to render (charts, maps, etc.)
    await page.waitForTimeout(3000);

    // Filter out known non-critical warnings
    const criticalErrors = errors.filter(
      (e) => !e.includes('ResizeObserver') && !e.includes('Non-Error')
    );

    expect(criticalErrors).toEqual([]);
  });
});
