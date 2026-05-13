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
from collections import defaultdict


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
    """加载 glyph_registry.json"""
    if registry_path is None:
        registry_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'registry', 'glyph_registry.json',
        )
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


def main():
    """主入口：运行冲突检测"""
    print('=' * 60)
    print('Phase 6: Conflict Detection（冲突检测）')
    print('=' * 60)

    registry = load_registry()
    entries = registry if isinstance(registry, list) else registry.get('entries', registry.get('registry', []))

    print(f'\n加载 registry: {len(entries)} entries')

    # Type A: Unicode conflicts
    unicode_conflicts = detect_unicode_conflicts(entries)
    print(f'\n[Type A] Unicode 冲突: {len(unicode_conflicts)} 个')

    for rec in unicode_conflicts:
        sev_icon = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(rec['severity'], '⚪')
        print(f'  {sev_icon} [{rec["severity"].upper()}] {rec["key"]}: {rec["variantCount"]} variants')
        print(f'      来源: {", ".join(rec["affectedProjects"])}')

    # 输出报告
    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'report')
    os.makedirs(report_dir, exist_ok=True)

    # JSON records
    all_conflicts = unicode_conflicts  # 后续可追加 Type B/C
    records_path = os.path.join(report_dir, 'conflict_records.json')
    with open(records_path, 'w', encoding='utf-8') as f:
        json.dump(all_conflicts, f, indent=2, ensure_ascii=False)
    print(f'\n输出: {records_path} ({len(all_conflicts)} records)')

    # Markdown report
    md_path = os.path.join(report_dir, 'conflict_report.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('# Phase 6: Conflict Report\n\n')
        f.write(f'总冲突数: {len(all_conflicts)}\n\n')

        severity_counts = defaultdict(int)
        for rec in all_conflicts:
            severity_counts[rec['severity']] += 1

        f.write('## 分级统计\n\n')
        for sev in ['critical', 'warning', 'info']:
            f.write(f'- **{sev.upper()}**: {severity_counts.get(sev, 0)}\n')
        f.write('\n')

        for rec in all_conflicts:
            f.write(f'### {rec["key"]} — [{rec["severity"].upper()}]\n\n')
            f.write(f'- 类型: {rec["type"]}\n')
            f.write(f'- 变体数: {rec["variantCount"]}\n')
            f.write(f'- 影响项目: {", ".join(rec["affectedProjects"])}\n')
            f.write(f'- 解决建议: {rec["resolution_hint"]}\n\n')

    print(f'输出: {md_path}')
    print('\nPhase 6 完成。')


if __name__ == '__main__':
    main()
