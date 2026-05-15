#!/usr/bin/env python3
"""Phase 6.8: Name-first Pre-resolution (Simulation)

Simulates the effect of resolving Type B (name_conflict) false positives
BEFORE re-detecting Type A (unicode_conflict) conflicts.

Logic:
  1. Read filtered_conflicts.json
  2. Identify Type B records where isFalsePositive=True
  3. Build name -> canonical glyphHash mapping
  4. For each Type A record, if a variant's name is in the mapping,
     replace its glyphHash with the canonical one
  5. Re-check Type A: if all variants now share the same glyphHash,
     the record disappears (no longer a conflict)
  6. Output statistics and intermediate data files

Usage:
    python pipeline/06_8_resolve_names.py

Input:
    report/filtered_conflicts.json

Output:
    report/name_first_simulation_report.md
    report/name_first_type_a_remaining.json  -- Type A records after simulation
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILTERED_PATH = os.path.join(DATA_DIR, 'report', 'filtered_conflicts.json')
REPORT_PATH = os.path.join(
    DATA_DIR, 'report', 'name_first_simulation_report.md')
REMAINING_PATH = os.path.join(
    DATA_DIR, 'report', 'name_first_type_a_remaining.json')
V2_PATH = os.path.join(DATA_DIR, 'report', 'filtered_conflicts_v2.json')


def load_filtered_conflicts():
    with open(FILTERED_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def simulate_name_first_resolution(data):
    records = data.get('records', [])

    # Separate by type
    type_a_records = [r for r in records if r.get(
        'type') == 'unicode_conflict']
    type_b_records = [r for r in records if r.get('type') == 'name_conflict']

    # Step 1: Find false positive Type B records
    fp_type_b = [r for r in type_b_records if r.get('isFalsePositive')]
    non_fp_type_b = [r for r in type_b_records if not r.get('isFalsePositive')]

    # Step 2: Build name -> canonical glyphHash mapping
    # For false positive Type B, all variants are visually identical,
    # so we pick the first variant's glyphHash as canonical
    name_to_canonical_hash = {}
    for r in fp_type_b:
        name = r.get('key', '')
        variants = r.get('variants', [])
        if variants and name:
            # Use first variant's glyphHash as canonical
            canonical_hash = variants[0].get('glyphHash', '')
            name_to_canonical_hash[name] = canonical_hash

    # Also build a mapping from variant glyphHash -> canonical glyphHash
    # This handles cases where the same name has multiple glyphHashes
    # and we want to normalize all of them to the canonical one
    hash_replacements = {}  # old_hash -> canonical_hash
    for r in fp_type_b:
        name = r.get('key', '')
        canonical = name_to_canonical_hash.get(name)
        if not canonical:
            continue
        for v in r.get('variants', []):
            old_hash = v.get('glyphHash', '')
            if old_hash and old_hash != canonical:
                hash_replacements[old_hash] = canonical

    # Step 3: Apply hash replacements to Type A records
    eliminated_records = []
    remaining_records = []
    modified_records = []

    for r in type_a_records:
        variants = r.get('variants', [])
        modified = False

        # Replace glyphHashes for variants whose name is in the mapping
        for v in variants:
            name = v.get('canonicalName') or v.get('name', '')
            if name in name_to_canonical_hash:
                canonical = name_to_canonical_hash[name]
                if v.get('glyphHash') != canonical:
                    v['glyphHash'] = canonical
                    modified = True

        # Check if all variants now have the same glyphHash
        unique_hashes = set(v.get('glyphHash', '') for v in variants)
        if len(unique_hashes) <= 1:
            eliminated_records.append(r)
        else:
            remaining_records.append(r)
            if modified:
                modified_records.append(r)

    return {
        'type_a_total': len(type_a_records),
        'type_b_total': len(type_b_records),
        'fp_type_b_count': len(fp_type_b),
        'non_fp_type_b_count': len(non_fp_type_b),
        'name_mappings': len(name_to_canonical_hash),
        'hash_replacements': len(hash_replacements),
        'type_a_eliminated': len(eliminated_records),
        'type_a_remaining': len(remaining_records),
        'type_a_modified': len(modified_records),
        'eliminated_records': eliminated_records,
        'remaining_records': remaining_records,
        'modified_records': modified_records,
        'fp_type_b_records': fp_type_b,
        'non_fp_type_b_records': non_fp_type_b,
    }


def generate_report(result, output_path):
    lines = []
    lines.append('# Phase 6.8 Name-first Pre-resolution 模拟报告\n')
    lines.append(f'生成时间: {datetime.now(timezone.utc).isoformat()}\n')

    lines.append('## 统计总览\n')
    lines.append(f'- Type A 原始总数: **{result["type_a_total"]}**')
    lines.append(f'- Type B 原始总数: **{result["type_b_total"]}**')
    lines.append(f'  - False Positive (自动合并): **{result["fp_type_b_count"]}**')
    lines.append(
        f'  - 非 False Positive (需人工审核): **{result["non_fp_type_b_count"]}**')
    lines.append(f'- 名称映射数: **{result["name_mappings"]}**')
    lines.append(f'- Hash 替换数: **{result["hash_replacements"]}**')
    lines.append('')
    lines.append('## Type A 变化\n')
    lines.append(
        f'- 消除的 Type A 记录: **{result["type_a_eliminated"]}** ({result["type_a_eliminated"]/result["type_a_total"]*100:.1f}%)')
    lines.append(
        f'- 剩余的 Type A 记录: **{result["type_a_remaining"]}** ({result["type_a_remaining"]/result["type_a_total"]*100:.1f}%)')
    lines.append(f'- 被修改但未消除的: **{result["type_a_modified"]}**')
    lines.append('')

    # Detail: eliminated records
    if result['eliminated_records']:
        lines.append('## 被消除的 Type A 记录\n')
        lines.append('| Unicode | 变体数 | 保留名称 | 说明 |')
        lines.append('|---------|--------|----------|------|')
        for r in result['eliminated_records'][:30]:
            names = [v.get('canonicalName') or v.get('name', '')
                     for v in r.get('variants', [])]
            unique_names = sorted(set(n for n in names if n))
            lines.append(
                f'| {r.get("key", "")} | {len(r.get("variants", []))} | {", ".join(unique_names[:3])} | 合并后所有变体共享同一 glyphHash |')
        if len(result['eliminated_records']) > 30:
            lines.append(
                f'\n... 共 {len(result["eliminated_records"])} 条，仅显示前 30 条')
        lines.append('')

    # Detail: non-fp Type B records
    if result['non_fp_type_b_records']:
        lines.append('## 仍需人工审核的 Type B 记录 (非 False Positive)\n')
        lines.append('| 名称 | 变体数 | 相似度 | 来源项目 |')
        lines.append('|------|--------|--------|----------|')
        for r in result['non_fp_type_b_records'][:20]:
            projects = r.get('affectedProjects', [])
            score = r.get('similarityScore', 'N/A')
            lines.append(
                f'| {r.get("key", "")} | {len(r.get("variants", []))} | {score} | {", ".join(projects[:3])} |')
        if len(result['non_fp_type_b_records']) > 20:
            lines.append(
                f'\n... 共 {len(result["non_fp_type_b_records"])} 条，仅显示前 20 条')
        lines.append('')

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def generate_remaining_json(result, output_path):
    """Generate a JSON file with the remaining Type A records after simulation."""
    output = {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'originalTypeACount': result['type_a_total'],
            'eliminatedCount': result['type_a_eliminated'],
            'remainingCount': result['type_a_remaining'],
            'simulationNote': 'Type B false positives have been pre-resolved',
        },
        'records': result['remaining_records'],
    }
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def generate_v2_conflicts(result, original_data, output_path):
    """Generate filtered_conflicts_v2.json for the new review UI.

    Contains:
      - Remaining Type A records (after hash replacements)
      - Non-false-positive Type B records (still need manual review)
      - Type C records (auto-merged, no review needed)
    """
    # Build v2 records: remaining Type A + non-fp Type B + Type C
    v2_records = []

    # Add remaining Type A (with hash replacements already applied)
    for r in result['remaining_records']:
        v2_records.append(r)

    # Add non-false-positive Type B (still need review)
    for r in result['non_fp_type_b_records']:
        v2_records.append(r)

    # Add Type C records (they don't need review but keep for completeness)
    original_records = original_data.get('records', [])
    type_c_records = [r for r in original_records if r.get(
        'type') == 'glyph_duplicate']
    for r in type_c_records:
        v2_records.append(r)

    # Sort by severity: critical -> warning -> info
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    v2_records.sort(key=lambda r: (severity_order.get(
        r.get('severity', 'info'), 9), r.get('key', '')))

    # Build metadata
    by_type = {}
    for r in v2_records:
        t = r.get('type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1

    output = {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'totalConflicts': len(v2_records),
            'byType': by_type,
            'preResolved': {
                'typeBEliminated': result['fp_type_b_count'],
                'typeAEliminated': result['type_a_eliminated'],
                'note': 'Type B false positives have been pre-resolved. Type A conflicts reduced.',
            },
        },
        'records': v2_records,
    }
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    print('=' * 60)
    print('Phase 6.8: Name-first Pre-resolution (Simulation)')
    print('=' * 60)

    if not os.path.exists(FILTERED_PATH):
        print(f'\n错误: 未找到 {FILTERED_PATH}')
        return 1

    data = load_filtered_conflicts()
    result = simulate_name_first_resolution(data)

    print(f'\nType A 原始总数: {result["type_a_total"]}')
    print(f'Type B 原始总数: {result["type_b_total"]}')
    print(f'  - False Positive (自动合并): {result["fp_type_b_count"]}')
    print(f'  - 非 False Positive (需人工): {result["non_fp_type_b_count"]}')
    print(f'\n名称映射数: {result["name_mappings"]}')
    print(f'Hash 替换数: {result["hash_replacements"]}')
    print(f'\nType A 变化:')
    print(
        f'  - 消除: {result["type_a_eliminated"]} ({result["type_a_eliminated"]/result["type_a_total"]*100:.1f}%)')
    print(
        f'  - 剩余: {result["type_a_remaining"]} ({result["type_a_remaining"]/result["type_a_total"]*100:.1f}%)')
    print(f'  - 修改但未消除: {result["type_a_modified"]}')

    generate_report(result, REPORT_PATH)
    print(f'\n报告: {REPORT_PATH}')

    generate_remaining_json(result, REMAINING_PATH)
    print(f'数据: {REMAINING_PATH}')

    generate_v2_conflicts(result, data, V2_PATH)
    print(f'v2 冲突数据: {V2_PATH}')

    print('\nPhase 6.8 模拟完成。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
