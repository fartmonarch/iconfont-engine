#!/usr/bin/env node
/**
 * Phase 12: Package Output
 *
 * Generates a standard iconfont distribution package in output/package/.
 * The package uses canonical `iconfont.*` naming so it can be dropped directly
 * into any front-end project.
 *
 * Input:
 *   output/iconfont_merged.ttf
 *   output/iconfont_merged.woff2
 *   output/iconfont_merged.json
 *
 * Output:
 *   output/package/
 *     iconfont.ttf
 *     iconfont.woff2
 *     iconfont.css          (standard @font-face + all icon classes)
 *     iconfont.json         (icon metadata: name/unicode/aliases/projects)
 *     demo_index.html       (self-contained preview — loads font via relative path)
 */

'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT_DIR = path.join(ROOT, 'output');
const PACKAGE_DIR = path.join(OUTPUT_DIR, 'package');
const FONT_FAMILY = 'iconfont';
const CSS_ICON_PREFIX = 'icon-';

// ─── helpers ────────────────────────────────────────────────────────────────

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function ensureDir(d) {
  fs.mkdirSync(d, { recursive: true });
}

// ─── CSS generation ─────────────────────────────────────────────────────────

function buildCss(icons) {
  const lines = [
    `@font-face {`,
    `  font-family: "${FONT_FAMILY}";`,
    `  src: url('iconfont.woff2') format('woff2'),`,
    `       url('iconfont.ttf') format('truetype');`,
    `  font-weight: normal;`,
    `  font-style: normal;`,
    `  font-display: block;`,
    `}`,
    ``,
    `.iconfont {`,
    `  font-family: "${FONT_FAMILY}" !important;`,
    `  font-size: 16px;`,
    `  font-style: normal;`,
    `  -webkit-font-smoothing: antialiased;`,
    `  -moz-osx-font-smoothing: grayscale;`,
    `}`,
    ``,
  ];

  // Primary icon classes
  for (const g of icons) {
    if (g.name && g.unicode) {
      lines.push(`.${CSS_ICON_PREFIX}${g.name}:before { content: "\\${g.unicode}"; }`);
    }
  }

  // Alias classes
  lines.push('');
  lines.push('/* Aliases */');
  for (const g of icons) {
    if (!g.unicode) continue;
    for (const alias of (g.aliases || [])) {
      if (alias && alias !== g.name) {
        lines.push(`.${CSS_ICON_PREFIX}${alias}:before { content: "\\${g.unicode}"; }`);
      }
    }
  }

  return lines.join('\n');
}

// ─── JSON manifest ───────────────────────────────────────────────────────────

function buildManifest(icons) {
  return icons.map((g) => ({
    name: g.name || '',
    unicode: g.unicode || '',
    aliases: g.aliases || [],
    projects: g.affectedProjects || [],
    resolution: g.resolution || '',
  }));
}

// ─── Demo HTML ───────────────────────────────────────────────────────────────

