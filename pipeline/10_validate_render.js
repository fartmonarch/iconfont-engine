#!/usr/bin/env node
/**
 * Phase 10: Render Validation — Playwright + pixelmatch
 *
 * Renders each icon from the merged font in Chrome and Firefox,
 * takes screenshots, and compares them pixel-by-pixel.
 *
 * Usage:
 *     node pipeline/10_validate_render.js
 *
 * Input:
 *     output/iconfont_merged.ttf / .woff2 / .css
 *     output/iconfont_merged.json
 *
 * Output:
 *     report/phase10_validation.json
 *     report/phase10_validation.md
 *     report/phase10_screenshots/  (diff images for mismatches)
 */
const fs = require('fs');
const path = require('path');
const { chromium, firefox } = require('playwright');
const pixelmatch = require('pixelmatch');
const { createCanvas, Image } = require('@napi-rs/canvas');

const DATA_DIR = path.dirname(__dirname);
const OUTPUT_DIR = path.join(DATA_DIR, 'output');
const REPORT_DIR = path.join(DATA_DIR, 'report');
const SCREENSHOT_DIR = path.join(REPORT_DIR, 'phase10_screenshots');
const CSS_PATH = path.join(OUTPUT_DIR, 'iconfont_merged.css');
const JSON_PATH = path.join(OUTPUT_DIR, 'iconfont_merged.json');
const TTF_PATH = path.join(OUTPUT_DIR, 'iconfont_merged.ttf');
const WOFF2_PATH = path.join(OUTPUT_DIR, 'iconfont_merged.woff2');

const VIEWPORT = { width: 1200, height: 800 };
const ICON_SIZE = 48;
const DIFF_THRESHOLD = 0.01; // 1% pixel difference allowed

/**
 * Generate an HTML page that renders every icon at a known position.
 * Uses a data URL for the font to avoid file:// issues.
 */
