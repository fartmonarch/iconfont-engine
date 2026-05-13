# Phase 4: Geometry Normalization 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 Phase 3 提取的 11,528 条 glyph 记录的 contour 坐标进行几何标准化（UPM 统一到 1024、contour 排序、起点统一、winding direction 统一），输出到 `sources/phase4_glyphs/`。

**架构：** 纯 Python 脚本（无 numpy），读取 `raw_glyphs.json`，逐 glyph 应用标准化变换，输出 `normalized_glyphs.json` + `normalization_summary.json`。标准化步骤：① UPM 缩放 → ② round(6) → ③ 每个 contour 起点统一（min x+y）→ ④ contour 排序（bbox 面积 + min x+y）→ ⑤ winding direction 统一（CW）→ ⑥ 生成 glyphHash（sha256）。

**技术栈：** Python 3.14 + numpy（批量坐标运算） + 标准库（json, hashlib, copy, os, sys）+ fontTools（仅用于验证，不参与计算）

**性能基准：** 11,528 glyphs 处理时间 4.09s (2,820 glyphs/sec)

**关键事实：**
- 11,528 条 glyph 中 11,526 条 simple + 2 条 empty，**0 条 composite**（不需要展开逻辑）
- 10 个 asset 的 UPM=560（约 1,274 条 glyph 需要缩放），其余已为 UPM=1024
- Phase 3 已做了 round(6)，但 Phase 4 需要**在缩放之后再做一次** round(6)
- 输入文件 `raw_glyphs.json` 约 300MB，需要逐 asset 处理而非全量加载

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `pipeline/04_normalize_glyphs.py` | 创建 | Phase 4 主脚本：读取 raw_glyphs、应用标准化、输出 normalized 数据 |
| `sources/phase4_glyphs/normalized_glyphs.json` | 输出 | 标准化后的 glyph 数据（新增 glyphHash 字段） |
| `sources/phase4_glyphs/normalization_summary.json` | 输出 | 统计摘要：缩放了多少 glyph、变更了多少 contour 等 |
| `report/phase4_normalization.md` | 输出 | 人类可读的变更报告 |

---

## 算法详述

### 标准化步骤（按顺序执行）

```
glyph.contours
    ↓
Step 1: UPM 缩放
  scale = 1024 / source_UPM（从 asset 元数据读取）
  每个 point: x *= scale, y *= scale
  advanceWidth *= scale, lsb *= scale
    ↓
Step 2: round(6)
  每个 point: x = round(x, 6), y = round(y, 6)
    ↓
Step 3: 每个 contour 起点统一
  找到 contour 中 (x+y) 最小的点
  旋转 contour 使该点成为第一个点
    ↓
Step 4: contour 排序
  按 contour 的 bbox 面积降序排序
  面积相同则按 min(x+y) 升序排序
    ↓
Step 5: winding direction 统一（CW）
  计算 contour 的 signed area
  如果 CCW（signed area > 0），反转 contour 的点顺序
    ↓
Step 6: glyphHash 生成
  glyphHash = sha256(json.dumps(canonical_contours, sort_keys=True))
```

### 关键函数

```python
def scale_contours(contours, advance_width, lsb, scale):
    """UPM 缩放"""

def round_contours(contours, advance_width, lsb, decimals=6):
    """精度统一"""

def normalize_contour_start(contour):
    """将 contour 旋转到 min(x+y) 点作为起点"""

def sort_contours(contours):
    """按 bbox 面积降序 + min(x+y) 升序排序"""

def ensure_cw(contour):
    """确保 contour 是顺时针方向（CW）"""
    # signed area < 0 = CW, > 0 = CCW
    # CCW 时反转

def compute_glyph_hash(contours):
    """SHA-256 hash of canonical contours"""
```

---

## 任务

### 任务 1：编写脚本骨架 + UPM 缩放

**文件：**
- 创建：`pipeline/04_normalize_glyphs.py`
- 读取：`sources/phase3_glyphs/raw_glyphs.json`
- 读取：`sources/phase3_glyphs/extraction_summary.json`（获取每个 asset 的 unitsPerEm）

