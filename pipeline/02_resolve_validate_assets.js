#!/usr/bin/env node
/**
 * 02_resolve_validate_assets.js — Phase 2 Script 03（质量门）
 *
 * 职责：校验 CSS+TTF 配对完整性，标记异常
 *
 * 输入：
 *   sources/meta/assets_manifest.json  （脚本 01 产出）
 *   sources/meta/css_mappings.json     （脚本 02 产出）
 *
 * 输出：
 *   sources/meta/assets_validation.json
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const MANIFEST_FILE = path.join(ROOT, 'sources/meta/assets_manifest.json');
const MAPPINGS_FILE = path.join(ROOT, 'sources/meta/css_mappings.json');
const OUTPUT_FILE = path.join(ROOT, 'sources/meta/assets_validation.json');

// ========== 校验规则 ==========

/**
 * 校验 TTF 是否为有效 TrueType 字体
 * TrueType 文件以 0x00010000 (version 1.0) 或 'true' (v1.1+) 开头
 * 或通过 size 粗略判断
 */
function validateTTF(filePath) {
  try {
    const stat = fs.statSync(filePath);
    if (stat.size < 1024) {
      return { valid: false, reason: 'file_too_small', size: stat.size };
    }
    const buf = Buffer.alloc(4);
    const fd = fs.openSync(filePath, 'r');
    fs.readSync(fd, buf, 0, 4, 0);
    fs.closeSync(fd);

    // TrueType version: 0x00010000
    if (buf[0] === 0x00 && buf[1] === 0x01 && buf[2] === 0x00 && buf[3] === 0x00) {
      return { valid: true, size: stat.size };
    }
    // 'true' (0x74727565)
    if (buf.toString('ascii') === 'true') {
      return { valid: true, size: stat.size };
    }
    // 'OTTO' (OpenType/CFF)
    if (buf.toString('ascii') === 'OTTO') {
      return { valid: true, size: stat.size, note: 'OpenType/CFF' };
    }
    // wOFF (尝试过可能是 woff 文件)
    if (buf.toString('ascii') === 'wOF2' || buf.toString('ascii') === 'wOFF') {
      return { valid: false, reason: 'wrong_format_is_woff', size: stat.size };
    }

    return { valid: false, reason: 'invalid_ttf_header', size: stat.size, header: buf.toString('hex') };
  } catch (err) {
    return { valid: false, reason: 'read_error', error: err.message };
  }
}

// ========== 主流程 ==========

