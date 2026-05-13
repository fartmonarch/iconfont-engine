"""
Phase 6: Conflict Detection — Tests

测试覆盖：
  - detect_unicode_conflicts_basic: 同 unicode 不同 glyphHash -> 1 conflict
  - detect_unicode_conflicts_no_conflict: 每个 unicode 只有 1 个 glyphHash -> 0 conflicts
  - detect_unicode_conflicts_same_hash: 同 unicode 同 glyphHash -> 0 conflicts (多来源)
  - detect_unicode_conflicts_null_unicode: null unicode 条目应跳过
"""

import importlib.util
import json
import os
import sys
import tempfile

# Load the module under test
spec = importlib.util.spec_from_file_location(
    'phase6', 'pipeline/06_detect_conflicts.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

detect_unicode_conflicts = mod.detect_unicode_conflicts
detect_name_conflicts = mod.detect_name_conflicts
detect_duplicate_glyphs = mod.detect_duplicate_glyphs
build_conflict_records = mod.build_conflict_records
classify_severity = mod.classify_severity
_build_conflict_record = mod._build_conflict_record
generate_records_json = mod.generate_records_json
generate_report_md = mod.generate_report_md


def make_source(asset_id, projects, css_url=''):
    return {
        'assetId': asset_id,
        'projects': projects,
        'cssUrl': css_url,
    }


def make_entry(glyph_hash, unicode_hex, name, sources):
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


def test_detect_unicode_conflicts_basic():
    """Same unicode, different glyphHash -> 1 conflict"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow-right',
                   [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 1, f'Expected 1 conflict, got {len(conflicts)}'
    rec = conflicts[0]
    assert rec['type'] == 'unicode_conflict'
    assert rec['key'] == 'U+E6B5'
    assert rec['variantCount'] == 2
    assert len(rec['variants']) == 2
    assert 'asset1' in rec['affectedAssets']
    assert 'asset2' in rec['affectedAssets']
    assert rec['resolution_hint'] == 'assign_pua'
    print('  PASS test_detect_unicode_conflicts_basic')


def test_detect_unicode_conflicts_no_conflict():
    """Each unicode has only 1 glyphHash -> 0 conflicts"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-up',
                   [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B7', 'icon-down',
                   [make_source('asset3', ['proj-c'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 0, f'Expected 0 conflicts, got {len(conflicts)}'
    print('  PASS test_detect_unicode_conflicts_no_conflict')


def test_detect_unicode_conflicts_same_hash():
    """Same unicode, same glyphHash -> 0 conflicts (just multi-source)"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(
        conflicts) == 0, f'Expected 0 conflicts (same hash), got {len(conflicts)}'
    print('  PASS test_detect_unicode_conflicts_same_hash')


def test_detect_unicode_conflicts_null_unicode():
    """Entries with null unicode should be skipped"""
    entries = [
        make_entry('hash_a', None, 'icon-unknown',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', None, 'icon-ghost',
                   [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B5', 'icon-arrow',
                   [make_source('asset3', ['proj-c'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    # null entries should be skipped, and the one valid entry has no conflict
    assert len(
        conflicts) == 0, f'Expected 0 conflicts (null skipped), got {len(conflicts)}'
    print('  PASS test_detect_unicode_conflicts_null_unicode')


def test_classify_severity():
    """Severity classification based on variant count"""
    assert classify_severity(5) == 'critical'
    assert classify_severity(10) == 'critical'
    assert classify_severity(3) == 'warning'
    assert classify_severity(4) == 'warning'
    assert classify_severity(2) == 'info'
    assert classify_severity(1) == 'info'  # shouldn't happen but safe default
    print('  PASS test_classify_severity')


def test_detect_name_conflicts_basic():
    """同 name 不同 glyphHash → 冲突"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B7', 'icon-up',
                   [make_source('asset1', ['proj-a'])]),
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
        make_entry('hash_a', 'E6B5', None, [
                   make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', '', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B7', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
    ]
    conflicts = detect_name_conflicts(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_name_conflicts_null_name')


def test_detect_name_conflicts_same_hash():
    """同 name 同 glyphHash → 不冲突"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_a', 'E6B6', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_name_conflicts(entries)
    assert len(conflicts) == 0
    print('  PASS test_detect_name_conflicts_same_hash')


def test_detect_duplicate_glyphs_basic():
    """同 glyphHash 多来源 → Duplicate Glyph"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [
            make_source('asset1', ['proj-a']),
            make_source('asset2', ['proj-b']),
        ]),
        make_entry('hash_b', 'E6B6', 'icon-up',
                   [make_source('asset1', ['proj-a'])]),
    ]
    conflicts = detect_duplicate_glyphs(entries)
    assert len(conflicts) == 1
    assert conflicts[0]['type'] == 'glyph_duplicate'
    assert conflicts[0]['key'] == 'hash_a'
    assert conflicts[0]['variantCount'] == 1
    assert conflicts[0]['resolution_hint'] == 'merge_alias'
    print('  PASS test_detect_duplicate_glyphs_basic')


def test_detect_duplicate_glyphs_single_source():
    """单来源 entry → 不是 duplicate"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-up',
                   [make_source('asset2', ['proj-b'])]),
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
    assert sev_map['hash_b'] == 'critical'
    assert sev_map['hash_a'] == 'info'
    print('  PASS test_detect_duplicate_glyphs_severity')


def test_build_conflict_records_all_types():
    """同时检测三类冲突，验证整合结果"""
    entries = [
        # Type A: U+E6B5 有 2 种不同 glyphHash
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
        # Type B: icon-help 有 2 种不同 glyphHash (different unicode too)
        make_entry('hash_c', 'E6C0', 'icon-help',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_d', 'E6C1', 'icon-help',
                   [make_source('asset2', ['proj-b'])]),
        # Type C: hash_e has multiple sources
        make_entry('hash_e', 'E6D0', 'icon-ok', [
            make_source('asset1', ['proj-a']),
            make_source('asset2', ['proj-b']),
        ]),
        # No conflict
        make_entry('hash_f', 'E6E0', 'icon-clear',
                   [make_source('asset3', ['proj-c'])]),
    ]
    records = build_conflict_records(entries)

    type_counts = {}
    for r in records:
        type_counts[r['type']] = type_counts.get(r['type'], 0) + 1

    assert type_counts.get(
        'unicode_conflict', 0) == 1, f'Expected 1 unicode_conflict, got {type_counts}'
    assert type_counts.get(
        'name_conflict', 0) == 2, f'Expected 2 name_conflict, got {type_counts}'
    assert type_counts.get(
        'glyph_duplicate', 0) == 1, f'Expected 1 glyph_duplicate, got {type_counts}'
    assert len(records) == 4, f'Expected 4 total records, got {len(records)}'
    print('  PASS test_build_conflict_records_all_types')


def test_build_conflict_records_required_fields():
    """验证每条 CONFLICT_RECORD 都有必需字段"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
    ]
    records = build_conflict_records(entries)
    required = ['type', 'severity', 'key', 'variantCount', 'variants',
                'affectedAssets', 'affectedProjects', 'resolution_hint']
    for r in records:
        for field in required:
            assert field in r, f'Missing field: {field} in {r["key"]}'
    print('  PASS test_build_conflict_records_required_fields')


def test_generate_records_json():
    """验证 JSON 输出格式和可读取性"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
    ]
    records = build_conflict_records(entries)

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, 'test_records.json')
        generate_records_json(records, output_path)

        with open(output_path, encoding='utf-8') as f:
            loaded = json.load(f)

        assert isinstance(loaded, dict)
        assert 'metadata' in loaded
        assert 'records' in loaded
        assert loaded['metadata']['total_conflicts'] == len(records)
        assert 'by_type' in loaded['metadata']
        assert 'by_severity' in loaded['metadata']
        assert loaded['metadata']['by_type'].get('unicode_conflict', 0) >= 1
    print('  PASS test_generate_records_json')


def test_generate_report_md():
    """验证 Markdown 报告格式"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
    ]
    records = build_conflict_records(entries)

    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, 'test_report.md')
        generate_report_md(records, output_path)

        with open(output_path, encoding='utf-8') as f:
            content = f.read()

        assert '# Phase 6' in content
        assert '统计总览' in content
        assert 'U+E6B5' in content
        assert 'unicode_conflict' in content or 'Unicode 冲突' in content
    print('  PASS test_generate_report_md')