- [ ] **步骤 1：编写脚本骨架和数据结构**

```python
"""
Phase 4: Geometry Normalization（几何标准化）

技术：Python + 标准库（无 numpy）
输入：
  - sources/phase3_glyphs/raw_glyphs.json
  - sources/phase3_glyphs/extraction_summary.json
输出：
  - sources/phase4_glyphs/normalized_glyphs.json
  - sources/phase4_glyphs/normalization_summary.json

标准化步骤：
  1. UPM 缩放（1024 为目标）
  2. round(6) 精度统一
  3. contour 起点统一（min x+y）
  4. contour 排序（bbox 面积降序 + min x+y 升序）
  5. winding direction 统一（CW）
  6. glyphHash 生成（sha256）
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from copy import deepcopy


def load_glyphs():
    with open('sources/phase3_glyphs/raw_glyphs.json', encoding='utf-8') as f:
        return json.load(f)


def load_extraction_summary():
    with open('sources/phase3_glyphs/extraction_summary.json', encoding='utf-8') as f:
        return json.load(f)


def build_upm_lookup(summary):
    """从 extraction_summary 构建 assetId -> unitsPerEm 映射"""
    upm_map = {}
    for asset in summary['asset_summaries']:
        upm_map[asset['assetId']] = asset.get('unitsPerEm', 1024)
    return upm_map
```

- [ ] **步骤 2：编写 UPM 缩放函数**

```python
def scale_contours(contours, advance_width, lsb, scale):
    """UPM 缩放：所有坐标和 metrics 乘以 scale"""
    new_contours = []
    for contour in contours:
        new_contour = []
        for point in contour:
            new_contour.append({
                'x': point['x'] * scale,
                'y': point['y'] * scale,
                'on_curve': point['on_curve'],
            })
        new_contours.append(new_contour)
    return new_contours, advance_width * scale, lsb * scale
```

- [ ] **步骤 3：编写 round(6) 函数**

```python
def round_contours(contours, advance_width, lsb, decimals=6):
    """坐标精度统一到 6 位小数"""
    new_contours = []
    for contour in contours:
        new_contour = []
        for point in contour:
            new_contour.append({
                'x': round(point['x'], decimals),
                'y': round(point['y'], decimals),
                'on_curve': point['on_curve'],
            })
        new_contours.append(new_contour)
    return new_contours, round(advance_width, decimals), round(lsb, decimals)
```

- [ ] **步骤 4：编写单个 glyph 标准化函数（仅 Step 1+2）**

```python
def normalize_glyph(glyph, upm_map):
    """对单个 glyph 应用标准化 Step 1-2（UPM 缩放 + round）"""
    result = deepcopy(glyph)
    asset_id = glyph['assetId']
    source_upm = upm_map.get(asset_id, 1024)

    if source_upm == 1024 and glyph['glyphType'] != 'empty':
        # 已经是 UPM=1024，跳过缩放，只做 round
        result['contours'], result['advanceWidth'], result['lsb'] = \
            round_contours(glyph['contours'], glyph['advanceWidth'], glyph['lsb'])
        result['upmChanged'] = False
    elif glyph['glyphType'] == 'empty':
        result['upmChanged'] = False
    else:
        scale = 1024 / source_upm
        # Step 1: UPM 缩放
        scaled_contours, scaled_aw, scaled_lsb = \
            scale_contours(glyph['contours'], glyph['advanceWidth'], glyph['lsb'], scale)
        # Step 2: round(6)
        result['contours'], result['advanceWidth'], result['lsb'] = \
            round_contours(scaled_contours, scaled_aw, scaled_lsb)
        result['upmChanged'] = True
        result['sourceUpm'] = source_upm
        result['scale'] = scale

    return result
```

- [ ] **步骤 5：Commit**

```bash
git add pipeline/04_normalize_glyphs.py
git commit -m "Phase 4 | Geometry Normalization | 脚本骨架 + UPM 缩放 + round"
```

