# Pipeline 优化方案

## 问题分析

### 问题 1: 假阳性冲突 (1,698 条冲突中大量误判)

**根本原因：**
- Phase 4 的 `round(6)` 精度过高，导致几何相近但坐标有微小差异的 glyph 被判定为不同
- Phase 5 的 glyphHash 是基于精确 contours 的 SHA-256，没有任何容差机制
- 同一图标在不同 asset 中可能因设计师微调、导出工具差异等产生坐标微小变化

**影响：**
- 大量假阳性冲突进入 Phase 6-7，被分配了不必要的 PUA 码位
- 导致最终的 `icon-arrows_right_v1` 到 `v6` 这种情况（实际可能是同一图标的微小变体）
- 增加了合并后字体的体积和使用复杂度

### 问题 2: 替换链接的潜在风险

**当前数据流：**
```
原始项目 CSS URL → assetId → glyphHash → finalUnicode/finalName → 新 CSS
```

**替换时可能出现的问题：**

1. **图标变了**
   - 原因：假阳性冲突导致同一视觉图标被分配了不同 glyphHash
   - 例：`icon-arrows_right` 在原项目用 `U+E6B5`，替换后用 `U+E001`，但 glyph 可能略有不同
   - 风险：用户看到图标样式改变

2. **图标显示不出来**
   - 原因：finalName 命名规则不一致（如 `icon-arrows_right_v2` vs 原来的 `icon-arrow`）
   - 原因：CSS class 名变化但项目代码未同步更新
   - 风险：`class="icon-arrow"` 找不到对应的 `.icon-icon-arrows_right_v2:before`

3. **位置偏移/大小变化**
   - 原因：advanceWidth/lsb 在 UPM 缩放后的精度损失
   - 原因：不同 asset 的原始 metrics 差异未完全消除
   - 风险：图标对齐问题

4. **溯源断裂**
   - 当前 `lineage.json` 只记录了来源，没有记录"替换指导信息"
   - 缺少：旧 CSS URL → 新 CSS URL 的映射
   - 缺少：旧 class 名 → 新 class 名的映射
   - 缺少：模板变量还原规则

### 问题 3: Phase 7 人工审核待完善

**现状：**
- 当前 Phase 7 的 `conflict_resolver.html` UI 已生成，但审核导出的 JSON 格式不完整
- 审核 JSON 只记录了 `keep/pua` 决策，缺少上下文信息

**需要的完整审核 JSON 应包含：**
1. **溯源信息**：该冲突涉及哪些原始 CSS URL、哪些 project
2. **最终 TTF 中的实际字形预览**：合并后字体里对应位置实际渲染的是什么图标
3. **使用位置**：这个图标在哪些代码文件的哪些位置被用到（来自 Task 3 扫描结果）

**优先级说明：** 先完成 Task 1-2（减少冲突数量），再同步完善 Phase 7 审核 UI。因为：
- 假阳性冲突减少后，需要人工审核的条目数量会显著降低
- 审核 UI 的数据结构依赖 Task 4（完整溯源链）和 Task 3（扫描使用位置）的输出
- 所以 Phase 7 审核优化 = Task 6，排在 Task 3-5 之后

---

## 优化方案

### Task 1: 降低 glyphHash 精度阈值 (Phase 4 优化) — 🟢 已完成

**目标：** 将 round(6) 改为 round(4)，允许更大的坐标容差

**文件修改：**
- `pipeline/04_normalize_glyphs.py`
  - `round_contours()` 函数，`decimals=6` → `decimals=4`

**验证结果：**
- 重新运行 Phase 4-6，unique glyphHash 从 1345 → 1062
- 冲突数量从 1,698 → 1,698（round(4) 对冲突数影响有限）
- **结论**：round(4) 不是冲突减少的主要原因，视觉相似度过滤才是关键

**风险：**
- 降低精度可能将真正不同的图标误判为相同
- 已通过视觉相似度过滤的 minScore 阈值兜底

---

### Task 2: 视觉相似度过滤层 (Phase 6.5 新增) — 🟢 已完成

