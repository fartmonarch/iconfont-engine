"""
Phase 6: Conflict Detection — Tests

测试覆盖：
  - detect_unicode_conflicts_basic: 同 unicode 不同 glyphHash -> 1 conflict
  - detect_unicode_conflicts_no_conflict: 每个 unicode 只有 1 个 glyphHash -> 0 conflicts
  - detect_unicode_conflicts_same_hash: 同 unicode 同 glyphHash -> 0 conflicts (多来源)
  - detect_unicode_conflicts_null_unicode: null unicode 条目应跳过
"""

import importlib.util
import os
import sys

# Load the module under test
spec = importlib.util.spec_from_file_location('phase6', 'pipeline/06_detect_conflicts.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

detect_unicode_conflicts = mod.detect_unicode_conflicts
classify_severity = mod.classify_severity
_build_conflict_record = mod._build_conflict_record


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
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B5', 'icon-arrow-right', [make_source('asset2', ['proj-b'])]),
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
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', 'E6B6', 'icon-up', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B7', 'icon-down', [make_source('asset3', ['proj-c'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 0, f'Expected 0 conflicts, got {len(conflicts)}'
    print('  PASS test_detect_unicode_conflicts_no_conflict')


def test_detect_unicode_conflicts_same_hash():
    """Same unicode, same glyphHash -> 0 conflicts (just multi-source)"""
    entries = [
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_a', 'E6B5', 'icon-arrow', [make_source('asset2', ['proj-b'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    assert len(conflicts) == 0, f'Expected 0 conflicts (same hash), got {len(conflicts)}'
    print('  PASS test_detect_unicode_conflicts_same_hash')


def test_detect_unicode_conflicts_null_unicode():
    """Entries with null unicode should be skipped"""
    entries = [
        make_entry('hash_a', None, 'icon-unknown', [make_source('asset1', ['proj-a'])]),
        make_entry('hash_b', None, 'icon-ghost', [make_source('asset2', ['proj-b'])]),
        make_entry('hash_c', 'E6B5', 'icon-arrow', [make_source('asset3', ['proj-c'])]),
    ]
    conflicts = detect_unicode_conflicts(entries)
    # null entries should be skipped, and the one valid entry has no conflict
    assert len(conflicts) == 0, f'Expected 0 conflicts (null skipped), got {len(conflicts)}'
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
