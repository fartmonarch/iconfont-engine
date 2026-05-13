# Iconfont Engine — 系统设计文档

> **系统本质**：不是"字体合并工具"，而是 **"Glyph 级别的资产数据库 + 可审计渲染管线"**
>
> **最终形态**：Agent-Orchestrated Font Engineering System

---

## 一、总体架构流程图

```
                ┌──────────────────────────────┐
                │        Agent Controller       │
                │  (LLM: GPT / Claude / Qwen)   │
                └──────────────┬───────────────┘
                               │
                               ▼
        ┌────────────────────────────────────────────┐
        │          Phase 0: Task Planning            │
        │  技术：LLM + JSON Planner                  │
        │  任务：生成执行计划 + 分配脚本任务         │
        └──────────────┬────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 1: Repo Discovery（仓库扫描）                          │
│ 技术：Node.js + simple-git + html parser                    │
│ 脚本：01_scan_repos.js                                       │
│ 任务：                                                     │
│   ---> clone多个git仓库                                      │
│   ---> 扫描index.html / app.html                             │
│   ---> 提取 <link rel="stylesheet">                         │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 2: Asset Resolver（资源解析）                          │
│ 技术：Node.js + regex + axios                               │
│ 脚本：02_resolve_download_assets.js                         │
│       02_resolve_parse_css_mappings.js                      │
│       02_resolve_validate_assets.js                         │
│ 任务：                                                     │
│   ---> 下载 111 个 CSS 文件                                 │
│   ---> 解析 @font-face 提取 TTF URL                         │
│   ---> 下载对应的 TTF 文件                                  │
│   ---> 提取 CSS 中 .icon-xxx:before 映射（name → unicode）  │
│   ---> 校验 CSS+TTF 配对完整性                              │
│   ---> 输出 assets_manifest.json（溯源锚点）                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 3: Glyph Extraction（字形提取）                       │
│ 技术：Python + fontTools                                    │
│ 脚本：03_extract_glyphs.py                                  │
│ 任务：                                                     │
│   ---> 解析TTF                                              │
│   ---> cmap unicode → glyphName                             │
│   ---> 提取 contours                                        │
│   ---> 生成 raw glyph dataset                               │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 4: Geometry Normalization（几何标准化）                 |
| 这个阶段开始使用superowers                                     │
│ 技术：Python + numpy + fontTools                            │
│ 脚本：04_normalize_glyphs.py                                │
│ 任务：                                                     │
│   ---> UPM统一（1024）                                      │
│   ---> contour排序                                         │
│   ---> 起点统一                                             │
│   ---> 精度round(6)                                         │
│   ---> composite展开（仅视图层）                            │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 5: Glyph Hash Registry（核心数据库）                  │
│ 技术：Python + sha256 + json                                │
│ 脚本：05_build_registry.py                                 │
│ 任务：                                                     │
│   ---> glyphHash生成                                        │
│   ---> 多源合并                                             │
│   ---> alias收集                                            │
│   ---> source tracking                                      │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 6: Conflict Detection（冲突检测）                     │
│ 技术：Python                                              │
│ 脚本：06_detect_conflicts.py                               │
│ 任务：                                                     │
│   ---> unicode冲突检测                                     │
│   ---> glyph冲突检测                                       │
│   ---> name冲突检测                                        │
│   ---> 生成 conflict report                                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 7: Conflict Resolution（冲突解决）                   │
│ 技术：Python                                              │
│ 脚本：07_resolve_conflicts.py                             │
│ 任务：                                                     │
│   ---> PUA unicode分配（E000-F8FF）                        │
│   ---> alias merge                                         │
│   ---> rename policy                                       │
│   ---> lineage记录                                         │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 8: Direct Glyf Merge（核心合并引擎）                 │
│ 技术：Python + fontTools                                   │
│ 脚本：08_merge_glyf.py                                     │
│ 任务：                                                     │
│   ---> glyph deep copy                                     │
│   ---> cmap rebuild                                        │
│   ---> hmtx normalize                                      │
│   ---> glyf table merge                                    │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 9: Font Build（字体生成）                             │
│ 技术：fontTools FontBuilder                                │
│ 脚本：09_build_font.py                                     │
│ 任务：                                                     │
│   ---> TTF生成                                             │
│   ---> WOFF2生成                                           │
│   ---> table补全                                           │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 10: Validation（验证层）                              │
│ 技术：Playwright + pixelmatch + PIL                        │
│ 脚本：10_validate_render.js                                │
│ 任务：                                                     │
│   ---> Chrome/Firefox渲染对比                              │
│   ---> pixel diff                                          │
│   ---> 输出 diff report                                    │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 11: Output & Manifest（发布层）                       │
│ 技术：Node.js                                             │
│ 脚本：11_generate_manifest.js                              │
│ 任务：                                                     │
│   ---> iconfont.css                                        │
│   ---> iconfont.json                                       │
│   ---> merge_manifest.json                                 │
│   ---> npm package output                                  │
└──────────────────────────────────────────────────────────────┘
```
```
项目代码结构 
iconfont-engine/
│
├── sources/                  # 原始多 iconfont 输入（按 Phase 分层）
│   ├── phase1_raw_links/     # Phase 1 原始数据：CSS 链接清单
│   │   ├── all_iconfont_links.json
│   │   ├── iconfont_urls.txt
│   │   └── <project>_iconfont_links.json
│   ├── phase2_assets/        # Phase 2 下载资产：<assetId>/iconfont.css + font.ttf
│   ├── phase2_mappings/      # Phase 2 CSS 映射数据
│   ├── phase2_validation/    # Phase 2 校验报告
│   └── meta/                 # 跨 Phase 元数据
│       ├── assets_manifest.json
│       ├── css_mappings.json
│       └── assets_validation.json
│
├── registry/                 # 核心资产数据库
│   ├── glyph_registry.json
│   ├── unicode_map.json
│   ├── hash_index.json
│   ├── lineage.json          # 溯源链
│
├── pipeline/
│   ├── 01_ingest.py
│   ├── 02_normalize_glyph.py
│   ├── 03_build_registry.py
│   ├── 04_detect_conflict.py
│   ├── 05_resolve_conflict.py
│   ├── 06_merge_glyf.py
│   ├── 07_build_font.py
│   ├── 08_validate_render.py
│
├── output/
│   ├── iconfont.ttf
│   ├── iconfont.woff2
│   ├── iconfont.css
│   ├── iconfont.json
│
├── report/
│   ├── conflict.md
│   ├── render_diff.png
│   ├── audit.json
```
---