**目标：** 在冲突检测后、解决前，增加一步"视觉相似度过滤"，将看起来相同的图标自动合并

**新文件：**
- `pipeline/_visual_similarity.js` — 像素渲染比对引擎
- `pipeline/06_5_filter_false_positives.py` — 假阳性过滤主脚本

**算法设计（已实现）：**
```javascript
// 1. 使用 @napi-rs/canvas 将 TrueType contours 渲染为 64x64 bitmap
// 2. 比较两个 bitmap 的像素重叠率
function comparePixels(imgA, imgB) {
    let same = 0;
    for (let i = 0; i < dataA.length; i += 4) {
        const a = dataA[i + 3] > 50;  // alpha > 50
        const b = dataB[i + 3] > 50;
        if (a === b) same++;
    }
    return same / total;
}
```

**判断逻辑（关键修正）：**
- ~~原方案：maxScore（任意一对相似就全合并）~~
- **现方案：minScore（所有 pair 都相似才合并）**

**工作流程：**
1. 读取 `report/conflict_records.json`
2. 对每个 Type A/B 冲突，渲染所有 variants 为 bitmap
3. 计算所有 pair 的像素重叠率，取 **minScore**
4. 如果 minScore >= 0.90，标记为 `false_positive`
5. 输出 `report/filtered_conflicts.json`（Phase 7 消费）

**实际结果（2026-05-14）：**
- 793 个 Type A/B 冲突记录
- 自动合并：**528** 个（minScore >= 0.90）
- 仍需人工决策：**265** 个
- 典型修复：U+E720（4 个客服耳机 + 1 个微信气泡）不再被错误合并

---

### Task 3: 扫描旧仓库图标使用位置 (新增 Phase 12) — 🟢 已完成

**目标：** 在做任何替换前，先扫描所有旧仓库的源码，找出每个图标类名在哪些文件的哪些位置被使用

**背景：** 当前 lineage.json 只记录了"图标来自哪个 asset/项目"，但不知道项目里具体哪个文件哪一行用了这个图标。自动化替换必须先有这份精准的使用位置索引。

**新文件：**
- `pipeline/12_scan_icon_usage.js`（Node.js 实现，与 Phase 1 保持技术栈一致）

**实际结果：**
- 扫描 57 个项目，16,698 个文件，11,340 处 icon 用法
- 输出 `report/icon_usage_index.json`

**扫描策略：**
- 目标目录：Phase 1 扫描过的各项目仓库（`git clone` 到本地的路径）
- 扫描文件类型：`*.vue`, `*.html`, `*.js`, `*.jsx`, `*.ts`, `*.tsx`
- 扫描内容：
  1. **class 属性中的图标类名**：`class="icon-arrow"`, `:class="'icon-help'"`, `:class="{ 'icon-home': true }"`
  2. **CSS 文件中的 iconfont 引用**：`<link>` 标签 / `import` / `@import` 中的 CSS URL
  3. **模板字符串**：`` `icon-${name}` `` 这类动态用法（标记为 dynamic，无法自动替换）

**输出数据结构：**
```json
{
  "generatedAt": "...",
  "totalFiles": 3420,
  "totalUsages": 18540,
  "projects": {
    "business-tool": {
      "cssLinks": [
        {
          "file": "src/index.html",
          "line": 12,
          "rawHtml": "<link rel='stylesheet' href='<%= iconfontPath %>/font_123.css'>",
          "resolvedUrl": "https://res.winbaoxian.com/ali-iconfont/font_123.css",
          "assetId": "cf6e3630a212",
          "templateVar": "<%= iconfontPath %>"
        }
      ],
      "iconUsages": [
        {
          "iconName": "icon-arrow",
          "usages": [
            {
              "file": "src/components/Header.vue",
              "line": 45,
              "column": 12,
              "context": "<i class=\"icon-arrow\"></i>",
              "usageType": "static_class",
              "canAutoReplace": true
            },
            {
              "file": "src/utils/icon.js",
              "line": 8,
              "context": "`icon-${iconName}`",
              "usageType": "dynamic_class",
              "canAutoReplace": false
            }
          ]
        }
      ]
    }
  }
}
```