def test_deterministic_output():
    """多次运行 build_conflict_records 输出一致"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow',
                   [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B6', 'icon-help',
                   [make_source('asset1', ['proj-a'])]),
        make_entry('hash_d', 'E6B6', 'icon-help',
                   [make_source('asset2', ['proj-b'])]),
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


def main():
    print('=' * 60)
    print('Phase 6: Conflict Detection — Tests')
    print('=' * 60)

    tests = [
        test_detect_unicode_conflicts_basic,
        test_detect_unicode_conflicts_no_conflict,
        test_detect_unicode_conflicts_same_hash,
        test_detect_unicode_conflicts_null_unicode,
        test_classify_severity,
        test_detect_name_conflicts_basic,
        test_detect_name_conflicts_null_name,
        test_detect_name_conflicts_same_hash,
        test_detect_duplicate_glyphs_basic,
        test_detect_duplicate_glyphs_single_source,
        test_detect_duplicate_glyphs_severity,
        test_build_conflict_records_all_types,
        test_build_conflict_records_required_fields,
        test_generate_records_json,
        test_generate_report_md,
        test_deterministic_output,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f'  FAIL {test.__name__}: {e}')

    print(f'\n--- Test 结果 ---')
    print(f'  通过: {passed}/{len(tests)}')
    print(f'  失败: {failed}/{len(tests)}')

    return 1 if failed > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