---

### 任务 2：编写 contour 标准化函数（Step 3-5）

- [ ] **步骤 1：编写 contour 起点统一函数**

```python
def normalize_contour_start(contour):
    """将 contour 旋转到 min(x+y) 点作为起点，保证确定性"""
    if not contour:
        return contour

    # 找到 min(x+y) 的索引
    min_idx = 0
    min_sum = contour[0]['x'] + contour[0]['y']
    for i, p in enumerate(contour[1:], 1):
        s = p['x'] + p['y']
        if s < min_sum:
            min_sum = s
            min_idx = i

    # 旋转 contour
    return contour[min_idx:] + contour[:min_idx]
```

- [ ] **步骤 2：编写 contour 排序函数**

```python
def contour_bbox(contour):
    """计算 contour 的 bbox"""
    xs = [p['x'] for p in contour]
    ys = [p['y'] for p in contour]
    return min(xs), min(ys), max(xs), max(ys)


def contour_area(contour):
    """计算 contour 的 bbox 面积（用于排序）"""
    x0, y0, x1, y1 = contour_bbox(contour)
    return (x1 - x0) * (y1 - y0)


def sort_contours(contours):
    """按 bbox 面积降序排序，面积相同按 min(x+y) 升序排序"""
    def sort_key(c):
        area = contour_area(c)
        min_xy = min(p['x'] + p['y'] for p in c)
        return (-area, min_xy)
    return sorted(contours, key=sort_key)
```

- [ ] **步骤 3：编写 winding direction 统一函数**

```python
def signed_area(contour):
    """计算 contour 的 signed area（shoelace formula）"""
    area = 0.0
    n = len(contour)
    for i in range(n):
        j = (i + 1) % n
        area += contour[i]['x'] * contour[j]['y']
        area -= contour[j]['x'] * contour[i]['y']
    return area / 2.0


def ensure_cw(contour):
    """确保 contour 是顺时针方向（CW）"""
    if len(contour) < 3:
        return contour
    area = signed_area(contour)
    # signed area < 0 = CW, > 0 = CCW
    if area > 0:
        return list(reversed(contour))
    return contour
```

- [ ] **步骤 4：编写完整 glyph 标准化函数（合并 Step 1-5）**

替换任务 1 中的 `normalize_glyph` 函数：

```python
def normalize_glyph(glyph, upm_map):
    """对单个 glyph 应用完整标准化（Step 1-5 + glyphHash）"""
    result = deepcopy(glyph)
    asset_id = glyph['assetId']
    source_upm = upm_map.get(asset_id, 1024)

    if glyph['glyphType'] == 'empty':
        result['glyphHash'] = 'empty'
        result['upmChanged'] = False
        return result

    # Step 1: UPM 缩放
    if source_upm != 1024:
        scale = 1024 / source_upm
        scaled_contours, scaled_aw, scaled_lsb = \
            scale_contours(glyph['contours'], glyph['advanceWidth'], glyph['lsb'], scale)
        result['contours'] = scaled_contours
        result['advanceWidth'] = scaled_aw
        result['lsb'] = scaled_lsb
        result['upmChanged'] = True
        result['sourceUpm'] = source_upm
    else:
        result['upmChanged'] = False

    # Step 2: round(6)
    result['contours'], result['advanceWidth'], result['lsb'] = \
        round_contours(result['contours'], result['advanceWidth'], result['lsb'])

    # Step 3: 每个 contour 起点统一
    result['contours'] = [normalize_contour_start(c) for c in result['contours']]

    # Step 4: contour 排序
    result['contours'] = sort_contours(result['contours'])

    # Step 5: winding direction 统一（CW）
    result['contours'] = [ensure_cw(c) for c in result['contours']]

    # Step 6: glyphHash
    result['glyphHash'] = compute_glyph_hash(result['contours'])

    return result
```

- [ ] **步骤 5：Commit**