**输出文件：**
- `report/icon_usage_index.json` — 完整的使用位置索引

**关键边界处理：**
- 动态拼接的图标名（`canAutoReplace: false`）仅标记，不自动替换
- 同一文件被多个 project 共享时去重
- 记录所有 CSS `@import` / `link` 标签以便替换 iconfont 引用

---

### Task 4: 增强溯源链 (lineage.json 扩展) — 🟢 已完成

**目标：** 将 Task 3 扫描结果与现有 lineage 数据合并，形成完整的"图标 → 原始 asset → 代码使用位置 → 最终替换方案"溯源链

**新文件：**
- `pipeline/13_enhance_lineage.py`

**实际结果：**
- 输出 `registry/lineage_resolved.json`
- 每个 glyph 包含完整的 replacement 信息（newName/newUnicode/nameChanged/unicodeChanged）

**当前 lineage.json 结构（仅有来源信息）：**
```json
{
  "glyphHash": "...",
  "canonicalName": "icon-arrow",
  "sources": [{"assetId": "...", "projects": [...], "cssUrl": "..."}]
}
```

**增强后的完整溯源链结构：**
```json
{
  "glyphHash": "1d721ec1b0181ac1",
  "canonicalName": "icon-arrow",
  "aliases": ["icon-arrows_right"],

  "sources": [
    {
      "assetId": "cf6e3630a212",
      "projects": ["business-tool"],
      "cssUrl": "https://res.winbaoxian.com/ali-iconfont/font_123.css",
      "originalUnicode": "E6B5",
      "ttfPath": "sources/phase2_assets/cf6e3630a212/font.ttf"
    }
  ],

  "usages": {
    "business-tool": {
      "cssLinkFiles": [
        {
          "file": "src/index.html",
          "line": 12,
          "templateVar": "<%= iconfontPath %>",
          "canAutoReplace": true
        }
      ],
      "iconUsageFiles": [
        {
          "file": "src/components/Header.vue",
          "line": 45,
          "iconName": "icon-arrow",
          "canAutoReplace": true
        },
        {
          "file": "src/utils/icon.js",
          "line": 8,
          "iconName": "dynamic",
          "canAutoReplace": false,
          "note": "动态拼接，需人工确认"
        }
      ]
    }
  },

  "replacement": {
    "newUnicode": "E000",
    "newName": "icon-icon-arrows_right_v1",
    "newCssUrl": "iconfont_merged.css",
    "nameChanged": true,
    "unicodeChanged": true,
    "oldNames": ["icon-arrow", "icon-arrows_right"],
    "autoReplaceReady": true,
    "manualCheckRequired": ["src/utils/icon.js 第8行：动态拼接无法自动替换"]
  },

  "versionHistory": [
    {"phase": "phase4", "unicode": "E6B5", "name": "icon-arrow", "glyphHash": "original"},
    {"phase": "phase7", "unicode": "E000", "name": "icon-icon-arrows_right_v1", "changeReason": "unicode_conflict"}
  ]
}
```

**文件修改：**
- `pipeline/05_build_registry.py`
  - `build_lineage()` 增加 `replacement` 字段框架（Phase 7 后填充）
  
- `pipeline/07_resolve_conflicts.py`
  - 解决冲突后写入 `versionHistory` 和 `replacement` 字段
  - 输出 `registry/lineage_resolved.json`（不覆盖原 lineage.json）

- `pipeline/12_scan_icon_usage.js` (Task 3 产出)
  - 扫描后写入每个 glyph 的 `usages` 字段
  - 输出 `registry/lineage_with_usages.json`

---

### Task 5: 生成自动化替换脚本 + 替换指导报告 — 🟢 已完成

**目标：** 基于完整溯源链，为每个 project 生成可直接执行的替换脚本和人工确认清单

**新文件：**
- `pipeline/14_generate_replacer.js`（生成替换脚本和 Markdown 报告）

