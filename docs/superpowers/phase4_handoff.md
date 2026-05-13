# Phase 4 核心技术文档 — 几何标准化

> 本文档记录 Phase 4 的核心算法细节、数据结构约定、性能基准和 Phase 5 对接点。
> 目的：确保后续 Phase 5 开发时无需回看代码就能理解 Phase 4 的输出格式和保证条件。

---

## 1. 输入 / 输出

### 1.1 输入

| 文件 | 大小 | 说明 |
|------|------|------|
| `sources/phase3_glyphs/raw_glyphs.json` | ~300MB | 11,528 条原始 glyph 记录（JSON 数组） |
| `sources/phase3_glyphs/extraction_summary.json` | ~20KB | 每个 asset 的 unitsPerEm 元数据 |

### 1.2 输出

| 文件 | 大小 | 说明 |
|------|------|------|
| `sources/phase4_glyphs/normalized_glyphs.json` | ~50MB | 11,528 条标准化 glyph（每条新增 `glyphHash`） |
| `sources/phase4_glyphs/normalization_summary.json` | ~5KB | 统计摘要 |
| `report/phase4_normalization.md` | ~2KB | 人类可读报告 |

---

## 2. 每条 glyph 的数据结构（Phase 3 → Phase 4 变化）

### Phase 3 输入格式（raw_glyphs.json 每条）：

```json
{
  "assetId": "d737f632f4df",
  "unicode": 59059,
  "unicode_hex": "E6B3",
  "glyphName": "add",
  "iconName": "icon-add",
  "glyphType": "simple",          // "simple" | "empty"（composite=0条）
  "numContours": 1,
  "contours": [                    // 原始 contour，坐标为 source UPM
    [{"x": 896.0, "y": 384.0, "on_curve": true}, ...]
  ],
  "advanceWidth": 1024,
  "lsb": 0
}
```

### Phase 4 输出格式（normalized_glyphs.json 每条）：

```json
{
  "assetId": "d737f632f4df",
  "unicode": 59059,
  "unicode_hex": "E6B3",
  "glyphName": "add",
  "iconName": "icon-add",
  "glyphType": "simple",
  "numContours": 1,
  "contours": [                    // ⚠️ 已标准化（详见第 3 节）
    [{"x": 896.0, "y": 384.0, "on_curve": true}, ...]
  ],
  "advanceWidth": 1024,
  "lsb": 0,
  "upmChanged": false,             // 新增：是否做了 UPM 缩放
  "glyphHash": "a1b2c3d4e5f6a7b8"  // 新增：SHA-256 前 16 位，canonical contours 的指纹
}
```

对于 UPM=560 的 asset 的 glyph，还会额外添加：
```json
{
  "sourceUpm": 560,
  "scale": 1.8285714285714286
}
```

---

## 3. 标准化算法（6 步，严格按顺序）

```
glyph.contours
    ↓
Step 1: UPM 缩放
  scale = 1024 / source_UPM
  所有 point.x, point.y, advanceWidth, lsb *= scale
  使用 numpy 批量处理：arr[:, 0:2] *= scale
    ↓
Step 2: round(6)
  所有 point.x, point.y = round(x, 6)
  使用 numpy：arr[:, 0:2] = np.round(arr[:, 0:2], 6)
    ↓
Step 3: 每个 contour 起点统一
  找到 contour 中 (x+y) 最小的点
  旋转 contour 使该点成为第一个点（保持顺序）
    ↓
Step 4: contour 排序
  按 contour 的 bbox 面积降序排序
  面积相同则按 min(x+y) 升序排序
    ↓
Step 5: winding direction 统一（CW）
  计算 contour 的 signed area（shoelace formula）
  signed area < 0 = CW（不修改）
  signed area > 0 = CCW → 反转 contour 点顺序
    ↓
Step 6: glyphHash 生成
  data = json.dumps(contours, sort_keys=True, separators=(',', ':'))
  glyphHash = sha256(data.encode('utf-8')).hexdigest()[:16]
```

### 关键保证

- **同 glyphHash = 相同视觉形状**（在不同 asset 中重复出现的图标会有相同 hash）
- **确定性**：相同输入一定产生相同 glyphHash
- **contours 在 Step 3-5 后是 canonical 的**：起点、顺序、方向都统一

---

## 4. 性能基准

| 指标 | 值 |
|------|-----|
| 处理 glyph 数 | 11,528 |
| 处理时间 | ~4.09 秒 |
| 吞吐量 | 2,820 glyphs/sec |
| 依赖 | Python 3.14 + numpy 2.4.4 |
| 内存峰值 | ~600MB（加载 300MB JSON + numpy 数组） |

---

## 5. 关键数据事实

### 5.1 glyph 分布

