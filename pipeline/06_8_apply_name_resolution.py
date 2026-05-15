#!/usr/bin/env python3
"""Phase 6.8: Apply Name Conflict Resolution to Registry

Reads Type B user decisions + glyph_registry.json, merges variants according
to decisions, allocates PUA codes, and outputs a resolved registry.

Usage:
    # With user decisions (after manual review):
    python pipeline/06_8_apply_name_resolution.py --decisions report/phase6_8_decisions.json

    # Without decisions (auto-merge false positives only):
    python pipeline/06_8_apply_name_resolution.py

Input:
    registry/glyph_registry.json
    report/filtered_conflicts.json
    report/phase6_8_decisions.json (optional)

Output:
    registry/glyph_registry_resolved.json
    report/phase6_8_resolution_report.md
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(DATA_DIR, 'registry', 'glyph_registry.json')
FILTERED_PATH = os.path.join(DATA_DIR, 'report', 'filtered_conflicts.json')
DECISIONS_PATH = os.path.join(DATA_DIR, 'report', 'phase6_8_decisions.json')
OUTPUT_REGISTRY_PATH = os.path.join(
    DATA_DIR, 'registry', 'glyph_registry_resolved.json')
REPORT_PATH = os.path.join(DATA_DIR, 'report', 'phase6_8_resolution_report.md')


def parse_args():
    global DECISIONS_PATH
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--decisions' and i + 1 < len(args):
            DECISIONS_PATH = os.path.abspath(args[i + 1])
            i += 2
        else:
            i += 1


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
    def log(self):
        return self._log


def load_json(path, required=True):
    if not os.path.exists(path):
        if required:
            print(f'错误: 未找到 {path}')
            sys.exit(1)
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_variants_to_entry(variants, base_name, pua=None):
    """Merge multiple Type B variants into a single registry entry."""
    if not variants:
        return None

    primary = variants[0]

    # Merge sources (deduplicate by assetId/cssUrl)
    all_sources = []
    seen_assets = set()
    for v in variants:
        for s in v.get('sources', []):
            asset_id = s.get('assetId', s.get('cssUrl', ''))
            if asset_id and asset_id not in seen_assets:
                seen_assets.add(asset_id)
                all_sources.append(s)

    # Determine unicode and name
    if pua is not None:
        canonical_unicode = pua
        canonical_unicode_hex = f'{pua:04X}'
        final_name = base_name  # Keep original name; PUA is internal
    else:
        first_source = primary.get('sources', [{}])[0]
        canonical_unicode = first_source.get('originalUnicode')
        canonical_unicode_hex = primary.get('canonicalUnicodeHex', '')
        final_name = base_name

    return {
        'glyphHash': primary['glyphHash'],
        'canonicalName': final_name,
        'canonicalUnicode': canonical_unicode,
        'canonicalUnicodeHex': canonical_unicode_hex,
        'sources': all_sources,
        'contours': primary.get('contours', []),
        'advanceWidth': primary.get('advanceWidth'),
        'glyphType': primary.get('glyphType', 'simple'),
        'mergedVariantCount': len(variants),
        'aliases': sorted(set(v.get('canonicalName') or v.get('name', '') for v in variants)),
    }


def apply_resolution():
    parse_args()

    print('=' * 60)
    print('Phase 6.8: Apply Name Conflict Resolution')
    print('=' * 60)
    print(f'决策文件: {DECISIONS_PATH}')

    # Load inputs
    registry = load_json(REGISTRY_PATH)
    registry_entries = registry if isinstance(
        registry, list) else registry.get('entries', [])
    print(f'\n加载 registry: {len(registry_entries)} entries')

    conflicts_data = load_json(FILTERED_PATH)
    all_records = conflicts_data.get('records', [])

    # Assign original_index for ID consistency
    for i, r in enumerate(all_records):
        r['original_index'] = i

    decisions_data = load_json(DECISIONS_PATH, required=False)
    decisions = decisions_data.get('decisions', {}) if decisions_data else {}
    print(
        f'加载用户决策: {len(decisions)} 条' if decisions else '未找到用户决策，将只自动合并 false positive')

    # Build glyphHash -> registry entry index lookup
    hash_to_idx = {}
    for idx, entry in enumerate(registry_entries):
        gh = entry.get('glyphHash', '')
        if gh:
            hash_to_idx[gh] = idx

    # Track modifications
    entries_to_remove = set()  # indices in registry_entries
    entries_to_add = []
    pua = PUAAllocator()

    stats = {
        'fp_merged': 0,
        'decision_merged': 0,
        'pua_assigned': 0,
        'skipped': 0,
    }

    type_b_records = [r for r in all_records if r.get(
        'type') == 'name_conflict']
    print(f'Type B 记录: {len(type_b_records)} 条')

    for record in type_b_records:
        rid = str(record.get('original_index'))
        record_decision = decisions.get(rid, {})
        base_name = record.get('key', 'unknown')
        variants = record.get('variants', [])

        # Collect glyphHashes in this record
        record_hashes = set(v.get('glyphHash', '') for v in variants)

        # Case 1: False positive (auto-merge all variants)
        if record.get('isFalsePositive') and not record_decision.get('unmerge'):
            new_entry = merge_variants_to_entry(variants, base_name)
            if new_entry:
                # Mark old entries for removal
                for v in variants:
                    gh = v.get('glyphHash', '')
                    if gh in hash_to_idx:
                        entries_to_remove.add(hash_to_idx[gh])
                entries_to_add.append(new_entry)
            stats['fp_merged'] += 1
            continue

        # Case 2: No decision and not false positive -> skip (needs manual review)
        if not record_decision:
            stats['skipped'] += 1
            continue

        # Case 3: Has decision (groups format)
        if 'groups' in record_decision:
            pua_counter = 1  # keep group is implicit v1
            for group in record_decision['groups']:
                vi_list = group.get('variants', [])
                group_variants = [variants[vi]
                                  for vi in vi_list if vi < len(variants)]
                if not group_variants:
                    continue

                if group['type'] == 'keep':
                    new_entry = merge_variants_to_entry(
                        group_variants, base_name)
                else:  # pua
                    pua_counter += 1
                    pua_name = f'{base_name}_v{pua_counter}'
                    # Merge all PUA group variants into ONE entry, assign new PUA unicode
                    new_pua = pua.allocate(
                        group_variants[0]['glyphHash'],
                        f'Type B PUA group for {base_name}'
                    )
                    new_entry = merge_variants_to_entry(
                        group_variants, pua_name, pua=new_pua)
                    stats['pua_assigned'] += 1

                if new_entry:
                    for v in group_variants:
                        gh = v.get('glyphHash', '')
                        if gh in hash_to_idx:
                            entries_to_remove.add(hash_to_idx[gh])
                    entries_to_add.append(new_entry)

            stats['decision_merged'] += 1
        else:
            # Old format: unmerge or simple keep/pua per variant
            # For simplicity, treat as skip for now
            stats['skipped'] += 1

    # Build new registry
    new_registry = []
    removed_hashes = set()
    for idx, entry in enumerate(registry_entries):
        if idx not in entries_to_remove:
            new_registry.append(entry)
        else:
            removed_hashes.add(entry.get('glyphHash', ''))

    new_registry.extend(entries_to_add)

    print(f'\n处理结果:')
    print(f'  False Positive 自动合并: {stats["fp_merged"]}')
    print(f'  按决策合并: {stats["decision_merged"]}')
    print(f'  PUA 分配: {stats["pua_assigned"]}')
    print(f'  跳过(待审核): {stats["skipped"]}')
    print(f'  移除旧 entries: {len(entries_to_remove)}')
    print(f'  新增合并 entries: {len(entries_to_add)}')
    print(f'  Registry: {len(registry_entries)} -> {len(new_registry)}')

    # Save resolved registry
    os.makedirs(os.path.dirname(OUTPUT_REGISTRY_PATH) or '.', exist_ok=True)
    with open(OUTPUT_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_registry, f, ensure_ascii=False, indent=2)
    print(f'\n输出: {OUTPUT_REGISTRY_PATH}')

    # Generate report
    lines = []
    lines.append('# Phase 6.8 Name Conflict Resolution Report\n')
    lines.append(f'生成时间: {datetime.now(timezone.utc).isoformat()}\n')
    lines.append('## 统计\n')
    lines.append(f'- False Positive 自动合并: **{stats["fp_merged"]}**')
    lines.append(f'- 按决策合并: **{stats["decision_merged"]}**')
    lines.append(f'- PUA 分配: **{stats["pua_assigned"]}**')
    lines.append(f'- 跳过(待审核): **{stats["skipped"]}**')
    lines.append(
        f'- Registry 变化: {len(registry_entries)} -> {len(new_registry)}')
    lines.append('')
    if pua.log:
        lines.append('## PUA 分配明细\n')
        lines.append('| glyphHash | PUA | 原因 |')
        lines.append('|-----------|-----|------|')
        for entry in pua.log:
            lines.append(
                f'| {entry["glyphHash"][:12]}... | {entry["pua"]} | {entry["reason"]} |')
        lines.append('')

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'报告: {REPORT_PATH}')

    print('\nPhase 6.8 完成。')
    return 0


if __name__ == '__main__':
    sys.exit(apply_resolution())