**实际结果：**
- 为 27 个项目生成替换脚本 `output/replacers/<project>_replace.js`
- 生成替换指导报告 `output/replacers/<project>_report.md`

**输出两类文件：**

**1. 自动替换脚本** `output/replacers/<project_name>_replace.js`
```javascript
// business-tool 自动替换脚本（生成后需人工审查再执行）
const replacements = [
  // CSS 链接替换
  {
    file: "src/index.html",
    line: 12,
    from: "<link rel='stylesheet' href='<%= iconfontPath %>/font_123.css'>",
    to:   "<link rel='stylesheet' href='<%= iconfontPath %>/iconfont_merged.css'>",
    type: "css_link"
  },
  // 图标类名替换
  {
    file: "src/components/Header.vue",
    line: 45,
    from: "icon-arrow",
    to:   "icon-icon-arrows_right_v1",
    type: "icon_class"
  }
];
// ... 执行替换逻辑
```

**2. 替换指导报告** `report/replacement_guides/<project_name>.md`
```markdown
# business-tool 图标替换指南

## 摘要
- 可自动替换：142 处
- 需人工确认：8 处（动态拼接）
- CSS 链接替换：5 处

## 需人工确认项

| 文件              | 行号 | 原因                    | 建议                   |
| ----------------- | ---- | ----------------------- | ---------------------- |
| src/utils/icon.js | 8    | 动态拼接 `icon-${name}` | 检查 name 变量的值范围 |

## 图标名变更清单
| 旧名称     | 新名称                    | Unicode 变化 | 视觉验证     |
| ---------- | ------------------------- | ------------ | ------------ |
| icon-arrow | icon-icon-arrows_right_v1 | E6B5→E000    | pixel diff=0 |
```

---

### Task 6: 重建 Phase 7 人工审核 UI + 导出 JSON (与 Task 5 同步) — 🟡 进行中

**依赖：** Task 3 (icon_usage_index.json) + Task 4 (lineage_with_usages.json) + 当前 merge_manifest.json

**目标：** 重建审核 UI 和导出 JSON，让审核人员能基于完整上下文做决策，导出的 JSON 能直接驱动 Task 5 的替换脚本

**已完成的增强：**
- `pipeline/07_generate_resolver_ui.py` 支持 false_positive 标注/筛选/排序
- `pipeline/15_rebuild_resolver_data.py` 重建审核 UI 数据源
- SVG 孔洞渲染修复（evenodd fill-rule 跨 contour 生效）
- 进度条显示 Auto-merged / Pending / Resolved 三态
- 卡片排序：Pending 在前，Auto-Merged 在后

**待完成：**
- 265 个 pending 冲突需在审核 UI 中人工决策（keep/PUA）
- 导出 decisions.json 后驱动替换脚本

**新的审核 UI 数据结构（conflict_resolver_data.json）：**
```json
{
  "conflictRecord": {
    "key": "U+E6B5",
    "type": "unicode_conflict",
    "severity": "critical"
  },
  "variants": [
    {
      "glyphHash": "1d721ec1b0181ac1",
      "previewUnicode": "E000",    // 当前分配的 PUA，供 TTF 预览用
      "sources": [...],            // 来自 lineage
      "usages": {                  // 来自 icon_usage_index.json
        "business-tool": {
          "staticCount": 12,       // 可自动替换的用法数
          "dynamicCount": 2,       // 需人工确认的用法数
          "files": ["src/Header.vue:45", "src/utils/icon.js:8"]
        }
      },
      "inFinalTTF": true,          // 该 glyph 是否在最终合并 TTF 中
      "finalTTFGlyphName": "icon-icon-arrows_right_v1"  // TTF 中的实际名称
    }
  ],
  "decision": null   // 待审核时为 null，审核后填写 "keep_v1" / "merge_all" / "pua_all"
}
```

**审核 UI 展示内容（对比当前）：**

| 当前                          | 优化后                                                |
| ----------------------------- | ----------------------------------------------------- |
| 只显示 glyphHash 和来源 asset | 新增：使用位置（哪个项目哪个文件）                    |
| 无字形预览                    | 新增：从合并后 TTF 渲染预览图（基于 finalUnicode）    |
| 导出 JSON 只有 keep/pua 决策  | 新增：decision 字段关联溯源链，可驱动 Task 5 替换脚本 |

