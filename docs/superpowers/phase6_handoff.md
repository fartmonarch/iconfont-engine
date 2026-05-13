# Phase 6 核心技术文档 — 冲突检测

> 本文档记录 Phase 6 的核心算法细节、数据结构约定、Phase 7 对接点。
> 目的：确保后续 Phase 7 开发时无需回看代码就能理解 Phase 6 的输出格式和保证条件。

---

## 1. 输入 / 输出

### 1.1 输入

| 文件 | 大小 | 说明 |
|------|------|------|
| `registry/glyph_registry.json` | ~9 MB | 1,346 条 Phase 5 注册表 entry |

### 1.2 输出

| 文件 | 大小 | 说明 |
|------|------|------|
| `report/conflict_records.json` | ~2 MB | 结构化冲突数据（Phase 7 直接消费） |
| `report/conflict_report.md` | ~200 KB | 人类可读分级报告 |
| `report/phase6_conflict_preview.html` | ~146 KB | 可视化决策面板（辅助参考） |

### 1.3 脚本

| 文件 | 说明 |
|------|------|
| `pipeline/06_detect_conflicts.py` | 主脚本：8 个核心函数 |
| `pipeline/test_06_conflicts.py` | 16 个单元测试 |

---

## 2. conflict_records.json 数据结构

### 顶层格式

```json
{
  "metadata": {
    "generatedAt": "2026-05-13T10:01:55.675491+00:00",
    "total_conflicts": 1698,
    "by_type": {
      "glyph_duplicate": 905,
      "unicode_conflict": 401,
      "name_conflict": 392
    },
    "by_severity": {
      "critical": 592,
      "warning": 509,
      "info": 597
    }
  },
  "records": [CONFLICT_RECORD, ...]
}
```

### CONFLICT_RECORD 格式

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

### records 排序规则

records 数组按 `(severity_order, key)` 排序：
- severity_order: critical=0, warning=1, info=2
- 同 severity 内按 key 字母序

---

## 3. 三类冲突定义

| 类型 | 检测条件 | resolution_hint | Phase 7 操作 |
|------|---------|----------------|-------------|
| **Type A: Unicode 冲突** | 同一 `canonicalUnicodeHex` → 多个不同 `glyphHash` | `assign_pua` | 分配新 PUA 码位 |
| **Type B: Name 冲突** | 同一 `canonicalName` → 多个不同 `glyphHash` | `rename` | rename + alias 合并 |
| **Type C: Duplicate Glyph** | 同一 entry 的 `len(sources) > 1` | `merge_alias` | merge sources（正常情况） |

---

## 4. 严重性分级

| 级别 | 条件 | Phase 7 处理优先级 |
|------|------|------------------|
| **critical** | 变体数 >= 5 | 最高优先级 |
| **warning** | 变体数 3-4 | 中等优先级 |
| **info** | 变体数 = 2 | 低优先级 |

---

## 5. 统计事实

| 指标 | 值 |
|------|-----|
| 总冲突数 | 1,698 |
| Unicode 冲突 | 401（Critical 12 / Warning 195 / Info 194） |
| Name 冲突 | 392（Critical 11 / Warning 155 / Info 226） |
| Duplicate Glyph | 905（Critical 569 / Warning 159 / Info 177） |

### Top Unicode 冲突（Type A Critical）

| Unicode | 变体数 | 说明 |
|---------|--------|------|
| U+E6B5 | 6 | icon-arrows_right 有 6 种不同字形 |
| U+E6B7 | 5 | 5 种不同字形 |
| U+E6C6 | 5 | 5 种不同字形 |
| U+E6CB | 5 | 5 种不同字形 |
| U+E6EC | 5 | 5 种不同字形 |

### Top Name 冲突（Type B Critical）

| Name | 变体数 | 说明 |
|------|--------|------|
| icon-arrows_right | 6 | 同名 6 种字形 |
| icon-wechat_surface | 6 | 同名 6 种字形 |
| icon-close_line | 5 | 同名 5 种字形 |

---

## 6. Phase 7 对接点

### 6.1 Phase 7 读取什么

```python
# Phase 7 需要读取的唯一文件
with open('report/conflict_records.json') as f:
    data = json.load(f)

records = data['records']  # list of CONFLICT_RECORD
```

### 6.2 Phase 7 处理顺序

1. 按 severity 遍历 records（critical → warning → info）
2. Type A (`unicode_conflict`): 为每个 variant 分配新的 PUA 码位（从 E000 起递增）
3. Type B (`name_conflict`): 为每个 variant 生成新 name + alias
4. Type C (`glyph_duplicate`): 标记 merge，无需额外操作

### 6.3 Phase 7 需要额外读取的数据

```python
# Phase 7 还需要这些文件来执行 rename/alias 替换
with open('registry/glyph_registry.json') as f:
    registry = json.load(f)  # 完整的 glyph 数据

with open('sources/meta/assets_manifest.json') as f:
    assets = json.load(f)  # assetId → sourceProjects, cssUrl, ttfPath

with open('sources/meta/css_mappings.json') as f:
    css_mappings = json.load(f)  # 用于项目文件中的 icon 类名替换
```

### 6.4 Phase 7 预期产出

- `report/lineage.json` 更新（记录 PUA 分配和 rename 历史）
- `registry/glyph_registry.json` 更新（添加 finalUnicode/finalName）
- 前端项目文件替换（iconfont CSS 链接更新、icon class 替换）

---

## 7. 运行方式

```bash
# 重跑 Phase 6
python pipeline/06_detect_conflicts.py

# 运行测试
python pipeline/test_06_conflicts.py

# 验证输出
python -c "
import json
with open('report/conflict_records.json') as f:
    d = json.load(f)
print(f'Total conflicts: {d[\"metadata\"][\"total_conflicts\"]}')
print(f'By type: {d[\"metadata\"][\"by_type\"]}')
print(f'By severity: {d[\"metadata\"][\"by_severity\"]}')
"
```

---

## 8. 测试覆盖

| 函数 | 测试数 | 覆盖 |
|------|--------|------|
| `detect_unicode_conflicts` | 4 | 基本冲突 / 无冲突 / 同 hash / null unicode |
| `detect_name_conflicts` | 3 | 基本冲突 / null name / 同 hash |
| `detect_duplicate_glyphs` | 3 | 基本检测 / 单来源 / 严重性分级 |
| `classify_severity` | 1 | 全部分级阈值 |
| `build_conflict_records` | 2 | 三类整合 / 必需字段 |
| `generate_records_json` | 1 | 输出格式 + metadata |
| `generate_report_md` | 1 | Markdown 结构 |
| `test_deterministic_output` | 1 | 多次运行输出一致 |
| **总计** | **16** | **100% 核心函数** |
