# Phase 6 冲突检测 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 从 registry/glyph_registry.json 检测三类冲突（Unicode/Name/Duplicate），按严重性分级，输出结构化 JSON 和 Markdown 报告。

**架构：** 纯 Python 脚本，读取 Phase 5 产出的 glyph_registry.json，按 unicode/name/glyphHash 分组检测冲突，组装 CONFLICT_RECORD 数据结构，生成 report/conflict_records.json 和 report/conflict_report.md。

**技术栈：** Python 3、collections.Counter、json

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `pipeline/06_detect_conflicts.py` | 创建 | 主脚本：8 个核心函数 + main 入口 |
| `pipeline/test_06_conflicts.py` | 创建 | 测试：覆盖检测逻辑、分级、输出格式 |
| `report/conflict_records.json` | 输出 | Phase 7 消费的结构化冲突数据 |
| `report/conflict_report.md` | 输出 | 人类可读分级报告 |

---

## 任务 1：核心检测函数 + 单元测试

**文件：**
- 创建：`pipeline/06_detect_conflicts.py`
- 创建：`pipeline/test_06_conflicts.py`

### 步骤 1：编写测试 — detect_unicode_conflicts

```python
# pipeline/test_06_conflicts.py — 头部 + make_entry helper + 第一个测试

import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location('phase6', 'pipeline/06_detect_conflicts.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

detect_unicode_conflicts = mod.detect_unicode_conflicts
detect_name_conflicts = mod.detect_name_conflicts
detect_duplicate_glyphs = mod.detect_duplicate_glyphs
classify_severity = mod.classify_severity
build_conflict_records = mod.build_conflict_records
generate_records_json = mod.generate_records_json
generate_report_md = mod.generate_report_md


def make_entry(glyph_hash, unicode_hex, name, sources):
    """Helper: 构造一条 registry entry"""
    return {
        'glyphHash': glyph_hash,
        'canonicalUnicode': int(unicode_hex, 16) if unicode_hex else None,
        'canonicalUnicodeHex': unicode_hex,
        'canonicalName': name,
        'canonicalAssetId': sources[0]['assetId'] if sources else None,
        'aliases': [name],
        'aliasesDetail': [],
        'sources': sources,
        'contours': [[{'x': 0.0, 'y': 0.0, 'on_curve': True}]],
        'advanceWidth': 1024,
        'glyphType': 'simple',
        'numContours': 1,
    }


def make_source(asset_id, projects, css_url=''):
    return {'assetId': asset_id, 'projects': projects, 'cssUrl': css_url}


def test_detect_unicode_conflicts_basic():
    """同 unicode 不同 glyphHash → 冲突"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B6', 'icon-up', [make_source('asset1', ['proj-a'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 1
    assert conflicts[0]['key'] == 'U+E6B5'
    assert len(conflicts[0]['variants']) == 2
    assert conflicts[0]['resolution_hint'] == 'assign_pua'
    # 确认 hash_c 不在冲突组中
    print('  PASS test_detect_unicode_conflicts_basic')
```

### 步骤 2：运行测试验证失败

```bash
python pipeline/test_06_conflicts.py
```
预期：FAIL，报错 `detect_unicode_conflicts not defined`

### 步骤 3：编写 detect_unicode_conflicts 实现

