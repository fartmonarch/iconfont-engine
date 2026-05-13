#!/usr/bin/env node
/**
 * 01_scan_repos_iconfont_scan_multi.js — Phase 1: 多项目 iconfont 链接扫描
 *
 * 输入：项目根目录 + 20 个手动链接
 * 输出：all_iconfont_links.json + iconfont_urls.txt + 每个项目单独 JSON
 *
 * 用法:
 *   node 01_scan_repos_iconfont_scan_multi.js D:/work/codestore
 */

const fs = require('fs');
const path = require('path');

// ==================== 手动提供的 20 个链接 ====================
const MANUAL_LINKS = [
  'https://res.winbaoxian.com/ali-iconfont/font_5165506_p8nm66u0fd.css',
  'https://res.winbaoxian.com/ali-iconfont/font_5147685_3yj1cl522ql.css',
  'https://res.winbaoxian.com/ali-iconfont/font_5139753_59xlfs1rv4t.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_7itacmrlk3.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_cj8pe527d8u.css',
  'https://res.winbaoxian.com/ali-iconfont/font_5083134_vfi4mapwxbh.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_jlenlrheaxn.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_99d69tcivr4.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_piwj8vscg7b.css',
  'https://res.winbaoxian.com/ali-iconfont/font_5083134_600xfof53ct.css',
  'https://res.winbaoxian.com/ali-iconfont/font_5083134_4f3egsm2o2c.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_19bv2uxkv45.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_8h17cvfvm7r.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_rzvsoddflce.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_oq3fahn36yo.css',
  'https://res.winbaoxian.com/ali-iconfont/font_4960269_cv46z0yckxg.css',
  'https://res.winbaoxian.com/ali-iconfont/font_4960269_9p2et13034r.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_oyu00uuny3j.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_7ip68eerepd.css',
  'https://res.winbaoxian.com/ali-iconfont/font_428664_fr92kem0hlr.css',
];

// ==================== 配置 ====================
const EXCLUDE_DIRS = new Set([
  'node_modules', '.git', '.svn', 'dist', 'out',
  '.next', '.nuxt', '.svelte-kit', '.cache', '.tmp',
  '.vscode', '.idea', 'tests', 'docs', 'mock'
]);

const SOURCE_EXTS = new Set([
  '.html', '.ejs', '.pug', '.hbs',
  '.css', '.scss', '.less', '.styl',
  '.js', '.ts', '.jsx', '.tsx', '.vue', '.svelte'
]);

const CONFIG_FILES = new Set([
  '.env', '.env.development', '.env.production', '.env.local',
  'vite.config.js', 'vite.config.ts',
  'vue.config.js', 'webpack.config.js', 'webpack.config.ts',
  'nuxt.config.js', 'nuxt.config.ts',
  'next.config.js', 'next.config.ts',
  'config/index.js'
]);

