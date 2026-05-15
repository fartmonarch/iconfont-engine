#!/usr/bin/env python3
"""Phase 7 Type A: Apply Unicode Conflict Resolution to Registry

Reads Type A user decisions + conflict_resolver_typea_data.json + glyph_registry.json,
assigns PUA codes to variants marked as PUA groups.

Key fix: decisions keys are IDs from conflict_resolver_typea_data.json (filtered Type A
records), NOT raw conflict_records.json indices.

Usage:
    python pipeline/07_apply_typea_resolution.py --decisions report/phase7_typea_decisions.json

Input:
    registry/glyph_registry.json
    report/conflict_resolver_typea_data.json
    report/phase7_typea_decisions.json

Output:
    registry/glyph_registry_resolved.json
    report/phase7_typea_resolution_report.md
    registry/lineage.json (updated with PUA assignments)
"""
import json
import os
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(DATA_DIR, 'registry', 'glyph_registry.json')
TYPEA_DATA_PATH = os.path.join(
    DATA_DIR, 'report', 'conflict_resolver_typea_data.json')
CONFLICTS_PATH = os.path.join(DATA_DIR, 'report', 'conflict_records.json')
DECISIONS_PATH = os.path.join(
    DATA_DIR, 'report', 'phase7_typea_decisions.json')
OUTPUT_REGISTRY_PATH = os.path.join(
    DATA_DIR, 'registry', 'glyph_registry_resolved.json')
REPORT_PATH = os.path.join(
    DATA_DIR, 'report', 'phase7_typea_resolution_report.md')
LINEAGE_PATH = os.path.join(DATA_DIR, 'registry', 'lineage.json')

PUA_START = 0xE000
PUA_END = 0xF8FF


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


def load_json(path, required=True):
    if not os.path.exists(path):
        if required:
            print(f'Error: not found {path}')
            sys.exit(1)
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class PUAAllocator:
    def __init__(self, start=PUA_START, end=PUA_END):
        self._next = start
        self._end = end
        self._used = set()
        self._log = []

    def mark_used(self, code):
        if code and PUA_START <= code <= PUA_END:
            self._used.add(code)

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
    def log(self):
        return self._log