## 二、Agent 真实角色

### Agent 不做：

- ❌ font parsing（脚本做）
- ❌ glyph transform（脚本做）
- ❌ file IO heavy ops（脚本做）
- ❌ 直接处理字体（脚本做）

### Agent 的职责只有 4 个：

1. **决策执行顺序**（pipeline orchestration）
2. **生成/修改脚本**（Node/Python）
3. **处理异常**（conflict decision）
4. **校验结果**（validation interpretation）

### 脚本 vs Agent 分工

| 类型 | 归属 |
|------|------|
| clone repo | 脚本 |
| HTML 解析 | 脚本 |
| CSS 解析 | 脚本 |
| TTF 解析 | 脚本 |
| glyph 提取 | 脚本 |
| hash 计算 | 脚本 |
| merge glyph | 脚本 |
| unicode 分配 | 脚本 |
| **冲突判断** | **Agent（规则决策）** |
| **rename 策略** | **Agent** |
| **merge 策略选择** | **Agent** |
| **pipeline 调度** | **Agent** |

### Agent 工作流（真实运行方式）

```
用户需求
   ↓
Agent 生成 pipeline plan (JSON)
   ↓
调用脚本执行 Phase 1
   ↓
返回结果
   ↓
Agent 分析
   ↓
生成 Phase 2 脚本调用
   ↓
循环直到 Phase 11
```

---

## 三、关键设计原则（避免系统崩溃）

### 三个绝对原则（决定无损）

#### 原则 1：不重建 glyph（核心）

```
❌ SVG roundtrip 禁止
❌ Bézier 重建禁止
```

👉 只能：**copy glyph object（glyf level）**

#### 原则 2：geometry 是唯一真相

```
glyphHash = canonical contours
```

优先级：

```
1. contours（唯一真值）
2. unicode（映射）
3. name（仅辅助）
```

#### 原则 3：所有冲突必须显式化

不能"自动覆盖"，必须：

- 标记
- 分级
- 可回滚
- 可追溯

### 其他原则

1. **所有重操作必须脚本化** — Agent 不做 font parsing、glyph transform、file IO heavy ops
2. **Agent 只做"决策树"**：
   ```
   if unicode conflict:
       assign PUA
   if glyph duplicate:
       merge sources
   if geometry mismatch:
       rename variant
   ```
