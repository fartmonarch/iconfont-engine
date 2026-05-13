# Phase 6 冲突检测设计文档

> 创建日期: 2026-05-13
> 状态: 已批准，待实现

## Context

Phase 5 已完成 Glyph Hash Registry，产出 1,346 条 entry。经初步分析发现：
- **401 个 Unicode 冲突**（同一 unicode 码位对应多个不同 glyphHash）
- **392 个 Name 冲突**（同一 iconName 对应多个不同 glyphHash）
- **905 个 Duplicate Glyph**（同一 glyphHash 被多个 asset 共享，属正常合并）

Phase 6 需要在合并字体前，将这些冲突显式化、分级、生成可审计报告，为 Phase 7 冲突解决提供结构化数据。

## 用户决策

| 编号 | 问题 | 选择 |
|------|------|------|
| Q1 | 冲突检测范围 | **全部三种（Type A + B + C）** |
| Q2 | 报告输出形式 | **JSON + Markdown**（不生成 HTML） |
| Q3 | 严重性分级阈值 | **三级: Critical(5+) / Warning(3-4) / Info(2)** |
| Q4 | PUA 分配策略 | **按严重程度顺序分配**（Critical 先分配低 PUA） |
| Q5 | 脚本语言 | **Python**（与 Phase 3-5 保持一致） |

## 架构

```
registry/glyph_registry.json
    │
    ├─ detect_unicode_conflicts()  → 同 unicode → 不同 glyphHash → 401 个
    ├─ detect_name_conflicts()     → 同 name → 不同 glyphHash → 392 个
    └─ detect_duplicate_glyphs()   → 同 glyphHash → 多来源 → 905 个
    │
    ▼
classify_severity() → Critical(5+) / Warning(3-4) / Info(2)
    │
    ▼
build_conflict_records() → CONFLICT_RECORD 数据结构
    │
    ├─ generate_records_json()  → report/conflict_records.json
    └─ generate_report_md()     → report/conflict_report.md
```

## 组件设计

### 核心函数

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `load_registry()` | `registry/glyph_registry.json` | `list[dict]` | 加载注册表数据 |
| `detect_unicode_conflicts()` | registry entries | `list[dict]` | 按 `canonicalUnicodeHex` 分组，筛选 glyphHash > 1 的组 |
| `detect_name_conflicts()` | registry entries | `list[dict]` | 按 `canonicalName` 分组，筛选 glyphHash > 1 的组 |
| `detect_duplicate_glyphs()` | registry entries | `list[dict]` | 筛选 `len(sources) > 1` 的 entry |
| `classify_severity()` | variant count | `str` | 5+→critical, 3-4→warning, 2→info |
| `build_conflict_records()` | 三类冲突结果 | `list[CONFLICT_RECORD]` | 组装标准化数据结构 |
| `generate_records_json()` | conflict records | `report/conflict_records.json` | Phase 7 消费的结构化数据 |
| `generate_report_md()` | conflict records | `report/conflict_report.md` | 人类可读分级报告 |

### 数据模型

```json
{
  "type": "unicode_conflict" | "name_conflict" | "glyph_duplicate",
  "severity": "critical" | "warning" | "info",
  "key": "U+E6B5" | "icon-home" | "sha256_xxx",
  "variantCount": 6,
  "variants": [
    {
      "glyphHash": "sha256_xxx",
      "canonicalUnicodeHex": "E6B5",
      "canonicalName": "icon-arrows_right",
      "sources": [
        {"assetId": "xxx", "projects": ["project-a"], "cssUrl": "..."}
      ],
      "contours": [...],
      "advanceWidth": 1024
    }
  ],
  "affectedAssets": ["assetId1", "assetId2"],
  "affectedProjects": ["project-a", "project-b"],
  "resolution_hint": "assign_pua" | "rename" | "merge_alias"
}
```

## 冲突类型定义

| 类型 | 定义 | Resolution Hint |
|------|------|----------------|
| **Type A: Unicode 冲突** | 同一 `canonicalUnicodeHex` 对应多个不同 `glyphHash` | `assign_pua` |
| **Type B: Name 冲突** | 同一 `canonicalName` 对应多个不同 `glyphHash` | `rename` |
| **Type C: Duplicate Glyph** | 同一 `glyphHash` 对应多个 `sources` | `merge_alias` |

## 严重性分级

| 级别 | 条件 | 含义 |
|------|------|------|
| **Critical** | 变体数 >= 5 | 一个码位/名字对应 5+ 种不同字形，需优先处理 |
| **Warning** | 变体数 3-4 | 中等程度冲突 |
| **Info** | 变体数 = 2 | 轻度冲突 |

## 文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `pipeline/06_detect_conflicts.py` | 主脚本 | 检测 + 分级 + 输出 |
| `pipeline/test_06_conflicts.py` | 测试 | 覆盖 3 类检测 + 分级 + 输出格式 |
| `report/conflict_records.json` | 输出 | Phase 7 输入的结构化数据 |
| `report/conflict_report.md` | 输出 | 人类可读分级报告 |

## 报告格式 (Markdown)

```markdown
# Phase 6 冲突检测报告

## 统计总览
| 类型 | 总数 | Critical | Warning | Info |
|------|------|----------|---------|------|
| Unicode 冲突 | 401 | X | X | X |
| Name 冲突 | 392 | X | X | X |
| Duplicate Glyph | 905 | X | X | X |

## Critical 冲突

### Unicode: U+E6B5 (6 种变体)
| # | glyphHash | Name | Sources |
|---|-----------|------|---------|
| 1 | 99bf463e... | icon-arrows_right | business-tool, ... |
...

## Warning 冲突
...

## Info 冲突
...
```

## Phase 7 衔接

Phase 7 读取 `conflict_records.json`，按 severity 顺序处理：
1. **Critical → Warning → Info** 依次遍历
2. Type A → 分配 PUA 码位（E000 起递增）
3. Type B → rename + alias 合并
4. Type C → merge sources（仅记录）

## 验证方式

1. `python pipeline/06_detect_conflicts.py` — 正常运行，无报错
2. `python pipeline/test_06_conflicts.py` — 单元测试通过
3. 检查 `report/conflict_records.json` 存在且格式正确
4. 检查 `report/conflict_report.md` 可读，分级统计正确
5. 验证 Type A + B + C 总数与 registry 数据一致