def apply_resolution():
    parse_args()

    print('=' * 60)
    print('Phase 7: Apply Type A Unicode Conflict Resolution')
    print('=' * 60)
    print(f'Decisions: {DECISIONS_PATH}')

    registry = load_json(REGISTRY_PATH)
    print(f'Registry entries: {len(registry)}')

    typea_data = load_json(TYPEA_DATA_PATH)
    typea_records = typea_data.get('records', [])
    print(f'Type A data records: {len(typea_records)}')

    # Build id -> record lookup
    id_to_record = {}
    for r in typea_records:
        rid = r.get('id')
        if rid is not None:
            id_to_record[int(rid)] = r

    decisions_data = load_json(DECISIONS_PATH, required=False)
    if not decisions_data:
        print('No decisions file found.')
        return 1
    decisions = decisions_data.get('decisions', {})
    print(f'Decisions total: {len(decisions)}')

    # Build glyphHash -> registry entry index lookup
    hash_to_idx = {}
    for idx, entry in enumerate(registry):
        gh = entry.get('glyphHash', '')
        if gh:
            hash_to_idx[gh] = idx

    # Collect all existing PUA codes from registry
    pua = PUAAllocator()
    for entry in registry:
        uc = entry.get('canonicalUnicode')
        if isinstance(uc, int):
            pua.mark_used(uc)
        elif isinstance(uc, str):
            try:
                pua.mark_used(int(uc, 16))
            except ValueError:
                pass

    # Load lineage if exists
    lineage = load_json(LINEAGE_PATH, required=False) or []
    if not isinstance(lineage, list):
        lineage = []

    stats = {
        'keep_groups': 0,
        'pua_groups': 0,
        'pua_allocated': 0,
        'entries_updated': 0,
        'skipped': 0,
    }

    for rid_str, dec in decisions.items():
        rid = int(rid_str)
        record = id_to_record.get(rid)
        if not record:
            stats['skipped'] += 1
            continue

        variants = record.get('variants', [])
        groups = dec.get('groups', [])

        for group in groups:
            gtype = group.get('type')
            vi_list = group.get('variants', [])
            group_variants = [variants[vi]
                              for vi in vi_list if 0 <= vi < len(variants)]

            if not group_variants:
                continue

            if gtype == 'keep':
                stats['keep_groups'] += 1
                # Keep variants retain original unicode - no change needed
                pass
            elif gtype == 'pua':
                stats['pua_groups'] += 1
                # Assign a unique PUA to each variant in the pua group
                for v in group_variants:
                    gh = v.get('glyphHash', '')
                    if not gh or gh not in hash_to_idx:
                        continue

                    idx = hash_to_idx[gh]
                    entry = registry[idx]
                    old_uc = entry.get('canonicalUnicode')
                    old_uc_hex = entry.get('canonicalUnicodeHex', '')

                    new_code = pua.allocate(
                        gh, f"Type A PUA for {record.get('key', '')}")
                    new_uc_hex = f'{new_code:04X}'

                    entry['canonicalUnicode'] = new_code
                    entry['canonicalUnicodeHex'] = new_uc_hex
                    stats['pua_allocated'] += 1
                    stats['entries_updated'] += 1

                    lineage.append({
                        'glyphHash': gh,
                        'action': 'assign_pua',
                        'oldUnicode': old_uc,
                        'oldUnicodeHex': old_uc_hex,
                        'newUnicode': new_code,
                        'newUnicodeHex': new_uc_hex,
                        'reason': f"Type A conflict resolution for {record.get('key', '')}",
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    })

    # ------------------------------------------------------------------
    # Auto-resolve remaining Type A records
    # Only process variants that STILL share the same unicode as keep variant
    # ------------------------------------------------------------------
    auto_resolved = 0

    for record in typea_records:
        rid = record.get('id')
        variants = record.get('variants', [])
        if not variants:
            continue

        dec = decisions.get(str(rid))
        grouped_indices = set()

        if dec:
            for g in dec.get('groups', []):
                grouped_indices.update(g.get('variants', []))

        # Determine which variants need PUA:
        # 1. No decision at all -> auto-group by sourceCount
        # 2. All variants in keep group -> move lowest sourceCount to PUA
        # 3. Some variants ungrouped -> move ungrouped to PUA
        keep_idx = None

        if not dec:
            # No user decision: keep variant with highest sourceCount
            keep_idx = max(range(len(variants)),
                           key=lambda i: variants[i].get('sourceCount', 0))
        elif all(i in grouped_indices for i in range(len(variants))):
            # All grouped
            keep_groups = [g for g in dec.get(
                'groups', []) if g.get('type') == 'keep']
            if keep_groups:
                keep_vi = keep_groups[0].get('variants', [])
                if len(keep_vi) > 1:
                    # Multiple in keep: keep highest sourceCount, PUA rest
                    keep_idx = max(keep_vi,
                                   key=lambda i: variants[i].get('sourceCount', 0))
                elif len(keep_vi) == 1:
                    keep_idx = keep_vi[0]
        else:
            # Some ungrouped: keep the grouped keep variant, PUA rest
            keep_groups = [g for g in dec.get(
                'groups', []) if g.get('type') == 'keep']
            if keep_groups and keep_groups[0].get('variants'):
                keep_idx = keep_groups[0]['variants'][0]

        if keep_idx is None:
            keep_idx = 0

        # Get the current unicode of the keep variant
        keep_gh = variants[keep_idx].get('glyphHash', '')
        keep_uc = None
        if keep_gh and keep_gh in hash_to_idx:
            keep_uc = registry[hash_to_idx[keep_gh]].get('canonicalUnicode')

        for vi in range(len(variants)):
            if vi == keep_idx:
                continue
            v = variants[vi]
            gh = v.get('glyphHash', '')
            if not gh or gh not in hash_to_idx:
                continue

            idx = hash_to_idx[gh]
            entry = registry[idx]

            # Skip if this variant already has a different unicode than keep
            if keep_uc is not None and entry.get('canonicalUnicode') != keep_uc:
                continue

            old_uc = entry.get('canonicalUnicode')
            old_uc_hex = entry.get('canonicalUnicodeHex', '')

            new_code = pua.allocate(
                gh, f"Type A auto PUA for {record.get('key', '')}")
            new_uc_hex = f'{new_code:04X}'

            entry['canonicalUnicode'] = new_code
            entry['canonicalUnicodeHex'] = new_uc_hex
            stats['pua_allocated'] += 1
            stats['entries_updated'] += 1
            auto_resolved += 1

            lineage.append({
                'glyphHash': gh,
                'action': 'assign_pua',
                'oldUnicode': old_uc,
                'oldUnicodeHex': old_uc_hex,
                'newUnicode': new_code,
                'newUnicodeHex': new_uc_hex,
                'reason': f"Type A auto resolution for {record.get('key', '')}",
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })

    if auto_resolved:
        print(f'Auto-resolved {auto_resolved} remaining variants')

    # ------------------------------------------------------------------
    # Phase 3: Resolve any remaining Type A conflicts from current
    # conflict_records.json (catches new conflicts caused by Type B merges)
    # ------------------------------------------------------------------
    current_conflicts = load_json(CONFLICTS_PATH, required=False)
    fallback_resolved = 0

    if current_conflicts:
        # Track hashes already updated in this run
        updated_hashes = set(entry['glyphHash'] for entry in pua.log)

        for record in current_conflicts.get('records', []):
            if record.get('type') != 'unicode_conflict':
                continue

            variants = record.get('variants', [])
            if len(variants) < 2:
                continue

            # Group variants by current canonicalUnicode in registry
            from collections import defaultdict
            uc_groups = defaultdict(list)
            for vi, v in enumerate(variants):
                gh = v.get('glyphHash', '')
                if gh and gh in hash_to_idx:
                    uc = registry[hash_to_idx[gh]].get('canonicalUnicode')
                    uc_groups[uc].append((vi, v))

            # For each group that still has multiple variants sharing a unicode
            for shared_uc, group in uc_groups.items():
                if len(group) < 2:
                    continue

                # Keep the one with highest sourceCount, PUA the rest
                sorted_group = sorted(
                    group,
                    key=lambda x: x[1].get('sourceCount', 0),
                    reverse=True
                )

                # Skip the keep variant, PUA the rest
                for vi, v in sorted_group[1:]:
                    gh = v.get('glyphHash', '')
                    if not gh or gh not in hash_to_idx:
                        continue
                    if gh in updated_hashes:
                        continue  # already updated this run

                    idx = hash_to_idx[gh]
                    entry = registry[idx]
                    old_uc = entry.get('canonicalUnicode')
                    old_uc_hex = entry.get('canonicalUnicodeHex', '')

                    new_code = pua.allocate(
                        gh, f"Type A fallback PUA for {record.get('key', '')}")
                    new_uc_hex = f'{new_code:04X}'

                    entry['canonicalUnicode'] = new_code
                    entry['canonicalUnicodeHex'] = new_uc_hex
                    stats['pua_allocated'] += 1
                    stats['entries_updated'] += 1
                    fallback_resolved += 1
                    updated_hashes.add(gh)

                    lineage.append({
                        'glyphHash': gh,
                        'action': 'assign_pua',
                        'oldUnicode': old_uc,
                        'oldUnicodeHex': old_uc_hex,
                        'newUnicode': new_code,
                        'newUnicodeHex': new_uc_hex,
                        'reason': f"Type A fallback resolution for {record.get('key', '')}",
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    })

    if fallback_resolved:
        print(
            f'Fallback-resolved {fallback_resolved} remaining variants from conflict_records')

    # Save updated registry
    os.makedirs(os.path.dirname(OUTPUT_REGISTRY_PATH) or '.', exist_ok=True)
    with open(OUTPUT_REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    print(
        f'\nOutput registry: {OUTPUT_REGISTRY_PATH} ({len(registry)} entries)')

    # Save updated lineage
    with open(LINEAGE_PATH, 'w', encoding='utf-8') as f:
        json.dump(lineage, f, ensure_ascii=False, indent=2)
    print(f'Output lineage: {LINEAGE_PATH} ({len(lineage)} records)')

    # Generate report
    lines = []
    lines.append('# Phase 7 Type A Unicode Conflict Resolution Report\n')
    lines.append(f'Generated: {datetime.now(timezone.utc).isoformat()}\n')
    lines.append('## Statistics\n')
    lines.append(f'- Keep groups: **{stats["keep_groups"]}**')
    lines.append(f'- PUA groups: **{stats["pua_groups"]}**')
    lines.append(f'- PUA codes allocated: **{stats["pua_allocated"]}**')
    lines.append(f'- Registry entries updated: **{stats["entries_updated"]}**')
    lines.append(f'- Skipped (no matching record): **{stats["skipped"]}**')
    lines.append('')
    if pua.log:
        lines.append('## PUA Assignment Details\n')
        lines.append('| glyphHash | PUA | Reason |')
        lines.append('|-----------|-----|--------|')
        for entry in pua.log:
            lines.append(
                f'| {entry["glyphHash"][:16]}... | {entry["pua"]} | {entry["reason"]} |')
        lines.append('')

    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'Report: {REPORT_PATH}')

    print('\nPhase 7 Type A resolution complete.')
    return 0


if __name__ == '__main__':
    sys.exit(apply_resolution() or 0)