3. **所有状态必须持久化** — registry.json、hash_index.json、manifest.json
4. **每一步必须可回滚** — snapshot_before_phase_X/

---

## 四、核心数据模型

### Glyph Canonical Model

```json
{
  "glyphHash": "sha256(contours)",
  "unicode": "e601",
  "name": "home",
  "aliases": ["house", "index"],
  "sources": ["A", "B"],
  "sourceUrls": [],
  "metrics": {
    "advanceWidth": 1024,
    "lsb": 0
  },
  "isComposite": false,
  "contours": "canonicalized_data"
}
```

---

## 五、核心算法设计

### 1. Glyph 规范化（最关键）

**目标**：同一个图形 → hash 必须一致

| 步骤 | 操作 |
|------|------|
| Step 1 | 展开 composite（只用于读取，不修改原 glyph，只展开"读取视图"） |
| Step 2 | 坐标归一化：`scale = BASE_UPM / source_UPM` |
| Step 3 | 精度统一：`round(x, 6)` |
| Step 4 | 轮廓标准化：起点统一（min x+y）、轮廓排序（bbox）、winding direction 统一（CW） |
| Step 5 | 序列化 hash：`glyphHash = sha256(canonical_contours)` |

### 2. 冲突检测系统

| 类型 | 定义 | 处理方式 |
|------|------|----------|
| **Type A: Unicode 冲突** | 同 unicode → 不同 glyphHash | 必须重新分配 unicode（PUA） |
| **Type B: Name 冲突** | 同 name → 不同 glyph | rename + alias |
| **Type C: Duplicate glyph** | 同 glyphHash → 多来源 | merge sources（正常情况） |

### 3. Unicode 分配策略

- **推荐区间**：`E000 - F8FF`（Private Use Area）
- **规则**：
  - 不覆盖历史 unicode
  - 只新增 mapping
  - 保留 alias

### 4. Direct Glyf Merge Engine

**禁止方式**：`SVG → TTF`

**正确方式**：`font["glyf"][glyphName] = deep_copy(glyph)`

必须同步的 Table：

| Table | 操作 |
|-------|------|
| glyf | copy |
| cmap | rebuild |
| hmtx | normalize |
| head | recalc |
| maxp | auto |
| loca | auto |

### 5. Metrics Normalize

```
BASE_UPM = 1024
transform: glyph.scale(BASE_UPM / source_UPM)
统一字段: advanceWidth, lsb, ascent/descent
```

### 6. Composite Glyph 策略

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **Mode A（推荐）** | 保留 composite | 最无损、最稳定、文件更小 |
| **Mode B（fallback）** | flatten composite | 跨 font dependency、broken reference |

### 7. Hinting 策略

**结论**：Web iconfont → hinting ≈ 可丢弃

**推荐策略**：删除所有 hinting tables（fpgm、prep、cvt）

### 8. Deterministic Build（企业级必须）

**目标**：同输入 = 同输出

必须保证：glyph sort、table order fixed、unicode stable、timestamp removed

### 9. Render Validation（最终保险）

**方法**：Playwright + screenshot diff（Chrome vs Firefox）

**判断**：`pixel diff == 0 → OK`

---

## 六、完整 Pipeline 执行流程

```
01 ingest sources
    ↓
02 normalize glyphs
    ↓
03 build glyph registry
    ↓
04 detect conflicts
    ↓
05 resolve unicode/name conflicts
    ↓
06 build glyph hash index
    ↓
07 direct glyf merge
    ↓
08 metrics normalize
    ↓
09 build TTF
    ↓
10 generate WOFF2
    ↓
11 render validation
    ↓
12 generate manifest
```

---

## 七、最终输出资产

```
iconfont.ttf
iconfont.woff2
iconfont.css
iconfont.json
manifest.json
conflict_report.md
render_diff.png
```

---

## 八、真实风险边界

### ❗ 仍然无法做到的"绝对无损"

| 项目 | 是否可能 |
|------|----------|
| binary byte-level identical | ❌ 不可能 |
| hinting 完整保留 | ⚠️ 基本不用 |
| glyph order 完全一致 | ❌ merge 必变 |

### ✅ 可以保证的

- 视觉完全一致
- glyph geometry 无损
- unicode 稳定
- 多源可追溯
- 浏览器一致渲染

---

## 九、溯源数据链模型

> 整个 pipeline 的核心是 **一条可回溯的数据链**。Phase 7 做 rename/alias 替换时，必须能回答：
> "这个 glyph 从哪个项目的哪个 CSS 来的？那个 CSS 对应的 TTF 是什么？项目里原来的模板变量是什么？"