**导出 JSON 格式（审核完成后）：**
```json
{
  "decisions": {
    "U+E6B5": {
      "action": "keep_v2",           // 选择保留哪个 variant
      "keptGlyphHash": "40d905e65af0eff7",
      "mergeIntoName": "icon-arrow", // 统一使用这个名字
      "reason": "视觉最接近原版"
    }
  },
  "exportedAt": "...",
  "readyForReplacement": true        // 标志位：Task 5 替换脚本可消费
}
```

---

## 执行顺序（实际执行）

```
[第一阶段：减少冲突]
Task 1 (Phase 4 精度调整: round 6→4) — ✅ 已完成
    ↓
重新运行 Phase 4 → 5 → 6
    ↓
Task 2 (Phase 6.5: 视觉相似度过滤假阳性) — ✅ 已完成
    ↓
重新运行 Phase 6.5 → 7 → 8 → 11
    ↓
[结果: 528 自动合并, 265 待决策, PUA 从 2109 降至 213]

[第二阶段：溯源链 + 使用位置]
Task 3 (Phase 12: 扫描旧仓库图标使用位置) — ✅ 已完成
    ↓  [输出: report/icon_usage_index.json]
Task 4 (增强溯源链) — ✅ 已完成
    ↓  [输出: registry/lineage_resolved.json]

[第三阶段：替换脚本 + 审核 UI]
Task 5 (Phase 14: 生成自动替换脚本) — ✅ 已完成
    ↓  [输出: output/replacers/]
Task 6 (Phase 7 审核 UI 增强) — 🟡 进行中
    ↓  [265 个 pending 冲突待人工决策]
Phase 10 验证 (pixel diff 确认视觉一致性)
```

---

## 验证标准（实际结果）

| 指标             | 目标                 | 实际                                 | 状态       |
| ---------------- | -------------------- | ------------------------------------ | ---------- |
| **假阳性减少率** | 冲突 < 500           | 528 自动合并 + 265 待决策            | ✅ 基本达成 |
| **视觉一致性**   | pixel diff = 0 > 99% | 待 Phase 10 验证                     | ⬜ 未执行   |
| **扫描覆盖率**   | 57 仓库全覆盖        | 16,698 文件 / 11,340 处用法          | ✅ 达成     |
| **溯源完整性**   | glyphHash → 文件行号 | lineage_resolved.json 含 replacement | ✅ 达成     |
| **替换安全性**   | canAutoReplace 标记  | 替换脚本含标记 + Markdown 报告       | ✅ 达成     |

---

## 风险与回滚

**风险：**
- Task 1 降低精度可能导致真正不同的图标被误合并
- Task 2 的相似度阈值需要调优（0.9 可能过高或过低）
- Task 3 扫描动态用法时存在漏扫（如运行时动态添加的 class）

**回滚方案：**
- 保留当前的 `normalized_glyphs.json` 和 `glyph_registry.json` 备份
- Task 1-2 的输出写入新文件，不覆盖原文件
- Phase 10 验证失败时，恢复到 round(6) 精度
- Task 3 扫描结果为只读分析，不修改任何源码

---

## 预期收益 vs 实际结果

| 收益项               | 预期             | 实际（2026-05-14）           | 状态     |
| -------------------- | ---------------- | ---------------------------- | -------- |
| **减少冲突数量**     | 1,698 → ~300-500 | 528 自动合并 + 265 待决策    | ✅ 超预期 |
| **减少 PUA 分配**    | 2,109 → ~500-800 | 2,109 → **213**              | ✅ 超预期 |
| **最终 glyph 数**    | —                | 1,269 → **1,062**            | ✅ 达成   |
| **自动化替换覆盖率** | ~85% 静态 class  | 27 个项目替换脚本已生成      | ✅ 达成   |
| **安全性**           | 全链路溯源       | glyphHash → asset → 代码行号 | ✅ 达成   |