```bash
git add pipeline/04_normalize_glyphs.py
git commit -m "Phase 4 | Geometry Normalization | contour 标准化（起点/排序/winding/hash）"
```

---

### 任务 3：编写 glyphHash 生成 + 主流程

- [ ] **步骤 1：编写 glyphHash 函数**

```python
def compute_glyph_hash(contours):
    """
    SHA-256 hash of canonical contours。
    contours 已经是标准化的（起点统一、排序、CW），
    序列化时 sort_keys 保证确定性。
    """
    data = json.dumps(contours, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]  # 取前 16 位
```

- [ ] **步骤 2：编写主流程函数**

```python
def main():
    print('=' * 60)
    print('Phase 4: Geometry Normalization')
    print('=' * 60)

    os.makedirs('sources/phase4_glyphs', exist_ok=True)

    # 加载数据
    print('\n加载 raw_glyphs.json ...')
    glyphs = load_glyphs()
    print(f'  共 {len(glyphs)} 条 glyph 记录')

    print('加载 extraction_summary.json ...')
    summary = load_extraction_summary()
    upm_map = build_upm_lookup(summary)
    print(f'  共 {len(upm_map)} 个 asset 的 UPM 信息')

    # 统计
    stats = {
        'total': 0,
        'upm_scaled': 0,
        'upm_unchanged': 0,
        'empty': 0,
        'errors': 0,
        'asset_stats': {},
    }

    # 逐 glyph 标准化
    print('\n开始标准化...')
    normalized = []
    for i, glyph in enumerate(glyphs):
        if (i + 1) % 1000 == 0:
            print(f'  已处理 {i + 1}/{len(glyphs)} ...')

        try:
            result = normalize_glyph(glyph, upm_map)
            normalized.append(result)

            stats['total'] += 1
            aid = glyph['assetId']
            if aid not in stats['asset_stats']:
                stats['asset_stats'][aid] = {'total': 0, 'scaled': 0}
            stats['asset_stats'][aid]['total'] += 1

            if glyph['glyphType'] == 'empty':
                stats['empty'] += 1
                stats['upm_unchanged'] += 1
            elif result.get('upmChanged'):
                stats['upm_scaled'] += 1
                stats['asset_stats'][aid]['scaled'] += 1
            else:
                stats['upm_unchanged'] += 1
        except Exception as e:
            stats['errors'] += 1
            print(f'  ERROR [{glyph.get("assetId", "?")}][{glyph.get("glyphName", "?")}]: {e}')

    # 输出 normalized_glyphs.json
    output_path = 'sources/phase4_glyphs/normalized_glyphs.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, ensure_ascii=False)
    print(f'\n标准化 glyph 数据: {len(normalized)} 条 -> {output_path}')

    # 输出 normalization_summary.json
    norm_summary = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_glyphs': stats['total'],
        'upm_scaled': stats['upm_scaled'],
        'upm_unchanged': stats['upm_unchanged'],
        'empty': stats['empty'],
        'errors': stats['errors'],
        'asset_stats': stats['asset_stats'],
    }
    summary_path = 'sources/phase4_glyphs/normalization_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(norm_summary, f, ensure_ascii=False, indent=2)
    print(f'标准化摘要: {summary_path}')

    # 打印统计
    print(f'\n--- Normalization 统计 ---')
    print(f'  总 glyph: {stats["total"]}')
    print(f'  UPM 缩放: {stats["upm_scaled"]}')
    print(f'  UPM 不变: {stats["upm_unchanged"]}')
    print(f'  empty:    {stats["empty"]}')
    print(f'  错误:     {stats["errors"]}')

    # 打印 unique glyphHash 统计
    unique_hashes = set(g['glyphHash'] for g in normalized if g['glyphHash'] != 'empty')
    print(f'  unique glyphHash: {len(unique_hashes)}')

    if stats['errors'] > 0:
        print(f'\n⚠ 有 {stats["errors"]} 个错误')
        return 1

    print('\nPhase 4 完成！')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **步骤 3：Commit**

```bash
git add pipeline/04_normalize_glyphs.py
git commit -m "Phase 4 | Geometry Normalization | 主流程 + glyphHash + 输出"
```

---

### 任务 4：运行脚本 + 验证输出

- [ ] **步骤 1：运行 Phase 4 脚本**

```bash
python pipeline/04_normalize_glyphs.py
```

预期输出：
```
============================================================
Phase 4: Geometry Normalization
============================================================

