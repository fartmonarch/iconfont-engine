#!/usr/bin/env node
/**
 * 02_resolve_download_assets.js — Phase 2 Script 01 (纯 IO)
 *
 * 职责：下载 111 个 CSS + 解析 @font-face 提取 TTF URL + 下载 TTF
 *
 * 输入：sources/phase1_raw_links/all_iconfont_links.json
 * 输出：
 *   sources/phase2_assets/<assetId>/iconfont.css
 *   sources/phase2_assets/<assetId>/font.ttf (尽可能)
 *   sources/meta/assets_manifest.json
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const zlib = require('zlib');

// ========== 配置 ==========

const ROOT = path.resolve(__dirname, '..');
const INPUT_FILE = path.join(ROOT, 'sources/phase1_raw_links/all_iconfont_links.json');
const ASSETS_DIR = path.join(ROOT, 'sources/phase2_assets');
const META_DIR = path.join(ROOT, 'sources/meta');
const MANIFEST_FILE = path.join(META_DIR, 'assets_manifest.json');
const CSS_TIMEOUT = 15000;
const TTF_TIMEOUT = 30000;
const CONCURRENCY = 5; // 同时下载数

// ========== 工具函数 ==========

/**
 * HTTP/HTTPS GET 下载，自动跟随 301/302 重定向，支持 gzip 解压
 */
function httpGet(url, timeout) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const req = client.get(url, { timeout, headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        const location = res.headers.location;
        if (location) {
          httpGet(location.startsWith('//') ? 'https:' + location : location, timeout)
            .then(resolve, reject);
          return;
        }
      }
      if (res.statusCode < 200 || res.statusCode >= 300) {
        reject(new Error(`HTTP ${res.statusCode}: ${url}`));
        return;
      }

      const isGzip = res.headers['content-encoding'] === 'gzip';
      let stream = res;
      if (isGzip) {
        stream = res.pipe(zlib.createGunzip());
      }

      const chunks = [];
      stream.on('data', chunk => chunks.push(chunk));
      stream.on('end', () => resolve(Buffer.concat(chunks)));
      stream.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error(`Timeout: ${url}`)); });
  });
}

/**
 * 生成 assetId = sha256(cssUrl)[0:12]
 */
function genAssetId(url) {
  return crypto.createHash('sha256').update(url).digest('hex').slice(0, 12);
}

/**
 * 计算内容的 sha256 hex
 */
function sha256(buf) {
  return crypto.createHash('sha256').update(buf).digest('hex');
}

/**
 * 从 CSS 中解析 @font-face 的 TTF/WOFF URL
 * 支持绝对路径和相对路径（相对路径会基于 CSS URL 解析）
 */
function extractFontUrls(css, cssUrl) {
  const urls = { ttf: null, woff2: null, woff: null };
  const srcRe = /url\s*\(\s*["']?([^"')\s]+\.(ttf|woff2?)(?:\?[^"')\s]*)?)\s*["']?\)/gi;
  let m;
  while ((m = srcRe.exec(css)) !== null) {
    let url = m[1];
    const ext = m[2].toLowerCase();
    if (url.startsWith('//')) {
      url = 'https:' + url;
    } else if (url.startsWith('/') && !url.startsWith('//')) {
      // 绝对路径，补充域名
      const parsed = new URL(cssUrl);
      url = parsed.protocol + '//' + parsed.host + url;
    } else if (!url.startsWith('http') && !url.startsWith('data:')) {
      // 相对路径，基于 CSS URL 解析
      try {
        url = new URL(url, cssUrl).href;
      } catch (e) {
        // 解析失败跳过
        continue;
      }
    }
    if (ext === 'ttf' && !urls.ttf) urls.ttf = url;
    else if (ext === 'woff2' && !urls.woff2) urls.woff2 = url;
    else if (ext === 'woff' && !urls.woff) urls.woff = url;
  }
  return urls;
}

/**
 * 延迟函数
 */
function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/**
 * 并发控制：一次最多 concurrency 个任务
 */
async function runWithConcurrency(tasks, concurrency) {
  const results = [];
  let index = 0;

  async function worker() {
    while (index < tasks.length) {
      const i = index++;
      results[i] = await tasks[i]();
    }
  }

  const workers = Array(Math.min(concurrency, tasks.length)).fill(null).map(() => worker());
  await Promise.all(workers);
  return results;
}

// ========== 主流程 ==========