```python
# pipeline/06_detect_conflicts.py — 头部 + 第一个函数

"""
Phase 6: Conflict Detection（冲突检测）

技术：Python + collections.defaultdict + Counter
输入：
  - registry/glyph_registry.json
输出：
  - report/conflict_records.json  — 结构化冲突数据（Phase 7 消费）
  - report/conflict_report.md    — 人类可读分级报告

核心逻辑：
  1. 按 unicode 分组 → 检测 Type A: Unicode 冲突
  2. 按 name 分组 → 检测 Type B: Name 冲突
  3. 按 sources 计数 → 检测 Type C: Duplicate Glyph
  4. 按变体数分级：Critical(5+) / Warning(3-4) / Info(2)
  5. 组装 CONFLICT_RECORD + 输出
"""

import json
import os
import sys
from collections import defaultdict


def load_registry():
    """加载 glyph_registry.json"""
    with open('registry/glyph_registry.json', encoding='utf-8') as f:
        return json.load(f)


def classify_severity(variant_count):
    """根据变体数量返回严重性级别"""
    if variant_count >= 5:
        return 'critical'
    elif variant_count >= 3:
        return 'warning'
    else:
        return 'info'


def detect_unicode_conflicts(entries):
    """Type A: 同 unicode → 不同 glyphHash"""
    uc_groups = defaultdict(list)
    for e in entries:
        uc = e.get('canonicalUnicodeHex')
        if uc:
            uc_groups[uc].append(e)

    conflicts = []
    for uc, group in sorted(uc_groups.items()):
        hashes = set(g['glyphHash'] for g in group)
        if len(hashes) > 1:
            conflicts.append(_build_conflict_record(
                conflict_type='unicode_conflict',
                key=f'U+{uc}',
                group=group,
                resolution_hint='assign_pua',
            ))

    return conflicts


def _build_conflict_record(conflict_type, key, group, resolution_hint):
    """通用冲突记录构建器"""
    variants = []
    affected_assets = set()
    affected_projects = set()

    for e in group:
        variants.append({
            'glyphHash': e['glyphHash'],
            'canonicalUnicodeHex': e.get('canonicalUnicodeHex'),
            'canonicalName': e.get('canonicalName'),
            'sources': e.get('sources', []),
            'contours': e.get('contours'),
            'advanceWidth': e.get('advanceWidth'),
        })
        for s in e.get('sources', []):
            affected_assets.add(s['assetId'])
            for p in s.get('projects', []):
                affected_projects.add(p)

    return {
        'type': conflict_type,
        'severity': classify_severity(len(variants)),
        'key': key,
        'variantCount': len(variants),
        'variants': variants,
        'affectedAssets': sorted(affected_assets),
        'affectedProjects': sorted(affected_projects),
        'resolution_hint': resolution_hint,
    }
```

### 步骤 4：运行测试验证通过

```bash
python pipeline/test_06_conflicts.py
```
预期：PASS test_detect_unicode_conflicts_basic

### 步骤 5：添加测试 — detect_unicode_conflicts 边界情况

```python
# 追加到 test_06_conflicts.py

def test_detect_unicode_conflicts_no_conflict():
    """每个 unicode 只有一个 glyphHash → 无冲突"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-up', [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_unicode_conflicts_no_conflict')


def test_detect_unicode_conflicts_same_hash():
    """同 unicode 同 glyphHash → 不冲突（只是多来源）"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_unicode_conflicts_same_hash')


def test_detect_unicode_conflicts_null_unicode():
    """unicode 为 null 的 entry 应被跳过"""
    entries = [
        make_entry('empty', None, None, [make_source('asset1', ['proj-a'])]),
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 1
    assert conflicts[0]['key'] == 'U+E6B5'
    print('  PASS test_detect_unicode_conflicts_null_unicode')
```

### 步骤 6：运行测试验证

```bash
python pipeline/test_06_conflicts.py
```
预期：3 PASS, 0 FAIL

---

## 任务 2：Name 冲突检测 + 测试

### 步骤 1：编写测试 — detect_name_conflicts

```python
# 追加到 test_06_conflicts.py

def test_detect_name_conflicts_basic():
    """同 name 不同 glyphHash → 冲突"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B7', 'icon-up', [make_source('asset1', ['proj-a'])]),
    ]
    conflicts = detect_name_conflicts(entries)
    assert len(conflicts) == 1
    assert conflicts[0]['key'] == 'icon-arrow'
    assert len(conflicts[0]['variants']) == 2
    assert conflicts[0]['resolution_hint'] == 'rename'
    print('  PASS test_detect_name_conflicts_basic')


def test_detect_name_conflicts_null_name():
    """name 为 null/空字符串应跳过"""
    entries = [
        make_entry('hash_a', 'E6B5', None, [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', '', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B7', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
    ]
    conflicts = detect_name_conflicts(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_name_conflicts_null_name')


def test_detect_name_conflicts_same_hash():
    """同 name 同 glyphHash → 不冲突"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_a', 'E6B6', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_name_conflicts(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_name_conflicts_same_hash')
```

### 步骤 2：运行测试验证失败

```bash
python pipeline/test_06_conflicts.py
```
预期：FAIL `test_detect_name_conflicts_basic`

### 步骤 3：编写 detect_name_conflicts 实现