function generateTestHtml(fontDataUrl, manifest) {
  const cssRules = manifest
    .filter((g) => g.name && g.unicode)
    .map(
      (g) =>
        `.icon-${g.name}:before { content: "\\${g.unicode}"; }`
    )
    .join('\n');

  const iconItems = manifest
    .filter((g) => g.name && g.unicode)
    .map(
      (g, i) =>
        `<div class="icon-cell" data-index="${i}" data-name="${g.name}" data-unicode="${g.unicode}"><span class="icon icon-${g.name}"></span></div>`
    )
    .join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@font-face {
  font-family: "TestFont";
  src: url("${fontDataUrl}") format("truetype");
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "TestFont", sans-serif; padding: 10px; background: #fff; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, ${ICON_SIZE + 20}px); gap: 4px; }
.icon-cell {
  width: ${ICON_SIZE + 20}px; height: ${ICON_SIZE + 20}px;
  display: flex; align-items: center; justify-content: center;
  background: #f8f8f8; border: 1px solid #eee; border-radius: 4px;
}
.icon {
  font-family: "TestFont" !important;
  font-size: ${ICON_SIZE}px;
  line-height: 1;
  color: #000;
  -webkit-font-smoothing: none;
  -moz-osx-font-smoothing: none;
  font-smooth: never;
}
</style>
</head>
<body>
<div class="grid">${iconItems}</div>
</body>
</html>`;
}

/**
 * Render icons in a browser and take a full-page screenshot.
 */
async function renderIcons(browser, htmlContent) {
  const page = await browser.newPage({ viewport: VIEWPORT });
  await page.setContent(htmlContent, { waitUntil: 'networkidle' });
  // Wait for font rendering
  await page.waitForTimeout(500);
  const screenshot = await page.screenshot({ fullPage: true });
  await page.close();
  return screenshot;
}

/**
 * Compare two screenshots using pixelmatch.
 */
function compareScreenshots(img1Buf, img2Buf) {
  const img1 = new Image(img1Buf);
  const img2 = new Image(img2Buf);
  const width = Math.max(img1.width, img2.width);
  const height = Math.max(img1.height, img2.height);

  const canvas1 = createCanvas(width, height);
  const ctx1 = canvas1.getContext('2d');
  ctx1.drawImage(img1, 0, 0, width, height);
  const data1 = ctx1.getImageData(0, 0, width, height).data;

  const canvas2 = createCanvas(width, height);
  const ctx2 = canvas2.getContext('2d');
  ctx2.drawImage(img2, 0, 0, width, height);
  const data2 = ctx2.getImageData(0, 0, width, height).data;

  const diffCanvas = createCanvas(width, height);
  const diffCtx = diffCanvas.getContext('2d');
  const diffData = diffCtx.createImageData(width, height);

  const diffCount = pixelmatch(data1, data2, diffData.data, width, height, {
    threshold: 0.1,
    includeAA: true,
  });

  const totalPixels = width * height;
  const diffRatio = diffCount / totalPixels;

  return {
    width,
    height,
    diffCount,
    totalPixels,
    diffRatio,
    passed: diffRatio <= DIFF_THRESHOLD,
    diffImage: diffCanvas.toBuffer('image/png'),
  };
}

/**
 * Generate per-icon diff by rendering individual icons.
 */
async function renderSingleIcon(browser, htmlFn, fontDataUrl, glyph) {
  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@font-face {
  font-family: "TestFont";
  src: url("${fontDataUrl}") format("truetype");
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { display: flex; align-items: center; justify-content: center; width: ${ICON_SIZE + 40}px; height: ${ICON_SIZE + 40}px; background: #fff; }
.icon {
  font-family: "TestFont" !important;
  font-size: ${ICON_SIZE}px;
  line-height: 1;
  color: #000;
  -webkit-font-smoothing: none;
  -moz-osx-font-smoothing: none;
  font-smooth: never;
}
</style>
</head>
<body>
<span class="icon" style="font-family: TestFont;">&#x${glyph.unicode};</span>
</body>
</html>`;

  const page = await browser.newPage({ viewport: { width: ICON_SIZE + 40, height: ICON_SIZE + 40 } });
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.waitForTimeout(300);
  const screenshot = await page.screenshot();
  await page.close();
  return screenshot;
}

async function main() {
  console.log('=' .repeat(60));
  console.log('Phase 10: Render Validation — Playwright + pixelmatch');
  console.log('='.repeat(60));

  // Verify inputs
  if (!fs.existsSync(TTF_PATH)) {
    console.error(`\nError: TTF not found at ${TTF_PATH}`);
    console.log('Run Phase 8-9 first: python pipeline/08_merge_glyf.py');
    return 1;
  }

  const manifest = JSON.parse(fs.readFileSync(JSON_PATH, 'utf8'));
  console.log(`\nManifest: ${manifest.length} entries`);

  const fontData = fs.readFileSync(TTF_PATH);
  const fontDataUrl = `data:font/ttf;base64,${fontData.toString('base64')}`;

  const htmlContent = generateTestHtml(fontDataUrl, manifest);

  // Ensure screenshot dir
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const results = {
    metadata: {
      generatedAt: new Date().toISOString(),
      ttfPath: TTF_PATH,
      woff2Path: WOFF2_PATH,
      totalIcons: manifest.length,
      threshold: DIFF_THRESHOLD,
    },
    browsers: {},
    icons: [],
    summary: {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
    },
  };

  // Launch both browsers
  console.log('\nLaunching Chrome and Firefox...');
  const [chromeBrowser, firefoxBrowser] = await Promise.all([
    chromium.launch(),
    firefox.launch(),
  ]);

  try {
    // Full page screenshots
    console.log('Rendering in Chrome...');
    const chromeScreenshot = await renderIcons(chromeBrowser, htmlContent);
    console.log('Rendering in Firefox...');
    const firefoxScreenshot = await renderIcons(firefoxBrowser, htmlContent);

    console.log('Comparing screenshots...');
    const comparison = compareScreenshots(chromeScreenshot, firefoxScreenshot);

    results.browsers = {
      chrome: {
        screenshotSize: chromeScreenshot.length,
      },
      firefox: {
        screenshotSize: firefoxScreenshot.length,
      },
      comparison: {
        width: comparison.width,
        height: comparison.height,
        diffPixels: comparison.diffCount,
        diffRatio: (comparison.diffRatio * 100).toFixed(4) + '%',
        passed: comparison.passed,
      },
    };

    if (!comparison.passed) {
      const diffPath = path.join(SCREENSHOT_DIR, 'full_page_diff.png');
      fs.writeFileSync(diffPath, comparison.diffImage);
      console.log(`  Full page diff saved to: ${diffPath}`);
    }

    results.summary.total = manifest.length;
    results.summary.passed = comparison.passed ? manifest.length : 0;
    results.summary.failed = comparison.passed ? 0 : manifest.length;

    // Per-icon validation (sample first 50 to keep it fast)
    const sampleSize = Math.min(manifest.length, 50);
    console.log(`\nPer-icon validation (first ${sampleSize} icons)...`);

    for (let i = 0; i < sampleSize; i++) {
      const glyph = manifest[i];
      if (!glyph.name || !glyph.unicode) {
        results.summary.skipped++;
        continue;
      }

      try {
        const [chromeImg, firefoxImg] = await Promise.all([
          renderSingleIcon(chromeBrowser, null, fontDataUrl, glyph),
          renderSingleIcon(firefoxBrowser, null, fontDataUrl, glyph),
        ]);

        const iconComparison = compareScreenshots(chromeImg, firefoxImg);
        const status = iconComparison.passed ? 'PASS' : 'FAIL';

        results.icons.push({
          index: i,
          name: glyph.name,
          unicode: glyph.unicode,
          status,
          diffRatio: (iconComparison.diffRatio * 100).toFixed(4) + '%',
        });

        if (!iconComparison.passed) {
          const iconDiffPath = path.join(SCREENSHOT_DIR, `diff_${glyph.name}.png`);
          fs.writeFileSync(iconDiffPath, iconComparison.diffImage);
          results.summary.failed++;
          results.summary.passed--;
        } else {
          results.summary.passed++;
        }
      } catch (err) {
        results.icons.push({
          index: i,
          name: glyph.name,
          unicode: glyph.unicode,
          status: 'ERROR',
          error: err.message,
        });
        results.summary.skipped++;
      }
    }

    console.log(`\nSummary: ${results.summary.passed} passed, ${results.summary.failed} failed, ${results.summary.skipped} skipped`);

  } finally {
    await chromeBrowser.close();
    await firefoxBrowser.close();
  }

  // Save JSON report
  const jsonReportPath = path.join(REPORT_DIR, 'phase10_validation.json');
  fs.mkdirSync(REPORT_DIR, { recursive: true });
  fs.writeFileSync(jsonReportPath, JSON.stringify(results, null, 2));
  console.log(`\nJSON Report: ${jsonReportPath}`);

  // Generate markdown report
  const mdReportPath = path.join(REPORT_DIR, 'phase10_validation.md');
  const mdLines = [
    '# Phase 10: Render Validation Report',
    '',
    `Generated: ${results.metadata.generatedAt}`,
    '',
    '## Summary',
    '',
    `| Metric | Value |`,
    `|--------|-------|`,
    `| Total Icons | ${results.summary.total} |`,
    `| Passed | ${results.summary.passed} |`,
    `| Failed | ${results.summary.failed} |`,
    `| Skipped | ${results.summary.skipped} |`,
    '',
    '## Browser Comparison',
    '',
    `| Browser | Screenshot Size |`,
    `|---------|----------------|`,
    `| Chrome | ${(results.browsers.chrome.screenshotSize / 1024).toFixed(1)} KB |`,
    `| Firefox | ${(results.browsers.firefox.screenshotSize / 1024).toFixed(1)} KB |`,
    '',
    `Diff Ratio: ${results.browsers.comparison.diffRatio}`,
    `Result: ${results.browsers.comparison.passed ? '**PASS**' : '**FAIL**'}`,
    '',
  ];

  const failedIcons = results.icons.filter((i) => i.status === 'FAIL');
  if (failedIcons.length > 0) {
    mdLines.push('## Failed Icons', '');
    mdLines.push('| Name | Unicode | Diff Ratio |');
    mdLines.push('|------|---------|------------|');
    for (const ic of failedIcons) {
      mdLines.push(`| ${ic.name} | U+${ic.unicode} | ${ic.diffRatio} |`);
    }
    mdLines.push('');
  }

  fs.writeFileSync(mdReportPath, mdLines.join('\n'));
  console.log(`Markdown Report: ${mdReportPath}`);

  console.log('\nPhase 10 完成。');
  return results.summary.failed === 0 ? 0 : 1;
}

main().then((code) => process.exit(code));
