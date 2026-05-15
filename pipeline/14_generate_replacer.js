#!/usr/bin/env node
/**
 * Task 5: Generate Automated Replacement Scripts + Guides
 *
 * Reads lineage_resolved.json, generates per-project replacement scripts
 * and human-readable replacement guides.
 *
 * Usage:
 *     node pipeline/14_generate_replacer.js
 *
 * Output:
 *     output/replacers/<project>_replace.js
 *     report/replacement_guides/<project>.md
 */
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.dirname(__dirname);
const LINEAGE_PATH = path.join(DATA_DIR, 'registry', 'lineage_resolved.json');
const ASSETS_MANIFEST_PATH = path.join(DATA_DIR, 'sources', 'meta', 'assets_manifest.json');
const REPLACER_DIR = path.join(DATA_DIR, 'output', 'replacers');
const GUIDE_DIR = path.join(DATA_DIR, 'report', 'replacement_guides');

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

function main() {
  console.log('='.repeat(51));
  console.log('Task 5: Generate Replacement Scripts + Guides');
  console.log('='.repeat(51));
  console.log();

  const lineage = loadJson(LINEAGE_PATH);
  const assetsManifest = loadJson(ASSETS_MANIFEST_PATH);

  // Build assetId -> cssUrl mapping
  const assetCssMap = {};
  for (const asset of assetsManifest) {
    assetCssMap[asset.assetId] = asset.cssUrl;
  }

  // Group replacements by project
  const projectReplacements = {};

  for (const entry of lineage.entries || []) {
    const replacement = entry.replacement;
    if (!replacement) continue;
    if (!replacement.nameChanged && !replacement.unicodeChanged) continue;

    const usages = entry.usages || {};
    for (const [project, projUsages] of Object.entries(usages)) {
      if (!projectReplacements[project]) {
        projectReplacements[project] = {
          cssLinks: [],
          iconReplacements: [],
        };
      }

      // CSS link replacements
      for (const link of projUsages.cssLinkFiles || []) {
        if (link.canAutoReplace !== false) {
          const existing = projectReplacements[project].cssLinks.find(
            l => l.file === link.file && l.line === link.line
          );
          if (!existing) {
            projectReplacements[project].cssLinks.push({
              file: link.file,
              line: link.line,
              from: link.resolvedUrl || link.rawHtml,
              to: 'iconfont_merged.css',
              type: 'css_link',
            });
          }
        }
      }

      // Icon name replacements
      for (const usage of projUsages.iconUsageFiles || []) {
        if (usage.canAutoReplace) {
          const oldName = usage.iconName;
          const newName = replacement.newName;
          if (oldName && newName && oldName !== newName) {
            projectReplacements[project].iconReplacements.push({
              file: usage.file,
              line: usage.line,
              from: oldName,
              to: newName,
              type: 'icon_class',
            });
          }
        }
      }
    }
  }

  fs.mkdirSync(REPLACER_DIR, { recursive: true });
  fs.mkdirSync(GUIDE_DIR, { recursive: true });

  console.log(`Generating replacements for ${Object.keys(projectReplacements).length} projects...`);
  console.log();

  for (const [project, data] of Object.entries(projectReplacements)) {
    const autoCount = data.iconReplacements.length;
    const cssCount = data.cssLinks.length;

    // Generate JS replacer script
    const replacerContent = `// ${project} 自动替换脚本（生成后需人工审查再执行）
const fs = require('fs');
const path = require('path');

const replacements = [
  // CSS 链接替换
${data.cssLinks.map(l => `  { file: "${l.file}", line: ${l.line}, from: "${l.from}", to: "${l.to}", type: "${l.type}" },`).join('\n')}
  // 图标类名替换
${data.iconReplacements.map(r => `  { file: "${r.file}", line: ${r.line}, from: "${r.from}", to: "${r.to}", type: "${r.type}" },`).join('\n')}
];

function applyReplacements(projectDir) {
  for (const r of replacements) {
    const filePath = path.join(projectDir, r.file);
    if (!fs.existsSync(filePath)) continue;
    let content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\\n');
    if (r.line > 0 && r.line <= lines.length) {
      const oldLine = lines[r.line - 1];
      if (r.type === 'css_link') {
        lines[r.line - 1] = oldLine.replace(r.from, r.to);
      } else if (r.type === 'icon_class') {
        const re = new RegExp('\\\\b' + r.from.replace(/-/g, '\\\\-') + '\\\\b', 'g');
        lines[r.line - 1] = oldLine.replace(re, r.to);
      }
      fs.writeFileSync(filePath, lines.join('\\n'), 'utf-8');
      console.log('Replaced:', r.file, 'line', r.line);
    }
  }
}

if (require.main === module) {
  const dir = process.argv[2] || '.';
  applyReplacements(dir);
}

module.exports = { applyReplacements };
`;

    fs.writeFileSync(path.join(REPLACER_DIR, `${project}_replace.js`), replacerContent, 'utf-8');

    // Generate MD guide
    const guideContent = `# ${project} 图标替换指南

## 摘要
- 可自动替换：${autoCount} 处
- CSS 链接替换：${cssCount} 处

## CSS 链接替换

| 文件 | 行号 | 旧链接 | 新链接 |
|------|------|--------|--------|
${data.cssLinks.map(l => `| ${l.file} | ${l.line} | ... | ${l.to} |`).join('\n')}

## 图标名变更清单

| 旧名称 | 新名称 | 文件 | 行号 |
|--------|--------|------|------|
${data.iconReplacements.slice(0, 50).map(r => `| ${r.from} | ${r.to} | ${r.file} | ${r.line} |`).join('\n')}
${data.iconReplacements.length > 50 ? `\n... 共 ${data.iconReplacements.length} 处` : ''}
`;

    fs.writeFileSync(path.join(GUIDE_DIR, `${project}.md`), guideContent, 'utf-8');

    console.log(`  ${project}: ${autoCount} icon replacements, ${cssCount} css links`);
  }

  console.log();
  console.log('Task 5 complete!');
}

main();