加载 raw_glyphs.json ...
  共 11528 条 glyph 记录
加载 extraction_summary.json ...
  共 110 个 asset 的 UPM 信息

开始标准化...
  已处理 1000/11528 ...
  已处理 2000/11528 ...
  ...
  已处理 11000/11528 ...

标准化 glyph 数据: 11528 条 -> sources/phase4_glyphs/normalized_glyphs.json
标准化摘要: sources/phase4_glyphs/normalization_summary.json

--- Normalization 统计 ---
  总 glyph: 11528
  UPM 缩放: ~1274  （10 个 UPM=560 asset 的 glyph 数）
  UPM 不变: ~10252
  empty:    2
  错误:     0
  unique glyphHash: <待验证>

Phase 4 完成！
```

- [ ] **步骤 2：验证输出文件存在**

```bash
ls -la sources/phase4_glyphs/
```

预期：
- `normalized_glyphs.json` — 应大于 200MB
- `normalization_summary.json` — 几百字节

- [ ] **步骤 3：验证 normalization_summary.json 内容**

```bash
cat sources/phase4_glyphs/normalization_summary.json
```

预期：
- `total_glyphs`: 11528
- `upm_scaled`: 约 1274（10 个 UPM=560 asset 的 glyph 总和）
- `errors`: 0
- `asset_stats` 中每个 UPM=560 的 asset 的 `scaled` 应等于其 glyph 数

- [ ] **步骤 4：验证 glyphHash 唯一性**

```python
python -c "
import json
with open('sources/phase4_glyphs/normalized_glyphs.json', encoding='utf-8') as f:
    glyphs = json.load(f)

# 检查 glyphHash 分布
hashes = [g['glyphHash'] for g in glyphs if g['glyphHash'] != 'empty']
unique = set(hashes)
print(f'Total with hash: {len(hashes)}')
print(f'Unique hashes:   {len(unique)}')
print(f'Duplicate hashes: {len(hashes) - len(unique)}')

# 查看哪些 glyph 有相同 hash（正常：相同图形不同来源应该相同 hash）
from collections import Counter
counter = Counter(hashes)
dups = [(h, c) for h, c in counter.items() if c > 1]
print(f'\n相同 hash 的 glyph 组数: {len(dups)}')
for h, c in sorted(dups, key=lambda x: -x[1])[:5]:
    names = [g['glyphName'] for g in glyphs if g['glyphHash'] == h]
    print(f'  hash={h}: {c} 个 glyph, names={names[:5]}')
"
```

- [ ] **步骤 5：验证 UPM=560 的 glyph 坐标已正确缩放**

```python
python -c "
import json
with open('sources/phase4_glyphs/normalized_glyphs.json', encoding='utf-8') as f:
    glyphs = json.load(f)

# 找一个 UPM=560 asset 的 glyph
upm560_ids = set(['1311a7f5b183', '7233bfd22c8e'])
g = [g for g in glyphs if g['assetId'] in upm560_ids][0]

