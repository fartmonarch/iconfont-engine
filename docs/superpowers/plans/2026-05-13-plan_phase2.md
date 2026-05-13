# Phase 2: Asset Resolver — 脚本计划

## 总览

```
02_resolve_download_assets.js  →  sources/meta/assets_manifest.json
        ↓
02_resolve_parse_css_mappings.js  →  sources/meta/css_mappings.json
        ↓
02_resolve_validate_assets.js  →  sources/meta/assets_validation.json
```

任何一步失败只重跑该步骤，不影响已完成的数据。

---

## 脚本 01：02_resolve_download_assets.js（纯 IO）

**职责**：下载 111 个 CSS + 解析 @font-face + 下载对应 TTF

**输入**：
- `sources/phase1_raw_links/all_iconfont_links.json`

**输出**：
- `sources/phase2_assets/<assetId>/iconfont.css` — 111 个 CSS 文件
- `sources/phase2_assets/<assetId>/font.ttf` — TTF 文件（尽可能下载）
- `sources/meta/assets_manifest.json` — 资产清单

**assetId 生成**：`sha256(cssUrl)[0:12]`

**流程**：

### Step 1: 读取输入
```js
const linksData = require('../sources/phase1_raw_links/all_iconfont_links.json');
const cssUrls = linksData.links.map(l => l.url); // 111 个
const urlToProjects = {}; // cssUrl → [project names]
```

### Step 2: 下载 CSS（参考 build_superset.js 的 fetch 逻辑）
```js
// fetch 函数：支持 http/https、自动跟随 301/302、15s 超时
function fetch(url) { ... }
```

### Step 3: 解析 @font-face 提取 TTF URL
从 CSS 中匹配：
```css
@font-face {
  font-family: 'iconfont';
  src: url('...font_123_xxx.ttf') format('truetype'),
       url('...font_123_xxx.woff2') format('woff2');
}
```
- 优先 `.ttf` URL
- 备选 `.woff`（后续 fontTools 可能需要转 TTF）
- 如果 CSS 中无 `@font-face`，标记 `downloadStatus: "no_ttf_url"`

### Step 4: 下载 TTF
- 下载每个 CSS 对应的 TTF 文件
- 超时 30s（TTF 文件较大）
- 下载失败标记 `downloadStatus: "ttf_404"`

### Step 5: 保存 + 输出清单
```
sources/phase2_assets/<assetId>/
├── iconfont.css
├── font.ttf          (可能存在)
```

`assets_manifest.json` 格式：
```json
[
  {
    "assetId": "a1b2c3d4e5f6",
    "cssUrl": "https://res.winbaoxian.com/ali-iconfont/font_123_xxx.css",
    "cssPath": "sources/phase2_assets/a1b2c3d4e5f6/iconfont.css",
    "cssContentHash": "sha256(css_content)",
    "fontUrl": "https://res.winbaoxian.com/ali-iconfont/font_123_xxx.ttf",
    "ttfPath": "sources/phase2_assets/a1b2c3d4e5f6/font.ttf",
    "ttfContentHash": "sha256(ttf_content)",
    "sourceProjects": ["project-a", "project-b"],
    "templateVar": "<%= htmlWebpackPlugin.options.iconfontPath %>/font_123_xxx.css",
    "downloadStatus": "ok" | "css_404" | "ttf_404" | "no_ttf_url"
  }
]
```

**参考逻辑**：`D:\work\build_superset.js` 的 `fetch()` + 下载循环 + 去重逻辑（`font_(\d+)_` 模式）

---

## 脚本 02：02_resolve_parse_css_mappings.js（纯解析）

**职责**：从已下载的 CSS 中提取 name → unicode 映射

**输入**：
- `sources/meta/assets_manifest.json`（脚本 01 产出）
- `sources/phase2_assets/<assetId>/iconfont.css`

**输出**：
- `sources/meta/css_mappings.json`

**流程**：

### Step 1: 遍历 assets_manifest.json
```js
const assets = require('../sources/meta/assets_manifest.json');
```

### Step 2: 提取 CSS 映射
参考 `build_superset.js` 的 `extractIcons()` 函数：

```js
// 正则匹配 .icon-xxx:before { content: "\e601" }
const iconRe = /\.icon-([a-zA-Z0-9_-]+)\s*:\s*before\s*\{[^}]*content\s*:\s*["']?\\([0-9a-fA-F]+)/g;
// 备选：.iconXxx:before
const iconNoHyphenRe = /\.icon([a-zA-Z][a-zA-Z0-9_-]*)\s*:\s*before\s*\{[^}]*content\s*:\s*["']?\\([0-9a-fA-F]+)/g;
// 备选：.s-xxx:before
const symRe = /\.s-([a-zA-Z0-9_-]+)\s*:\s*before\s*\{[^}]*content\s*:\s*["']?\\([0-9a-fA-F]+)/g;
```

