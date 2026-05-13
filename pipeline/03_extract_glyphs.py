"""
Phase 3: Glyph Extraction（字形提取）

技术：Python + fontTools
输入：
  - sources/phase2_assets/<assetId>/font.ttf
  - sources/meta/assets_manifest.json
  - sources/meta/css_mappings.json

输出：
  - sources/phase3_glyphs/raw_glyphs.json
  - sources/phase3_glyphs/extraction_summary.json
"""

import json
import os
import sys
from datetime import datetime, timezone
from fontTools.ttLib import TTFont


def load_manifest():
    with open('sources/meta/assets_manifest.json', encoding='utf-8') as f:
        return json.load(f)


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


def extract_glyph_contours(glyph):
    """提取 glyph 的 contour 数据。"""
    if glyph.numberOfContours == 0:
        return []

    if glyph.isComposite():
        components = []
        for comp in glyph.components:
            components.append({
                'glyphName': comp.glyphName,
                'x': comp.x if hasattr(comp, 'x') else getattr(comp, 'x', 0),
                'y': comp.y if hasattr(comp, 'y') else getattr(comp, 'y', 0),
            })
        return components

    # Simple glyph: extract contour points
    contours = []
    coords = glyph.coordinates
    ends = glyph.endPtsOfContours
    flags = glyph.flags
    for i in range(glyph.numberOfContours):
        start = ends[i - 1] + 1 if i > 0 else 0
        end = ends[i]
        contour_points = []
        for j in range(start, end + 1):
            contour_points.append({
                'x': round(float(coords[j][0]), 6),
                'y': round(float(coords[j][1]), 6),
                'on_curve': bool(flags[j] & 0x01),
            })
        contours.append(contour_points)
    return contours


def extract_asset_glyphs(asset, css_name_lookup):
    """提取单个 asset 的所有 glyph 数据。"""
    asset_id = asset['assetId']
    ttf_path = asset['ttfPath']

    result = {
        'assetId': asset_id,
        'sourceProjects': asset.get('sourceProjects', []),
        'cssUrl': asset.get('cssUrl'),
        'glyphs': [],
        'errors': [],
    }

    if not os.path.exists(ttf_path):
        result['errors'].append(f'TTF file not found: {ttf_path}')
        return result

    try:
        font = TTFont(ttf_path)
    except Exception as e:
        result['errors'].append(f'Failed to open TTF: {e}')
        return result

    try:
        cmap = font.getBestCmap()
        glyf_table = font['glyf']
        hmtx_table = font['hmtx']
        head_table = font['head']
        maxp_table = font['maxp']

        units_per_em = head_table.unitsPerEm
        num_glyphs = maxp_table.numGlyphs

        result['unitsPerEm'] = units_per_em
        result['numGlyphs'] = num_glyphs

        for unicode_pt, glyph_name in (cmap or {}).items():
            glyph = glyf_table.get(glyph_name)
            if glyph is None:
                continue

            advance_width, lsb = hmtx_table.metrics.get(glyph_name, (0, 0))

            if glyph.isComposite():
                glyph_type = 'composite'
            elif glyph.numberOfContours > 0:
                glyph_type = 'simple'
            else:
                glyph_type = 'empty'

            contours = extract_glyph_contours(glyph)

            # Look up icon name from CSS mappings
            icon_name = css_name_lookup.get((asset_id, unicode_pt))

            glyph_record = {
                'assetId': asset_id,
                'unicode': unicode_pt,
                'unicode_hex': f'{unicode_pt:04X}',
                'glyphName': glyph_name,
                'iconName': icon_name,
                'glyphType': glyph_type,
                'numContours': glyph.numberOfContours,
                'contours': contours,
                'advanceWidth': advance_width,
                'lsb': lsb,
            }

            result['glyphs'].append(glyph_record)

    except Exception as e:
        result['errors'].append(f'Extraction error: {e}')
    finally:
        font.close()

    return result


def main():
    print('=' * 60)
    print('Phase 3: Glyph Extraction')
    print('=' * 60)

    os.makedirs('sources/phase3_glyphs', exist_ok=True)

    # Load metadata
    print('\n加载 assets_manifest.json ...')
    manifest = load_manifest()
    print(f'  共 {len(manifest)} 个 assets')

    print('加载 css_mappings.json ...')
    css_name_lookup = load_css_mappings()
    print(f'  共 {len(css_name_lookup)} 个 name 映射')

    # Filter ok assets
    ok_assets = [a for a in manifest if a.get('downloadStatus') == 'ok']
    print(f'\n需要提取的 TTF 文件: {len(ok_assets)} 个\n')

    # Extract
    all_glyphs = []
    asset_summaries = []
    total_errors = 0
    status_counts = {'ok': 0, 'error': 0}

    for i, asset in enumerate(ok_assets, 1):
        if i % 20 == 0:
            print(f'  已提取 {i}/{len(ok_assets)} ...')

        result = extract_asset_glyphs(asset, css_name_lookup)

        if result['errors']:
            status_counts['error'] += 1
            total_errors += len(result['errors'])
            for err in result['errors']:
                print(f'  ERROR [{asset["assetId"]}]: {err}')
        else:
            status_counts['ok'] += 1

        all_glyphs.extend(result['glyphs'])

        asset_summaries.append({
            'assetId': result['assetId'],
            'sourceProjects': result['sourceProjects'],
            'numGlyphs': len(result['glyphs']),
            'unitsPerEm': result.get('unitsPerEm'),
            'errors': result['errors'],
        })

    print(f'  提取完成: {len(ok_assets)}/{len(ok_assets)}\n')

    # Write raw_glyphs.json
    glyphs_path = 'sources/phase3_glyphs/raw_glyphs.json'
    with open(glyphs_path, 'w', encoding='utf-8') as f:
        json.dump(all_glyphs, f, ensure_ascii=False)
    print(f'原始 glyph 数据: {len(all_glyphs)} 条记录 -> {glyphs_path}')

    # Write summary
    summary = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_assets': len(ok_assets),
        'total_glyphs': len(all_glyphs),
        'status_summary': status_counts,
        'total_errors': total_errors,
        'asset_summaries': asset_summaries,
    }

    summary_path = 'sources/phase3_glyphs/extraction_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f'提取摘要: {summary_path}')

    # Print stats
    glyph_type_counts = {'simple': 0, 'composite': 0, 'empty': 0}
    for g in all_glyphs:
        glyph_type_counts[g['glyphType']] = glyph_type_counts.get(g['glyphType'], 0) + 1

    print(f'\n--- Glyph 统计 ---')
    print(f'  总 glyph 记录: {len(all_glyphs)}')
    print(f'  simple: {glyph_type_counts["simple"]}')
    print(f'  composite: {glyph_type_counts["composite"]}')
    print(f'  empty: {glyph_type_counts["empty"]}')
    print(f'  错误: {total_errors}')

    if total_errors > 0:
        print(f'\n⚠ 有 {total_errors} 个错误，请检查 extraction_summary.json')
        return 1

    print('\nPhase 3 完成！')
    return 0


if __name__ == '__main__':
    sys.exit(main())