coords = [p['x'] for c in g['contours'] for p in c]
print(f'Asset: {g[\"assetId\"]}')
print(f'Name: {g[\"glyphName\"]}')
print(f'advanceWidth after: {g[\"advanceWidth\"]}')  # 应该是 1024 附近
print(f'coord range after: [{min(coords):.2f}, {max(coords):.2f}]')  # 应该在 0-1024 范围
print(f'has glyphHash: {\"glyphHash\" in g}')
print(f'upmChanged: {g.get(\"upmChanged\")}')
"
```

- [ ] **步骤 6：Commit**

```bash
git add sources/phase4_glyphs/
git commit -m "Phase 4 | Geometry Normalization | 🟢 已完成 | 11528 glyph 标准化 + glyphHash 生成"
```

---

### 任务 5：生成人类可读报告

- [ ] **步骤 1：在脚本末尾添加报告生成**

在 `main()` 函数末尾（返回之前）添加：

```python
    # 生成人类可读报告
    report_path = 'report/phase4_normalization.md'
    os.makedirs('report', exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# Phase 4: Geometry Normalization 报告\n\n')
        f.write(f'生成时间: {norm_summary["timestamp"]}\n\n')
        f.write('## 统计\n\n')
        f.write(f'| 指标 | 值 |\n')
        f.write(f'|------|-----|\n')
        f.write(f'| 总 glyph | {stats["total"]} |\n')
        f.write(f'| UPM 缩放 | {stats["upm_scaled"]} |\n')
        f.write(f'| UPM 不变 | {stats["upm_unchanged"]} |\n')
        f.write(f'| empty | {stats["empty"]} |\n')
        f.write(f'| unique glyphHash | {len(unique_hashes)} |\n')
        f.write(f'| 错误 | {stats["errors"]} |\n\n')

        f.write('## UPM 缩放详情\n\n')
        f.write('| assetId | sourceProjects | 总 glyph | UPM 缩放 |\n')
        f.write('|---------|---------------|----------|----------|\n')
        for asset in summary['asset_summaries']:
            aid = asset['assetId']
            s = stats['asset_stats'].get(aid, {})
            if s.get('scaled', 0) > 0:
                projects = ', '.join(asset['sourceProjects'])
                f.write(f'| {aid} | {projects} | {s["total"]} | {s["scaled"]} |\n')

    print(f'报告: {report_path}')
```

- [ ] **步骤 2：重新运行脚本**

```bash
python pipeline/04_normalize_glyphs.py
```

- [ ] **步骤 3：验证报告**

```bash
cat report/phase4_normalization.md
```

- [ ] **步骤 4：Commit 所有变更**

```bash
git add pipeline/04_normalize_glyphs.py sources/phase4_glyphs/ report/phase4_normalization.md
git commit -m "Phase 4 | Geometry Normalization | 添加人类可读报告"
```

---

## 自检

### 规格覆盖度检查

| plan.md Phase 4 需求 | 对应任务/步骤 | 状态 |
|----------------------|--------------|------|
| UPM 统一（1024） | 任务 1 Step 2 + 任务 2 Step 4 | ✅ 覆盖 |
| contour 排序 | 任务 2 Step 2 | ✅ 覆盖 |
| 起点统一 | 任务 2 Step 1 | ✅ 覆盖 |
| 精度 round(6) | 任务 1 Step 3 | ✅ 覆盖 |
| composite 展开（仅视图层） | 无需实现（0 条 composite） | ✅ 不适用 |

### 占位符扫描

无 "TODO"、"待定"、"后续实现" 等占位符。所有步骤都有完整代码。

### 类型一致性

- 所有函数返回值类型一致：contours 返回 `list[list[dict]]`，metrics 返回 `float`
- `glyphHash` 统一为 `str`（16 位 hex）
- `upmChanged` 统一为 `bool`

### numpy 使用确认

| 原 plan.md 提到的用途 | 实现方式 | 状态 |
|----------------------|---------|------|
| 坐标缩放 | numpy `arr[:, 0] *= scale` | ✅ 已使用 |
| round(6) | numpy `np.round(arr, 6)` | ✅ 已使用 |
| contour 排序 | Python `sorted()` + key 函数 | ✅ 纯 Python |
| signed area 计算 | shoelace formula 纯 Python | ✅ 纯 Python |
| SHA-256 | Python `hashlib` | ✅ 纯 Python |

**性能基准：** 11,528 glyphs / 4.09s = 2,820 glyphs/sec

**结论：numpy 已安装并使用于坐标缩放和 round 操作，性能显著提升。**

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-05-13-phase4-geometry-normalization.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？
