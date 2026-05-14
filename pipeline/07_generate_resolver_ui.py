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
DATA_JSON_PATH = os.path.join(DATA_DIR, 'report', 'conflict_resolver_data.json')

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
        # 全 off-curve contour（TrueType 圆/孔洞）：
        # 在最后一个和第一个 off-curve 点之间插入隐含 on-curve 点
        mid_x = (pts[-1]['x'] + pts[0]['x']) / 2
        mid_y = (pts[-1]['y'] + pts[0]['y']) / 2
        d = f'M {mid_x:.1f} {mid_y:.1f} '
        for i in range(len(pts)):
            pt = pts[i]
            next_pt = pts[(i + 1) % len(pts)]
            if i == len(pts) - 1:
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {mid_x:.1f} {mid_y:.1f} '
            else:
                mid2_x = (pt['x'] + next_pt['x']) / 2
                mid2_y = (pt['y'] + next_pt['y']) / 2
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {mid2_x:.1f} {mid2_y:.1f} '
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
            paths.append(f'<path d="{d}" fill="#333"/>')
    if not paths:
        return None
    svg_content = ''.join(paths)
    return (
        f'<svg viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" '
        f'width="{size}" height="{size}" fill-rule="evenodd" xmlns="http://www.w3.org/2000/svg">'
        f'{svg_content}</svg>'
    )


