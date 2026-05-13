"""
Phase 5: Glyph Hash Registry（字形哈希注册表）

技术：Python + collections.Counter + json
输入：
  - sources/phase4_glyphs/normalized_glyphs.json
  - sources/meta/assets_manifest.json
  - sources/meta/css_mappings.json
输出：
  - registry/glyph_registry.json        — 核心注册表
  - registry/unicode_map.json          — glyphHash → canonical unicode 映射
  - registry/hash_index.json           — glyphHash → entry 快速索引
  - registry/lineage.json              — 完整溯源链
  - registry/registry_summary.json     — 统计摘要
  - report/phase5_registry.md          — 人类可读报告

核心逻辑：
  1. 按 glyphHash 分组
  2. 为每组选择 canonical 代表（unicode/name/assetId）
  3. 收集所有 aliases 和 sources
  4. 输出注册表 + 辅助索引
"""

import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone


def load_normalized_glyphs():
    with open('sources/phase4_glyphs/normalized_glyphs.json', encoding='utf-8') as f:
        return json.load(f)


def load_assets_manifest():
    with open('sources/meta/assets_manifest.json', encoding='utf-8') as f:
        manifest = json.load(f)
    # Build lookup: assetId -> asset record
    return {a['assetId']: a for a in manifest}


def load_css_mappings():
    with open('sources/meta/css_mappings.json', encoding='utf-8') as f:
        mappings_list = json.load(f)
    # Build lookup: (assetId, unicode_int) -> icon_name
    lookup = {}
    for m in mappings_list:
        asset_id = m['assetId']
        for entry in m.get('mappings', []):
            unicode_val = int(entry['unicode'], 16)
            lookup[(asset_id, unicode_val)] = entry['name']
    return lookup


def group_by_hash(glyphs):
    """按 glyphHash 分组，返回 dict[hash] -> list of glyphs"""
    groups = defaultdict(list)
    for g in glyphs:
        groups[g['glyphHash']].append(g)
    return groups


def select_canonical(glyphs_for_hash):
    """
    从同一 hash 的多个 glyph 中选择 canonical 代表。
    规则：
      1. canonicalUnicode: 出现次数最多的 unicode
      2. canonicalName: 该 unicode 下出现次数最多的 iconName
      3. canonicalAssetId: canonical unicode + name 对应的 assetId（出现最多的）
    """
    # Step 1: 选出现次数最多的 unicode
    unicode_counts = Counter(g['unicode'] for g in glyphs_for_hash)
    canonical_unicode = unicode_counts.most_common(1)[0][0]

    # Step 2: 在 canonical unicode 中选出现最多的 iconName
    same_unicode = [g for g in glyphs_for_hash if g['unicode'] == canonical_unicode]
    name_counts = Counter(g.get('iconName') or '' for g in same_unicode)
    canonical_name = name_counts.most_common(1)[0][0]

    # Step 3: 选 canonical unicode + name 对应的 assetId（出现最多的）
    same_name_unicode = [g for g in same_unicode if (g.get('iconName') or '') == canonical_name]
    candidates = same_name_unicode if same_name_unicode else same_unicode
    asset_counts = Counter(g['assetId'] for g in candidates)
    canonical_asset = asset_counts.most_common(1)[0][0]

    return {
        'unicode': canonical_unicode,
        'name': canonical_name,
        'assetId': canonical_asset,
    }


def collect_aliases(glyphs_for_hash):
    """收集所有不同的 iconName 作为 alias"""
    aliases = set()
    aliases_detail = []
    for g in glyphs_for_hash:
        name = g.get('iconName')
        if name:
            aliases.add(name)
            aliases_detail.append({
                'assetId': g['assetId'],
                'iconName': name,
                'unicode': g['unicode'],
                'unicodeHex': g['unicode_hex'],
            })
    return sorted(aliases), aliases_detail


def collect_sources(glyphs_for_hash, manifest_lookup):
    """按 assetId 去重收集来源信息"""
    sources = {}
    for g in glyphs_for_hash:
        aid = g['assetId']
        if aid not in sources:
            manifest = manifest_lookup.get(aid, {})
            sources[aid] = {
                'assetId': aid,
                'projects': manifest.get('sourceProjects', []),
                'cssUrl': manifest.get('cssUrl'),
                'originalUnicode': g['unicode'],
            }
    return list(sources.values())


