#!/usr/bin/env python3
"""Phase 7: Conflict Resolution — Decision Engine

Consumes phase7_decisions.json (user decisions) + conflict_records.json + glyph_registry.json,
resolves all conflicts (Type A/B/C), allocates PUA codes, and outputs clean mappings.

Usage:
    python pipeline/07_resolve_conflicts.py [--decisions=report/phase7_decisions.json]

Output:
    report/phase7_resolution.json        — Phase 8 input
    report/phase7_resolution_report.md   — Human-readable audit log
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICTS_PATH = os.path.join(DATA_DIR, 'report', 'conflict_records.json')
REGISTRY_PATH = os.path.join(DATA_DIR, 'registry', 'glyph_registry.json')
DECISIONS_PATH = os.path.join(DATA_DIR, 'report', 'phase7_decisions.json')
RESOLUTION_PATH = os.path.join(DATA_DIR, 'report', 'phase7_resolution.json')
REPORT_PATH = os.path.join(DATA_DIR, 'report', 'phase7_resolution_report.md')

PUA_START = 0xE000
PUA_END = 0xF8FF


class PUAAllocator:
    """Sequential PUA code allocator."""

    def __init__(self, start=PUA_START, end=PUA_END):
        self._next = start
        self._end = end
        self._used = set()
        self._log = []

    def allocate(self, glyph_hash, reason=''):
        while self._next <= self._end and self._next in self._used:
            self._next += 1
        if self._next > self._end:
            raise RuntimeError(f'PUA range exhausted at U+{self._next:04X}')
        code = self._next
        self._used.add(code)
        self._next += 1
        self._log.append({
            'glyphHash': glyph_hash,
            'pua': f'U+{code:04X}',
            'reason': reason,
        })
        return code

    @property
    def assigned_count(self):
        return len(self._used)

    @property
    def range_used(self):
        if not self._used:
            return 'none'
        return f'U+{min(self._used):04X}-U+{max(self._used):04X}'

    @property
    def log(self):
        return self._log


def load_conflicts():
    with open(CONFLICTS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_registry():
    with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get('entries', data.get('registry', []))


def load_decisions():
    if not os.path.exists(DECISIONS_PATH):
        return None
    with open(DECISIONS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_type_a(records, decisions, pua):
    """Resolve Unicode conflicts: same unicode, different glyphHash."""
    resolved = []
    stats = {'kept': 0, 'pua_assigned': 0, 'auto_resolved': 0}

    for record in records:
        rid = str(record['id']) if 'id' in record else str(records.index(record))
        record_decisions = decisions.get(rid, {}).get('variants', {}) if decisions else {}

        for vi, v in enumerate(record['variants']):
            glyph = _build_glyph_entry(v, record)
            variant_key = str(vi)
            variant_decision = record_decisions.get(variant_key)

            if variant_decision == 'keep':
                # Keep original unicode/name
                try:
                    glyph['finalUnicode'] = int(record['key'].replace('U+', ''), 16)
                except (ValueError, AttributeError):
                    glyph['finalUnicode'] = None
                glyph['finalUnicodeHex'] = record['key'].replace('U+', '')
                glyph['finalName'] = v.get('canonicalName') or v.get('name', '')
                glyph['resolution'] = 'kept_original'
                stats['kept'] += 1
            else:
                # PUA or undecided: assign PUA code + rename
                pua_code = pua.allocate(v['glyphHash'], f'Type A variant, record key={record["key"]}, vi={vi}')
                glyph['finalUnicode'] = pua_code
                glyph['finalUnicodeHex'] = f'{pua_code:04X}'
                glyph['finalName'] = (v.get('canonicalName') or v.get('name', '')) + f'_v{vi + 1}'
                glyph['resolution'] = 'pua_assigned'
                glyph['aliases'] = [v.get('canonicalName') or v.get('name', '')]
                stats['pua_assigned'] += 1
                if variant_decision is None:
                    stats['auto_resolved'] += 1
            resolved.append(glyph)

    return resolved, stats


def resolve_type_b(records, decisions, pua):
    """Resolve Name conflicts: same name, different glyphHash."""
    resolved = []
    stats = {'kept': 0, 'pua_assigned': 0, 'auto_resolved': 0}

    for record in records:
        rid = str(record['id']) if 'id' in record else str(records.index(record))
        record_decisions = decisions.get(rid, {}).get('variants', {}) if decisions else {}
        base_name = record.get('key', 'unknown')

        for vi, v in enumerate(record['variants']):
            glyph = _build_glyph_entry(v, record)
            variant_key = str(vi)
            variant_decision = record_decisions.get(variant_key)

            if variant_decision == 'keep':
                # Keep original name, original unicode
                glyph['finalUnicode'] = v.get('sources', [{}])[0].get('originalUnicode')
                if glyph['finalUnicode']:
                    glyph['finalUnicodeHex'] = f'{glyph["finalUnicode"]:04X}'
                else:
                    glyph['finalUnicodeHex'] = ''
                glyph['finalName'] = base_name
                glyph['resolution'] = 'kept_original'
                stats['kept'] += 1
            else:
                # PUA or undecided
                suffix_name = base_name + f'_v{vi + 1}'
                pua_code = pua.allocate(v['glyphHash'], f'Type B variant, name={base_name}, vi={vi}')
                glyph['finalUnicode'] = pua_code
                glyph['finalUnicodeHex'] = f'{pua_code:04X}'
                glyph['finalName'] = suffix_name
                glyph['resolution'] = 'pua_assigned'
                glyph['aliases'] = [base_name]
                stats['pua_assigned'] += 1
                if variant_decision is None:
                    stats['auto_resolved'] += 1
            resolved.append(glyph)

    return resolved, stats


def resolve_type_c_auto(registry_entries):
    """Auto-resolve Type C: same glyphHash, multiple sources. Just merge aliases."""
    resolved = []
    merged_count = 0

    for entry in registry_entries:
        sources = entry.get('sources', [])
        if len(sources) <= 1:
            continue

        glyph = {
            'glyphHash': entry['glyphHash'],
            'finalUnicode': entry.get('canonicalUnicode'),
            'finalUnicodeHex': entry.get('canonicalUnicodeHex'),
            'finalName': entry.get('canonicalName') or '',
            'aliases': entry.get('aliases', []),
            'advanceWidth': entry.get('advanceWidth'),
            'glyphType': entry.get('glyphType', 'unknown'),
            'resolution': 'alias_merged',
            'sources': sources,
        }
        # Merge alias names from all sources
        all_names = set()
        for src in sources:
            css_name = src.get('cssUrl', '').split('/')[-1].replace('.css', '')
            # We already have canonicalName from the registry
        if entry.get('aliases'):
            all_names.update(entry['aliases'])
        glyph['aliases'] = sorted(all_names)
        glyph['mergedSourceCount'] = len(sources)

        resolved.append(glyph)
        merged_count += 1

    return resolved, {'merged': merged_count}


def _build_glyph_entry(variant, record):
    """Build a glyph entry from a variant within a conflict record."""
    sources = variant.get('sources', [])
    # Collect all project names
    projects = set()
    for s in sources:
        for p in s.get('projects', []):
            projects.add(p)

    return {
        'glyphHash': variant['glyphHash'],
        'finalUnicode': None,
        'finalUnicodeHex': '',
        'finalName': '',
        'aliases': [],
        'advanceWidth': variant.get('advanceWidth'),
        'glyphType': 'simple',
        'resolution': '',
        'conflictRecordKey': record.get('key', ''),
        'conflictType': record.get('type', ''),
        'sources': sources,
        'affectedProjects': sorted(projects),
    }


def build_alias_map(resolved_glyphs):
    """Build name → glyphHash map for alias lookup."""
    alias_map = {}
    for g in resolved_glyphs:
        if g.get('finalName'):
            alias_map[g['finalName']] = g['glyphHash']
        for alias in g.get('aliases', []):
            alias_map[alias] = g['glyphHash']
    return alias_map


def generate_resolution_json(resolved_glyphs, pua, type_a_stats, type_b_stats, type_c_stats, decisions):
    """Build the final phase7_resolution.json output."""
    return {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'decisionsSource': DECISIONS_PATH if decisions else 'none (auto-resolved)',
            'totalGlyphs': len(resolved_glyphs),
            'resolvedConflicts': type_a_stats['kept'] + type_a_stats['pua_assigned'] + type_a_stats['auto_resolved'] +
                                 type_b_stats['kept'] + type_b_stats['pua_assigned'] + type_b_stats['auto_resolved'],
            'puaCodesAssigned': pua.assigned_count,
            'puaRangeUsed': pua.range_used,
            'stats': {
                'type_a': type_a_stats,
                'type_b': type_b_stats,
                'type_c': type_c_stats,
            },
        },
        'glyphs': resolved_glyphs,
        'aliasMap': build_alias_map(resolved_glyphs),
        'puaAssignmentLog': pua.log,
    }


def generate_report_md(resolution, output_path):
    """Generate human-readable markdown report."""
    meta = resolution['metadata']
    glyphs = resolution['glyphs']
    lines = []

    lines.append('# Phase 7 冲突解决报告\n')
    lines.append(f'生成时间: {meta["generatedAt"]}\n')

    lines.append('## 统计总览\n')
    lines.append(f'总 Glyph 数: **{meta["totalGlyphs"]}**\n')
    lines.append(f'已解决冲突: **{meta["resolvedConflicts"]}**\n')
    lines.append(f'PUA 分配数: **{meta["puaCodesAssigned"]}**\n')
    lines.append(f'PUA 使用范围: `{meta["puaRangeUsed"]}`\n')
    lines.append(f'决策来源: {meta["decisionsSource"]}\n')

    # Stats by type
    stats = meta['stats']
    lines.append('## 按类型统计\n')
    lines.append('| 类型 | 保留原始 | PUA 分配 | 自动解决 |')
    lines.append('|------|----------|----------|----------|')
    ta = stats['type_a']
    tb = stats['type_b']
    tc = stats['type_c']
    lines.append(f'| Type A (Unicode) | {ta["kept"]} | {ta["pua_assigned"]} | {ta["auto_resolved"]} |')
    lines.append(f'| Type B (Name)    | {tb["kept"]} | {tb["pua_assigned"]} | {tb["auto_resolved"]} |')
    lines.append(f'| Type C (Alias)   | — | — | {tc["merged"]} |')
    lines.append('')

    # Resolution breakdown
    by_resolution = defaultdict(int)
    for g in glyphs:
        by_resolution[g.get('resolution', 'unknown')] += 1

    lines.append('## 解决方式分布\n')
    lines.append('| 解决方式 | 数量 |')
    lines.append('|----------|------|')
    for k, v in sorted(by_resolution.items(), key=lambda x: -x[1]):
        lines.append(f'| {k} | {v} |')
    lines.append('')

    # PUA assignment summary
    if resolution.get('puaAssignmentLog'):
        lines.append('## PUA 分配明细\n')
        lines.append('| glyphHash | PUA | 原因 |')
        lines.append('|-----------|-----|------|')
        for entry in resolution['puaAssignmentLog'][:50]:
            lines.append(f'| {entry["glyphHash"][:12]}... | {entry["pua"]} | {entry["reason"][:60]} |')
        if len(resolution['puaAssignmentLog']) > 50:
            lines.append(f'\n... 共 {len(resolution["puaAssignmentLog"])} 条分配记录')
        lines.append('')

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    print('=' * 60)
    print('Phase 7: Conflict Resolution — Decision Engine')
    print('=' * 60)

    # Load inputs
    if not os.path.exists(CONFLICTS_PATH):
        print(f'\n错误: 未找到冲突数据 {CONFLICTS_PATH}')
        return 1

    conflicts_data = load_conflicts()
    records = conflicts_data.get('records', [])
    print(f'\n加载冲突数据: {len(records)} 条')

    registry = load_registry()
    print(f'加载 glyph registry: {len(registry)} entries')

    decisions_data = load_decisions()
    decisions = decisions_data.get('decisions', {}) if decisions_data else {}

    # Migrate old format (action/variantIndex) to new format (variants map)
    for rid, dec in list(decisions.items()):
        if 'variants' not in dec and 'action' in dec:
            decisions[rid] = {
                'recordType': dec.get('recordType', ''),
                'key': dec.get('key', ''),
                'variants': {str(dec['variantIndex']): dec['action']}
            }

    decided_count = len(decisions)
    if decided_count:
        print(f'加载用户决策: {decided_count} 条')
    else:
        print('未找到用户决策文件，将自动解决所有冲突')

    # Separate by type
    type_a_records = [r for r in records if r['type'] == 'unicode_conflict']
    type_b_records = [r for r in records if r['type'] == 'name_conflict']
    print(f'Type A: {len(type_a_records)} 条')
    print(f'Type B: {len(type_b_records)} 条')

    # PUA allocator
    pua = PUAAllocator()

    # Resolve Type A
    resolved_a, type_a_stats = resolve_type_a(type_a_records, decisions, pua)
    print(f'\nType A 解决: {type_a_stats}')

    # Resolve Type B
    resolved_b, type_b_stats = resolve_type_b(type_b_records, decisions, pua)
    print(f'Type B 解决: {type_b_stats}')

    # Auto-resolve Type C
    resolved_c, type_c_stats = resolve_type_c_auto(registry)
    print(f'Type C 自动合并: {type_c_stats}')

    # Combine all resolved glyphs
    # Deduplicate by glyphHash — keep the first occurrence
    seen_hashes = set()
    all_resolved = []
    for g in resolved_a + resolved_b + resolved_c:
        if g['glyphHash'] not in seen_hashes:
            seen_hashes.add(g['glyphHash'])
            all_resolved.append(g)
        else:
            # Merge: if both entries have the same glyphHash, combine sources
            existing = next(x for x in all_resolved if x['glyphHash'] == g['glyphHash'])
            existing_sources = {s.get('assetId') for s in existing.get('sources', [])}
            for s in g.get('sources', []):
                if s.get('assetId') not in existing_sources:
                    existing['sources'].append(s)
                    existing_sources.add(s['assetId'])

    print(f'\n最终 Glyph 数: {len(all_resolved)} (去重后)')
    print(f'PUA 分配: {pua.assigned_count} 个 ({pua.range_used})')

    # Build output
    resolution = generate_resolution_json(
        all_resolved, pua, type_a_stats, type_b_stats, type_c_stats, decisions_data)

    # Write outputs
    os.makedirs(os.path.dirname(RESOLUTION_PATH) or '.', exist_ok=True)
    with open(RESOLUTION_PATH, 'w', encoding='utf-8') as f:
        json.dump(resolution, f, ensure_ascii=False, indent=2)
    print(f'\n输出: {RESOLUTION_PATH}')

    generate_report_md(resolution, REPORT_PATH)
    print(f'输出: {REPORT_PATH}')

    print('\nPhase 7 完成。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