| 类型 | 数量 |
|------|------|
| simple | 11,526 |
| empty | 2 |
| composite | **0** |

### 5.2 UPM 分布

| UPM | glyph 数 | asset 数 |
|-----|---------|---------|
| 1024 | 10,265 | 100 |
| 560 | 1,263 | 10 |

### 5.3 glyphHash 去重

- 11,526 条有 hash 的 glyph
- **1,345 个唯一 glyphHash**
- 意味着平均每个 glyph 在 ~8.6 个 asset 中重复出现
- 这是 Phase 5 注册表的核心：通过 glyphHash 将多来源的相同图形合并为一条记录

### 5.4 UPM=560 的 asset 列表（Phase 5 可能需要）

| assetId | sourceProjects | glyph 数 |
|---------|---------------|---------|
| 1311a7f5b183 | business-tool | 170 |
| 7233bfd22c8e | business-tool | 93 |
| 04dce05e46cf | business-tool | 73 |
| 6a48244a285f | business-tool | 117 |
| a28da8cb6a8f | fed-toolset | 159 |
| 682513d5fcad | insurance-group-mobile | 115 |
| 5e6043beee56 | insurance-group-mobile | 119 |
| 019f321bbcff | insurance-group-mobile | 173 |
| dae51330f742 | tools-customer-acquisition | 172 |
| a8b4b50b4446 | websites-wyjj | 73 |

---

## 6. Phase 5 对接点

### 6.1 Phase 5 读取什么

```python
# Phase 5 需要读取的唯一文件
with open('sources/phase4_glyphs/normalized_glyphs.json') as f:
    glyphs = json.load(f)  # 11,528 条
```

### 6.2 Phase 5 必须使用的字段

| 字段 | 用途 |
|------|------|
| `glyphHash` | Phase 5 的核心 key — 相同 hash 的 glyph 合并为一条 registry entry |
| `assetId` | 溯源：记录这个 glyph 来自哪个 asset |
| `unicode` | 原始 unicode 码点 |
| `glyphName` | 原始 glyph 名称 |
| `iconName` | CSS 中对应的 icon 类名（如 "icon-add"） |
| `sources`（Phase 5 需构建） | 同一个 glyphHash 可能来自多个 asset，需收集所有来源 |
| `aliases`（Phase 5 需收集） | 同一个 glyphHash 在不同 asset 中可能有不同 iconName |

### 6.3 Phase 5 预期产出

```json
// registry/glyph_registry.json
[
  {
    "glyphHash": "a1b2c3d4e5f6a7b8",
    "canonicalUnicode": "e601",      // 选一个代表 unicode
    "canonicalName": "home",          // 选一个代表 name
    "aliases": ["house", "index"],    // 其他 asset 中的不同 name
    "sources": [
      {"assetId": "d737f632f4df", "projects": ["project-a"], "originalUnicode": "e601"},
      {"assetId": "abc123def456", "projects": ["project-b"], "originalUnicode": "e602"}
    ]
  }
]
```

### 6.4 Phase 5 需要额外读取的元数据

```python
# Phase 5 还需要这些文件来构建完整的溯源链
with open('sources/meta/assets_manifest.json') as f:
    assets = json.load(f)  # assetId → sourceProjects, cssUrl, ttfPath

with open('sources/meta/css_mappings.json') as f:
    css_mappings = json.load(f)  # assetId → icon name → unicode 映射
```

---

## 7. 运行方式

```bash
# 重跑 Phase 4
python pipeline/04_normalize_glyphs.py

# 运行测试
python -m pytest pipeline/test_04_normalize.py -v

# 验证输出
python -c "
import json
with open('sources/phase4_glyphs/normalized_glyphs.json') as f:
    g = json.load(f)
print(f'{len(g)} glyphs, {len(set(x[\"glyphHash\"] for x in g if x[\"glyphHash\"]!=\"empty\"))} unique hashes')
"
```

---

## 8. 测试覆盖

| 函数 | 测试数 | 覆盖 |
|------|--------|------|
| `scale_contours` | 2 | 缩放正确性 + on_curve 保留 |
| `round_contours` | 1 | round(6) 精度 |
| `normalize_glyph` | 4 | UPM=560 缩放 / UPM=1024 跳过 / empty / 完整流程 |
| `build_upm_lookup` | 1 | 默认值处理 |
| `normalize_contour_start` | 2 | 旋转正确 + 空 contour |
| `sort_contours` | 2 | 面积排序 + 同面积 min 排序 |
| `ensure_cw` | 2 | CW 不反转 + CCW 反转 |
| `compute_glyph_hash` | 2 | 确定性 + 区分性 |
| **总计** | **17** | **100% 核心函数** |
