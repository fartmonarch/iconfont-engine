#!/usr/bin/env python3
"""Phase 7: Conflict Resolution — Interactive HTML Generator

Reads conflict_records.json + glyph_registry.json, generates a self-contained
HTML page with SVG-rendered glyphs for visual conflict resolution.

Usage:
    python pipeline/07_generate_resolver_ui.py

Output:
    report/conflict_resolver.html
"""
import json
import html as htmlmod
import os
import sys

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICTS_PATH = os.path.join(DATA_DIR, 'report', 'conflict_records.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'report', 'conflict_resolver.html')

TYPE_LABELS = {
    'unicode_conflict': 'Type A: Unicode',
    'name_conflict': 'Type B: Name',
}

SEVERITY_LABELS = {
    'critical': 'Critical',
    'warning': 'Warning',
    'info': 'Info',
}


def contour_to_path(contour):
    """Convert TTF contour points to SVG path data."""
    if not contour:
        return ''
    pts = list(contour)
    first_on = None
    for i, pt in enumerate(pts):
        if pt.get('on_curve'):
            first_on = i
            break
    if first_on is None:
        d = f'M {pts[0]["x"]:.1f} {pts[0]["y"]:.1f} '
        for pt in pts[1:]:
            d += f'L {pt["x"]:.1f} {pt["y"]:.1f} '
        d += 'Z'
        return d
    pts = pts[first_on:] + pts[:first_on]
    d = f'M {pts[0]["x"]:.1f} {pts[0]["y"]:.1f} '
    i = 1
    while i < len(pts):
        pt = pts[i]
        if pt.get('on_curve'):
            d += f'L {pt["x"]:.1f} {pt["y"]:.1f} '
            i += 1
        else:
            if i + 1 < len(pts) and pts[i + 1].get('on_curve'):
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {pts[i+1]["x"]:.1f} {pts[i+1]["y"]:.1f} '
                i += 2
            elif i + 1 < len(pts) and not pts[i + 1].get('on_curve'):
                mid_x = (pt['x'] + pts[i + 1]['x']) / 2
                mid_y = (pt['y'] + pts[i + 1]['y']) / 2
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {mid_x:.1f} {mid_y:.1f} '
                i += 1
            else:
                first = pts[0]
                mid_x = (pt['x'] + first['x']) / 2
                mid_y = (pt['y'] + first['y']) / 2
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {mid_x:.1f} {mid_y:.1f} '
                i += 1
    d += 'Z'
    return d


def contours_to_svg(contours, upm=1024, size=80):
    """Convert contours to inline SVG with auto-fit viewBox."""
    if not contours:
        return None
    all_x, all_y = [], []
    for contour in contours:
        for pt in contour:
            all_x.append(pt['x'])
            all_y.append(upm - pt['y'])
    if not all_x:
        return None
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    pad = max(max_x - min_x, max_y - min_y) * 0.1
    vx = min_x - pad
    vy = min_y - pad
    vw = (max_x - min_x) + 2 * pad
    vh = (max_y - min_y) + 2 * pad
    if vw < 1 or vh < 1:
        return None
    paths = []
    for contour in contours:
        flipped = [{'x': p['x'], 'y': upm - p['y'], 'on_curve': p['on_curve']} for p in contour]
        d = contour_to_path(flipped)
        if d:
            paths.append(f'<path d="{d}" fill="currentColor"/>')
    if not paths:
        return None
    svg_content = ''.join(paths)
    return (
        f'<svg viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" '
        f'width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">'
        f'{svg_content}</svg>'
    )


def load_conflicts():
    with open(CONFLICTS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_embedded_records(data):
    """Build compact JSON for HTML embedding. Only Type A+B, with SVG strings."""
    records = data['records']
    embedded = []
    for idx, r in enumerate(records):
        if r['type'] not in ('unicode_conflict', 'name_conflict'):
            continue
        variants = []
        for vi, v in enumerate(r['variants']):
            svg = contours_to_svg(v.get('contours'), 1024, 80)
            source_names = []
            for s in v.get('sources', []):
                for p in s.get('projects', []):
                    source_names.append(p)
            variants.append({
                'glyphHash': v['glyphHash'],
                'name': v.get('canonicalName') or '(none)',
                'sourceCount': len(v.get('sources', [])),
                'sources': ', '.join(source_names[:5]),
                'svg': svg,
            })
        embedded.append({
            'id': idx,
            'type': r['type'],
            'severity': r['severity'],
            'key': r['key'],
            'variantCount': r['variantCount'],
            'resolution_hint': r['resolution_hint'],
            'variants': variants,
        })
    return embedded


def generate_html(embedded_records):
    """Generate the complete self-contained HTML page."""
    total = len(embedded_records)
    type_a = sum(1 for r in embedded_records if r['type'] == 'unicode_conflict')
    type_b = sum(1 for r in embedded_records if r['type'] == 'name_conflict')
    crit = sum(1 for r in embedded_records if r['severity'] == 'critical')
    warn = sum(1 for r in embedded_records if r['severity'] == 'warning')
    info = sum(1 for r in embedded_records if r['severity'] == 'info')

    data_json = json.dumps({'records': embedded_records}, ensure_ascii=False, separators=(',', ':'))
    data_json_escaped = data_json.replace('</script>', '<\\/script>')

    html_parts = []
    html_parts.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phase 7 Conflict Resolution</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif; background: #f0f2f5; padding: 0; }}

/* Header */
#app-header {{
    position: sticky; top: 0; z-index: 100;
    background: #fff; border-bottom: 1px solid #e8e8e8;
    padding: 12px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}}