```python
# 追加到 06_detect_conflicts.py

def detect_name_conflicts(entries):
    """Type B: 同 name → 不同 glyphHash"""
    name_groups = defaultdict(list)
    for e in entries:
        name = e.get('canonicalName')
        if name:
            name_groups[name].append(e)

    conflicts = []
    for name, group in sorted(name_groups.items()):
        hashes = set(g['glyphHash'] for g in group)
        if len(hashes) > 1:
            conflicts.append(_build_conflict_record(
                conflict_type='name_conflict',
                key=name,
                group=group,
                resolution_hint='rename',
            ))

    return conflicts
```

### 步骤 4：运行测试验证通过

```bash
python pipeline/test_06_conflicts.py
```
预期：6 PASS, 0 FAIL

### 步骤 5：Commit

```bash
git add pipeline/06_detect_conflicts.py pipeline/test_06_conflicts.py
git commit -m "feat(phase6): 实现 Type A Unicode 冲突 + Type B Name 冲突检测"
```

---

## 任务 3：Duplicate Glyph 检测 + 测试

### 步骤 1：编写测试 — detect_duplicate_glyphs

```python
# 追加到 test_06_conflicts.py

def test_detect_duplicate_glyphs_basic():
    """同 glyphHash 多来源 → Duplicate Glyph"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [
            make_source('asset1', ['proj-a']),
            make_source('asset2', ['proj-b']),
        ]),
        make_entry('hash_b', 'E6B6', 'icon-up', [make_source('asset1', ['proj-a'])]),
    ]
    conflicts = detect_duplicate_glyphs(entries)
    assert len(conflicts) == 1
    assert conflicts[0]['type'] == 'glyph_duplicate'
    assert conflicts[0]['key'] == 'hash_a'
    assert conflicts[0]['variantCount'] == 1  # 1 个 glyphHash
    assert conflicts[0]['resolution_hint'] == 'merge_alias'
    print('  PASS test_detect_duplicate_glyphs_basic')


def test_detect_duplicate_glyphs_single_source():
    """单来源 entry → 不是 duplicate"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-up', [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_duplicate_glyphs(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_duplicate_glyphs_single_source')


def test_detect_duplicate_glyphs_severity():
    """按 sources 数量分级"""
    entries_2src = make_entry('hash_a', 'E6B5', 'icon-a', [
        make_source('asset1', ['p1']), make_source('asset2', ['p2'])
    ])
    entries_5src = make_entry('hash_b', 'E6B6', 'icon-b', [
        make_source('a1', ['p1']), make_source('a2', ['p2']),
        make_source('a3', ['p3']), make_source('a4', ['p4']),
        make_source('a5', ['p5']),
    ])
    conflicts = detect_duplicate_glyphs([entries_2src, entries_5src])
    assert len(conflicts) == 2
    sev_map = {c['key']: c['severity'] for c in conflicts}
    assert sev_map['hash_b'] == 'critical'  # 5 sources
    assert sev_map['hash_a'] == 'info'      # 2 sources
    print('  PASS test_detect_duplicate_glyphs_severity')
```

### 步骤 2：运行测试验证失败

```bash
python pipeline/test_06_conflicts.py
```
预期：FAIL `test_detect_duplicate_glyphs_basic`

### 步骤 3：编写 detect_duplicate_glyphs 实现

```python
# 追加到 06_detect_conflicts.py

def detect_duplicate_glyphs(entries):
    """Type C: 同 glyphHash → 多来源（正常合并情况）"""
    conflicts = []
    for e in entries:
        sources = e.get('sources', [])
        if len(sources) > 1:
            conflicts.append(_build_conflict_record(
                conflict_type='glyph_duplicate',
                key=e['glyphHash'],
                group=[e],
                resolution_hint='merge_alias',
            ))

    return conflicts
```

### 步骤 4：运行测试验证通过

```bash
python pipeline/test_06_conflicts.py
```
预期：9 PASS, 0 FAIL

### 步骤 5：Commit

```bash
git add pipeline/06_detect_conflicts.py pipeline/test_06_conflicts.py
git commit -m "feat(phase6): 实现 Type C Duplicate Glyph 检测"
```

---

## 任务 4：classify_severity 全面测试

### 步骤 1：编写测试

```python
# 追加到 test_06_conflicts.py

def test_classify_severity():
    assert classify_severity(2) == 'info'
    assert classify_severity(3) == 'warning'
    assert classify_severity(4) == 'warning'
    assert classify_severity(5) == 'critical'
    assert classify_severity(10) == 'critical'
    assert classify_severity(1) == 'info'  # edge: 1 is still info
    print('  PASS test_classify_severity')
```

