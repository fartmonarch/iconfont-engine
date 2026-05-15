#!/usr/bin/env node
/**
 * Phase 11: Output & Manifest — 发布层
 *
 * Generates the final npm-package-ready output:
 *   - output/iconfont_merged.css   (already from Phase 8-9, verified)
 *   - output/iconfont_merged.json  (already from Phase 8-9, verified)
 *   - output/merge_manifest.json   (comprehensive manifest with full溯源 chain)
 *   - output/demo_index.html       (self-contained demo page)
 *
 * Usage:
 *     node pipeline/11_generate_manifest.js
 *
 * Input:
 *     report/phase7_resolution.json
 *     report/phase89_build.json
 *     output/iconfont_merged.json
 *     output/iconfont_merged.css
 *     sources/meta/assets_manifest.json
 *
 * Output:
 *     output/merge_manifest.json
 *     output/demo_index.html
 *     report/phase11_output.md
 */
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.dirname(__dirname);
const OUTPUT_DIR = path.join(DATA_DIR, 'output');
const REPORT_DIR = path.join(DATA_DIR, 'report');
const SOURCES_META = path.join(DATA_DIR, 'sources', 'meta', 'assets_manifest.json');

const FONT_FAMILY = 'iconfont-merged';
const OUTPUT_PREFIX = 'iconfont_merged';
const CSS_ICON_PREFIX = 'icon-';


/**
 * Build the comprehensive merge_manifest.json with full traceability.
 */
function buildMergeManifest(outputJson, phase7, phase89, assetsManifest) {
  // Build assetId -> manifest entry map
  const assetMap = {};
  for (const entry of Object.values(assetsManifest)) {
    assetMap[entry.assetId] = entry;
  }

  const manifest = outputJson.map((g) => {
    const sources = (g.sources || []).map((s) => {
      const assetEntry = assetMap[s.assetId];
      return {
        assetId: s.assetId,
        projects: s.projects || [],
        originalUnicode: s.originalUnicode,
        cssUrl: assetEntry?.cssUrl || '',
        ttfPath: assetEntry?.ttfPath || '',
      };
    });

    return {
      glyphHash: g.glyphHash,
      finalUnicode: g.unicode,
      finalName: g.name,
      aliases: g.aliases || [],
      sources,
      affectedProjects: g.affectedProjects || [],
      resolution: g.resolution || '',
    };
  });

  return {
    version: '1.0.0',
    generatedAt: new Date().toISOString(),
    fontFamily: FONT_FAMILY,
    outputPrefix: OUTPUT_PREFIX,
    buildInfo: phase89 || {},
    totalGlyphs: manifest.length,
    totalAliases: manifest.reduce((sum, g) => sum + (g.aliases?.length || 0), 0),
    totalSources: new Set(manifest.flatMap((g) => g.sources.map((s) => s.assetId))).size,
    glyphs: manifest,
  };
}


/**
 * Generate a self-contained demo_index.html page.
 * Uses CSS class-based rendering (no unicode entities needed).
 */
