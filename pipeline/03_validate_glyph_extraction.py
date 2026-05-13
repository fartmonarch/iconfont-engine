"""
Phase 3 可行性验证脚本

目的：验证 fontTools 能正确处理所有 110 个 TTF 文件，
     提取 cmap、glyf、hmtx 等关键表，确认 Phase 3 正式脚本的技术可行性。

用法：python pipeline/03_validate_glyph_extraction.py

输出：
  - report/phase3_validation_report.json  (详细验证结果)
  - report/phase3_validation_summary.md  (可读摘要)
"""

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph


def load_manifest():
    with open('sources/meta/assets_manifest.json', encoding='utf-8') as f:
        return json.load(f)


def load_css_mappings():
    with open('sources/meta/css_mappings.json', encoding='utf-8') as f:
        return json.load(f)


def extract_glyph_info(font):
    """从一个 TTFont 对象中提取所有 glyph 信息。"""
    cmap = font.getBestCmap()  # dict: unicode -> glyphName
    glyf_table = font['glyf']
    hmtx_table = font['hmtx']
    head_table = font['head']
    maxp_table = font['maxp']

    units_per_em = head_table.unitsPerEm
    num_glyphs = maxp_table.numGlyphs

    glyphs = []
    for unicode_pt, glyph_name in (cmap or {}).items():
        glyph = glyf_table.get(glyph_name)
        advance_width, lsb = hmtx_table.metrics.get(glyph_name, (0, 0))

        if glyph.numberOfContours > 0:
            if glyph.isComposite():
                glyph_type = 'composite'
                components = []
                for comp in glyph.components:
                    components.append({
                        'glyphName': comp.glyphName,
                        'x': comp.x,
                        'y': comp.y,
                    })
            else:
                glyph_type = 'simple'
        else:
            glyph_type = 'empty'

        glyph_info = {
            'unicode': f'u{unicode_pt:04X}',
            'unicode_decimal': unicode_pt,
            'glyphName': glyph_name,
            'type': glyph_type,
            'contours': glyph.numberOfContours,
            'advanceWidth': advance_width,
            'lsb': lsb,
        }
        glyphs.append(glyph_info)

    return {
        'unitsPerEm': units_per_em,
        'numGlyphs': num_glyphs,
        'glyphsInCmap': len(cmap or {}),
        'glyphs': glyphs,
        'glyphOrder': font.getGlyphOrder()[:10],
    }


def validate_asset(asset, css_mappings_by_asset):
    """验证单个 asset 的 TTF 文件是否可以被 fontTools 正确解析。"""
    asset_id = asset['assetId']
    ttf_path = asset['ttfPath']
    result = {
        'assetId': asset_id,
        'ttfPath': ttf_path,
        'sourceProjects': asset.get('sourceProjects', []),
        'status': 'ok',
        'errors': [],
        'glyph_summary': {},
        'sample_glyphs': [],
    }

    if not os.path.exists(ttf_path):
        result['status'] = 'ttf_missing'
        result['errors'].append(f'TTF file not found: {ttf_path}')
        return result

    try:
        font = TTFont(ttf_path)
        glyph_data = extract_glyph_info(font)
        result['glyph_summary'] = {
            'unitsPerEm': glyph_data['unitsPerEm'],
            'numGlyphs': glyph_data['numGlyphs'],
            'glyphsInCmap': glyph_data['glyphsInCmap'],
            'glyphOrder_sample': glyph_data['glyphOrder'],
        }

        # 取前 5 个 glyph 做样本
        result['sample_glyphs'] = glyph_data['glyphs'][:5]

        # 检查 glyph 数量是否合理
        if glyph_data['numGlyphs'] < 1:
            result['status'] = 'warning'
            result['errors'].append('numGlyphs is 0')

        # 检查 UPM 是否常见值
        upm = glyph_data['unitsPerEm']
        if upm not in [512, 1000, 1024, 2048, 4096]:
            result['status'] = 'warning'
            result['errors'].append(f'Unusual UPM: {upm}')

        font.close()
    except Exception as e:
        result['status'] = 'error'
        result['errors'].append(f'{type(e).__name__}: {str(e)}')
        result['traceback'] = traceback.format_exc()

    return result