def build_registry_entry(glyph_hash, glyphs_for_hash, manifest_lookup):
    """为同一 glyphHash 的所有 glyph 构建一条注册表记录"""
    # Handle empty glyphs
    if glyph_hash == 'empty':
        return {
            'glyphHash': 'empty',
            'canonicalUnicode': None,
            'canonicalUnicodeHex': None,
            'canonicalName': None,
            'canonicalAssetId': None,
            'aliases': [],
            'aliasesDetail': [],
            'sources': collect_sources(glyphs_for_hash, manifest_lookup),
            'contours': None,
            'advanceWidth': None,
            'glyphType': 'empty',
            'numContours': 0,
        }

    # Select canonical representative
    canonical = select_canonical(glyphs_for_hash)

    # Collect aliases
    aliases, aliases_detail = collect_aliases(glyphs_for_hash)

    # Collect sources
    sources = collect_sources(glyphs_for_hash, manifest_lookup)

    # Take contours/advanceWidth from first glyph (all same hash have identical contours)
    first = glyphs_for_hash[0]

    return {
        'glyphHash': glyph_hash,
        'canonicalUnicode': canonical['unicode'],
        'canonicalUnicodeHex': f'{canonical["unicode"]:04X}',
        'canonicalName': canonical['name'],
        'canonicalAssetId': canonical['assetId'],
        'aliases': aliases,
        'aliasesDetail': aliases_detail,
        'sources': sources,
        'contours': first.get('contours'),
        'advanceWidth': first.get('advanceWidth'),
        'glyphType': first.get('glyphType'),
        'numContours': first.get('numContours'),
    }


def build_unicode_map(registry):
    """glyphHash → canonical unicode 映射"""
    return {
        entry['glyphHash']: entry['canonicalUnicode']
        for entry in registry
        if entry['canonicalUnicode'] is not None
    }


def build_hash_index(registry):
    """glyphHash → entry 快速索引（不含 contours 等大字段）"""
    index = {}
    for entry in registry:
        index[entry['glyphHash']] = {
            'canonicalUnicode': entry['canonicalUnicode'],
            'canonicalUnicodeHex': entry['canonicalUnicodeHex'],
            'canonicalName': entry['canonicalName'],
            'canonicalAssetId': entry['canonicalAssetId'],
            'aliasCount': len(entry['aliases']),
            'sourceCount': len(entry['sources']),
            'glyphType': entry['glyphType'],
        }
    return index


def build_lineage(registry):
    """完整溯源链：每个 glyph 的完整来源历史"""
    lineage = []
    for entry in registry:
        lineage.append({
            'glyphHash': entry['glyphHash'],
            'canonicalUnicode': entry['canonicalUnicode'],
            'canonicalUnicodeHex': entry['canonicalUnicodeHex'],
            'canonicalName': entry['canonicalName'],
            'canonicalAssetId': entry['canonicalAssetId'],
            'aliases': entry['aliases'],
            'sources': entry['sources'],
        })
    return lineage


