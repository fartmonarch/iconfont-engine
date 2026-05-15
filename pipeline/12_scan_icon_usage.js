#!/usr/bin/env node
/**
 * Phase 12: Scan Icon Usage in Source Repositories
 *
 * Scans all cloned repositories for icon class usage and CSS link references.
 *
 * Usage:
 *     node pipeline/12_scan_icon_usage.js
 *
 * Input:
 *     sources/meta/css_mappings.json  — icon name mappings per asset
 *     sources/meta/assets_manifest.json — asset → project mapping
 *
 * Output:
 *     report/icon_usage_index.json
 */
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.dirname(__dirname);
const CODESTORE_DIR = 'D:\\work\\codestore';
const ASSETS_MANIFEST_PATH = path.join(DATA_DIR, 'sources', 'meta', 'assets_manifest.json');
const CSS_MAPPINGS_PATH = path.join(DATA_DIR, 'sources', 'meta', 'css_mappings.json');
const OUTPUT_PATH = path.join(DATA_DIR, 'report', 'icon_usage_index.json');

const SCAN_EXTENSIONS = new Set(['.vue', '.html', '.htm', '.js', '.jsx', '.ts', '.tsx']);
const ICON_CLASS_RE = /(?:class|:class)\s*=\s*["'`]([^"'`]*\bicon-[\w-]+\b[^"'`]*)["'`]/g;
const ICON_CLASS_EXTRACT_RE = /\bicon-[\w-]+\b/g;
const CSS_LINK_RE = /<link[^>]*rel=["']stylesheet["'][^>]*href=["']([^"']*iconfont[^"']*)["'][^>]*>/gi;
const CSS_IMPORT_RE = /@import\s+["']([^"']*iconfont[^"']*)["']/gi;
const DYNAMIC_ICON_RE = /[`'"](?:[^`'"]*icon-[^`'"]*)[`'"]|\$\{[^}]*icon-[^}]*\}/g;

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

function* walkDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '.git' || entry.name === 'dist' || entry.name === 'build') continue;
      yield* walkDir(fullPath);
    } else if (entry.isFile() && SCAN_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      yield fullPath;
    }
  }
}

function scanFile(filePath, projectName, iconNames) {
  const usages = [];
  const cssLinks = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const relPath = path.relative(path.join(CODESTORE_DIR, projectName), filePath).replace(/\\/g, '/');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    // CSS link references
    let m;
    const cssLinkRe = new RegExp(CSS_LINK_RE.source, 'gi');
    while ((m = cssLinkRe.exec(line)) !== null) {
      cssLinks.push({
        file: relPath,
        line: lineNum,
        rawHtml: line.trim(),
        resolvedUrl: m[1],
      });
    }

    const cssImportRe = new RegExp(CSS_IMPORT_RE.source, 'gi');
    while ((m = cssImportRe.exec(line)) !== null) {
      cssLinks.push({
        file: relPath,
        line: lineNum,
        rawHtml: line.trim(),
        resolvedUrl: m[1],
      });
    }

    // Icon class usage
    const iconClassRe = new RegExp(ICON_CLASS_RE.source, 'g');
    while ((m = iconClassRe.exec(line)) !== null) {
      const classValue = m[1];
      const foundIcons = classValue.match(ICON_CLASS_EXTRACT_RE) || [];
      for (const iconName of foundIcons) {
        usages.push({
          file: relPath,
          line: lineNum,
          column: line.indexOf(iconName) + 1,
          context: line.trim(),
          iconName,
          usageType: 'static_class',
          canAutoReplace: true,
        });
      }
    }

    // Dynamic icon usage (template strings, variables)
    const dynamicRe = new RegExp(DYNAMIC_ICON_RE.source, 'g');
    while ((m = dynamicRe.exec(line)) !== null) {
      const matchStr = m[0];
      const foundIcons = matchStr.match(ICON_CLASS_EXTRACT_RE) || [];
      for (const iconName of foundIcons) {
        usages.push({
          file: relPath,
          line: lineNum,
          column: line.indexOf(iconName) + 1,
          context: line.trim(),
          iconName,
          usageType: 'dynamic_class',
          canAutoReplace: false,
        });
      }
    }
  }

  return { usages, cssLinks };
}

function main() {
  console.log('='.repeat(51));
  console.log('Phase 12: Scan Icon Usage in Source Repositories');
  console.log('='.repeat(51));
  console.log();

  // Load mappings
  console.log('Loading assets manifest and CSS mappings...');
  const assetsManifest = loadJson(ASSETS_MANIFEST_PATH);
  const cssMappings = loadJson(CSS_MAPPINGS_PATH);

  // Build icon name set from all mappings
  const allIconNames = new Set();
  for (const asset of cssMappings) {
    for (const mapping of asset.mappings || []) {
      if (mapping.name) allIconNames.add(mapping.name);
    }
  }
  console.log(`  Known icon names: ${allIconNames.size}`);
  console.log();

  // Build asset → project mapping
  const assetProjects = {};
  for (const asset of assetsManifest) {
    assetProjects[asset.assetId] = asset.sourceProjects || [];
  }

  // Scan each project
  const projects = fs.readdirSync(CODESTORE_DIR, { withFileTypes: true })
    .filter(e => e.isDirectory())
    .map(e => e.name);

  console.log(`Scanning ${projects.length} projects in ${CODESTORE_DIR}...`);
  console.log();

  const result = {
    generatedAt: new Date().toISOString(),
    totalFiles: 0,
    totalUsages: 0,
    projects: {},
  };

  for (const projectName of projects) {
    const projectDir = path.join(CODESTORE_DIR, projectName);
    if (!fs.existsSync(projectDir)) continue;

    let projectUsages = [];
    let projectCssLinks = [];
    let fileCount = 0;

    try {
      for (const filePath of walkDir(projectDir)) {
        fileCount++;
        const scan = scanFile(filePath, projectName, allIconNames);
        projectUsages.push(...scan.usages);
        projectCssLinks.push(...scan.cssLinks);
      }
    } catch (err) {
      console.log(`  [WARN] ${projectName}: ${err.message}`);
    }

    if (projectUsages.length > 0 || projectCssLinks.length > 0) {
      // Group usages by iconName
      const iconUsagesMap = {};
      for (const u of projectUsages) {
        if (!iconUsagesMap[u.iconName]) iconUsagesMap[u.iconName] = [];
        iconUsagesMap[u.iconName].push(u);
      }

      result.projects[projectName] = {
        cssLinks: projectCssLinks,
        iconUsages: Object.entries(iconUsagesMap).map(([iconName, usages]) => ({
          iconName,
          usages,
        })),
      };

      result.totalFiles += fileCount;
      result.totalUsages += projectUsages.length;
      console.log(`  ${projectName}: ${fileCount} files, ${projectUsages.length} usages, ${projectCssLinks.length} css links`);
    } else {
      console.log(`  ${projectName}: ${fileCount} files, no icon usage found`);
    }
  }

  console.log();
  console.log(`Total: ${result.totalFiles} files, ${result.totalUsages} icon usages`);
  console.log(`Writing output: ${OUTPUT_PATH}`);

  fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(result, null, 2), 'utf-8');

  console.log('Phase 12 complete!');
}

main();