### 步骤 2：运行测试验证

```bash
python pipeline/test_06_conflicts.py
```
预期：10 PASS, 0 FAIL

（这一步应该直接通过，classify_severity 已在任务 1 实现）

### 步骤 3：Commit

```bash
git add pipeline/test_06_conflicts.py
git commit -m "test(phase6): 添加 classify_severity 测试"
```

---

## 任务 5：build_conflict_records 整合 + 测试

### 步骤 1：编写测试

```python
# 追加到 test_06_conflicts.py

def test_build_conflict_records_all_types():
    """同时检测三类冲突，验证整合结果"""
    entries = [
        # Type A: U+E6B5 有 2 种不同 glyphHash
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
        # Type B: icon-arrow 有 2 种不同 glyphHash (hash_a + hash_b 已计入)
        # 另外增加一组
        make_entry('hash_c', 'E6C0', 'icon-help', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_d', 'E6C1', 'icon-help', [make_source('asset2', ['proj-b'])]),
        # Type C: hash_a 多来源
        make_entry('hash_e', 'E6D0', 'icon-ok', [
            make_source('asset1', ['proj-a']),
            make_source('asset2', ['proj-b']),
        ]),
        # 无冲突的 entry
        make_entry('hash_f', 'E6E0', 'icon-clear', [make_source('asset3', ['proj-c'])]),
    ]
    records = build_conflict_records(entries)

    type_counts = {}
    for r in records:
        type_counts[r['type']] = type_counts.get(r['type'], 0) + 1

    assert type_counts.get('unicode_conflict', 0) == 1   # U+E6B5
    assert type_counts.get('name_conflict', 0) == 2       # icon-arrow + icon-help
    assert type_counts.get('glyph_duplicate', 0) == 1    # hash_e
    assert len(records) == 4
    print('  PASS test_build_conflict_records_all_types')


def test_build_conflict_records_required_fields():
    """验证每条 CONFLICT_RECORD 都有必需字段"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    records = build_conflict_records(entries)
    required = ['type', 'severity', 'key', 'variantCount', 'variants',
                'affectedAssets', 'affectedProjects', 'resolution_hint']
    for r in records:
        for field in required:
            assert field in r, f'Missing field: {field} in {r["key"]}'
    print('  PASS test_build_conflict_records_required_fields')
```

### 步骤 2：运行测试验证失败

```bash
python pipeline/test_06_conflicts.py
```
预期：FAIL `test_build_conflict_records_all_types`

### 步骤 3：编写 build_conflict_records 实现

```python
# 追加到 06_detect_conflicts.py

def build_conflict_records(entries):
    """整合三类冲突检测结果，返回所有 CONFLICT_RECORD 列表"""
    unicode_conflicts = detect_unicode_conflicts(entries)
    name_conflicts = detect_name_conflicts(entries)
    duplicate_conflicts = detect_duplicate_glyphs(entries)

    all_records = unicode_conflicts + name_conflicts + duplicate_conflicts

    # 按 severity 排序: critical → warning → info
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_records.sort(key=lambda r: (severity_order.get(r['severity'], 9), r['key']))

    return all_records
```

### 步骤 4：运行测试验证通过

```bash
python pipeline/test_06_conflicts.py
```
预期：12 PASS, 0 FAIL

### 步骤 5：Commit

```bash
git add pipeline/06_detect_conflicts.py pipeline/test_06_conflicts.py
git commit -m "feat(phase6): 实现 build_conflict_records 整合三类冲突"
```

---

## 任务 6：generate_records_json + 测试

### 步骤 1：编写测试

```python
# 追加到 test_06_conflicts.py

def test_generate_records_json(tmp_path=None):
    """验证 JSON 输出格式和可读取性"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    records = build_conflict_records(entries)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, 'test_records.json')
        generate_records_json(records, output_path)

        with open(output_path, encoding='utf-8') as f:
            loaded = json.load(f)

        assert isinstance(loaded, dict)
        assert 'metadata' in loaded
        assert 'records' in loaded
        assert len(loaded['records']) == 1
        assert loaded['records'][0]['type'] == 'unicode_conflict'
        assert loaded['metadata']['total_conflicts'] == 1
        assert loaded['metadata']['by_type']['unicode_conflict'] == 1
    print('  PASS test_generate_records_json')
```

### 步骤 2：运行测试验证失败