function buildDemoHtml(icons) {
  const isPuaConflict = (u) => { const n = parseInt(u, 16); return n >= 0xe000 && n < 0xe600; };

  const named = icons.filter((g) => g.name && g.unicode).sort((a, b) => a.name.localeCompare(b.name));

  const cssRules = named
    .map((g) => `.${CSS_ICON_PREFIX}${g.name}:before { content: "\\${g.unicode}"; }`)
    .join('\n');

  const puaCount = named.filter((g) => isPuaConflict(g.unicode)).length;
  const originalCount = named.length - puaCount;
  const aliasCount = named.reduce((s, g) => s + (g.aliases?.length || 0), 0);
  const projectSet = new Set(named.flatMap((g) => g.affectedProjects || []));

  const items = named
    .map((g) => {
      const isPua = isPuaConflict(g.unicode);
      const badge = isPua ? '<span class="badge-pua">PUA</span>' : '';
      const liClass = isPua ? 'dib dib-pua' : 'dib';
      const dec = parseInt(g.unicode, 16);
      const aliasList = (g.aliases || []).filter((a) => a !== g.name).slice(0, 3).join(', ');
      return `<li class="${liClass}" data-name="${g.name}">
        <span class="iconfont ${CSS_ICON_PREFIX}${g.name}"></span>
        <div class="name">${g.name} ${badge}</div>
        <div class="code">&#${dec}; / U+${g.unicode}</div>
        ${aliasList ? `<div class="alias">${aliasList}</div>` : ''}
      </li>`;
    })
    .join('\n');

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>iconfont — ${named.length} icons</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;list-style:none}
body{background:#f5f5f5;color:#333;font-family:"PingFang SC","Helvetica Neue",Arial,sans-serif}
@font-face{font-family:"iconfont";src:url("iconfont.woff2") format("woff2"),url("iconfont.ttf") format("truetype");font-display:block}
.iconfont{font-family:"iconfont"!important;font-style:normal;-webkit-font-smoothing:antialiased}
${cssRules}
.header{background:#fff;padding:24px 32px;border-bottom:1px solid #eee;position:sticky;top:0;z-index:10}
.header h1{font-size:20px;font-weight:600;margin-bottom:8px}
.stats{display:flex;gap:24px;margin-top:10px}
.stats .item{text-align:center}
.stats .num{font-size:22px;font-weight:700;color:#1677ff}
.stats .lbl{font-size:11px;color:#999;margin-top:2px}
.search-bar{margin-top:12px}
.search-bar input{width:320px;padding:6px 12px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;outline:none}
.search-bar input:focus{border-color:#1677ff}
.main{padding:24px 32px}
.legend{display:flex;gap:16px;margin-bottom:16px;font-size:12px;color:#666}
.legend-item{display:flex;align-items:center;gap:6px}
.legend-dot{width:10px;height:10px;border-radius:2px}
.dot-orig{background:#e6f4ff;border:1px solid #91caff}
.dot-pua{background:#fffde7;border:1px solid #ff9800}
ul.grid{display:flex;flex-wrap:wrap;gap:10px}
.dib{width:140px;padding:14px 10px;background:#fff;border:1px solid #eee;border-radius:8px;text-align:center;cursor:default;transition:.15s}
.dib:hover{box-shadow:0 2px 8px rgba(0,0,0,.1);transform:translateY(-1px)}
.dib .iconfont{font-size:32px;color:#333;display:block;margin-bottom:8px}
.dib .name{font-size:11px;color:#555;word-break:break-all;line-height:1.4;margin-bottom:3px;max-height:2.8em;overflow:hidden}
.dib .code{font-size:10px;color:#aaa;font-family:monospace}
.dib .alias{font-size:9px;color:#bbb;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dib-pua{border-color:#ff9800!important;background:#fffde7}
.badge-pua{display:inline-block;background:#ff9800;color:#fff;font-size:8px;padding:1px 4px;border-radius:2px;margin-left:3px;vertical-align:middle}
.hidden{display:none!important}
.footer{margin-top:40px;padding:20px;text-align:center;color:#bbb;font-size:11px;border-top:1px solid #eee}
</style>
</head>
<body>
<div class="header">
  <h1>iconfont — 统一图标库</h1>
  <div class="stats">
    <div class="item"><div class="num">${named.length}</div><div class="lbl">图标总数</div></div>
    <div class="item"><div class="num">${originalCount}</div><div class="lbl">原始图标</div></div>
    <div class="item"><div class="num">${puaCount}</div><div class="lbl">PUA 冲突解决</div></div>
    <div class="item"><div class="num">${aliasCount}</div><div class="lbl">别名数</div></div>
    <div class="item"><div class="num">${projectSet.size}</div><div class="lbl">来源项目</div></div>
  </div>
  <div class="search-bar">
    <input type="text" id="search" placeholder="搜索图标名称..." oninput="filterIcons(this.value)">
  </div>
</div>

<div class="main">
  <div class="legend">
    <div class="legend-item"><div class="legend-dot dot-orig"></div><span>原始编码 (E600+)</span></div>
    <div class="legend-item"><div class="legend-dot dot-pua"></div><span>PUA 冲突解决 (E000–E5FF)</span></div>
  </div>
  <ul class="grid" id="icon-grid">
${items}
  </ul>
  <p id="empty-tip" style="display:none;color:#999;padding:40px;text-align:center">未找到匹配图标</p>
</div>

<div class="footer">
  iconfont-engine 生成 · ${named.length} icons · ${new Date().toISOString().slice(0, 10)}
</div>

<script>
function filterIcons(q) {
  q = q.trim().toLowerCase();
  const items = document.querySelectorAll('#icon-grid .dib');
  let shown = 0;
  items.forEach(el => {
    const match = !q || el.dataset.name.toLowerCase().includes(q);
    el.classList.toggle('hidden', !match);
    if (match) shown++;
  });
  document.getElementById('empty-tip').style.display = shown === 0 ? 'block' : 'none';
}
</script>
</body>
</html>`;
}

// ─── main ────────────────────────────────────────────────────────────────────

function main() {
  console.log('='.repeat(60));
  console.log('Phase 12: Package Output');
  console.log('='.repeat(60));

  ensureDir(PACKAGE_DIR);

  // Load merged JSON
  const mergedJsonPath = path.join(OUTPUT_DIR, 'iconfont_merged.json');
  if (!fs.existsSync(mergedJsonPath)) {
    console.error(`错误: 未找到 ${mergedJsonPath}，请先运行 Phase 8-9 + 11`);
    process.exit(1);
  }
  const icons = loadJson(mergedJsonPath);
  console.log(`\n加载图标数据: ${icons.length} entries`);

  // 1. Copy font files
  for (const [src, dst] of [
    ['iconfont_merged.ttf', 'iconfont.ttf'],
    ['iconfont_merged.woff2', 'iconfont.woff2'],
  ]) {
    const srcPath = path.join(OUTPUT_DIR, src);
    const dstPath = path.join(PACKAGE_DIR, dst);
    if (fs.existsSync(srcPath)) {
      fs.copyFileSync(srcPath, dstPath);
      const size = Math.round(fs.statSync(dstPath).size / 1024);
      console.log(`  复制: ${dst} (${size} KB)`);
    } else {
      console.warn(`  警告: 未找到 ${src}`);
    }
  }

  // 2. Generate iconfont.css
  const namedIcons = icons.filter((g) => g.name && g.unicode);
  const css = buildCss(namedIcons);
  const cssPath = path.join(PACKAGE_DIR, 'iconfont.css');
  fs.writeFileSync(cssPath, css, 'utf8');
  console.log(`  生成: iconfont.css (${namedIcons.length} icons, ${(namedIcons.reduce((s, g) => s + (g.aliases?.length || 0), 0))} aliases)`);

  // 3. Generate iconfont.json
  const manifest = buildManifest(namedIcons);
  const jsonPath = path.join(PACKAGE_DIR, 'iconfont.json');
  fs.writeFileSync(jsonPath, JSON.stringify(manifest, null, 2), 'utf8');
  console.log(`  生成: iconfont.json (${manifest.length} entries)`);

  // 4. Generate demo_index.html
  const html = buildDemoHtml(icons);
  const htmlPath = path.join(PACKAGE_DIR, 'demo_index.html');
  fs.writeFileSync(htmlPath, html, 'utf8');
  console.log(`  生成: demo_index.html`);

  // Summary
  console.log('\n整合包已生成:');
  console.log(`  ${PACKAGE_DIR}`);
  console.log('\n包含文件:');
  for (const f of fs.readdirSync(PACKAGE_DIR)) {
    const size = Math.round(fs.statSync(path.join(PACKAGE_DIR, f)).size / 1024);
    console.log(`  - package/${f} (${size} KB)`);
  }
  console.log('\n使用方式:');
  console.log('  1. 将 output/package/ 目录上传到 CDN');
  console.log('  2. 在项目中引入 iconfont.css');
  console.log('  3. 使用 <span class="iconfont icon-xxx"></span>');
  console.log('\nPhase 12 完成。');
}

main();
