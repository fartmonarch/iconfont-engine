#!/usr/bin/env python3
"""Phase 8-9: Direct Glyf Merge & Font Build

Reads phase7_resolution.json + normalized_glyphs.json, merges all resolved
glyphs into a single TTF using fontTools FontBuilder + TTGlyphPen, then
exports WOFF2.

Usage:
    python pipeline/08_merge_glyf.py

Input:
    report/phase7_resolution.json       — Phase 7 resolved glyphs (finalUnicode, finalName, glyphHash)
    sources/phase4_glyphs/normalized_glyphs.json — Normalized contours data

Output:
    output/iconfont_merged.ttf
    output/iconfont_merged.woff2
    output/iconfont_merged.css
    output/iconfont_merged.json
    report/phase89_build.json           — Build metadata
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE7_RES_PATH = os.path.join(DATA_DIR, 'report', 'phase7_resolution.json')
NORMALIZED_GLYPHS_PATH = os.path.join(DATA_DIR, 'sources', 'phase4_glyphs', 'normalized_glyphs.json')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
OUTPUT_PREFIX = 'iconfont_merged'
FONT_FAMILY = 'iconfont-merged'
BASE_UPM = 1024
CSS_ICON_PREFIX = 'icon-'


def load_phase7_resolution():
    """Load Phase 7 resolved glyphs."""
    with open(PHASE7_RES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_normalized_glyphs():
    """Load normalized glyphs indexed by (glyphHash, assetId)."""
    with open(NORMALIZED_GLYPHS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Build lookup: (glyphHash, assetId) -> entry
    lookup = {}
    for entry in data.values() if isinstance(data, dict) else data:
        key = (entry.get('glyphHash', ''), entry.get('assetId', ''))
        lookup[key] = entry
    return lookup


def draw_contours_to_pen(pen, contours):
    """Draw normalized contours using TTGlyphPen (quadratic TrueType).

    Winding directions preserved from normalization phase:
    - Outer contours: CW (signed_area < 0)
    - Inner holes: CCW (signed_area > 0)
    """
    for contour in contours:
        if not contour:
            continue

        n = len(contour)

        # Find first on-curve point
        first_on_idx = -1
        for idx, pt in enumerate(contour):
            if pt.get('on_curve', True):
                first_on_idx = idx
                break

        if first_on_idx == -1:
            # All off-curve: implied on-curve at midpoints
            p0 = contour[-1]
            p1 = contour[0]
            start_x = (int(round(p0['x'])) + int(round(p1['x']))) // 2
            start_y = (int(round(p0['y'])) + int(round(p1['y']))) // 2
            pen.moveTo((start_x, start_y))

            for idx in range(n):
                curr = contour[idx]
                next_pt = contour[(idx + 1) % n]
                cx, cy = int(round(curr['x'])), int(round(curr['y']))
                if next_pt.get('on_curve', True):
                    pen.qCurveTo(
                        (cx, cy),
                        (int(round(next_pt['x'])), int(round(next_pt['y']))))
                else:
                    nx, ny = int(round(next_pt['x'])), int(round(next_pt['y']))
                    mid_x, mid_y = (cx + nx) // 2, (cy + ny) // 2
                    pen.qCurveTo((cx, cy), (mid_x, mid_y))
        else:
            # Start from first on-curve
            reordered = contour[first_on_idx:] + contour[:first_on_idx]
            start = reordered[0]
            pen.moveTo((int(round(start['x'])), int(round(start['y']))))

            idx = 1
            while idx < len(reordered):
                pt = reordered[idx]
                if pt.get('on_curve', True):
                    pen.lineTo((int(round(pt['x'])), int(round(pt['y']))))
                    idx += 1
                else:
                    off_points = []
                    while idx < len(reordered) and not reordered[idx].get('on_curve', True):
                        p = reordered[idx]
                        off_points.append((int(round(p['x'])), int(round(p['y']))))
                        idx += 1
                    if idx < len(reordered):
                        end_pt = reordered[idx]
                        off_points.append((int(round(end_pt['x'])), int(round(end_pt['y']))))
                        pen.qCurveTo(*off_points)
                        idx += 1
                    else:
                        off_points.append((int(round(start['x'])), int(round(start['y']))))
                        pen.qCurveTo(*off_points)

        pen.closePath()


def resolve_glyph_contours(phase7_glyph, norm_lookup):
    """Find the contour data for a resolved glyph from normalized_glyphs.

    Phase 7 glyphs have glyphHash + sources (with assetId).
    We look up (glyphHash, any_source_assetId) in the normalized data.
    """
    glyph_hash = phase7_glyph['glyphHash']

    # Try each source's assetId
    sources = phase7_glyph.get('sources', [])
    for src in sources:
        asset_id = src.get('assetId', '')
        key = (glyph_hash, asset_id)
        if key in norm_lookup:
            return norm_lookup[key]

    # Fallback: try any entry with matching glyphHash
    for (gh, aid), entry in norm_lookup.items():
        if gh == glyph_hash:
            return entry

    return None


def main():
    print('=' * 60)
    print('Phase 8-9: Direct Glyf Merge & Font Build')
    print('=' * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load inputs
    print('\nLoading Phase 7 resolution...')
    phase7 = load_phase7_resolution()
    resolved_glyphs = phase7.get('glyphs', [])
    print(f'  Resolved glyphs: {len(resolved_glyphs)}')

    print('Loading normalized glyphs...')
    norm_lookup = load_normalized_glyphs()
    print(f'  Normalized entries: {len(norm_lookup)}')

    # Filter valid glyphs: must have finalUnicode, contours, and be simple type
    valid_glyphs = []
    skip_no_contours = 0
    skip_no_unicode = 0
    skip_composite = 0

    for g in resolved_glyphs:
        if not g.get('finalUnicode'):
            skip_no_unicode += 1
            continue

        # Resolve contours from normalized data
        norm_entry = resolve_glyph_contours(g, norm_lookup)
        if norm_entry is None:
            skip_no_contours += 1
            continue

        contours = norm_entry.get('contours')
        if not contours:
            skip_no_contours += 1
            continue

        glyph_type = norm_entry.get('glyphType', 'simple')
        if glyph_type != 'simple':
            skip_composite += 1
            # Still include composite glyphs if they have contours
            # (Phase 4 already expanded composites for reading)

        # Build enriched glyph with contours
        enriched = {
            **g,
            'contours': contours,
            'glyphType': glyph_type,
            'advanceWidth': norm_entry.get('advanceWidth', BASE_UPM),
        }
        valid_glyphs.append(enriched)

    print(f'\nValid glyphs to merge: {len(valid_glyphs)}')
    print(f'  Skipped (no contours): {skip_no_contours}')
    print(f'  Skipped (no unicode): {skip_no_unicode}')
    print(f'  Skipped (composite): {skip_composite}')

    # Build font using FontBuilder + TTGlyphPen
    glyph_names = ['.notdef'] + [f'glyph_{i}' for i in range(len(valid_glyphs))]
    cmap_mapping = {
        g['finalUnicode']: f'glyph_{i}'
        for i, g in enumerate(valid_glyphs)
    }

    fb = FontBuilder(BASE_UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_names)
    fb.setupCharacterMap(cmap_mapping)
    fb.setupNameTable({
        'familyName': FONT_FAMILY,
        'styleName': 'Regular',
    })

    # Draw glyphs
    glyph_table = {}
    metrics = {'.notdef': (BASE_UPM, 0)}
    success_count = 0
    error_count = 0

    # .notdef empty glyph
    pen = TTGlyphPen(glyphSet=None)
    glyph_table['.notdef'] = pen.glyph()

    for i, g in enumerate(valid_glyphs):
        glyph_name = f'glyph_{i}'
        advance_width = g.get('advanceWidth', BASE_UPM)

        try:
            pen = TTGlyphPen(glyphSet=None)
            draw_contours_to_pen(pen, g['contours'])
            glyph_table[glyph_name] = pen.glyph()
            metrics[glyph_name] = (int(round(advance_width)), 0)
            success_count += 1
        except Exception as e:
            pen = TTGlyphPen(glyphSet=None)
            glyph_table[glyph_name] = pen.glyph()
            metrics[glyph_name] = (BASE_UPM, 0)
            error_count += 1
            if error_count <= 10:
                print(f'  WARNING: glyph_{i} ({g.get("finalName", "?")}): {e}')

    fb.setupGlyf(glyph_table)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=896, descent=-128)
    fb.setupOS2(sTypoAscender=896, sTypoDescender=-128, sTypoLineGap=0)
    fb.setupPost()

    font = fb.font

    # Save TTF
    ttf_path = os.path.join(OUTPUT_DIR, f'{OUTPUT_PREFIX}.ttf')
    font.save(ttf_path)
    print(f'\n  TTF: {ttf_path}')
    print(f'  Success: {success_count}, Errors: {error_count}')

    # Save WOFF2
    woff2_path = None
    try:
        woff2_path = os.path.join(OUTPUT_DIR, f'{OUTPUT_PREFIX}.woff2')
        font.flavor = 'woff2'
        font.save(woff2_path)
        font.flavor = None
        print(f'  WOFF2: {woff2_path}')
    except Exception as e:
        print(f'  WOFF2 failed: {e}')

    # --- Generate CSS ---
    css_lines = [
        '@font-face {',
        f'  font-family: "{FONT_FAMILY}";',
        f'  src: url("{OUTPUT_PREFIX}.woff2") format("woff2"),',
        f'       url("{OUTPUT_PREFIX}.ttf") format("truetype");',
        '  font-weight: normal;',
        '  font-style: normal;',
        '  font-display: block;',
        '}',
        '',
        f"[class^='{CSS_ICON_PREFIX}'], [class*=' {CSS_ICON_PREFIX}'] {{",
        f'  font-family: "{FONT_FAMILY}" !important;',
        '  font-size: 16px;',
        '  font-style: normal;',
        '  -webkit-font-smoothing: antialiased;',
        '  -moz-osx-font-smoothing: grayscale;',
        '}',
        '',
    ]

    for g in valid_glyphs:
        name = g.get('finalName', '')
        if name:
            css_lines.append(
                f'.{CSS_ICON_PREFIX}{name}:before {{ content: "\\{g["finalUnicodeHex"]}"; }}')

    css_lines.append('')
    css_lines.append('/* Aliases */')
    alias_total = 0
    for g in valid_glyphs:
        uhex = g['finalUnicodeHex']
        for alias in g.get('aliases', []):
            if alias and alias != g.get('finalName', ''):
                css_lines.append(
                    f'.{CSS_ICON_PREFIX}{alias}:before {{ content: "\\{uhex}"; }}')
                alias_total += 1

    css_path = os.path.join(OUTPUT_DIR, f'{OUTPUT_PREFIX}.css')
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(css_lines))
    print(f'  CSS: {css_path} ({alias_total} aliases)')

    # --- Generate JSON manifest ---
    manifest = []
    for g in valid_glyphs:
        manifest.append({
            'glyphHash': g['glyphHash'],
            'unicode': g['finalUnicodeHex'],
            'name': g.get('finalName', ''),
            'aliases': g.get('aliases', []),
            'sources': [
                {
                    'assetId': s.get('assetId', ''),
                    'projects': s.get('projects', []),
                    'originalUnicode': f'{s.get("originalUnicode", 0):04X}',
                }
                for s in g.get('sources', [])
            ],
            'affectedProjects': g.get('affectedProjects', []),
            'resolution': g.get('resolution', ''),
        })
    manifest_path = os.path.join(OUTPUT_DIR, f'{OUTPUT_PREFIX}.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f'  Manifest: {manifest_path}')

    # --- Generate validation HTML ---
    html = generate_validation_html(valid_glyphs, phase7)
    html_path = os.path.join(OUTPUT_DIR, 'validation.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  HTML: {html_path}')

    # Save build info
    build_info = {
        'ttf_path': ttf_path,
        'woff2_path': woff2_path,
        'css_path': css_path,
        'manifest_path': manifest_path,
        'glyphs_merged': success_count,
        'errors': error_count,
        'total_resolved': len(resolved_glyphs),
        'total_valid': len(valid_glyphs),
        'skipped_no_contours': skip_no_contours,
        'skipped_no_unicode': skip_no_unicode,
        'skipped_composite': skip_composite,
        'generatedAt': datetime.now(timezone.utc).isoformat(),
    }
    info_path = os.path.join(DATA_DIR, 'report', 'phase89_build.json')
    os.makedirs(os.path.dirname(info_path), exist_ok=True)
    with open(info_path, 'w', encoding='utf-8') as f:
        json.dump(build_info, f, ensure_ascii=False, indent=2)

    print(f'\nPhase 8-9 完成。')
    return 0


def generate_validation_html(valid_glyphs, phase7):
    """Generate HTML page for visual verification."""
    meta = phase7.get('metadata', {})
    pua_log = phase7.get('puaAssignmentLog', [])
    pua_hashes = {e.get('glyphHash', '') for e in pua_log}

    # Group by source assetId
    source_groups = defaultdict(list)
    for g in valid_glyphs:
        for src in g.get('sources', []):
            source_groups[src.get('assetId', 'unknown')].append(g)

    pua_glyphs = [g for g in valid_glyphs if g['glyphHash'] in pua_hashes]
    normal_glyphs = [g for g in valid_glyphs if g['glyphHash'] not in pua_hashes]

    shared = sum(1 for g in valid_glyphs if len(g.get('sources', [])) > 1)
    unique = len(valid_glyphs) - shared

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Iconfont Merge - Validation Report</title>
<link rel="stylesheet" href="{OUTPUT_PREFIX}.css">
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; background: #f8f9fa; color: #333; margin: 0; }}
h1 {{ color: #1a1a2e; margin-bottom: 5px; }}
h2 {{ color: #16213e; margin-top: 40px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
h3 {{ color: #0f3460; margin-top: 20px; }}
.subtitle {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
.stats {{ background: white; padding: 20px; border-radius: 12px; margin-bottom: 24px; display: flex; gap: 30px; flex-wrap: wrap; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.stats .item {{ text-align: center; min-width: 80px; }}
.stats .item .num {{ font-size: 28px; font-weight: bold; color: #1976d2; }}
.stats .item .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; }}
.icon-item {{ background: white; border: 1px solid #e8e8e8; border-radius: 8px; padding: 12px 6px 8px; text-align: center; transition: all 0.2s; position: relative; }}
.icon-item:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-1px); }}
.icon-item .icon-display {{ font-size: 28px; margin-bottom: 6px; color: #333; line-height: 1; }}
.icon-item .icon-name {{ font-size: 9px; color: #666; word-break: break-all; line-height: 1.3; max-height: 2.6em; overflow: hidden; }}
.icon-item .icon-code {{ font-size: 9px; color: #aaa; margin-top: 3px; font-family: monospace; }}
.icon-item.pua {{ border-color: #ff9800; background: #fff8e1; }}
.icon-item.pua::after {{ content: "PUA"; position: absolute; top: 3px; right: 3px; font-size: 8px; background: #ff9800; color: white; padding: 1px 3px; border-radius: 3px; }}
.conflict-section {{ background: #fff3e0; border: 1px solid #ffcc02; border-radius: 12px; padding: 20px; margin: 20px 0; }}
.conflict-section h3 {{ color: #e65100; margin-top: 0; }}
.section {{ margin-bottom: 30px; }}
.badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 4px; }}
.badge-shared {{ background: #e3f2fd; color: #1565c0; }}
.badge-unique {{ background: #f3e5f5; color: #7b1fa2; }}
.badge-pua {{ background: #fff3e0; color: #e65100; }}
</style>
</head>
<body>
"""
    html += f'<h1>Iconfont Merge - Validation Report</h1>\n'
    html += f'<p class="subtitle">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | '
    html += f'Strategy: auto PUA | Sources: {len(source_groups)}</p>\n'

    # Stats
    html += '<div class="stats">\n'
    html += f'<div class="item"><div class="num">{len(valid_glyphs)}</div><div class="label">Total Glyphs</div></div>\n'
    html += f'<div class="item"><div class="num">{len(source_groups)}</div><div class="label">Unique Assets</div></div>\n'
    html += f'<div class="item"><div class="num">{shared}</div><div class="label">Multi-source</div></div>\n'
    html += f'<div class="item"><div class="num">{unique}</div><div class="label">Unique</div></div>\n'
    html += f'<div class="item"><div class="num">{len(pua_log)}</div><div class="label">PUA Assigned</div></div>\n'
    html += '</div>\n'

    # PUA section
    if pua_glyphs:
        html += '<div class="conflict-section">\n'
        html += '<h3>PUA Reassigned Glyphs (Conflict Resolved)</h3>\n'
        html += f'<p>{len(pua_glyphs)} glyphs were reassigned to Private Use Area.</p>\n'
        html += '<div class="grid">\n'
        for g in pua_glyphs:
            name = g.get('finalName', '')
            uhex = g['finalUnicodeHex']
            html += f'<div class="icon-item pua">'
            html += f'<div class="icon-display" style="font-family:{FONT_FAMILY}">&#x{uhex};</div>'
            html += f'<div class="icon-name">{name}</div>'
            html += f'<div class="icon-code">U+{uhex}</div>'
            html += f'</div>\n'
        html += '</div>\n</div>\n'

    # All merged icons
    html += '<div class="section">\n<h2>All Merged Icons</h2>\n<div class="grid">\n'
    for g in valid_glyphs:
        name = g.get('finalName', '')
        uhex = g['finalUnicodeHex']
        is_pua = g['glyphHash'] in pua_hashes
        cls = 'icon-item pua' if is_pua else 'icon-item'
        html += f'<div class="{cls}">'
        html += f'<div class="icon-display" style="font-family:{FONT_FAMILY}">&#x{uhex};</div>'
        html += f'<div class="icon-name">{name}</div>'
        html += f'<div class="icon-code">U+{uhex}</div>'
        html += f'</div>\n'
    html += '</div>\n</div>\n'

    # Per-source breakdown
    html += '<h2>Per-Source Breakdown</h2>\n'
    for asset_id, glyphs in sorted(source_groups.items()):
        shared_count = sum(1 for g in glyphs if len(g.get('sources', [])) > 1)
        html += f'<div class="section">\n'
        html += f'<h3>Source: {asset_id[:12]}'
        html += f' <span class="badge badge-shared">{shared_count} shared</span>'
        html += f' <span class="badge badge-unique">{len(glyphs) - shared_count} unique</span>'
        html += f'</h3>\n<div class="grid">\n'
        for g in glyphs[:20]:  # Limit per source to avoid huge HTML
            name = g.get('finalName', '')
            uhex = g['finalUnicodeHex']
            is_pua = g['glyphHash'] in pua_hashes
            cls = 'icon-item pua' if is_pua else 'icon-item'
            html += f'<div class="{cls}">'
            html += f'<div class="icon-display" style="font-family:{FONT_FAMILY}">&#x{uhex};</div>'
            html += f'<div class="icon-name">{name}</div>'
            html += f'<div class="icon-code">U+{uhex}</div>'
            html += f'</div>\n'
        if len(glyphs) > 20:
            html += f'<p style="color:#888;font-size:12px;">... and {len(glyphs) - 20} more</p>\n'
        html += '</div>\n</div>\n'

    html += '</body>\n</html>'
    return html


if __name__ == '__main__':
    sys.exit(main())
