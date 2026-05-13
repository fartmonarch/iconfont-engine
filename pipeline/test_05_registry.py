"""
Phase 5: Glyph Hash Registry 测试

测试覆盖：
  - group_by_hash: 分组正确性
  - select_canonical: canonical 选择规则
  - collect_aliases: alias 收集 + 去重
  - collect_sources: 来源收集 + assetId 去重
  - build_registry_entry: 完整 entry 构建 + empty glyph
  - deterministic output: 多次运行输出一致
"""

import importlib.util
import json
import os
import sys

# Load the module under test
spec = importlib.util.spec_from_file_location('phase5', 'pipeline/05_build_registry.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

group_by_hash = mod.group_by_hash
select_canonical = mod.select_canonical
collect_aliases = mod.collect_aliases
collect_sources = mod.collect_sources
build_registry_entry = mod.build_registry_entry


def make_glyph(asset_id, unicode_pt, icon_name, glyph_hash='hash1', glyph_type='simple'):
    display_name = icon_name if icon_name else ''
    return {
        'assetId': asset_id,
        'unicode': unicode_pt,
        'unicode_hex': f'{unicode_pt:04X}',
        'glyphName': display_name.replace('icon-', ''),
        'iconName': icon_name,
        'glyphType': glyph_type,
        'numContours': 1,
        'contours': [[{'x': 0.0, 'y': 0.0, 'on_curve': True}]],
        'advanceWidth': 1024,
        'lsb': 0,
        'glyphHash': glyph_hash,
    }


MANIFEST_LOOKUP = {
    'asset1': {'assetId': 'asset1', 'sourceProjects': ['proj-a'], 'cssUrl': 'https://example.com/a.css'},
    'asset2': {'assetId': 'asset2', 'sourceProjects': ['proj-b'], 'cssUrl': 'https://example.com/b.css'},
    'asset3': {'assetId': 'asset3', 'sourceProjects': ['proj-c', 'proj-d'], 'cssUrl': 'https://example.com/c.css'},
}


def test_group_by_hash():
    glyphs = [
        make_glyph('a1', 59059, 'icon-add', 'hash1'),
        make_glyph('a2', 59060, 'icon-plus', 'hash1'),
        make_glyph('a3', 59061, 'icon-jia', 'hash2'),
    ]
    groups = group_by_hash(glyphs)
    assert len(groups) == 2
    assert len(groups['hash1']) == 2
    assert len(groups['hash2']) == 1
    assert groups['hash1'][0]['assetId'] == 'a1'
    assert groups['hash1'][1]['assetId'] == 'a2'
    print('  PASS test_group_by_hash')


def test_select_canonical():
    # Same hash, different unicodes and names
    glyphs = [
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
        make_glyph('asset2', 59060, 'icon-plus', 'hash1'),
        make_glyph('asset3', 59059, 'icon-jia', 'hash1'),
    ]
    canonical = select_canonical(glyphs)
    # unicode 59059 appears 3 times (most common)
    assert canonical['unicode'] == 59059
    # 'icon-add' appears 2 times among 59059 (most common)
    assert canonical['name'] == 'icon-add'
    # 'asset1' has 'icon-add' + 59059 most times
    assert canonical['assetId'] == 'asset1'
    print('  PASS test_select_canonical')


def test_select_canonical_no_name():
    glyphs = [
        make_glyph('asset1', 59059, '', 'hash1'),
        make_glyph('asset2', 59060, '', 'hash1'),
    ]
    canonical = select_canonical(glyphs)
    assert canonical['unicode'] == 59059
    assert canonical['name'] == ''
    print('  PASS test_select_canonical_no_name')


def test_collect_aliases():
    glyphs = [
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
        make_glyph('asset2', 59060, 'icon-plus', 'hash1'),
        make_glyph('asset3', 59061, 'icon-jia', 'hash1'),
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),  # duplicate
    ]
    aliases, aliases_detail = collect_aliases(glyphs)
    assert aliases == ['icon-add', 'icon-jia', 'icon-plus']
    assert len(aliases_detail) == 4
    # All entries have assetId, iconName, unicode, unicodeHex
    assert all(k in aliases_detail[0] for k in ['assetId', 'iconName', 'unicode', 'unicodeHex'])
    print('  PASS test_collect_aliases')


def test_collect_aliases_no_name():
    glyphs = [
        make_glyph('asset1', 59059, None, 'hash1'),
        make_glyph('asset2', 59060, '', 'hash1'),
    ]
    aliases, aliases_detail = collect_aliases(glyphs)
    assert aliases == []
    assert aliases_detail == []
    print('  PASS test_collect_aliases_no_name')


def test_collect_sources():
    glyphs = [
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
        make_glyph('asset1', 59060, 'icon-plus', 'hash1'),  # same asset, different unicode
        make_glyph('asset2', 59061, 'icon-jia', 'hash1'),
    ]
    sources = collect_sources(glyphs, MANIFEST_LOOKUP)
    assert len(sources) == 2  # deduplicated by assetId
    asset1_src = next(s for s in sources if s['assetId'] == 'asset1')
    assert asset1_src['projects'] == ['proj-a']
    assert asset1_src['originalUnicode'] == 59059  # first seen unicode
    asset2_src = next(s for s in sources if s['assetId'] == 'asset2')
    assert asset2_src['projects'] == ['proj-b']
    print('  PASS test_collect_sources')