async function main() {
  console.log('=== Phase 2: Asset Resolver (Script 01: Download) ===');
  console.log('');

  // 确保输出目录存在
  fs.mkdirSync(ASSETS_DIR, { recursive: true });
  fs.mkdirSync(META_DIR, { recursive: true });

  // Step 1: 读取输入
  console.log('[1/5] 读取输入文件...');
  const linksData = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));
  const links = linksData.links;
  console.log(`  共 ${links.length} 个 CSS URL`);
  console.log('');

  // Step 2: 下载 CSS
  console.log('[2/5] 下载 CSS 文件...');
  let cssOk = 0;
  let cssFail = 0;

  const cssTasks = links.map((link, idx) => async () => {
    const url = link.url;
    const assetId = genAssetId(url);
    const assetDir = path.join(ASSETS_DIR, assetId);

    try {
      const cssBuf = await httpGet(url, CSS_TIMEOUT);
      fs.mkdirSync(assetDir, { recursive: true });
      fs.writeFileSync(path.join(assetDir, 'iconfont.css'), cssBuf);
      cssOk++;
      return {
        idx,
        url,
        assetId,
        usedBy: link.usedBy || [],
        cssBuf,
        cssContentHash: sha256(cssBuf),
        cssPath: `sources/phase2_assets/${assetId}/iconfont.css`,
        cssOk: true
      };
    } catch (err) {
      cssFail++;
      console.log(`  CSS 失败 [${idx + 1}/${links.length}] ${url.substring(0, 80)}... : ${err.message}`);
      return {
        idx,
        url,
        assetId,
        usedBy: link.usedBy || [],
        cssOk: false,
        cssError: err.message
      };
    }
  });

  const cssResults = await runWithConcurrency(cssTasks, CONCURRENCY);
  console.log(`  CSS 下载完成: 成功 ${cssOk}, 失败 ${cssFail}`);
  console.log('');

  // Step 3: 解析 @font-face 提取 TTF URL
  console.log('[3/5] 解析 @font-face 提取字体 URL...');
  let hasTtfUrl = 0;
  let noTtfUrl = 0;

  for (const r of cssResults) {
    if (!r.cssOk) {
      r.fontUrl = null;
      r.downloadStatus = 'css_404';
      noTtfUrl++;
      continue;
    }
    const cssText = r.cssBuf.toString('utf-8');
    const fontUrls = extractFontUrls(cssText, r.url);
    r.fontUrls = fontUrls;

    if (fontUrls.ttf) {
      r.fontUrl = fontUrls.ttf;
      hasTtfUrl++;
    } else if (fontUrls.woff2) {
      r.fontUrl = fontUrls.woff2;
      r.fontFormat = 'woff2';
      hasTtfUrl++;
    } else if (fontUrls.woff) {
      r.fontUrl = fontUrls.woff;
      r.fontFormat = 'woff';
      hasTtfUrl++;
    } else {
      r.fontUrl = null;
      r.downloadStatus = 'no_ttf_url';
      noTtfUrl++;
      console.log(`  无字体 URL [${r.idx + 1}] ${r.url.substring(0, 80)}...`);
    }
  }

  console.log(`  找到字体 URL: ${hasTtfUrl}, 无字体: ${noTtfUrl}`);
  console.log('');

  // Step 4: 下载 TTF
  console.log('[4/5] 下载字体文件...');
  let ttfOk = 0;
  let ttfFail = 0;

  const ttfTasks = cssResults.map((r) => async () => {
    if (!r.fontUrl) {
      return; // CSS 失败或无字体 URL，跳过
    }

    let fontUrl = r.fontUrl;
    if (fontUrl.startsWith('//')) {
      fontUrl = 'https:' + fontUrl;
    }

    try {
      const ttfBuf = await httpGet(fontUrl, TTF_TIMEOUT);
      const assetDir = path.join(ASSETS_DIR, r.assetId);
      fs.writeFileSync(path.join(assetDir, 'font.ttf'), ttfBuf);
      r.ttfPath = `sources/phase2_assets/${r.assetId}/font.ttf`;
      r.ttfContentHash = sha256(ttfBuf);
      r.downloadStatus = 'ok';
      ttfOk++;
    } catch (err) {
      ttfFail++;
      r.downloadStatus = 'ttf_404';
      r.ttfError = err.message;
      console.log(`  TTF 失败 ${r.assetId}: ${err.message}`);
    }
  });

  // 只对有 fontUrl 的执行下载
  const ttfActualTasks = cssResults.filter(r => r.fontUrl).map(r => {
    return ttfTasks[cssResults.indexOf(r)];
  });

  await runWithConcurrency(ttfActualTasks, CONCURRENCY);
  console.log(`  TTF 下载完成: 成功 ${ttfOk}, 失败 ${ttfFail}`);
  console.log('');

  // Step 5: 输出 manifest
  console.log('[5/5] 输出 assets_manifest.json...');

  const manifest = cssResults.map(r => ({
    assetId: r.assetId,
    cssUrl: r.url,
    cssPath: r.cssPath || null,
    cssContentHash: r.cssContentHash || null,
    fontUrl: r.fontUrl || null,
    fontFormat: r.fontFormat || 'ttf',
    ttfPath: r.ttfPath || null,
    ttfContentHash: r.ttfContentHash || null,
    sourceProjects: r.usedBy,
    templateVar: null, // 后续从 Phase 1 项目文件回填
    downloadStatus: r.downloadStatus || 'css_404'
  }));

  fs.writeFileSync(MANIFEST_FILE, JSON.stringify(manifest, null, 2), 'utf-8');
  console.log(`  已写入 ${MANIFEST_FILE}`);
  console.log('');

  // 汇总
  const statusSummary = {};
  for (const m of manifest) {
    statusSummary[m.downloadStatus] = (statusSummary[m.downloadStatus] || 0) + 1;
  }

  console.log('=== 完成 ===');
  console.log(`  总计: ${manifest.length} assets`);
  console.log('  状态分布:');
  for (const [status, count] of Object.entries(statusSummary)) {
    console.log(`    ${status}: ${count}`);
  }
  console.log(`  输出目录: ${ASSETS_DIR}`);
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