function main() {
  console.log('=== Phase 2: Asset Resolver (Script 03: Validate Assets) ===');
  console.log('');

  // Step 1: 读取输入
  console.log('[1/4] 读取输入文件...');
  const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
  const mappings = JSON.parse(fs.readFileSync(MAPPINGS_FILE, 'utf-8'));

  // 建立 mapping lookup
  const mappingMap = {};
  for (const m of mappings) {
    mappingMap[m.assetId] = m;
  }
  console.log(`  manifest: ${manifest.length} assets`);
  console.log(`  mappings: ${mappings.length} entries`);
  console.log('');

  // Step 2: 逐个校验
  console.log('[2/4] 校验每个 asset...');
  const details = [];
  const statusSummary = {
    ok: 0,
    css_404: 0,
    ttf_missing: 0,
    empty_mappings: 0,
    ttf_corrupt: 0
  };

  for (const a of manifest) {
    const detail = {
      assetId: a.assetId,
      cssUrl: a.cssUrl,
      sourceProjects: a.sourceProjects,
      downloadStatus: a.downloadStatus,
      cssExists: false,
      cssSize: 0,
      ttfExists: false,
      ttfSize: 0,
      ttfValid: null,
      mappingsCount: 0,
      status: 'ok',
      issues: []
    };

    // 检查 CSS 文件
    if (a.cssPath) {
      const cssPath = path.join(ROOT, a.cssPath);
      try {
        const stat = fs.statSync(cssPath);
        detail.cssExists = true;
        detail.cssSize = stat.size;
      } catch (e) {
        detail.issues.push('css_file_missing');
      }
    } else {
      detail.issues.push('css_path_missing');
    }

    // 检查 TTF 文件
    if (a.ttfPath) {
      const ttfPath = path.join(ROOT, a.ttfPath);
      try {
        const stat = fs.statSync(ttfPath);
        detail.ttfExists = true;
        detail.ttfSize = stat.size;
        const ttfResult = validateTTF(ttfPath);
        detail.ttfValid = ttfResult.valid;
        if (!ttfResult.valid) {
          detail.issues.push('ttf_corrupt: ' + ttfResult.reason);
          statusSummary.ttf_corrupt++;
          detail.status = 'ttf_corrupt';
        }
      } catch (e) {
        detail.issues.push('ttf_file_missing');
        if (!detail.ttfExists) {
          detail.issues.push('ttf_not_downloaded');
        }
      }
    }

    // 检查 mappings（css_404 的 asset 不检查，因为必然为空）
    if (a.downloadStatus !== 'css_404') {
      const mappingEntry = mappingMap[a.assetId];
      if (mappingEntry && mappingEntry.mappings && mappingEntry.mappings.length > 0) {
        detail.mappingsCount = mappingEntry.mappings.length;
      } else {
        detail.issues.push('empty_mappings');
        statusSummary.empty_mappings++;
      }
    }

    // 确定最终状态
    if (detail.status === 'ok') {
      if (a.downloadStatus === 'css_404') {
        detail.status = 'css_404';
        statusSummary.css_404++;
      } else if (detail.issues.some(i => i.startsWith('ttf_'))) {
        detail.status = 'ttf_missing';
        statusSummary.ttf_missing++;
      } else if (detail.issues.includes('empty_mappings')) {
        detail.status = 'empty_mappings';
      } else {
        statusSummary.ok++;
      }
    }

    // 清理空 issues
    if (detail.issues.length === 0) delete detail.issues;

    details.push(detail);
  }

  console.log('  校验完成');
  console.log('');

  // Step 3: 输出
  console.log('[3/4] 输出 assets_validation.json...');
  const output = {
    timestamp: new Date().toISOString(),
    totalAssets: manifest.length,
    statusSummary,
    details
  };
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2), 'utf-8');
  console.log(`  已写入 ${OUTPUT_FILE}`);
  console.log('');

  // Step 4: 汇总报告
  console.log('[4/4] 汇总报告');
  console.log('');
  console.log('=== 校验结果 ===');
  console.log(`  总资产数: ${output.totalAssets}`);
  console.log('  状态分布:');
  for (const [status, count] of Object.entries(statusSummary)) {
    const mark = status === 'ok' ? '✅' : '⚠️';
    console.log(`    ${mark} ${status}: ${count}`);
  }

  // 打印非 ok 的 asset 详情
  const problemAssets = details.filter(d => d.status !== 'ok');
  if (problemAssets.length > 0) {
    console.log('');
    console.log('  异常资产明细:');
    for (const d of problemAssets) {
      console.log(`    ${d.assetId} [${d.status}] ${d.cssUrl.substring(0, 80)}`);
      if (d.issues) {
        console.log(`      问题: ${d.issues.join(', ')}`);
      }
    }
  }

  // 统计数据范围
  const validAssets = details.filter(d => d.status === 'ok');
  if (validAssets.length > 0) {
    const sizes = validAssets.map(d => d.mappingsCount);
    const totalIcons = validAssets.reduce((sum, d) => sum + d.mappingsCount, 0);
    const minSize = Math.min(...sizes);
    const maxSize = Math.max(...sizes);
    const avgSize = Math.round(totalIcons / validAssets.length);
    console.log('');
    console.log('  正常资产统计:');
    console.log(`    图标总数: ${totalIcons}`);
    console.log(`    单 asset 图标数范围: ${minSize} ~ ${maxSize} (平均 ${avgSize})`);
    console.log(`    TTF 文件大小范围: ${Math.round(validAssets.filter(d=>d.ttfExists).reduce((s,d)=>s+d.ttfSize,0)/1024)} KB 总计`);
  }
}

main();