def main():
    print('=' * 60)
    print('Phase 5: Glyph Hash Registry')
    print('=' * 60)

    os.makedirs('registry', exist_ok=True)
    os.makedirs('report', exist_ok=True)

    # Load data
    print('\n加载 normalized_glyphs.json ...')
    glyphs = load_normalized_glyphs()
    print(f'  共 {len(glyphs)} 条 glyph 记录')

    print('加载 assets_manifest.json ...')
    manifest_lookup = load_assets_manifest()
    print(f'  共 {len(manifest_lookup)} 个 asset 记录')

    print('加载 css_mappings.json ...')
    css_lookup = load_css_mappings()
    print(f'  共 {len(css_lookup)} 个 name 映射')

    # Group by glyphHash
    print('\n按 glyphHash 分组...')
    groups = group_by_hash(glyphs)
    print(f'  共 {len(groups)} 个唯一 glyphHash')

    # Build registry entries
    print('\n构建注册表...')
    registry = []
    errors = 0
    for i, (glyph_hash, glyphs_group) in enumerate(sorted(groups.items())):
        if (i + 1) % 200 == 0:
            print(f'  已处理 {i + 1}/{len(groups)} ...')

        try:
            entry = build_registry_entry(glyph_hash, glyphs_group, manifest_lookup)
            registry.append(entry)
        except Exception as e:
            errors += 1
            print(f'  ERROR [{glyph_hash}]: {e}')

    print(f'  注册表构建完成: {len(registry)} 条记录')

    # Sort registry by canonicalUnicode for deterministic output
    registry.sort(key=lambda e: (e['canonicalUnicode'] or 0, e['glyphHash']))

    # Build auxiliary indexes
    print('\n构建辅助索引...')
    unicode_map = build_unicode_map(registry)
    hash_index = build_hash_index(registry)
    lineage = build_lineage(registry)

    # Write outputs
    print('\n写入输出文件...')

    registry_path = 'registry/glyph_registry.json'
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False)
    print(f'  注册表: {registry_path} ({len(registry)} entries)')

    unicode_map_path = 'registry/unicode_map.json'
    with open(unicode_map_path, 'w', encoding='utf-8') as f:
        json.dump(unicode_map, f, ensure_ascii=False)
    print(f'  Unicode 映射: {unicode_map_path} ({len(unicode_map)} entries)')

    hash_index_path = 'registry/hash_index.json'
    with open(hash_index_path, 'w', encoding='utf-8') as f:
        json.dump(hash_index, f, ensure_ascii=False)
    print(f'  Hash 索引: {hash_index_path} ({len(hash_index)} entries)')

    lineage_path = 'registry/lineage.json'
    with open(lineage_path, 'w', encoding='utf-8') as f:
        json.dump(lineage, f, ensure_ascii=False)
    print(f'  溯源链: {lineage_path} ({len(lineage)} entries)')

    # Compute stats
    multi_source = sum(1 for e in registry if len(e['sources']) > 1)
    max_sources = max((len(e['sources']) for e in registry), default=0)
    total_aliases = sum(len(e['aliases']) for e in registry)
    empty_count = sum(1 for e in registry if e['glyphType'] == 'empty')
    simple_count = sum(1 for e in registry if e['glyphType'] == 'simple')

    # Write summary
    summary = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_entries': len(registry),
        'simple': simple_count,
        'empty': empty_count,
        'multi_source_entries': multi_source,
        'max_sources_per_entry': max_sources,
        'total_aliases': total_aliases,
        'errors': errors,
        'hash_distribution': {
            'single_source': len(registry) - multi_source,
            'two_to_five': sum(1 for e in registry if 2 <= len(e['sources']) <= 5),
            'six_to_ten': sum(1 for e in registry if 6 <= len(e['sources']) <= 10),
            'eleven_plus': sum(1 for e in registry if len(e['sources']) > 10),
        },
    }
    summary_path = 'registry/registry_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f'  统计摘要: {summary_path}')

    # Print stats
    print(f'\n--- Registry 统计 ---')
    print(f'  总 entry:    {len(registry)}')
    print(f'  simple:      {simple_count}')
    print(f'  empty:       {empty_count}')
    print(f'  多来源:      {multi_source}')
    print(f'  最大来源数:  {max_sources}')
    print(f'  总 alias:    {total_aliases}')
    print(f'  错误:        {errors}')
    print(f'  Hash 分布:')
    print(f'    单来源:    {len(registry) - multi_source}')
    print(f'    2-5 来源:  {summary["hash_distribution"]["two_to_five"]}')
    print(f'    6-10 来源: {summary["hash_distribution"]["six_to_ten"]}')
    print(f'    11+ 来源:  {summary["hash_distribution"]["eleven_plus"]}')

    # Generate human-readable report
    report_path = 'report/phase5_registry.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# Phase 5: Glyph Hash Registry 报告\n\n')
        f.write(f'生成时间: {summary["timestamp"]}\n\n')
        f.write('## 统计\n\n')
        f.write('| 指标 | 值 |\n')
        f.write('|------|-----|\n')
        f.write(f'| 总 registry entry | {len(registry)} |\n')
        f.write(f'| simple | {simple_count} |\n')
        f.write(f'| empty | {empty_count} |\n')
        f.write(f'| 多来源 entry | {multi_source} |\n')
        f.write(f'| 最大来源数 | {max_sources} |\n')
        f.write(f'| 总 alias | {total_aliases} |\n')
        f.write(f'| 错误 | {errors} |\n\n')
        f.write('## Hash 分布\n\n')
        f.write('| 范围 | 数量 |\n')
        f.write('|------|------|\n')
        f.write(f'| 单来源 | {len(registry) - multi_source} |\n')
        f.write(f'| 2-5 来源 | {summary["hash_distribution"]["two_to_five"]} |\n')
        f.write(f'| 6-10 来源 | {summary["hash_distribution"]["six_to_ten"]} |\n')
        f.write(f'| 11+ 来源 | {summary["hash_distribution"]["eleven_plus"]} |\n\n')

        # Top 10 most-duplicated glyphs
        top_dups = sorted(registry, key=lambda e: len(e['sources']), reverse=True)[:10]
        f.write('## 重复度 Top 10\n\n')
        f.write('| glyphHash | canonicalName | 来源数 | alias 数 |\n')
        f.write('|-----------|--------------|--------|----------|\n')
        for entry in top_dups:
            f.write(f'| {entry["glyphHash"]} | {entry["canonicalName"] or "(empty)"} | {len(entry["sources"])} | {len(entry["aliases"])} |\n')
        f.write('\n')

        # Top 10 most-aliased glyphs
        top_aliases = sorted(registry, key=lambda e: len(e['aliases']), reverse=True)[:10]
        f.write('## Alias 数 Top 10\n\n')
        f.write('| glyphHash | canonicalName | alias 数 | aliases |\n')
        f.write('|-----------|--------------|----------|---------|\n')
        for entry in top_aliases:
            alias_preview = ', '.join(entry['aliases'][:5])
            if len(entry['aliases']) > 5:
                alias_preview += f' ... (+{len(entry["aliases"]) - 5})'
            f.write(f'| {entry["glyphHash"]} | {entry["canonicalName"] or "(empty)"} | {len(entry["aliases"])} | {alias_preview} |\n')

    print(f'  报告: {report_path}')

    if errors > 0:
        print(f'\n有 {errors} 个错误')
        return 1

    print('\nPhase 5 完成！')
    return 0


if __name__ == '__main__':
    sys.exit(main())