```bash
python pipeline/test_06_conflicts.py
```
预期：FAIL `test_generate_records_json`

### 步骤 3：编写 generate_records_json 实现

```python
# 追加到 06_detect_conflicts.py

from datetime import datetime, timezone


def generate_records_json(records, output_path):
    """生成结构化 JSON 文件（Phase 7 消费）"""
    by_type = defaultdict(int)
    by_severity = defaultdict(int)
    for r in records:
        by_type[r['type']] += 1
        by_severity[r['severity']] += 1

    output = {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'total_conflicts': len(records),
            'by_type': dict(by_type),
            'by_severity': dict(by_severity),
        },
        'records': records,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
```

### 步骤 4：运行测试验证通过

```bash
python pipeline/test_06_conflicts.py
```
预期：13 PASS, 0 FAIL

### 步骤 5：Commit

```bash
git add pipeline/06_detect_conflicts.py pipeline/test_06_conflicts.py
git commit -m "feat(phase6): 实现 generate_records_json 输出"
```

---

## 任务 7：generate_report_md + 测试

### 步骤 1：编写测试

```python
# 追加到 test_06_conflicts.py

def test_generate_report_md():
    """验证 Markdown 报告格式"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    records = build_conflict_records(entries)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, 'test_report.md')
        generate_report_md(records, output_path)

        with open(output_path, encoding='utf-8') as f:
            content = f.read()

        # 基本结构检查
        assert '# Phase 6' in content
        assert '统计总览' in content
        assert 'U+E6B5' in content
        assert 'unicode_conflict' in content or 'Unicode 冲突' in content
        assert 'hash_a' in content or 'hash_b' in content
    print('  PASS test_generate_report_md')
```

### 步骤 2：运行测试验证失败

```bash
python pipeline/test_06_conflicts.py
```
预期：FAIL `test_generate_report_md`

### 步骤 3：编写 generate_report_md 实现

```python
# 追加到 06_detect_conflicts.py

def generate_report_md(records, output_path):
    """生成人类可读 Markdown 报告"""
    # 统计
    by_type = defaultdict(int)
    by_severity = defaultdict(int)
    by_type_severity = defaultdict(lambda: defaultdict(int))
    for r in records:
        by_type[r['type']] += 1
        by_severity[r['severity']] += 1
        by_type_severity[r['type']][r['severity']] += 1

    type_labels = {
        'unicode_conflict': 'Unicode 冲突',
        'name_conflict': 'Name 冲突',
        'glyph_duplicate': 'Duplicate Glyph',
    }

    lines = []
    lines.append('# Phase 6 冲突检测报告\n')
    lines.append(f'生成时间: {datetime.now(timezone.utc).isoformat()}\n')

    # 统计总览表
    lines.append('## 统计总览\n')
    lines.append(f'总冲突数: **{len(records)}**\n')
    lines.append('| 类型 | 总数 | Critical | Warning | Info |')
    lines.append('|------|------|----------|---------|------|')
    for t in ['unicode_conflict', 'name_conflict', 'glyph_duplicate']:
        total = by_type.get(t, 0)
        c = by_type_severity[t].get('critical', 0)
        w = by_type_severity[t].get('warning', 0)
        i = by_type_severity[t].get('info', 0)
        lines.append(f'| {type_labels[t]} | {total} | {c} | {w} | {i} |')
    lines.append('')

    # 分级列出冲突
    for severity in ['critical', 'warning', 'info']:
        sev_records = [r for r in records if r['severity'] == severity]
        if not sev_records:
            continue

        sev_label = severity.capitalize()
        lines.append(f'## {sev_label} 冲突 ({len(sev_records)} 个)\n')

        for r in sev_records:
            lines.append(f'### {r["type"]}: {r["key"]} ({r["variantCount"]} 种变体)\n')
            lines.append(f'`resolution_hint`: {r["resolution_hint"]}\n')
            lines.append(f'影响项目: {", ".join(r["affectedProjects"][:5])}\n')

            # 变体列表
            lines.append('| # | glyphHash | Name | 来源数 |')
            lines.append('|---|-----------|------|--------|')
            for i, v in enumerate(r['variants'], 1):
                name = v.get('canonicalName') or '(none)'
                lines.append(f'| {i} | {v["glyphHash"][:12]}... | {name} | {len(v.get("sources", []))} |')
            lines.append('')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
```

### 步骤 4：运行测试验证通过