function generateDemoHtml(outputJson) {
  const icons = outputJson
    .filter((g) => g.name && g.unicode)
    .sort((a, b) => a.name.localeCompare(b.name));

  const cssRules = icons
    .map((g) => `.${CSS_ICON_PREFIX}${g.name}:before { content: "\\${g.unicode}"; }`)
    .join('\n');

  // E000-E5FF = newly allocated by pipeline (conflict PUA)
  // E600-EAFF = original source icons (naturally in PUA range)
  const isPuaConflict = (unicode) => { const u = parseInt(unicode, 16); return u >= 0xE000 && u < 0xE600; };

  const iconItems = icons
    .map((g) => {
      const isPua = isPuaConflict(g.unicode);
      const badge = isPua ? '<span class="badge-pua">PUA</span>' : '';
      const liClass = isPua ? 'dib dib-pua' : 'dib';
      const decimal = parseInt(g.unicode, 16);
      return `      <li class="${liClass}">
        <span class="iconfont ${CSS_ICON_PREFIX}${g.name}" style="font-size:36px;color:#333;display:block;margin-bottom:8px"></span>
        <div class="name">${g.name} ${badge}</div>
        <div class="code-name">&amp;#${decimal};</div>
      </li>`;
    })
    .join('\n');

  // Stats
  const puaCount = icons.filter((g) => isPuaConflict(g.unicode)).length;
  const aliasCount = icons.reduce((sum, g) => sum + (g.aliases?.length || 0), 0);
  const projectSet = new Set(icons.flatMap((g) => g.affectedProjects || []));

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>iconfont-merged — ${icons.length} icons</title>
<style>
*{margin:0;padding:0;list-style:none}
body{background:#f5f5f5;color:#333;font-family:"Helvetica Neue",Helvetica,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",Arial,sans-serif}

@font-face{font-family:"iconfont";src:url("${OUTPUT_PREFIX}.woff2") format("woff2"),url("${OUTPUT_PREFIX}.ttf") format("truetype")}
.iconfont{font-family:"iconfont" !important;font-size:16px;font-style:normal;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}

${cssRules}

.main{max-width:1400px;margin:0 auto;padding:20px}
.header{margin-bottom:24px;padding:24px;background:linear-gradient(135deg,#3967FF,#B500FE);border-radius:12px;color:#fff}
.header h1{font-size:24px;margin-bottom:8px}
.header p{font-size:14px;opacity:0.9}

.stats{display:flex;gap:24px;flex-wrap:wrap;margin-top:16px}
.stats .item{background:rgba(255,255,255,0.15);padding:12px 20px;border-radius:8px;text-align:center;min-width:100px}
.stats .item .num{font-size:24px;font-weight:bold}
.stats .item .label{font-size:11px;opacity:0.8;margin-top:2px}

.nav-tabs{background:#fff;border-radius:8px;padding:0 16px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 1px 3px rgba(0,0,0,0.06)}
.nav-tabs ul{display:flex}
.nav-tabs li{padding:14px 20px;cursor:pointer;font-size:14px;color:#666;border-bottom:2px solid transparent;transition:all 0.2s}
.nav-tabs li.active{color:#333;border-bottom-color:#3967FF}
.nav-tabs li:hover{color:#3967FF}

.search-box{padding:10px 16px;border:1px solid #e0e0e0;border-radius:6px;font-size:14px;width:240px;outline:none;transition:border-color 0.2s}
.search-box:focus{border-color:#3967FF}

.dib-box{display:flex;flex-wrap:wrap;gap:12px}
.icon-list .dib{width:calc(12.5% - 9px);min-width:140px;margin-bottom:12px;padding:16px 12px;background:#fff;border:1px solid #eee;border-radius:8px;text-align:center;transition:all 0.2s}
.icon-list .dib:hover{box-shadow:0 4px 12px rgba(0,0,0,0.1);transform:translateY(-2px)}
.icon-list .dib .name{font-size:11px;color:#666;margin-bottom:4px;word-break:break-all;line-height:1.3;max-height:2.6em;overflow:hidden}
.icon-list .dib .code-name{font-size:10px;color:#999;font-family:monospace}

.dib-pua{border-color:#ff9800 !important;background:#fffde7}
.badge-pua{display:inline-block;background:#ff9800;color:#fff;font-size:9px;padding:1px 4px;border-radius:3px;margin-left:3px;vertical-align:middle}

.tab-font{display:none}

.footer{margin-top:40px;padding:20px;text-align:center;color:#999;font-size:12px}
</style>
</head>
<body>
<div class="main">
  <div class="header">
    <h1>iconfont-merged — 合并字体预览</h1>
    <p>从 60+ 前端项目中扫描、提取、合并的统一 iconfont 字体</p>
    <div class="stats">
      <div class="item"><div class="num">${icons.length}</div><div class="label">图标总数</div></div>
      <div class="item"><div class="num">${puaCount}</div><div class="label">PUA 分配</div></div>
      <div class="item"><div class="num">${aliasCount}</div><div class="label">别名数</div></div>
      <div class="item"><div class="num">${projectSet.size}</div><div class="label">来源项目</div></div>
    </div>
  </div>

  <div class="nav-tabs">
    <ul>
      <li class="active" onclick="switchTab(0)"><span>Font class</span></li>
      <li onclick="switchTab(1)"><span>Unicode</span></li>
    </ul>
    <input type="text" class="search-box" placeholder="搜索图标..." oninput="filterIcons(this.value)">
  </div>

  <!-- Font class Tab -->
  <div class="tab-font" id="tab-font">
    <ul class="icon-list dib-box" id="icon-grid">
${iconItems}
    </ul>
  </div>

  <!-- Unicode Tab -->
  <div class="tab-unicode" id="tab-unicode" style="display:none">
    <ul class="icon-list dib-box">
${icons.map((g) => {
    const isPua = isPuaConflict(g.unicode);
    const badge = isPua ? '<span class="badge-pua">PUA</span>' : '';
    const liClass = isPua ? 'dib dib-pua' : 'dib';
    const decimal = parseInt(g.unicode, 16);
    return `      <li class="${liClass}" data-name="${g.name}">
        <span class="iconfont" style="font-size:36px;color:#333;display:block;margin-bottom:8px" data-code="${g.unicode}"></span>
        <div class="name">${g.name} ${badge}</div>
        <div class="code-name">U+${g.unicode} (&amp;#${decimal};)</div>
      </li>`;
  }).join('\n')}
    </ul>
  </div>

  <div class="footer">
    Generated by iconfont-engine pipeline | ${new Date().toISOString().split('T')[0]}
  </div>
</div>

<script>
function switchTab(idx) {
  var tabs = document.querySelectorAll('.nav-tabs li');
  tabs.forEach(function(t) { t.classList.remove('active'); });
  tabs[idx].classList.add('active');
  document.getElementById('tab-font').style.display = idx === 0 ? 'block' : 'none';
  document.getElementById('tab-unicode').style.display = idx === 1 ? 'block' : 'none';
}

// Convert unicode escape to actual character
window.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('[data-code]').forEach(function(el) {
    var code = el.getAttribute('data-code');
    try {
      var charCode = parseInt(code, 16);
      el.textContent = String.fromCharCode(charCode);
    } catch(e) {
      el.textContent = code;
    }
  });
});

// Search / filter
function filterIcons(query) {
  var q = query.toLowerCase().trim();
  var items = document.querySelectorAll('#icon-grid li');
  items.forEach(function(item) {
    var name = item.getAttribute('data-name') || '';
    var code = item.querySelector('.code-name')?.textContent || '';
    if (!q || name.toLowerCase().includes(q) || code.toLowerCase().includes(q)) {
      item.style.display = '';
    } else {
      item.style.display = 'none';
    }
  });
}
</script>
</body>
</html>`;
}


/**
 * Generate the Phase 11 output report.
 */
function generateReport(mergeManifest, demoHtml) {
  const md = [
    '# Phase 11: Output & Manifest 报告',
    '',
    `生成时间: ${new Date().toISOString()}`,
    '',
    '## 输出文件',
    '',
    '| 文件 | 说明 |',
    '|------|------|',
    `| output/${OUTPUT_PREFIX}.ttf | 合并后的 TTF 字体 |`,
    `| output/${OUTPUT_PREFIX}.woff2 | 合并后的 WOFF2 字体 |`,
    `| output/${OUTPUT_PREFIX}.css | CSS @font-face + icon class 规则 |`,
    `| output/${OUTPUT_PREFIX}.json | Glyph 元数据 JSON |`,
    `| output/merge_manifest.json | 完整溯源链 manifest |`,
    `| output/demo_index.html | 可视化预览页面 |`,
    '',
    '## 统计',
    '',
    `| 指标 | 值 |`,
    `|------|-----|`,
    `| 总 Glyph 数 | ${mergeManifest.totalGlyphs} |`,
    `| 别名总数 | ${mergeManifest.totalAliases} |`,
    `| 来源字体数 | ${mergeManifest.totalSources} |`,
    `| 字体族 | ${mergeManifest.fontFamily} |`,
    '',
    '## 使用方式',
    '',
    '```html',
    `<!-- 引入 CSS -->`,
    `<link rel="stylesheet" href="iconfont_merged.css">`,
    '',
    `<!-- 使用图标 -->`,
    `<span class="${CSS_ICON_PREFIX}home"></span>`,
    '```',
    '',
    '## NPM Package 结构',
    '',
    '```',
    'iconfont-merged/',
    `├── ${OUTPUT_PREFIX}.ttf`,
    `├── ${OUTPUT_PREFIX}.woff2`,
    `├── ${OUTPUT_PREFIX}.css`,
    `├── ${OUTPUT_PREFIX}.json`,
    '├── merge_manifest.json',
    '└── demo_index.html',
    '```',
    '',
  ];
  return md.join('\n');
}


function main() {
  console.log('='.repeat(60));
  console.log('Phase 11: Output & Manifest');
  console.log('='.repeat(60));

  // Verify inputs
  const outputJsonPath = path.join(OUTPUT_DIR, `${OUTPUT_PREFIX}.json`);
  if (!fs.existsSync(outputJsonPath)) {
    console.error(`\nError: ${outputJsonPath} not found. Run Phase 8-9 first.`);
    return 1;
  }

  const outputJson = JSON.parse(fs.readFileSync(outputJsonPath, 'utf8'));
  console.log(`\nLoaded output JSON: ${outputJson.length} entries`);

  // Load Phase 7 resolution
  const phase7Path = path.join(REPORT_DIR, 'phase7_resolution.json');
  let phase7 = {};
  if (fs.existsSync(phase7Path)) {
    phase7 = JSON.parse(fs.readFileSync(phase7Path, 'utf8'));
    console.log(`Loaded Phase 7 resolution`);
  }

  // Load Phase 8-9 build info
  const phase89Path = path.join(REPORT_DIR, 'phase89_build.json');
  let phase89 = {};
  if (fs.existsSync(phase89Path)) {
    phase89 = JSON.parse(fs.readFileSync(phase89Path, 'utf8'));
    console.log(`Loaded Phase 8-9 build info`);
  }

  // Load assets manifest for溯源
  let assetsManifest = {};
  if (fs.existsSync(SOURCES_META)) {
    assetsManifest = JSON.parse(fs.readFileSync(SOURCES_META, 'utf8'));
    console.log(`Loaded assets manifest: ${Object.keys(assetsManifest).length} entries`);
  }

  // Build merge_manifest.json
  console.log('\nBuilding merge_manifest.json...');
  const mergeManifest = buildMergeManifest(outputJson, phase7, phase89, assetsManifest);
  const manifestPath = path.join(OUTPUT_DIR, 'merge_manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(mergeManifest, null, 2));
  console.log(`  Written: ${manifestPath}`);

  // Generate demo HTML
  console.log('Generating demo_index.html...');
  const demoHtml = generateDemoHtml(outputJson);
  const demoHtmlPath = path.join(OUTPUT_DIR, 'demo_index.html');
  fs.writeFileSync(demoHtmlPath, demoHtml, 'utf8');
  console.log(`  Written: ${demoHtmlPath}`);

  // Generate report
  console.log('Generating report...');
  const reportMd = generateReport(mergeManifest, demoHtml);
  const reportPath = path.join(REPORT_DIR, 'phase11_output.md');
  fs.mkdirSync(REPORT_DIR, { recursive: true });
  fs.writeFileSync(reportPath, reportMd, 'utf8');
  console.log(`  Written: ${reportPath}`);

  console.log('\nPhase 11 完成。');
  console.log('\n输出文件汇总:');
  console.log(`  - output/${OUTPUT_PREFIX}.ttf`);
  console.log(`  - output/${OUTPUT_PREFIX}.woff2`);
  console.log(`  - output/${OUTPUT_PREFIX}.css`);
  console.log(`  - output/${OUTPUT_PREFIX}.json`);
  console.log(`  - output/merge_manifest.json`);
  console.log(`  - output/demo_index.html`);
  console.log(`  - report/phase11_output.md`);

  return 0;
}

main();
