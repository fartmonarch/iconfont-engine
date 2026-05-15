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
from datetime import datetime, timezone


# ─── CONFLICT_RECORD 数据模型 ──────────────────────────────────────
# {
#   "type": "unicode_conflict",
#   "severity": "critical" | "warning" | "info",
#   "key": "U+E6B5",
#   "variantCount": 2,
#   "variants": [...],
#   "affectedAssets": ["asset1", "asset2"],
#   "affectedProjects": ["proj-a", "proj-b"],
#   "resolution_hint": "assign_pua"
# }


def load_registry(registry_path=None):
    """加载 glyph_registry.json，优先使用 resolved 版本。"""
    if registry_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        resolved_path = os.path.join(
            base_dir, 'registry', 'glyph_registry_resolved.json')
        default_path = os.path.join(
            base_dir, 'registry', 'glyph_registry.json')
        registry_path = resolved_path if os.path.exists(
            resolved_path) else default_path
    with open(registry_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def classify_severity(variant_count):
    """
    根据变体数量分级：
      - critical: 5+
      - warning: 3-4
      - info: 2
    """
    if variant_count >= 5:
        return 'critical'
    elif variant_count >= 3:
        return 'warning'
    else:
        return 'info'


def _build_conflict_record(conflict_type, key, group, resolution_hint):
    """
    组装 CONFLICT_RECORD。

    Args:
        conflict_type: e.g. 'unicode_conflict'
        key: e.g. 'U+E6B5'
        group: list of entries sharing the same key
        resolution_hint: e.g. 'assign_pua', 'rename', 'merge'

    Returns:
        dict conform CONFLICT_RECORD 数据模型
    """
    variants = []
    affected_assets = set()
    affected_projects = set()

    for entry in group:
        variants.append({
            'glyphHash': entry['glyphHash'],
            'canonicalUnicodeHex': entry['canonicalUnicodeHex'],
            'canonicalName': entry['canonicalName'],
            'sources': entry['sources'],
            'contours': entry.get('contours'),
            'advanceWidth': entry.get('advanceWidth'),
        })
        for src in entry.get('sources', []):
            affected_assets.add(src['assetId'])
            for proj in src.get('projects', []):
                affected_projects.add(proj)

    variant_count = len(variants)
    severity = classify_severity(variant_count)

    return {
        'type': conflict_type,
        'severity': severity,
        'key': key,
        'variantCount': variant_count,
        'variants': variants,
        'affectedAssets': sorted(affected_assets),
        'affectedProjects': sorted(affected_projects),
        'resolution_hint': resolution_hint,
    }


def detect_unicode_conflicts(entries):
    """
    检测 Type A: Unicode 冲突。

    按 canonicalUnicode 分组，找出同一 unicode 对应多个不同 glyphHash 的情况。

    Args:
        entries: list of registry entries (glyph_registry.json 数组)

    Returns:
        list of CONFLICT_RECORD
    """
    # 按 unicode 分组，跳过 null unicode
    unicode_groups = defaultdict(list)
    for entry in entries:
        uni = entry.get('canonicalUnicode')
        if uni is None:
            continue
        unicode_groups[uni].append(entry)

    conflicts = []
    for uni, group in unicode_groups.items():
        # 检查是否有不同的 glyphHash
        unique_hashes = set(e['glyphHash'] for e in group)
        if len(unique_hashes) <= 1:
            # 同一 unicode 同一 glyphHash -> 只是多来源，不算冲突
            continue

        key = f'U+{group[0]["canonicalUnicodeHex"]}'
        record = _build_conflict_record(
            conflict_type='unicode_conflict',
            key=key,
            group=group,
            resolution_hint='assign_pua',
        )
        conflicts.append(record)

    return conflicts


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


def detect_duplicate_glyphs(entries):
    """Type C: 同 glyphHash 多来源（正常合并情况）"""
    conflicts = []
    for e in entries:
        sources = e.get('sources', [])
        if len(sources) > 1:
            record = _build_conflict_record(
                conflict_type='glyph_duplicate',
                key=e['glyphHash'],
                group=[e],
                resolution_hint='merge_alias',
            )
            # variantCount 是 entry 数（=1），severity 按 source 数分级
            record['severity'] = classify_severity(len(sources))
            conflicts.append(record)

    return conflicts


def build_conflict_records(entries):
    """整合三类冲突检测结果，返回所有 CONFLICT_RECORD 列表"""
    unicode_conflicts = detect_unicode_conflicts(entries)
    name_conflicts = detect_name_conflicts(entries)
    duplicate_conflicts = detect_duplicate_glyphs(entries)

    all_records = unicode_conflicts + name_conflicts + duplicate_conflicts

    # 按 severity 排序: critical → warning → info
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_records.sort(key=lambda r: (
        severity_order.get(r['severity'], 9), r['key']))

    return all_records


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

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def generate_report_md(records, output_path):
    """生成人类可读 Markdown 报告"""
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
            lines.append(
                f'### {r["type"]}: {r["key"]} ({r["variantCount"]} 种变体)\n')
            lines.append(f'`resolution_hint`: {r["resolution_hint"]}\n')
            lines.append(f'影响项目: {", ".join(r["affectedProjects"][:5])}\n')

            # 变体列表
            lines.append('| # | glyphHash | Name | 来源数 |')
            lines.append('|---|-----------|------|--------|')
            for idx, v in enumerate(r['variants'], 1):
                name = v.get('canonicalName') or '(none)'
                gh = v['glyphHash']
                gh_display = gh[:12] + '...' if len(gh) > 12 else gh
                lines.append(
                    f'| {idx} | {gh_display} | {name} | {len(v.get("sources", []))} |')
            lines.append('')

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    """主入口：运行冲突检测"""
    print('=' * 60)
    print('Phase 6: Conflict Detection（冲突检测）')
    print('=' * 60)

    registry = load_registry()
    entries = registry if isinstance(registry, list) else registry.get(
        'entries', registry.get('registry', []))

    print(f'\n加载 registry: {len(entries)} entries')

    # 检测全部冲突
    records = build_conflict_records(entries)

    # 统计
    by_type = defaultdict(int)
    by_severity = defaultdict(int)
    for r in records:
        by_type[r['type']] += 1
        by_severity[r['severity']] += 1

    print(f'\n[Type A] Unicode 冲突:    {by_type.get("unicode_conflict", 0)} 个')
    print(f'[Type B] Name 冲突:       {by_type.get("name_conflict", 0)} 个')
    print(f'[Type C] Duplicate Glyph: {by_type.get("glyph_duplicate", 0)} 个')
    print(f'\n总冲突数: {len(records)}')
    print(f'  Critical: {by_severity.get("critical", 0)}')
    print(f'  Warning:  {by_severity.get("warning", 0)}')
    print(f'  Info:     {by_severity.get("info", 0)}')

    # 输出报告
    report_dir = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), 'report')
    os.makedirs(report_dir, exist_ok=True)

    records_path = os.path.join(report_dir, 'conflict_records.json')
    generate_records_json(records, records_path)
    print(f'\n输出: {records_path}')

    md_path = os.path.join(report_dir, 'conflict_report.md')
    generate_report_md(records, md_path)
    print(f'输出: {md_path}')

    print('\nPhase 6 完成。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
