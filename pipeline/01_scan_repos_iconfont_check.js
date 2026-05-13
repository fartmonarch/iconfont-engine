#!/usr/bin/env node
/**
 * 01_scan_repos_iconfont_check.js — Phase 1: 单项目 iconfont 链接扫描（升级版）
 *
 * 改进点：
 *   1. 不再依赖 index.html，改为全局扫描源码文件
 *   2. 多模式正则匹配：HTML link、CSS @import、JS 动态引入、本地 iconfont.css 递归解析
 *   3. webpack 模板变量替换：读取项目配置提取 publicPath
 *   4. 智能目录过滤，跳过 node_modules/dist 等无关目录
 *
 * 用法:
 *   node 01_scan_repos_iconfont_check.js <项目目录>
 */

const fs = require('fs');
const path = require('path');

// ==================== 配置 ====================

const EXCLUDE_DIRS = new Set([
  'node_modules', '.git', '.svn', 'dist', 'build', 'out',
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

// ==================== 正则 ====================

// 匹配 iconfont CDN 链接（兼容 at.alicdn.com / i.alicdn.com / gw.alicdn.com 及 res.winbaoxian.com / res.wyins.net）
const ICONFONT_CDN_REGEX = /(?:https?:)?\/\/(?:at|i|gw)\.alicdn\.com\/t\/(?:c\/)?font_\d+_[a-zA-Z0-9]+\.(?:css|js)/g;
const ICONFONT_RES_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/(?:ali-)?iconfont\/font_\d+_[a-zA-Z0-9]+\.(?:css|eot|woff2?|ttf|svg)/g;
const ICONFONT_RES_SYMBOLS_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/iconfont\/\d+\/css\/symbols\.css/g;

const ICONFONT_STATIC_PATH_REGEX = /(?:https?:)?\/\/(?:res\.winbaoxian\.com|res\.wyins\.net)\/[\w./-]*iconfont[\w./-]*\.(?:css|js)/g;

const ICONFONT_LOCAL_CSS_REGEX = /['"]([\w./-]*iconfont[\w./-]*\.css)['"]/g;

// CSS @import 匹配
const CSS_IMPORT_REGEX = /@import\s+(?:url\(\s*)?['"]?([^'")\s;]+iconfont[^'")\s;]*)['"]?\s*\)?\s*;/g;

// ==================== 工具函数 ====================

function normalizeUrl(url) {
  if (!url) return url;
  url = url.trim();
  if (url.startsWith('//')) url = 'https:' + url;
  if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'https://' + url;
  // CDN 域名统一：res.wyins.net → res.winbaoxian.com
  url = url.replace(/https:\/\/res\.wyins\.net\//g, 'https://res.winbaoxian.com/');
  // 清理多余斜杠
  url = url.replace(/([^:]\/)\/+/g, '$1');
  return url;
}

/**
 * 从项目配置中提取 publicPath
 * 支持 vue.config.js 和 config/index.js
 */
function extractPublicPath(projectDir) {
  const results = {};

  // 尝试读取 package.json 获取项目名称
  let pkgName = '';
  const pkgPath = path.join(projectDir, 'package.json');
  if (fs.existsSync(pkgPath)) {
    try {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      pkgName = pkg.name || '';
    } catch {
      // ignore
    }
  }

  // 尝试 vue.config.js
  const vueConfigPath = path.join(projectDir, 'vue.config.js');
  if (fs.existsSync(vueConfigPath)) {
    const content = fs.readFileSync(vueConfigPath, 'utf8');

    // 匹配 publicPath: '...' 或 publicPath: `...`（字符串字面量）
    const publicPathMatch = content.match(/publicPath\s*:\s*['"`]([^'"`]+)['"`]/);
    if (publicPathMatch) {
      results.vuePublicPath = publicPathMatch[1];
    }

    // 匹配 publicPath: variableName（变量引用），然后找变量定义
    if (!results.vuePublicPath) {
      const varRefMatch = content.match(/publicPath\s*:\s*([a-zA-Z_]\w*)/);
      if (varRefMatch) {
        const varName = varRefMatch[1];
        // 在文件中找该变量的定义
        const varDefMatch = content.match(new RegExp(`(?:const|let|var)\\s+${varName}\\s*=\\s*['"\`](.*?)['"\`]`));
        if (varDefMatch) {
          results.vuePublicPath = varDefMatch[1].replace(/\$\{pkg\.name\}/g, pkgName);
        }
      }
    }

    // 额外匹配 res.wyins.net 的 publicPath（insurance-group-mobile 类型）
    const wyinsPathMatch = content.match(/assetsPublicPath_pro\s*=\s*['"`](\/\/res\.wyins\.net[^'"`]+)['"`]/);
    if (wyinsPathMatch && !results.vuePublicPath) {
      results.vuePublicPath = wyinsPathMatch[1].replace(/\$\{pkg\.name\}/g, pkgName);
    }
  }

  // 尝试 config/index.js (webpack 旧项目)
  const configIndexPath = path.join(projectDir, 'config', 'index.js');
  if (fs.existsSync(configIndexPath)) {
    const content = fs.readFileSync(configIndexPath, 'utf8');
    // 匹配 build.assetsPublicPath 中的 CDN 域名
    const cdnMatch = content.match(/assetsPublicPath\s*:\s*['"`](\/\/res\.winbaoxian\.com[^'"`]*?)['"`]/);
    if (cdnMatch) {
      results.assetsPublicPath = cdnMatch[1].replace(/\$\{pkg\.name\}/g, pkgName);
    }
  }

  return results;
}

/**
 * 替换 webpack 模板变量为实际路径（不 normalize，由调用方统一处理）
 */
function resolveTemplateVars(url, publicPaths, projectDir, sourceFile) {
  if (!url.includes('htmlWebpackPlugin')) return url;

  // 替换 <%= htmlWebpackPlugin.options.path %>
  if (url.includes('htmlWebpackPlugin.options.path')) {
    if (publicPaths.vuePublicPath) {
      url = url.replace(/<%=\s*htmlWebpackPlugin\.options\.path\s*%>/g, publicPaths.vuePublicPath);
    }
  }

  // 替换 <%= htmlWebpackPlugin.options.assetsPublicPath %>
  if (url.includes('htmlWebpackPlugin.options.assetsPublicPath')) {
    if (publicPaths.assetsPublicPath) {
      url = url.replace(/<%=\s*htmlWebpackPlugin\.options\.assetsPublicPath\s*%>/g, publicPaths.assetsPublicPath);
    }
  }

  return url;
}

/**
 * 去除注释中的内容，避免匹配注释中的链接
 */
function stripComments(content, ext) {
  // HTML/Vue 文件：去除 <!-- -->
  if (['.html', '.htm', '.vue', '.svelte', '.pug', '.hbs', '.ejs'].includes(ext)) {
    content = content.replace(/<!--[\s\S]*?-->/g, (match) => ' '.repeat(match.length));
    // Vue 文件中只对 <script> 和 <style> 块去除 // 和 /* */
    content = content.replace(/(<script[\s\S]*?>)([\s\S]*?)(<\/script>)/gi, (_, open, inner, close) => {
      return open + inner.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length)).replace(/(?<![:'"`])\/\/[^\n]*/g, (m) => ' '.repeat(m.length)) + close;
    });
    content = content.replace(/(<style[\s\S]*?>)([\s\S]*?)(<\/style>)/gi, (_, open, inner, close) => {
      return open + inner.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length)) + close;
    });
    return content;
  }
  // 纯 JS/TS 文件：去除 // 和 /* */
  if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) {
    content = content.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length));
    content = content.replace(/(?<![:'"`])\/\/[^\n]*/g, (m) => ' '.repeat(m.length));
    return content;
  }
  // 纯 CSS/SCSS/Less：去除 /* */
  if (['.css', '.scss', '.less', '.styl'].includes(ext)) {
    content = content.replace(/\/\*[\s\S]*?\*\//g, (m) => ' '.repeat(m.length));
    return content;
  }
  return content;
}

// ==================== 核心扫描逻辑 ====================

function collectIconfontUrls(content, publicPaths, projectDir, sourceFile, foundUrls) {
  // 先去除注释
  const ext = path.extname(sourceFile).toLowerCase();
  content = stripComments(content, ext);
  // 再替换模板变量，再做正则匹配
  let processedContent = content;
  if (content.includes('htmlWebpackPlugin')) {
    // 替换内容中的所有模板变量占位
    if (publicPaths.vuePublicPath) {
      processedContent = processedContent.replace(/<%=\s*htmlWebpackPlugin\.options\.path\s*%>/g, publicPaths.vuePublicPath);
    }
    if (publicPaths.assetsPublicPath) {
      processedContent = processedContent.replace(/<%=\s*htmlWebpackPlugin\.options\.assetsPublicPath\s*%>/g, publicPaths.assetsPublicPath);
    }
  }

  const patterns = [
    ICONFONT_CDN_REGEX,
    ICONFONT_RES_REGEX,
    ICONFONT_RES_SYMBOLS_REGEX,
    ICONFONT_STATIC_PATH_REGEX,
  ];

  for (const regex of patterns) {
    regex.lastIndex = 0; // reset
    let match;
    while ((match = regex.exec(processedContent)) !== null) {
      let url = normalizeUrl(match[0]);
      if (!foundUrls.has(url)) {
        foundUrls.add(url);
      }
    }
  }

  // CSS @import 匹配
  CSS_IMPORT_REGEX.lastIndex = 0;
  let importMatch;
  while ((importMatch = CSS_IMPORT_REGEX.exec(processedContent)) !== null) {
    let url = importMatch[1].trim();
    if (url.startsWith('//') || url.startsWith('http')) {
      url = normalizeUrl(url);
      if (url.toLowerCase().includes('iconfont') || /font_\d+/.test(url)) {
        if (!foundUrls.has(url)) {
          foundUrls.add(url);
        }
      }
    }
  }
}

/**
 * 递归解析本地 iconfont.css 文件
 */
function resolveLocalIconfontCss(filePath, publicPaths, projectDir, foundUrls, processedFiles) {
  if (processedFiles.has(filePath)) return;
  processedFiles.add(filePath);

  try {
    const content = fs.readFileSync(filePath, 'utf8');

    // 提取其中的 @font-face src url
    const fontUrlRegex = /url\(\s*['"]?([^'")\s]+)['"]?\s*\)/g;
    let match;
    while ((match = fontUrlRegex.exec(content)) !== null) {
      let url = match[1].trim();
      // 只处理在线字体文件
      if (url.startsWith('//') || url.startsWith('http')) {
        url = normalizeUrl(url);
        if (url.toLowerCase().includes('iconfont') || /font_\d+/.test(url)) {
          if (!foundUrls.has(url)) {
            foundUrls.add(url);
          }
        }
      }
    }

    // 也检查其中的 CDN link
    collectIconfontUrls(content, publicPaths, projectDir, filePath, foundUrls);

  } catch (err) {
    // ignore
  }
}

/**
 * 递归遍历目录
 */
async function traverseDir(dir, projectDir, publicPaths, foundUrls, foundFiles, processedFiles) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    if (entry.isDirectory()) {
      if (EXCLUDE_DIRS.has(entry.name)) continue;
      await traverseDir(path.join(dir, entry.name), projectDir, publicPaths, foundUrls, foundFiles, processedFiles);
    } else {
      const ext = path.extname(entry.name).toLowerCase();
      const isSourceFile = SOURCE_EXTS.has(ext);
      const isConfigFile = CONFIG_FILES.has(entry.name) || entry.name.startsWith('.env');

      if (!isSourceFile && !isConfigFile) continue;

      const filePath = path.join(dir, entry.name);
      processedFiles.add(filePath);

      // 完整读取文件（不截断，避免遗漏后半部分的链接）
      let content;
      try {
        content = fs.readFileSync(filePath, 'utf8');
      } catch {
        continue;
      }

      // 提取 iconfont CDN 链接
      collectIconfontUrls(content, publicPaths, projectDir, filePath, foundUrls);

      // 匹配本地 iconfont.css 并递归解析
      ICONFONT_LOCAL_CSS_REGEX.lastIndex = 0;
      let localMatch;
      while ((localMatch = ICONFONT_LOCAL_CSS_REGEX.exec(content)) !== null) {
        const localPath = localMatch[1];
        // 跳过明显不是本地路径的
        if (localPath.startsWith('http') || localPath.startsWith('//')) continue;
        const absolutePath = path.resolve(path.dirname(filePath), localPath);
        if (fs.existsSync(absolutePath)) {
          resolveLocalIconfontCss(absolutePath, publicPaths, projectDir, foundUrls, processedFiles);
        }
      }

      // 记录文件映射
      if (foundUrls.size > 0) {
        foundFiles.set(filePath, [...foundUrls]);
      }
    }
  }
}

// ==================== 主流程 ====================

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.log('用法: node 01_scan_repos_iconfont_check.js <项目目录>');
    process.exit(1);
  }

  const projectDir = path.resolve(args[0]);
  const projectName = path.basename(projectDir);

  if (!fs.existsSync(projectDir)) {
    console.error(`错误: 目录不存在: ${projectDir}`);
    process.exit(1);
  }

  console.log(`[Phase 1 v2] 扫描项目: ${projectName}`);
  console.log(`  目录: ${projectDir}`);

  // Step 0: 提取 publicPath 配置
  const publicPaths = extractPublicPath(projectDir);
  if (Object.keys(publicPaths).length > 0) {
    console.log(`  配置发现:`);
    if (publicPaths.vuePublicPath) {
      console.log(`    vue.config.js publicPath: ${publicPaths.vuePublicPath}`);
    }
    if (publicPaths.assetsPublicPath) {
      console.log(`    config/index.js assetsPublicPath: ${publicPaths.assetsPublicPath}`);
    }
  }

  const foundUrls = new Set();
  const foundFiles = new Map(); // filePath -> [urls found in this file]
  const processedFiles = new Set();

  // Step 1: 全局扫描源码
  await traverseDir(projectDir, projectDir, publicPaths, foundUrls, foundFiles, processedFiles);

  const uniqueLinks = [...foundUrls];

  // CDN 去重：同文件名只留最短的 URL
  // 策略：font_*.css 按文件名去重（文件名含唯一 hash）
  // symbols.css / iconfont.css 按 "上级目录名/文件名" 去重（如 1483933727382/symbols.css）
  const nameMap = new Map(); // dedupKey -> shortestUrl
  for (const url of uniqueLinks) {
    try {
      const pathname = new URL(url).pathname;
      const parts = pathname.split('/').filter(Boolean);
      const filename = parts[parts.length - 1];
      const ext = path.extname(filename).toLowerCase();
      if (!['.css', '.js'].includes(ext)) continue;

      let dedupKey;
      // font_xxx.css 类型：文件名本身就是唯一标识
      if (/^font_\d+_\w+\.css$/i.test(filename)) {
        dedupKey = filename;
      }
      // symbols.css / iconfont.css：找路径中的数字 ID 目录做 key
      else {
        const numericDir = [...parts].reverse().find(p => /^\d{10,}$/.test(p));
        dedupKey = numericDir ? numericDir + '/' + filename : filename;
      }

      if (!nameMap.has(dedupKey) || url.length < nameMap.get(dedupKey).length) {
        nameMap.set(dedupKey, url);
      }
    } catch {
      // 无效 URL 跳过
    }
  }

  const dedupedLinks = [...nameMap.values()];
  const dupCount = uniqueLinks.length - dedupedLinks.length;

  // 打印去重详情
  if (dupCount > 0) {
    console.log('\n  去重详情:');
    for (const [key, url] of nameMap) {
      const duplicates = uniqueLinks.filter(u => {
        try {
          const pathname = new URL(u).pathname;
          const parts = pathname.split('/').filter(Boolean);
          const filename = parts[parts.length - 1];
          let dk;
          if (/^font_\d+_\w+\.css$/i.test(filename)) dk = filename;
          else { const nd = [...parts].reverse().find(p => /^\d{10,}$/.test(p)); dk = nd ? nd + '/' + filename : filename; }
          return dk === key && u !== url;
        } catch { return false; }
      });
      if (duplicates.length > 0) {
        console.log(`  [${key}] 保留: ${url}`);
        for (const dup of duplicates) {
          console.log(`         去除: ${dup}`);
        }
      }
    }
    console.log('');
  }

  if (uniqueLinks.length === 0) {
    console.log('  未找到任何 iconfont 链接');
    const result = { project: projectName, path: projectDir, filesScanned: processedFiles.size, links: [] };
    console.log(JSON.stringify(result, null, 2));
    process.exit(0);
  }

  console.log(`  扫描了 ${processedFiles.size} 个文件`);
  console.log(`  找到 ${uniqueLinks.length} 个链接，CDN 去重后 ${dedupedLinks.length} 个（去重 ${dupCount} 个）`);
  for (const link of dedupedLinks) {
    console.log(`    - ${link}`);
    // 找出引用此链接的文件
    const referencingFiles = [];
    for (const [filePath, urls] of foundFiles) {
      if (urls.includes(link)) {
        referencingFiles.push(path.relative(projectDir, filePath));
      }
    }
    for (const f of referencingFiles) {
      console.log(`        在: ${f}`);
    }
  }

  // Step 2: 输出 JSON
  const result = {
    project: projectName,
    path: projectDir,
    filesScanned: processedFiles.size,
    links: dedupedLinks.map(url => {
      const referencingFiles = [];
      for (const [filePath, urls] of foundFiles) {
        if (urls.includes(url)) {
          referencingFiles.push(path.relative(projectDir, filePath));
        }
      }
      return { url, foundIn: referencingFiles };
    }),
    linkCount: dedupedLinks.length,
  };

  // Step 3: 保存到 sources/ 目录
  const sourcesDir = path.join(__dirname, '..', 'sources');
  if (!fs.existsSync(sourcesDir)) {
    fs.mkdirSync(sourcesDir, { recursive: true });
  }

  const outputPath = path.join(sourcesDir, `${projectName}_iconfont_links.json`);
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf8');
  console.log(`\n  结果已保存: ${outputPath}`);
}

main().catch(console.error);