def load_conflicts():
    with open(CONFLICTS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_embedded_records(data):
    """Build JSON for embedding. Only Type A+B, with inline SVG strings."""
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
.card-hint {{
    padding: 4px 14px; background: #fffbe6; border-bottom: 1px solid #ffe58f;
    font-size: 12px; color: #d46b08;
}}
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
    color: #303133;
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
    padding: 4px 10px; border: 1px solid #d9d9d9; border-radius: 4px;
    cursor: pointer; font-size: 11px; font-weight: 600;
    transition: all 0.2s; background: #fff;
}}
.btn-keep {{ color: #52c41a; border-color: #52c41a; }}
.btn-keep:hover {{ background: #f6ffed; }}
.btn-pua {{ color: #fa8c16; border-color: #fa8c16; }}
.btn-pua:hover {{ background: #fff7e6; }}

.variant-panel.selected {{ border-color: #52c41a; background: #f6ffed; }}
.variant-panel.selected:hover {{ border-color: #52c41a; }}
.variant-panel.pua-active {{ border-color: #fa8c16; background: #fff7e6; }}
.variant-panel.pua-active:hover {{ border-color: #fa8c16; }}

.variant-panel.selected .btn-keep {{ background: #52c41a; color: #fff; border-color: #52c41a; }}
.variant-panel.pua-active .btn-pua {{ background: #fa8c16; color: #fff; border-color: #fa8c16; }}

/* No icon placeholder */
.no-icon {{ width: 80px; height: 80px; margin: 0 auto; background: #f0f0f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #ccc; font-size: 24px; }}

/* Responsive */
@media (max-width: 768px) {{
    .card-body {{ flex-wrap: wrap; }}
    .variant-panel {{ width: 100%; max-width: 200px; }}
}}
.loading {{ text-align: center; padding: 60px; color: #909399; font-size: 16px; }}
</style>
</head>
<body>

<header id="app-header">
    <h1>Phase 7 Conflict Resolution</h1>
    <div class="progress-section">
        <span id="progress-text">Loading...</span>
        <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
    </div>
    <div class="filter-bar" id="filter-bar">
        <button class="filter-btn active" data-filter="all">All</button>
    </div>
    <div class="actions">
        <button id="export-btn" disabled>Export Decisions (JSON)</button>
    </div>
</header>

<main id="card-container"><div class="loading">Loading data...</div></main>

<script>
(function() {{
    'use strict';

    function escapeHtml(str) {{
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }}

    const state = {{
        decisions: {{}},
        totalRecords: 0,
        totalVariants: 0,
    }};
    let records = [];

    const container = document.getElementById('card-container');

    // Load data from external JSON file (same approach as review.html)
    fetch('conflict_resolver_data.json')
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            records = data.records || [];
            state.totalRecords = records.length;
            state.totalVariants = records.reduce(function(sum, r) {{
                return sum + (r.variants ? r.variants.length : 0);
            }}, 0);
            buildFilterButtons();
            renderCards();
            updateProgress();
        }})
        .catch(function(e) {{
            container.innerHTML = '<div class="loading">Failed to load data: ' + e.message + '<br/>Please serve this page via an HTTP server (e.g., python -m http.server)</div>';
        }});

    function buildFilterButtons() {{
        var type_a = records.filter(function(r) {{ return r.type === 'unicode_conflict'; }}).length;
        var type_b = records.filter(function(r) {{ return r.type === 'name_conflict'; }}).length;
        var crit = records.filter(function(r) {{ return r.severity === 'critical'; }}).length;
        var warn = records.filter(function(r) {{ return r.severity === 'warning'; }}).length;
        var info = records.filter(function(r) {{ return r.severity === 'info'; }}).length;
        var total = records.length;
        document.getElementById('filter-bar').innerHTML =
            '<button class="filter-btn active" data-filter="all">All (' + total + ')</button>' +
            '<button class="filter-btn" data-filter="critical">Critical (' + crit + ')</button>' +
            '<button class="filter-btn" data-filter="warning">Warning (' + warn + ')</button>' +
            '<button class="filter-btn" data-filter="info">Info (' + info + ')</button>' +
            '<button class="filter-btn" data-filter="unicode_conflict">Type A (' + type_a + ')</button>' +
            '<button class="filter-btn" data-filter="name_conflict">Type B (' + type_b + ')</button>';
        // Re-bind filter events
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
    }}

    function renderCards() {{
        const fragment = document.createDocumentFragment();

    records.forEach(function(record) {{
        const card = document.createElement('div');
        card.className = 'conflict-card';
        card.dataset.id = record.id;
        card.dataset.type = record.type;
        card.dataset.severity = record.severity;

        const typeLabel = record.type === 'unicode_conflict' ? 'Unicode: ' + record.key : 'Name: ' + record.key;
        const sevLabel = record.severity.charAt(0).toUpperCase() + record.severity.slice(1);
        const actionHint = record.type === 'unicode_conflict'
            ? '保留一个变体在原 unicode，其余分配 PUA'
            : '保留一个变体在原名称，其余分配 PUA + _vN 后缀';

        let variantsHtml = '';
        record.variants.forEach(function(v, vi) {{
            const svgHtml = v.svg
                ? '<div class="svg-container">' + v.svg + '</div>'
                : '<div class="svg-placeholder"></div>';

            variantsHtml += '<div class="variant-panel" data-variant="' + vi + '">'
                + svgHtml
                + '<div class="variant-meta">'
                + '<span class="name">' + escapeHtml(v.name) + '</span>'
                + '<code>' + escapeHtml(v.glyphHash.substring(0, 12)) + '</code><br/>'
                + '<span class="sources">' + escapeHtml(v.sources) + '</span>'
                + '</div>'
                + '<div class="btn-group">'
                + '<button class="btn btn-keep" data-rid="' + record.id + '" data-vi="' + vi + '" data-act="keep">保留</button>'
                + '<button class="btn btn-pua" data-rid="' + record.id + '" data-vi="' + vi + '" data-act="pua">PUA</button>'
                + '</div>'
                + '</div>';
        }});

        card.innerHTML =
            '<div class="card-header">'
            + '<span class="key">' + escapeHtml(record.key) + '</span>'
            + '<span class="sev-badge ' + record.severity + '">' + sevLabel + '</span>'
            + '<span class="type-label">' + typeLabel + '</span>'
            + '<span class="variant-count">' + record.variantCount + ' variants</span>'
            + '<span class="decision-status">&#10003; Resolved</span>'
            + '</div>'
            + '<div class="card-hint">' + actionHint + '</div>'
            + '<div class="card-body">' + variantsHtml + '</div>';

        fragment.appendChild(card);
    }});

        container.innerHTML = '';
        container.appendChild(fragment);

        // Event delegation for decision buttons
        container.addEventListener('click', function(e) {{
            var btn = e.target.closest('.btn');
            if (!btn) return;
            var rid = btn.dataset.rid;
            var vi = btn.dataset.vi;
            var act = btn.dataset.act;
            if (rid === undefined) return;
            _decide(parseInt(rid), parseInt(vi), act);
        }});
    }}

    function _decide(recordId, variantIndex, action) {{
        var card = container.querySelector('.conflict-card[data-id="' + recordId + '"]');
        if (!card) return;

        var record = records[recordId];
        var panel = card.querySelector('.variant-panel[data-variant="' + variantIndex + '"]');
        if (!panel) return;

        // Ensure decisions entry exists for this record
        if (!state.decisions[recordId]) {{
            state.decisions[recordId] = {{
                recordType: record.type,
                key: record.key,
                variants: {{}}
            }};
        }}

        var variantKey = String(variantIndex);
        var currentDecision = state.decisions[recordId].variants[variantKey];

        if (currentDecision === action) {{
            // Toggle off: deselect this action
            delete state.decisions[recordId].variants[variantKey];
            panel.classList.remove('selected', 'pua-active');
        }} else {{
            // Apply new action
            panel.classList.remove('selected', 'pua-active');
            if (action === 'keep') {{
                panel.classList.add('selected');
            }} else if (action === 'pua') {{
                panel.classList.add('pua-active');
            }}
            state.decisions[recordId].variants[variantKey] = action;
        }}

        // Update card resolved state
        var decidedCount = Object.keys(state.decisions[recordId].variants).length;
        var allDecided = decidedCount === record.variants.length;
        card.classList.toggle('resolved', allDecided);

        updateProgress();
    }}

    function updateProgress() {{
        var decidedCount = 0;
        for (var rid in state.decisions) {{
            decidedCount += Object.keys(state.decisions[rid].variants).length;
        }}
        var pct = (decidedCount / state.totalVariants * 100).toFixed(1);
        document.getElementById('progress-text').textContent = decidedCount + ' / ' + state.totalVariants + ' variants resolved';
        document.getElementById('progress-fill').style.width = pct + '%';
        // Export enabled when there is at least one decision
        document.getElementById('export-btn').disabled = (decidedCount === 0);
    }};

    // Export
    document.getElementById('export-btn').addEventListener('click', function() {{
        var decidedCount = 0;
        for (var rid in state.decisions) {{
            decidedCount += Object.keys(state.decisions[rid].variants).length;
        }}
        const output = {{
            generatedAt: new Date().toISOString(),
            totalRecords: state.totalRecords,
            totalVariants: state.totalVariants,
            decidedCount: decidedCount,
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

    # Write JSON data file (loaded via fetch, same as review.html)
    with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump({'records': embedded}, f, ensure_ascii=False)
    data_size_kb = os.path.getsize(DATA_JSON_PATH) / 1024
    print(f'\n数据: {DATA_JSON_PATH} ({data_size_kb:.1f} KB)')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)

    size_kb = len(html_content) / 1024
    print(f'\n输出: {OUTPUT_PATH}')
    print(f'大小: {size_kb:.1f} KB')
    print(f'卡片数: {len(embedded)}')
    print(f'SVG 数: {svg_count}')
    print(f'\n注意: 此页面需要通过 HTTP 服务器访问（与 review.html 一样）')
    print(f'  cd report && python -m http.server 8080')
    print(f'  浏览器打开: http://localhost:8080/conflict_resolver.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