### Step 3: 输出
```json
[
  {
    "assetId": "a1b2c3d4e5f6",
    "cssUrl": "https://...",
    "mappings": [
      { "name": "home", "unicode": "e601", "selector": ".icon-home:before" },
      { "name": "user", "unicode": "e602", "selector": ".icon-user:before" }
    ],
    "extractStatus": "ok" | "no_icons" | "parse_error"
  }
]
```

---

## 脚本 01 测试结果

### 运行 #1：发现 gzip 问题（2026-05-13 初版）
- 结果：110 CSS 成功 + 1 CSS 404，109 TTF 成功 + 1 无字体 URL
- 问题：`management-community-operations` 的 CSS 是 gzip 压缩的，脚本未解压导致匹配不到 `@font-face`
- 问题：部分 CSS 中相对路径 `../fonts/symbols.ttf` 解析失败

### 运行 #2：修复 gzip + 相对路径后
| 指标 | 结果 |
|------|------|
| CSS 总数 | 111 |
| CSS 下载成功 | 110 |
| CSS 失败 (404) | 1 — `insurance-group-mobile-webpack4` CI 临时地址已过期 |
| 找到字体 URL | 110 |
| TTF 下载成功 | 110 |
| TTF 失败 | 0 |

### 异常 asset 明细
- `css_404`（1 个）：`insurance-group-mobile-webpack4` — CI 临时链接已过期，无法恢复

### 已修复问题
- gzip 压缩 CSS 未解压 → 增加 `zlib.createGunzip()` 处理 `Content-Encoding: gzip`
- 相对路径 `../fonts/symbols.ttf` 解析失败 → 用 `new URL(relative, cssUrl)` 正确解析
- 相对路径 `iconfont.ttf?t=...` 解析失败 → 同上

---

## 脚本 02 测试结果

### 运行 #1：发现三个问题（2026-05-13）
- 结果：100 ok + 10 no_icons
- 问题 1：generator 函数缺少 `*`，语法错误
- 问题 2：symbol CSS（`.s-xxx`）采用**逗号分隔多 selector 单 block** 格式，原正则按单 selector 匹配失败
- 问题 3：symbol CSS 的 `content: "\EA01"` 末尾无 `;`，原正则 `[;}]` 匹配失败（`}` 已被 block 正则吞掉）

### 运行 #2：修复全部问题后
| 指标 | 结果 |
|------|------|
| CSS 可解析 | 110 |
| 解析成功 | 110 |
| 解析失败 | 0 |
| 总图标数 | 11494 |
| 无图标 asset | 0 |

### 已修复问题
- `function extractIconMappings` → `function*` → 改为普通函数 `function` + 返回数组
- 解析策略：改为逐 `{ }` block 解析，先找 `content`，再解析前面逗号分隔的 selectors
- `CONTENT_RE` 末尾改为 `(?:[;}]|$)` 兼容无 `;` 的情况

---

## 脚本 03 测试结果

### 运行 #1：发现计数问题（2026-05-13）
- 结果：110 ok + 1 css_404，但 empty_mappings 误报 1（css_404 asset 必然无 mappings）
- 修复：跳过 `css_404` asset 的 mappings 检查

### 运行 #2：修复后
| 指标 | 结果 |
|------|------|
| 总资产数 | 111 |
| ✅ ok | 110 |
| ⚠️ css_404 | 1 — CI 临时地址已过期 |
| ⚠️ ttf_missing | 0 |
| ⚠️ empty_mappings | 0 |
| ⚠️ ttf_corrupt | 0 |
| 图标总数 | 11494 |
| TTF 总计 | 3628 KB |

### Phase 2 全部脚本校验通过

| 脚本 | 状态 | 输出文件 |
|------|------|----------|
| 02_resolve_download_assets.js | ✅ 通过 | `sources/meta/assets_manifest.json` |
| 02_resolve_parse_css_mappings.js | ✅ 通过 | `sources/meta/css_mappings.json` |
| 02_resolve_validate_assets.js | ✅ 通过 | `sources/meta/assets_validation.json` |

**Phase 2 完成。** 可以进入 Phase 3。


**职责**：校验 CSS+TTF 配对完整性，标记异常（见下方测试结果）

---