### 数据模型

```
Phase 1 产出 ──────────────────────────────────────────────────
│
│  CSS_URL_RECORD
│  {
│    cssUrl:          "https://res.winbaoxian.com/ali-iconfont/font_123_xxx.css",
│    sourceProjects:  ["ai-customer-acquisition", "business-tool"],
│    templateVar:     "<%= htmlWebpackPlugin.options.iconfontPath %>/font_123_xxx.css",
│    templateVarRaw:  "<%= htmlWebpackPlugin.options.iconfontPath %>",
│    cdnDomain:       "res.winbaoxian.com"
│  }
│
└──────┬───────────────────────────────────────────────────────
       │ cssUrl（Phase 2 消费）
       ▼
Phase 2 产出 ──────────────────────────────────────────────────
│
│  ASSET_RECORD（溯源锚点，整个链的核心 ID）
│  {
│    assetId:         sha256(cssUrl)[0:12],      // 如 "a1b2c3d4e5f6"
│    cssUrl:          "https://.../font_123_xxx.css",
│    cssPath:         "sources/a1b2c3d4e5f6/iconfont.css",
│    cssContentHash:  sha256(css_content),         // CSS 内容指纹
│    fontUrl:         "https://.../font_123_xxx.ttf",  // 从 @font-face 解析
│    ttfPath:         "sources/a1b2c3d4e5f6/font.ttf",
│    ttfContentHash:  sha256(ttf_content),         // TTF 内容指纹
│    sourceProjects:  ["ai-customer-acquisition", "business-tool"],
│    templateVar:     "...（Phase 1 传递）...",
│    downloadStatus:  "ok" | "css_404" | "ttf_404" | "no_ttf_url",
│    iconMappings:    [                            // CSS 中 .icon-xxx:before 映射
│      { name: "home", unicode: "e601" },
│      { name: "user", unicode: "e602" }
│    ]
│  }
│
│  assets_manifest.json  =  [AssetRecord, ...]
│
└──────┬───────────────────────────────────────────────────────
       │ assetId（Phase 3 消费）
       ▼
Phase 3-4 产出 ────────────────────────────────────────────────
│
│  GLYPH_RECORD
│  {
│    glyphHash:    sha256(canonical_contours),
│    assetId:      "a1b2c3d4e5f6",       // ← 指向 AssetRecord
│    unicode:      "e601",
│    name:         "home",
│    contours:     [...],
│    metrics:      { advanceWidth: 1024, lsb: 0 }
│  }
│
└──────┬───────────────────────────────────────────────────────
       │ glyphHash（Phase 5 消费）
       ▼
Phase 5 产出 ──────────────────────────────────────────────────
│
│  REGISTRY_ENTRY
│  {
│    glyphHash:    "sha256_xxx...",
│    unicode:      "e601",
│    name:         "home",
│    aliases:      ["house", "index"],
│    sources:      ["a1b2c3d4e5f6", "f6e5d4c3b2a1"],  // ← 多个 AssetId
│    sourceDetail: [
│      { assetId: "a1b2c3d4e5f6", projects: ["project-a"], originalUnicode: "e601" },
│      { assetId: "f6e5d4c3b2a1", projects: ["project-b"], originalUnicode: "e602" }
│    ]
│  }
│
└──────┬───────────────────────────────────────────────────────
       │ glyphHash（Phase 6-7 消费）
       ▼
Phase 6-7 产出 ────────────────────────────────────────────────
│
│  CONFLICT_RECORD
│  {
│    type:          "unicode_conflict" | "name_conflict" | "glyph_duplicate",
│    glyphHashes:   ["sha256_a", "sha256_b"],
│    resolution:    "assign_pua" | "rename" | "merge_alias",
│    newUnicode:    "e900",
│    newName:       "home_v2",
│    affectedAssets: ["a1b2c3d4e5f6"],
│    affectedProjects: [
│      { project: "project-a", templateVar: "...", oldName: "icon-home", newName: "icon-home-v2" }
│    ]
│  }
│
│  Phase 7 替换项目文件时，通过 affectedProjects → templateVar 还原模板变量形式
│
└──────┬───────────────────────────────────────────────────────
       │ glyphHash（Phase 8-9 消费）
       ▼
Phase 8-11 产出 ───────────────────────────────────────────────
│
│  FINAL_MANIFEST
│  {
│    glyphHash:    "sha256_xxx...",
│    finalUnicode: "e001",         // 合并后的 PUA
│    finalName:    "icon-home",
│    aliases:      ["house"],
│    sources:      [
│      { project: "project-a", cssUrl: "https://.../font_123.css", ttfPath: "sources/.../font.ttf" },
│      { project: "project-b", cssUrl: "https://.../font_456.css", ttfPath: "sources/.../font.ttf" }
│    ]
│  }
│
│  任意 glyph 都能溯源到：项目名 → CSS URL → CSS 文件 → TTF 文件 → 原始 unicode
```