```bash
python pipeline/test_06_conflicts.py
```
预期：14 PASS, 0 FAIL

### 步骤 5：Commit

```bash
git add pipeline/06_detect_conflicts.py pipeline/test_06_conflicts.py
git commit -m "feat(phase6): 实现 generate_report_md 输出"
```

---

## 任务 8：main 入口 + 真实数据运行

### 步骤 1：编写 main 函数

```python
# 追加到 06_detect_conflicts.py

def main():
    print('=' * 60)
    print('Phase 6: Conflict Detection')
    print('=' * 60)

    os.makedirs('report', exist_ok=True)

    # Load
    print('\n加载 glyph_registry.json ...')
    entries = load_registry()
    print(f'  共 {len(entries)} 条 registry entry')

    # Detect
    print('\n检测冲突...')
    records = build_conflict_records(entries)

    # Stats
    by_type = defaultdict(int)
    by_severity = defaultdict(int)
    for r in records:
        by_type[r['type']] += 1
        by_severity[r['severity']] += 1

    print(f'  Unicode 冲突:   {by_type.get("unicode_conflict", 0)}')
    print(f'  Name 冲突:      {by_type.get("name_conflict", 0)}')
    print(f'  Duplicate Glyph: {by_type.get("glyph_duplicate", 0)}')
    print(f'  总冲突数:       {len(records)}')
    print(f'  Critical:       {by_severity.get("critical", 0)}')
    print(f'  Warning:        {by_severity.get("warning", 0)}')
    print(f'  Info:           {by_severity.get("info", 0)}')

    # Output
    print('\n写入输出文件...')

    records_path = 'report/conflict_records.json'
    generate_records_json(records, records_path)
    print(f'  冲突记录: {records_path}')

    report_path = 'report/conflict_report.md'
    generate_report_md(records, report_path)
    print(f'  报告:     {report_path}')

    print('\nPhase 6 完成！')
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

### 步骤 2：运行主脚本

```bash
python pipeline/06_detect_conflicts.py
```
预期：正常输出，生成 report/conflict_records.json 和 report/conflict_report.md

### 步骤 3：验证输出文件

```bash
python -c "import json; d=json.load(open('report/conflict_records.json')); print('Records:', d['metadata']['total_conflicts']); print('By type:', d['metadata']['by_type'])"
```
预期：显示总冲突数和按类型分类的数量

### 步骤 4：验证报告可读性

```bash
head -30 report/conflict_report.md
```
预期：显示统计总览表

### 步骤 5：运行全部测试确认

```bash
python pipeline/test_06_conflicts.py
```
预期：全部 PASS

### 步骤 6：Commit

```bash
git add pipeline/06_detect_conflicts.py report/conflict_records.json report/conflict_report.md
git commit -m "feat(phase6): 完成冲突检测主脚本 + 真实数据运行"
```

---

## 任务 9：确定性测试

### 步骤 1：编写测试

```python
# 追加到 test_06_conflicts.py

def test_deterministic_output():
    """多次运行 build_conflict_records 输出一致"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B6', 'icon-help', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_d', 'E6B6', 'icon-help', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_e', 'E6C0', 'icon-ok', [
            make_source('asset1', ['proj-a']),
            make_source('asset2', ['proj-b']),
        ]),
    ]

    results = []
    for _ in range(3):
        records = build_conflict_records(entries)
        results.append(json.dumps(records, sort_keys=True, ensure_ascii=False))

    assert results[0] == results[1] == results[2], 'Non-deterministic output!'
    print('  PASS test_deterministic_output')
```

### 步骤 2：运行测试验证

```bash
python pipeline/test_06_conflicts.py
```
预期：15 PASS, 0 FAIL

### 步骤 3：Commit

```bash
git add pipeline/test_06_conflicts.py
git commit -m "test(phase6): 添加确定性输出测试"
```

---

## 验证清单

全部任务完成后，逐项验证：

- [ ] `python pipeline/test_06_conflicts.py` — 全部测试通过
- [ ] `python pipeline/06_detect_conflicts.py` — 正常运行，无报错
- [ ] `report/conflict_records.json` 存在，格式正确，包含 metadata + records
- [ ] `report/conflict_report.md` 存在，可读，分级统计正确
- [ ] Type A + B + C 总数与 registry 数据一致
- [ ] 输出确定性：多次运行 `06_detect_conflicts.py` 生成相同 JSON