const ICONFONT_CDN_REGEX = /(?:https?:)?\/\/(?:at|i|gw)\.alicdn\.com\/t\/(?:c\/)?font_\d+_[a-zA-Z0-9]+\.(?:css|js)/g;
const ICONFONT_RES_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/(?:ali-)?iconfont\/font_\d+_[a-zA-Z0-9]+\.(?:css|eot|woff2?|ttf|svg)/g;
const ICONFONT_RES_SYMBOLS_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/iconfont\/\d+\/css\/symbols\.css/g;
const ICONFONT_STATIC_PATH_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/[\w./-]*iconfont[\w./-]*\.css/g;
const CSS_IMPORT_REGEX = /@import\s+(?:url\(\s*)?['"]?([^'")\s;]+iconfont[^'")\s;]*)['"]?\s*\)?\s*;/g;

// @font-face src 中的字体文件匹配（.ttf/.eot/.woff/.woff2）
const FONT_FILE_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/[\w./-]*font_\d+_[a-zA-Z0-9]+\.(?:eot|woff2?|ttf)/g;

// ==================== 工具函数 ====================

function normalizeUrl(url) {
  if (!url) return url;
  url = url.trim();
  if (url.startsWith('//')) url = 'https:' + url;
  if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'https://' + url;
  url = url.replace(/https:\/\/res\.wyins\.net\//g, 'https://res.winbaoxian.com/');
  url = url.replace(/([^:]\/)\/+/g, '$1');
  return url;
}

function extractPublicPath(projectDir) {
  const results = {};
  let pkgName = '';
  const pkgPath = path.join(projectDir, 'package.json');
  if (fs.existsSync(pkgPath)) {
    try { pkgName = JSON.parse(fs.readFileSync(pkgPath, 'utf8')).name || ''; } catch {}
  }

  const vueConfigPath = path.join(projectDir, 'vue.config.js');
  if (fs.existsSync(vueConfigPath)) {
    const content = fs.readFileSync(vueConfigPath, 'utf8');
    const publicPathMatch = content.match(/publicPath\s*:\s*['"`]([^'"`]+)['"`]/);
    if (publicPathMatch) {
      results.vuePublicPath = publicPathMatch[1];
    }
    if (!results.vuePublicPath) {
      const varRefMatch = content.match(/publicPath\s*:\s*([a-zA-Z_]\w*)/);
      if (varRefMatch) {
        const varDefMatch = content.match(new RegExp(`(?:const|let|var)\\s+${varRefMatch[1]}\\s*=\\s*['"\`](.*?)['"\`]`));
        if (varDefMatch) {
          results.vuePublicPath = varDefMatch[1].replace(/\$\{pkg\.name\}/g, pkgName);
        }
      }
    }
    const wyinsPathMatch = content.match(/assetsPublicPath_pro\s*=\s*['"`](\/\/res\.wyins\.net[^'"`]+)['"`]/);
    if (wyinsPathMatch && !results.vuePublicPath) {
      results.vuePublicPath = wyinsPathMatch[1].replace(/\$\{pkg\.name\}/g, pkgName);
    }
  }

  const configIndexPath = path.join(projectDir, 'config', 'index.js');
  if (fs.existsSync(configIndexPath)) {
    const content = fs.readFileSync(configIndexPath, 'utf8');
    const cdnMatch = content.match(/assetsPublicPath\s*:\s*['"`](\/\/res\.winbaoxian\.com[^'"`]*?)['"`]/);
    if (cdnMatch) {
      results.assetsPublicPath = cdnMatch[1].replace(/\$\{pkg\.name\}/g, pkgName);
    }
  }

  return results;
}

// 去除注释中的内容，避免匹配注释中的链接
function stripComments(content, ext) {
  // HTML/Vue 文件：去除 <!-- -->
  if (['.html', '.htm', '.vue', '.svelte', '.pug', '.hbs', '.ejs'].includes(ext)) {
    content = content.replace(/<!--[\s\S]*?-->/g, (match) => ' '.repeat(match.length));
    // Vue 文件中只对 <script> 和 <style> 块去除 // 和 /* */
    content = content.replace(/(<script[\s\S]*?>)([\s\S]*?)(<\/script>)/gi, (_, open, inner, close) => {
      return open + inner.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length)).replace(/(?<![:"'])\/\/[^\n]*/g, (m) => ' '.repeat(m.length)) + close;
    });
    content = content.replace(/(<style[\s\S]*?>)([\s\S]*?)(<\/style>)/gi, (_, open, inner, close) => {
      return open + inner.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length)) + close;
    });
    return content;
  }
  // 纯 JS/TS 文件：去除 // 和 /* */
  if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) {
    content = content.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length));
    // // 注释：不在 " 或 ' 内的
    content = content.replace(/(?<![:'"`])\/\/[^\n]*/g, (m) => ' '.repeat(m.length));
    return content;
  }
  // 纯 CSS/SCSS/Less：去除 /* */
  if (['.css', '.scss', '.less', '.styl'].includes(ext)) {
    content = content.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length));
    return content;
  }
  // 其他文件（如 .env）：不去除
  return content;
}

function collectIconfontUrls(content, publicPaths, projectDir, sourceFile, foundUrls) {
  // 先去除注释
  const ext = path.extname(sourceFile).toLowerCase();
  content = stripComments(content, ext);
  let processedContent = content;
  if (content.includes('htmlWebpackPlugin')) {
    if (publicPaths.vuePublicPath) {
      processedContent = processedContent.replace(/<%=\s*htmlWebpackPlugin\.options\.path\s*%>/g, publicPaths.vuePublicPath);
    }
    if (publicPaths.assetsPublicPath) {
      processedContent = processedContent.replace(/<%=\s*htmlWebpackPlugin\.options\.assetsPublicPath\s*%>/g, publicPaths.assetsPublicPath);
    }
  }

  const patterns = [ICONFONT_CDN_REGEX, ICONFONT_RES_REGEX, ICONFONT_RES_SYMBOLS_REGEX, ICONFONT_STATIC_PATH_REGEX, FONT_FILE_REGEX];
  for (const regex of patterns) {
    regex.lastIndex = 0;
    let match;
    while ((match = regex.exec(processedContent)) !== null) {
      const url = normalizeUrl(match[0]);
      foundUrls.add(url);
    }
  }

  CSS_IMPORT_REGEX.lastIndex = 0;
  let importMatch;
  while ((importMatch = CSS_IMPORT_REGEX.exec(processedContent)) !== null) {
    let url = importMatch[1].trim();
    if (url.startsWith('//') || url.startsWith('http')) {
      url = normalizeUrl(url);
      if (url.toLowerCase().includes('iconfont') || /font_\d+/.test(url)) {
        foundUrls.add(url);
      }
    }
  }
}

function resolveLocalIconfontCss(filePath, publicPaths, projectDir, foundUrls, processedFiles) {
  if (processedFiles.has(filePath)) return;
  processedFiles.add(filePath);
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const fontUrlRegex = /url\(\s*['"]?([^'")\s]+)['"]?\s*\)/g;
    let match;
    while ((match = fontUrlRegex.exec(content)) !== null) {
      let url = match[1].trim();
      if (url.startsWith('//') || url.startsWith('http')) {
        url = normalizeUrl(url);
        if (url.toLowerCase().includes('iconfont') || /font_\d+/.test(url)) {
          foundUrls.add(url);
        }
      }
    }
    collectIconfontUrls(content, publicPaths, projectDir, filePath, foundUrls);
  } catch {}
}

function scanProject(projectDir) {
  const projectName = path.basename(projectDir);
  const publicPaths = extractPublicPath(projectDir);
  const foundUrls = new Set();
  const foundFiles = new Map();
  const processedFiles = new Set();

  function traverse(dir) {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const entry of entries) {
      if (entry.isDirectory()) {
        if (EXCLUDE_DIRS.has(entry.name)) continue;
        traverse(path.join(dir, entry.name));
      } else {
        const ext = path.extname(entry.name).toLowerCase();
        const isSource = SOURCE_EXTS.has(ext);
        const isConfig = CONFIG_FILES.has(entry.name) || entry.name.startsWith('.env');
        if (!isSource && !isConfig) continue;

        const filePath = path.join(dir, entry.name);
        processedFiles.add(filePath);

        // 完整读取文件（不截断，避免遗漏后半部分的链接）
        let content;
        try {
          content = fs.readFileSync(filePath, 'utf8');
        } catch { continue; }

        collectIconfontUrls(content, publicPaths, projectDir, filePath, foundUrls);

        // 递归解析本地 iconfont.css
        const ICONFONT_LOCAL_CSS_REGEX = /['"]([\w./-]*iconfont[\w./-]*\.css)['"]/g;
        ICONFONT_LOCAL_CSS_REGEX.lastIndex = 0;
        let localMatch;
        while ((localMatch = ICONFONT_LOCAL_CSS_REGEX.exec(content)) !== null) {
          const localPath = localMatch[1];
          if (localPath.startsWith('http') || localPath.startsWith('//')) continue;
          const absolutePath = path.resolve(path.dirname(filePath), localPath);
          if (fs.existsSync(absolutePath)) {
            resolveLocalIconfontCss(absolutePath, publicPaths, projectDir, foundUrls, processedFiles);
          }
        }
      }
    }
  }

  traverse(projectDir);
  return { projectName, foundUrls: [...foundUrls], processedFiles, publicPaths };
}

// CDN 去重
function dedupLinks(urls) {
  const nameMap = new Map();
  for (const url of urls) {
    try {
      const pathname = new URL(url).pathname;
      const parts = pathname.split('/').filter(Boolean);
      const filename = parts[parts.length - 1];
      const ext = path.extname(filename).toLowerCase();
      if (!['.css', '.js'].includes(ext)) continue;

      let dedupKey;
      if (/^font_\d+_\w+\.css$/i.test(filename)) {
        dedupKey = filename;
      } else {
        const numericDir = [...parts].reverse().find(p => /^\d{10,}$/.test(p));
        dedupKey = numericDir ? numericDir + '/' + filename : filename;
      }

      if (!nameMap.has(dedupKey) || url.length < nameMap.get(dedupKey).length) {
        nameMap.set(dedupKey, url);
      }
    } catch {}
  }
  return [...nameMap.values()];
}

// ==================== 主流程 ====================

function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.log('用法: node 01_scan_repos_iconfont_scan_multi.js <项目根目录>');
    process.exit(1);
  }

  const rootDir = path.resolve(args[0]);
  if (!fs.existsSync(rootDir)) {
    console.error(`错误: 目录不存在: ${rootDir}`);
    process.exit(1);
  }

  console.log(`[Phase 1] 多项目扫描`);
  console.log(`  根目录: ${rootDir}`);

  // 获取所有子项目目录
  const projectDirs = fs.readdirSync(rootDir, { withFileTypes: true })
    .filter(e => e.isDirectory())
    .map(e => path.join(rootDir, e.name))
    .sort();

  console.log(`  找到 ${projectDirs.length} 个项目\n`);

  // 扫描所有项目
  const allProjectResults = [];
  const globalLinkMap = new Map(); // url -> [projects using it]

  let done = 0;
  for (const projectDir of projectDirs) {
    const { projectName, foundUrls, processedFiles } = scanProject(projectDir);
    const deduped = dedupLinks(foundUrls);
    done++;

    if (deduped.length > 0) {
      console.log(`  [${done}/${projectDirs.length}] ${projectName}: ${deduped.length} 个链接（扫描 ${processedFiles.size} 文件）`);
    } else {
      console.log(`  [${done}/${projectDirs.length}] ${projectName}: 无 iconfont 链接（扫描 ${processedFiles.size} 文件）`);
    }

    // 构建项目结果
    const projResult = { project: projectName, linkCount: deduped.length, links: deduped };
    allProjectResults.push(projResult);

    // 全局映射
    for (const url of deduped) {
      if (!globalLinkMap.has(url)) globalLinkMap.set(url, []);
      globalLinkMap.get(url).push(projectName);
    }

    // 保存单个项目 JSON
    const sourcesDir = path.join(__dirname, '..', 'sources');
    if (!fs.existsSync(sourcesDir)) fs.mkdirSync(sourcesDir, { recursive: true });
    const projPath = path.join(sourcesDir, `${projectName}_iconfont_links.json`);
    fs.writeFileSync(projPath, JSON.stringify({ project: projectName, links: deduped, linkCount: deduped.length }, null, 2), 'utf8');
  }

  // 添加手动链接（标记来源）
  for (const url of MANUAL_LINKS) {
    const normalized = normalizeUrl(url);
    if (!globalLinkMap.has(normalized)) {
      globalLinkMap.set(normalized, ['manual']);
    }
  }

  // 合并所有 URL + 手动链接
  const allUrls = new Set();
  for (const [url] of globalLinkMap) allUrls.add(url);
  for (const url of MANUAL_LINKS) allUrls.add(normalizeUrl(url));
  const finalDeduped = dedupLinks([...allUrls]);

  console.log('\n' + '='.repeat(60));
  console.log('  汇总统计');
  console.log('='.repeat(60));
  console.log(`  项目总数:          ${projectDirs.length}`);
  console.log(`  有 iconfont 的项目: ${allProjectResults.filter(r => r.linkCount > 0).length}`);
  console.log(`  手动提供的链接:    ${MANUAL_LINKS.length}`);
  console.log(`  去重后总链接数:    ${finalDeduped.length}`);
  console.log('='.repeat(60));

  // 构建 all_iconfont_links.json
  const allLinksData = {
    version: '2.0.0',
    rootDir,
    totalProjects: projectDirs.length,
    projectsWithIconfont: allProjectResults.filter(r => r.linkCount > 0).length,
    manualLinkCount: MANUAL_LINKS.length,
    uniqueLinkCount: finalDeduped.length,
    links: finalDeduped.map(url => ({
      url,
      usedBy: globalLinkMap.get(url) || [],
    })),
    byProject: allProjectResults,
  };

  const sourcesDir = path.join(__dirname, '..', 'sources');
  if (!fs.existsSync(sourcesDir)) fs.mkdirSync(sourcesDir, { recursive: true });

  const allOutputPath = path.join(sourcesDir, 'all_iconfont_links.json');
  fs.writeFileSync(allOutputPath, JSON.stringify(allLinksData, null, 2), 'utf8');
  console.log(`\n  整合结果: ${allOutputPath}`);

  const linksOnlyPath = path.join(sourcesDir, 'iconfont_urls.txt');
  fs.writeFileSync(linksOnlyPath, finalDeduped.join('\n') + '\n', 'utf8');
  console.log(`  链接列表: ${linksOnlyPath}`);
  console.log(`  项目详情: ${projectDirs.length} 个文件 (${sourcesDir}/<project>_iconfont_links.json)`);
  console.log('\n  扫描完成。');
}

main();