### 溯源查询路径

| 问题 | 查询路径 |
|------|----------|
| 这个 glyph 从哪来？ | glyphHash → Registry.sources → AssetRecord.sourceProjects |
| 这个项目的 iconfont 有哪些图标？ | CSS URL → AssetRecord.iconMappings |
| Phase 7 要替换哪个项目？ | ConflictRecord.affectedProjects → templateVar |
| 合并后的 font 里这个图标能还原吗？ | FINAL_MANIFEST.sources → cssUrl → ttfPath → 原始 TTF |
| 哪个 CSS 下载失败了？ | assets_manifest[].downloadStatus |

---

## 十、Phase 进度状态

> 状态说明：`⬜ 未开始` | `🟡 进行中` | `🟢 已完成` | `🔧 脚本已收集待迁移`

| Phase | 名称 | 状态 | 脚本 | 说明 |
|-------|------|------|------|------|
| Phase 0 | Task Planning | ⬜ 未开始 | — | Agent 生成 JSON pipeline plan |
| Phase 1 | Repo Discovery | 🟢 已完成 | `01_scan_repos_*.js` (3个) | 57仓库全扫描 + 20手动链接 → 111个CSS链接 |
| Phase 2 | Asset Resolver | 🟢 已完成 | `02_resolve_*.js` (3个) | 110/111 CSS下载 + 110 TTF下载 + 11494图标映射提取 |
| Phase 3 | Glyph Extraction | 🟢 已完成 | `03_extract_glyphs.py` + `03_validate_glyph_extraction.py` | fontTools 解析 TTF、110/110 + 11528 glyph 记录 |

> **扫描语义说明**：全程脚本覆盖扫描的是**"文本里存在的完整链接"**，而不是**"运行时最终生效的链接"**。
> webpack 模板变量（如 `<%= htmlWebpackPlugin.options.path %>`）在提取阶段做了文本替换以获取真实 CDN 路径，后续 Phase 7 替换项目中 iconfont 链接时，需**还原回模板变量形式**。
| Phase 4 | Geometry Normalization | 🟢 已完成 | `04_normalize_glyphs.py` + `test_04_normalize.py` | 11528 glyph 标准化 + 1345 唯一 glyphHash + numpy 加速 |
| Phase 5 | Glyph Hash Registry | ⬜ 待编写 | `05_build_registry.py` | 需使用 fontTools + sha256 |
| Phase 6 | Conflict Detection | 🔧 脚本已收集 | `06_detect_conflicts_*.js` (2个) | iconfont_compare.js + iconfont_conflicts_doc.js |
| Phase 7 | Conflict Resolution | 🔧 脚本已收集 | `07_resolve_conflicts_*.js` (4个) | apply_rename.js + apply_alias.js + cmp 测试脚本 |
| Phase 8 | Direct Glyf Merge | ⬜ 待编写 | `08_merge_glyf.py` | 核心合并引擎，fontTools |
| Phase 9 | Font Build | ⬜ 待编写 | `09_build_font.py` | TTF/WOFF2 生成 |
| Phase 10 | Validation | ⬜ 待编写 | `10_validate_render.js` | Playwright + pixelmatch |
| Phase 11 | Output & Manifest | 🔧 脚本已收集 | `11_generate_manifest_gen_demo.js` (1个) | gen_merged_demo.js |

**脚本统计**：已完成 Phase 1 (3个) + Phase 2 (3个) + Phase 3 (2个) + Phase 4 (2个) / 已收集 6 个 / 待编写 3 个 / 共 17 个

详细脚本清单见 `script.md`。

---

## 十一、Phase 2 脚本详细计划

见独立文件 `plan_phase2.md`。包含 3 个脚本的职责/输入/流程/输出定义。

---

## 十二、下一步升级路径

1. **MCP Agent Tool Schema**（可直接接 Claude / Qwen）
2. **自动 CI 字体发布系统**（npm + CDN）
3. **icon 语义识别**（AI 自动分类 icon）