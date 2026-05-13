#!/usr/bin/env node
/**
 * 02_resolve_parse_css_mappings.js — Phase 2 Script 02（纯解析）
 *
 * 职责：从已下载的 CSS 中提取 name → unicode 映射
 *
 * 输入：
 *   sources/meta/assets_manifest.json
 *   sources/phase2_assets/<assetId>/iconfont.css
 *
 * 输出：
 *   sources/meta/css_mappings.json
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const MANIFEST_FILE = path.join(ROOT, 'sources/meta/assets_manifest.json');
const OUTPUT_FILE = path.join(ROOT, 'sources/meta/css_mappings.json');

// ========== 正则 ==========

// 匹配 content 值：content: "\e601"  content: '\e601'  content: \e601
// 注意：某些 CSS（如 symbol 格式）末尾无 ;，需允许 $ 结束
const CONTENT_RE = /content\s*:\s*["']?\\([0-9a-fA-F]+)["']?\s*(?:[;}]|$)/;

// 从单个 CSS 选择器字符串提取 icon name
// .icon-xxx:before  → icon-xxx
// .iconXxx:before   → iconXxx
// .s-xxx:before     → s-xxx
function selectorToName(sel) {
  const trimmed = sel.trim();
  // .icon-xxx:before
  let m = trimmed.match(/^\.icon-([a-zA-Z0-9_-]+)(?::\w+)?$/);
  if (m) return 'icon-' + m[1];
  // .iconXxx:before
  m = trimmed.match(/^\.icon([A-Z][a-zA-Z0-9_-]*)(?::\w+)?$/);
  if (m) return 'icon' + m[1];
  // .s-xxx:before
  m = trimmed.match(/^\.s-([a-zA-Z0-9_-]+)(?::\w+)?$/);
  if (m) return 's-' + m[1];
  return null;
}

/**
 * 从 CSS 文本提取 icon 映射
 * 处理：
 *   - 单 selector 单 block（标准格式）
 *   - 逗号分隔多 selector 单 block（老旧 symbol CSS）
 * 返回 [{ name, unicode, selector }]
 */
function extractIconMappings(css) {
  const results = [];
  // 逐块解析：找到 { } 块，提取 content，然后解析块前面的 selectors
  const blockRe = /([^{}]+?)\{([^}]*)\}/g;
  let match;
  while ((match = blockRe.exec(css)) !== null) {
    const selectorPart = match[1].trim();
    const bodyPart = match[2].trim();
    const contentMatch = bodyPart.match(CONTENT_RE);
    if (!contentMatch) continue;
    const unicode = contentMatch[1].toLowerCase();
    // selectorPart 可能是逗号分隔的多个 selector
    const selectors = selectorPart.split(',');
    for (const sel of selectors) {
      const name = selectorToName(sel);
      if (name) {
        results.push({ name, unicode, selector: `.${name}:before` });
      }
    }
  }
  return results;
}

// ========== 主流程 ==========

function main() {
  console.log('=== Phase 2: Asset Resolver (Script 02: Parse CSS Mappings) ===');
  console.log('');

  // Step 1: 读取 manifest
  console.log('[1/3] 读取 assets_manifest.json...');
  const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
  const validAssets = manifest.filter(a => a.downloadStatus !== 'css_404');
  console.log(`  可解析 asset: ${validAssets.length}（排除 ${manifest.length - validAssets.length} 个 CSS 404）`);
  console.log('');

  // Step 2: 逐个解析
  console.log('[2/3] 解析 CSS 映射...');
  const mappings = [];
  let totalIcons = 0;
  let noIcons = 0;

  for (const a of validAssets) {
    const cssPath = path.join(ROOT, a.cssPath);
    const result = {
      assetId: a.assetId,
      cssUrl: a.cssUrl,
      mappings: [],
      extractStatus: 'ok'
    };

    try {
      const css = fs.readFileSync(cssPath, 'utf-8');
      const iconList = extractIconMappings(css);
      result.mappings = iconList;
      totalIcons += iconList.length;
      if (iconList.length === 0) {
        result.extractStatus = 'no_icons';
        noIcons++;
      }
    } catch (err) {
      result.extractStatus = 'parse_error';
      result.error = err.message;
      noIcons++;
    }

    mappings.push(result);
  }

  console.log(`  解析完成: ${validAssets.length} assets, ${totalIcons} icons, ${noIcons} 无图标`);
  console.log('');

  // Step 3: 输出
  console.log('[3/3] 输出 css_mappings.json...');
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(mappings, null, 2), 'utf-8');
  console.log(`  已写入 ${OUTPUT_FILE}`);
  console.log('');

  // 汇总统计
  const statusSummary = {};
  for (const m of mappings) {
    statusSummary[m.extractStatus] = (statusSummary[m.extractStatus] || 0) + 1;
  }
  // 按图标数排序前 5
  const top5 = [...mappings].sort((a, b) => b.mappings.length - a.mappings.length).slice(0, 5);
  const bottom5 = mappings.filter(m => m.mappings.length === 0).slice(0, 5);

  console.log('=== 完成 ===');
  console.log(`  总图标数: ${totalIcons}`);
  console.log('  状态分布:');
  for (const [status, count] of Object.entries(statusSummary)) {
    console.log(`    ${status}: ${count}`);
  }
  if (top5.length > 0) {
    console.log('  图标最多的 asset:');
    for (const m of top5) {
      console.log(`    ${m.assetId}: ${m.mappings.length} icons`);
    }
  }
  if (bottom5.length > 0) {
    console.log('  无图标的 asset:');
    for (const m of bottom5) {
      console.log(`    ${m.assetId}: ${m.cssUrl.substring(0, 80)}...`);
    }
  }
}

main();