def test_build_registry_entry():
    glyphs = [
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
        make_glyph('asset2', 59060, 'icon-plus', 'hash1'),
    ]
    entry = build_registry_entry('hash1', glyphs, MANIFEST_LOOKUP)
    assert entry['glyphHash'] == 'hash1'
    assert entry['canonicalUnicode'] == 59059
    assert entry['canonicalUnicodeHex'] == 'E6B3'
    assert entry['canonicalName'] == 'icon-add'
    assert entry['canonicalAssetId'] == 'asset1'
    assert entry['aliases'] == ['icon-add', 'icon-plus']
    assert len(entry['sources']) == 2
    assert entry['glyphType'] == 'simple'
    assert entry['numContours'] == 1
    assert entry['advanceWidth'] == 1024
    print('  PASS test_build_registry_entry')


def test_build_registry_entry_empty():
    glyphs = [
        make_glyph('asset1', 0, '', 'empty', 'empty'),
    ]
    entry = build_registry_entry('empty', glyphs, MANIFEST_LOOKUP)
    assert entry['glyphHash'] == 'empty'
    assert entry['glyphType'] == 'empty'
    assert entry['canonicalUnicode'] is None
    assert entry['contours'] is None
    print('  PASS test_build_registry_entry_empty')


def test_registry_entry_required_fields():
    glyphs = [
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
    ]
    entry = build_registry_entry('hash1', glyphs, MANIFEST_LOOKUP)
    required_fields = [
        'glyphHash', 'canonicalUnicode', 'canonicalUnicodeHex',
        'canonicalName', 'canonicalAssetId', 'aliases', 'aliasesDetail',
        'sources', 'contours', 'advanceWidth', 'glyphType', 'numContours',
    ]
    for field in required_fields:
        assert field in entry, f'Missing field: {field}'
    print('  PASS test_registry_entry_required_fields')


def test_unicode_map_format():
    registry = [
        {'glyphHash': 'hash1', 'canonicalUnicode': 59059, 'canonicalUnicodeHex': 'E6B3'},
        {'glyphHash': 'hash2', 'canonicalUnicode': 59060, 'canonicalUnicodeHex': 'E6B4'},
        {'glyphHash': 'empty', 'canonicalUnicode': None, 'canonicalUnicodeHex': None},
    ]
    umap = mod.build_unicode_map(registry)
    assert umap['hash1'] == 59059
    assert umap['hash2'] == 59060
    assert 'empty' not in umap
    assert isinstance(umap, dict)
    print('  PASS test_unicode_map_format')


def test_hash_index_format():
    registry = [
        {
            'glyphHash': 'hash1', 'canonicalUnicode': 59059,
            'canonicalUnicodeHex': 'E6B3', 'canonicalName': 'icon-add',
            'canonicalAssetId': 'asset1', 'aliases': ['a', 'b'],
            'sources': [1, 2, 3], 'glyphType': 'simple',
        },
    ]
    index = mod.build_hash_index(registry)
    assert 'hash1' in index
    idx_entry = index['hash1']
    assert idx_entry['canonicalUnicode'] == 59059
    assert idx_entry['aliasCount'] == 2
    assert idx_entry['sourceCount'] == 3
    assert 'contours' not in idx_entry  # should not include large fields
    print('  PASS test_hash_index_format')


def test_deterministic_output():
    """Run build_registry_entry multiple times, verify same result"""
    glyphs = [
        make_glyph('asset1', 59059, 'icon-add', 'hash1'),
        make_glyph('asset2', 59060, 'icon-plus', 'hash1'),
        make_glyph('asset3', 59061, 'icon-jia', 'hash2'),
    ]
    groups = group_by_hash(glyphs)

    results = []
    for _ in range(3):
        entries = []
        for h, g_list in sorted(groups.items()):
            entries.append(build_registry_entry(h, g_list, MANIFEST_LOOKUP))
        entries.sort(key=lambda e: (e['canonicalUnicode'] or 0, e['glyphHash']))
        results.append(json.dumps(entries, sort_keys=True, ensure_ascii=False))

    assert results[0] == results[1] == results[2], 'Non-deterministic output detected!'
    print('  PASS test_deterministic_output')


def main():
    print('=' * 60)
    print('Phase 5: Glyph Hash Registry — Tests')
    print('=' * 60)

    tests = [
        test_group_by_hash,
        test_select_canonical,
        test_select_canonical_no_name,
        test_collect_aliases,
        test_collect_aliases_no_name,
        test_collect_sources,
        test_build_registry_entry,
        test_build_registry_entry_empty,
        test_registry_entry_required_fields,
        test_unicode_map_format,
        test_hash_index_format,
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