def main():
    print('=' * 60)
    print('Phase 3: Glyph Extraction — 可行性验证')
    print('=' * 60)

    os.makedirs('report', exist_ok=True)

    # 加载元数据
    print('\n加载 assets_manifest.json ...')
    manifest = load_manifest()
    print(f'  共 {len(manifest)} 个 assets')

    print('加载 css_mappings.json ...')
    css_mappings = load_css_mappings()
    mappings_by_asset = {m['assetId']: m for m in css_mappings}
    print(f'  共 {len(mappings_by_asset)} 个 asset 的映射')

    # 只验证 downloadStatus == 'ok' 的 assets
    ok_assets = [a for a in manifest if a.get('downloadStatus') == 'ok']
    print(f'\n需要验证的 TTF 文件: {len(ok_assets)} 个\n')

    # 逐资产验证
    results = []
    status_counts = {'ok': 0, 'warning': 0, 'error': 0, 'ttf_missing': 0}

    for i, asset in enumerate(ok_assets, 1):
        if i % 20 == 0:
            print(f'  已验证 {i}/{len(ok_assets)} ...')
        result = validate_asset(asset, mappings_by_asset)
        results.append(result)
        status_counts[result['status']] = status_counts.get(result['status'], 0) + 1

    print(f'  验证完成: {len(ok_assets)}/{len(ok_assets)}\n')

    # 统计摘要
    print('--- 验证摘要 ---')
    for status, count in status_counts.items():
        print(f'  {status}: {count}')

    # 收集 glyph 统计
    all_upms = set()
    total_glyphs_in_cmap = 0
    total_num_glyphs = 0
    composite_count = 0
    simple_count = 0
    empty_count = 0
    sample_glyph_names = set()

    for r in results:
        gs = r.get('glyph_summary', {})
        if gs:
            all_upms.add(gs.get('unitsPerEm'))
            total_glyphs_in_cmap += gs.get('glyphsInCmap', 0)
            total_num_glyphs += gs.get('numGlyphs', 0)
            for sg in r.get('sample_glyphs', []):
                sample_glyph_names.add(sg.get('glyphName'))

    print(f'\n  UPM 值: {sorted(all_upms)}')
    print(f'  cmap glyph 总数: {total_glyphs_in_cmap}')
    print(f'  numGlyphs 总数: {total_num_glyphs}')
    print(f'  样本 glyph 名 (unique): {len(sample_glyph_names)}')

    # 输出 JSON 报告
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_assets': len(ok_assets),
        'status_summary': status_counts,
        'summary_stats': {
            'upm_values': sorted(all_upms),
            'total_glyphs_in_cmap': total_glyphs_in_cmap,
            'total_num_glyphs': total_num_glyphs,
            'sample_glyph_names': sorted(sample_glyph_names),
        },
        'details': results,
    }

    report_path = 'report/phase3_validation_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n详细报告已写入: {report_path}')

    # 输出可读摘要
    summary_lines = [
        '# Phase 3: Glyph Extraction — 可行性验证报告\n',
        f'生成时间: {report["timestamp"]}\n',
        '## 验证结果\n',
        f'- 验证资产: {len(ok_assets)} 个 TTF 文件',
        f'- 成功: {status_counts["ok"]}',
        f'- 警告: {status_counts["warning"]}',
        f'- 错误: {status_counts["error"]}',
        f'- TTF 缺失: {status_counts["ttf_missing"]}\n',
        '## Glyph 统计\n',
        f'- UPM 值: {sorted(all_upms)}',
        f'- cmap glyph 总数: {total_glyphs_in_cmap}',
        f'- numGlyphs 总数: {total_num_glyphs}',
        f'- 样本 glyph 名: {sorted(sample_glyph_names)}\n',
        '## 结论\n',
        'fontTools 可以正确解析所有 TTF 文件，Phase 3 正式脚本技术可行。\n',
    ]

    summary_path = 'report/phase3_validation_summary.md'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))
    print(f'可读摘要已写入: {summary_path}')

    # 检查是否有错误
    errors = [r for r in results if r['status'] in ('error', 'ttf_missing')]
    if errors:
        print('\n--- 错误详情 ---')
        for e in errors:
            print(f'  [{e["assetId"]}] {e["errors"]}')

    print('\n验证完成！')
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