#app-header h1 {{ font-size: 18px; margin-bottom: 8px; }}

/* Progress */
.progress-section {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
#progress-text {{ font-size: 13px; color: #666; white-space: nowrap; }}
.progress-bar {{ flex: 1; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }}
.progress-fill {{ height: 100%; background: #52c41a; transition: width 0.3s; width: 0%; }}

/* Filters */
.filter-bar {{ display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }}
.filter-btn {{
    padding: 4px 12px; border: 1px solid #d9d9d9; border-radius: 4px;
    background: #fff; cursor: pointer; font-size: 12px; transition: all 0.2s;
}}
.filter-btn:hover {{ border-color: #1890ff; color: #1890ff; }}
.filter-btn.active {{ background: #1890ff; color: #fff; border-color: #1890ff; }}

/* Export */
.actions {{ display: flex; gap: 8px; }}
#export-btn {{
    padding: 6px 16px; background: #1890ff; color: #fff; border: none;
    border-radius: 4px; cursor: pointer; font-size: 13px;
}}
#export-btn:hover {{ background: #40a9ff; }}
#export-btn:disabled {{ background: #d9d9d9; cursor: not-allowed; }}

/* Cards container */
#card-container {{ padding: 16px 20px; max-width: 1400px; margin: 0 auto; }}

/* Conflict card */
.conflict-card {{
    background: #fff; border-radius: 8px; margin-bottom: 12px;
    border: 1px solid #e8e8e8; overflow: hidden;
    transition: opacity 0.3s;
}}
.conflict-card.resolved {{ opacity: 0.6; }}
.conflict-card[data-severity="critical"] {{ border-left: 4px solid #ff4d4f; }}
.conflict-card[data-severity="warning"] {{ border-left: 4px solid #fa8c16; }}
.conflict-card[data-severity="info"] {{ border-left: 4px solid #1890ff; }}
.conflict-card.hidden {{ display: none; }}

/* Card header */
.card-header {{
    display: flex; align-items: center; gap: 8px;
    padding: 10px 14px; background: #fafafa; border-bottom: 1px solid #f0f0f0;
}}
.card-header .key {{ font-weight: 700; font-size: 14px; font-family: monospace; }}
.sev-badge {{
    padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;
}}
.sev-badge.critical {{ background: #fff1f0; color: #cf1322; }}
.sev-badge.warning {{ background: #fff7e6; color: #d46b08; }}
.sev-badge.info {{ background: #e6f7ff; color: #096dd9; }}
.type-label {{ font-size: 11px; color: #999; }}
.variant-count {{ font-size: 12px; color: #666; margin-left: auto; }}
.decision-status {{ font-size: 12px; color: #52c41a; font-weight: 600; display: none; }}
.conflict-card.resolved .decision-status {{ display: inline; }}

/* Card body */
.card-body {{
    display: flex; gap: 12px; padding: 14px;
    overflow-x: auto; flex-wrap: nowrap;
}}

/* Variant panel */
.variant-panel {{
    flex: 0 0 auto; width: 160px;
    border: 2px solid #e8e8e8; border-radius: 8px;
    padding: 10px; text-align: center;
    transition: border-color 0.2s, background 0.2s;
}}
.variant-panel:hover {{ border-color: #1890ff; background: #f0f5ff; }}
.variant-panel.selected {{ border-color: #52c41a; background: #f6ffed; }}
.variant-panel.selected:hover {{ border-color: #52c41a; }}

/* SVG container */
.svg-container {{
    width: 80px; height: 80px; margin: 0 auto 8px;
    display: flex; align-items: center; justify-content: center;
    color: #333;
}}
.svg-container svg {{ display: block; }}
.svg-placeholder {{
    width: 80px; height: 80px;
    background: #fafafa; border: 1px dashed #d9d9d9;
    border-radius: 4px;
}}

/* Variant meta */
.variant-meta {{ font-size: 11px; color: #666; margin-bottom: 8px; line-height: 1.5; }}
.variant-meta code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 10px; }}
.variant-meta .name {{ display: block; font-weight: 500; color: #333; margin: 2px 0; }}
.variant-meta .sources {{ display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

/* Buttons */
.btn-group {{ display: flex; gap: 4px; justify-content: center; }}
.btn {{
    padding: 4px 10px; border: none; border-radius: 4px;
    cursor: pointer; font-size: 11px; font-weight: 600;
    transition: all 0.2s;
}}
.btn-keep {{ background: #52c41a; color: #fff; }}
.btn-keep:hover {{ background: #73d13d; }}
.btn-pua {{ background: #1890ff; color: #fff; }}
.btn-pua:hover {{ background: #40a9ff; }}
.btn:disabled {{ background: #d9d9d9; color: #999; cursor: not-allowed; }}

/* No icon placeholder */
.no-icon {{ width: 80px; height: 80px; margin: 0 auto; background: #f0f0f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #ccc; font-size: 24px; }}

/* Responsive */
@media (max-width: 768px) {{
    .card-body {{ flex-wrap: wrap; }}
    .variant-panel {{ width: 100%; max-width: 200px; }}
}}
</style>
</head>
<body>

<header id="app-header">
    <h1>Phase 7 Conflict Resolution</h1>
    <div class="progress-section">
        <span id="progress-text">0 / {total} resolved</span>
        <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
    </div>
    <div class="filter-bar">
        <button class="filter-btn active" data-filter="all">All ({total})</button>
        <button class="filter-btn" data-filter="critical">Critical ({crit})</button>
        <button class="filter-btn" data-filter="warning">Warning ({warn})</button>
        <button class="filter-btn" data-filter="info">Info ({info})</button>
        <button class="filter-btn" data-filter="unicode_conflict">Type A ({type_a})</button>
        <button class="filter-btn" data-filter="name_conflict">Type B ({type_b})</button>
    </div>
    <div class="actions">
        <button id="export-btn" disabled>Export Decisions (JSON)</button>
    </div>
</header>

<main id="card-container"></main>

<script id="conflict-data" type="application/json">{data_json_escaped}</script>

<script>
(function() {{
    'use strict';

    const state = {{
        decisions: {{}},
        totalRecords: 0,
    }};

    // Parse embedded data
    const data = JSON.parse(document.getElementById('conflict-data').textContent);
    const records = data.records || [];
    state.totalRecords = records.length;

    // Render cards
    const container = document.getElementById('card-container');
    const fragment = document.createDocumentFragment();

    records.forEach(function(record) {{
        const card = document.createElement('div');
        card.className = 'conflict-card';
        card.dataset.id = record.id;
        card.dataset.type = record.type;
        card.dataset.severity = record.severity;

        const typeLabel = record.type === 'unicode_conflict' ? 'Type A: Unicode' : 'Type B: Name';
        const sevLabel = record.severity.charAt(0).toUpperCase() + record.severity.slice(1);

        let variantsHtml = '';
        record.variants.forEach(function(v, vi) {{
            const svgHtml = v.svg
                ? v.svg
                : '<div class="no-icon">--</div>';
            const svgContainer = v.svg
                ? '<div class="svg-container" data-svg=\'' + v.svg.replace(/'/g, "\\'") + '\'></div>'
                : '<div class="svg-placeholder"></div>';

            variantsHtml += '<div class="variant-panel" data-variant="' + vi + '">'
                + svgContainer
                + '<div class="variant-meta">'
                + '<code>' + escapeHtml(v.glyphHash.substring(0, 12)) + '...</code>'
                + '<span class="name">' + escapeHtml(v.name) + '</span>'
                + '<span class="sources">' + escapeHtml(v.sources) + '</span>'
                + '</div>'
                + '<div class="btn-group">'
                + '<button class="btn btn-keep" onclick="window._decide(' + record.id + ', ' + vi + ', \'keep\')">保留</button>'
                + '<button class="btn btn-pua" onclick="window._decide(' + record.id + ', ' + vi + ', \'pua\')">PUA</button>'
                + '</div>'
                + '</div>';
        }});

        card.innerHTML =
            '<div class="card-header">'
            + '<span class="key">' + escapeHtml(record.key) + '</span>'
            + '<span class="sev-badge ' + record.severity + '">' + sevLabel + '</span>'
            + '<span class="type-label">' + typeLabel + '</span>'
            + '<span class="variant-count">' + record.variantCount + ' variants</span>'
            + '<span class="decision-status">✓ Resolved</span>'
            + '</div>'
            + '<div class="card-body">' + variantsHtml + '</div>';

        fragment.appendChild(card);
    }});

    container.appendChild(fragment);

    // Lazy load SVGs with IntersectionObserver
    if ('IntersectionObserver' in window) {{
        const observer = new IntersectionObserver(function(entries) {{
            entries.forEach(function(entry) {{
                if (entry.isIntersecting) {{
                    const el = entry.target;
                    if (el.dataset.svg && !el.dataset.rendered) {{
                        el.innerHTML = el.dataset.svg;
                        el.dataset.rendered = '1';
                    }}
                    observer.unobserve(el);
                }}
            }});
        }}, {{ rootMargin: '200px' }});

        document.querySelectorAll('.svg-container[data-svg]').forEach(function(el) {{
            observer.observe(el);
        }});
    }} else {{
        // Fallback: render all at once
        document.querySelectorAll('.svg-container[data-svg]').forEach(function(el) {{
            el.innerHTML = el.dataset.svg;
        }});
    }}

    // Decision logic
    window._decide = function(recordId, variantIndex, action) {{
        const card = container.querySelector('.conflict-card[data-id="' + recordId + '"]');
        if (!card) return;

        // Remove previous selection
        card.querySelectorAll('.variant-panel').forEach(function(p) {{
            p.classList.remove('selected');
            p.querySelectorAll('.btn').forEach(function(b) {{ b.disabled = false; }});
        }});

        // Mark selected
        const panel = card.querySelector('.variant-panel[data-variant="' + variantIndex + '"]');
        panel.classList.add('selected');
        panel.querySelectorAll('.btn').forEach(function(b) {{
            if ((action === 'keep' && b.classList.contains('btn-keep')) ||
                (action === 'pua' && b.classList.contains('btn-pua'))) {{
                b.disabled = true;
            }}
        }});

        card.classList.add('resolved');

        // Store decision
        const record = records[recordId];
        state.decisions[recordId] = {{
            recordType: record.type,
            key: record.key,
            action: action,
            variantIndex: variantIndex,
            keptGlyphHash: record.variants[variantIndex].glyphHash,
        }};

        updateProgress();
    }};

    function updateProgress() {{
        const count = Object.keys(state.decisions).length;
        const pct = (count / state.totalRecords * 100).toFixed(1);
        document.getElementById('progress-text').textContent = count + ' / ' + state.totalRecords + ' resolved';
        document.getElementById('progress-fill').style.width = pct + '%';
        document.getElementById('export-btn').disabled = (count < state.totalRecords);
    }};

    // Filters
    document.querySelectorAll('.filter-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
            btn.classList.add('active');
            const filter = btn.dataset.filter;
            document.querySelectorAll('.conflict-card').forEach(function(card) {{
                if (filter === 'all') {{
                    card.classList.remove('hidden');
                }} else {{
                    const match = card.dataset.severity === filter || card.dataset.type === filter;
                    card.classList.toggle('hidden', !match);
                }}
            }});
        }});
    }});

    // Export
    document.getElementById('export-btn').addEventListener('click', function() {{
        const output = {{
            generatedAt: new Date().toISOString(),
            totalRecords: state.totalRecords,
            decidedCount: Object.keys(state.decisions).length,
            decisions: state.decisions,
        }};
        const blob = new Blob([JSON.stringify(output, null, 2)], {{ type: 'application/json' }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'phase7_decisions.json';
        a.click();
        URL.revokeObjectURL(url);
    }});

    function escapeHtml(str) {{
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }};
}})();
</script>
</body>
</html>''')

    return '\n'.join(html_parts)


def main():
    print('=' * 60)
    print('Phase 7: Conflict Resolution — HTML Generator')
    print('=' * 60)

    if not os.path.exists(CONFLICTS_PATH):
        print(f'\n错误: 未找到冲突数据文件 {CONFLICTS_PATH}')
        print('请先运行 Phase 6: python pipeline/06_detect_conflicts.py')
        return 1

    data = load_conflicts()
    total_records = len(data.get('records', []))
    print(f'\n加载冲突数据: {total_records} 条')

    embedded = build_embedded_records(data)
    type_a = sum(1 for r in embedded if r['type'] == 'unicode_conflict')
    type_b = sum(1 for r in embedded if r['type'] == 'name_conflict')
    print(f'过滤后: {len(embedded)} 条 (Type A: {type_a}, Type B: {type_b})')

    # Count SVGs generated
    svg_count = sum(len(r['variants']) for r in embedded)
    print(f'生成 SVG 预览: {svg_count} 个')

    html_content = generate_html(embedded)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)

    size_kb = len(html_content) / 1024
    print(f'\n输出: {OUTPUT_PATH}')
    print(f'大小: {size_kb:.1f} KB')
    print(f'卡片数: {len(embedded)}')
    print(f'SVG 数: {svg_count}')
    print('\nPhase 7 HTML 生成完成。在浏览器中打开上述路径进行决策。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
