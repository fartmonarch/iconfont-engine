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
│ 脚本：02_resolve_iconfont_links.js                          │
│ 任务：                                                     │
│   ---> CSS URL解析                                           │
│   ---> 提取 TTF 链接                                         │
│   ---> 下载 font.ttf / font.css                             │
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
│ Phase 4: Geometry Normalization（几何标准化）               │
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
├── sources/                  # 原始多 iconfont 输入
│   ├── A/
│   ├── B/
│   ├── C/
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

## 九、Phase 进度状态

> 状态说明：`⬜ 未开始` | `🟡 进行中` | `🟢 已完成` | `🔧 脚本已收集待迁移`

| Phase | 名称 | 状态 | 脚本 | 说明 |
|-------|------|------|------|------|
| Phase 0 | Task Planning | ⬜ 未开始 | — | Agent 生成 JSON pipeline plan |
| Phase 1 | Repo Discovery | 🟢 已完成 | `01_scan_repos_*.js` (3个) | 57仓库全扫描 + 20手动链接 → 111个CSS链接 |

> **扫描语义说明**：全程脚本覆盖扫描的是**"文本里存在的完整链接"**，而不是**"运行时最终生效的链接"**。
> webpack 模板变量（如 `<%= htmlWebpackPlugin.options.path %>`）在提取阶段做了文本替换以获取真实 CDN 路径，后续 Phase 7 替换项目中 iconfont 链接时，需**还原回模板变量形式**。
| Phase 2 | Asset Resolver | 🔧 脚本已收集 | `02_resolve_iconfont_links_*.js` (2个) | build_superset.js + iconfont_file_compare.js |
| Phase 3 | Glyph Extraction | ⬜ 待编写 | `03_extract_glyphs.py` | 需使用 fontTools |
| Phase 4 | Geometry Normalization | ⬜ 待编写 | `04_normalize_glyphs.py` | 需使用 fontTools + numpy |
| Phase 5 | Glyph Hash Registry | ⬜ 待编写 | `05_build_registry.py` | 需使用 fontTools + sha256 |
| Phase 6 | Conflict Detection | 🔧 脚本已收集 | `06_detect_conflicts_*.js` (2个) | iconfont_compare.js + iconfont_conflicts_doc.js |
| Phase 7 | Conflict Resolution | 🔧 脚本已收集 | `07_resolve_conflicts_*.js` (4个) | apply_rename.js + apply_alias.js + cmp 测试脚本 |
| Phase 8 | Direct Glyf Merge | ⬜ 待编写 | `08_merge_glyf.py` | 核心合并引擎，fontTools |
| Phase 9 | Font Build | ⬜ 待编写 | `09_build_font.py` | TTF/WOFF2 生成 |
| Phase 10 | Validation | ⬜ 待编写 | `10_validate_render.js` | Playwright + pixelmatch |
| Phase 11 | Output & Manifest | 🔧 脚本已收集 | `11_generate_manifest_gen_demo.js` (1个) | gen_merged_demo.js |

**脚本统计**：已收集 9 个 / 已完成 Phase 1 (3个脚本) / 待编写 6 个 / 共 18 个

详细脚本清单见 `script.md`。

---

## 十、下一步升级路径

1. **MCP Agent Tool Schema**（可直接接 Claude / Qwen）
2. **自动 CI 字体发布系统**（npm + CDN）
3. **icon 语义识别**（AI 自动分类 icon）