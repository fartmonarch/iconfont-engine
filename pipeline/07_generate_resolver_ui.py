#!/usr/bin/env python3
"""Phase 7: Conflict Resolution — Interactive HTML Generator v2

Reads filtered_conflicts.json + glyph_registry.json, generates a self-contained
HTML page with SVG-rendered glyphs and GROUP-BASED conflict resolution.

New features:
- Group-based decisions: Keep Group + multiple PUA Groups
- Checkbox multi-select for variants
- Manual merge button for pending cards
- localStorage persistence
- Correct SVG evenodd fill across contours
"""
import json
import os
import sys

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICTS_PATH = os.path.join(DATA_DIR, 'report', 'filtered_conflicts.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'report', 'conflict_resolver.html')
DATA_JSON_PATH = os.path.join(
    DATA_DIR, 'report', 'conflict_resolver_data.json')


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
    subpaths = []
    for contour in contours:
        flipped = [{'x': p['x'], 'y': upm - p['y'],
                    'on_curve': p['on_curve']} for p in contour]
        d = contour_to_path(flipped)
        if d:
            subpaths.append(d)
    if not subpaths:
        return None
    svg_content = f'<path d="{" ".join(subpaths)}" fill="#333"/>'
    return (
        f'<svg viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" '
        f'width="{size}" height="{size}" fill-rule="evenodd" xmlns="http://www.w3.org/2000/svg">'
        f'{svg_content}</svg>'
    )


def build_embedded_records(data):
    """Build JSON for embedding. Only Type A+B, with inline SVG strings.

    CRITICAL: id MUST be the original index in filtered_conflicts.json
    so that decisions can be matched by resolve script.
    """
    all_records = data['records']
    embedded = []
    for original_idx, r in enumerate(all_records):
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
            'id': original_idx,
            'type': r['type'],
            'severity': r['severity'],
            'key': r['key'],
            'variantCount': r['variantCount'],
            'resolution_hint': r['resolution_hint'],
            'isFalsePositive': r.get('isFalsePositive', False),
            'similarityScore': r.get('similarityScore'),
            'similarityType': r.get('similarityType', ''),
            'variants': variants,
        })
    return embedded


def generate_html(embedded_records):
    """Generate the complete self-contained HTML page."""
    total = len(embedded_records)
    type_a = sum(
        1 for r in embedded_records if r['type'] == 'unicode_conflict')
    type_b = sum(1 for r in embedded_records if r['type'] == 'name_conflict')
    crit = sum(1 for r in embedded_records if r['severity'] == 'critical')
    warn = sum(1 for r in embedded_records if r['severity'] == 'warning')
    info = sum(1 for r in embedded_records if r['severity'] == 'info')
    fp_count = sum(1 for r in embedded_records if r.get('isFalsePositive'))

    html_parts = []
    html_parts.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phase 7 Conflict Resolution v2</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", "Segoe UI", sans-serif; background: #f0f2f5; padding: 0; }}

#app-header {{
    position: sticky; top: 0; z-index: 100;
    background: #fff; border-bottom: 1px solid #e8e8e8;
    padding: 12px 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}}
#app-header h1 {{ font-size: 18px; margin-bottom: 8px; }}

.progress-section {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
#progress-text {{ font-size: 13px; color: #666; white-space: nowrap; }}
.progress-bar {{ flex: 1; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }}
.progress-fill {{ height: 100%; background: #52c41a; transition: width 0.3s; width: 0%; }}

.filter-bar {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }}
.filter-btn {{ padding: 4px 12px; border: 1px solid #d9d9d9; background: #fff; border-radius: 4px; cursor: pointer; font-size: 12px; }}
.filter-btn.active {{ background: #1890ff; color: #fff; border-color: #1890ff; }}
.filter-btn:hover {{ border-color: #1890ff; }}

.actions {{ text-align: right; }}
#export-btn {{ padding: 6px 16px; background: #1890ff; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }}
#export-btn:disabled {{ background: #d9d9d9; cursor: not-allowed; }}
#export-btn:hover:not(:disabled) {{ background: #40a9ff; }}
#clear-cache-btn {{ padding: 6px 16px; background: #fff; color: #666; border: 1px solid #d9d9d9; border-radius: 4px; cursor: pointer; font-size: 13px; margin-right: 8px; }}

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
.conflict-card.false-positive {{ border-left: 4px solid #52c41a; background: #f6ffed; }}
.conflict-card.false-positive .card-header {{ background: #f6ffed; }}
.conflict-card.false-positive .card-hint {{ background: #d9f7be; color: #237804; }}
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
.fp-badge {{ background: #52c41a; color: #fff; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-left: 8px; }}

/* Variant selection toolbar */
.variant-toolbar {{
    display: flex; align-items: center; gap: 8px;
    padding: 8px 14px; background: #fafafa; border-bottom: 1px solid #f0f0f0;
}}
.variant-toolbar label {{ font-size: 12px; color: #666; cursor: pointer; display: flex; align-items: center; gap: 4px; }}
.variant-toolbar input[type="checkbox"] {{ cursor: pointer; }}
.btn-group-action {{
    padding: 3px 10px; border: 1px solid #d9d9d9; background: #fff;
    border-radius: 4px; cursor: pointer; font-size: 12px;
}}
.btn-group-action:hover {{ border-color: #1890ff; color: #1890ff; }}
.btn-group-action.primary {{ background: #1890ff; color: #fff; border-color: #1890ff; }}
.btn-group-action.primary:hover {{ background: #40a9ff; }}
.btn-group-action.success {{ background: #52c41a; color: #fff; border-color: #52c41a; }}
.btn-group-action.success:hover {{ background: #73d13d; }}
.btn-group-action.warning {{ background: #fa8c16; color: #fff; border-color: #fa8c16; }}
.btn-group-action.warning:hover {{ background: #ffa940; }}

/* Card body */
.card-body {{
    display: flex; gap: 12px; padding: 14px;
    overflow-x: auto; flex-wrap: nowrap;
}}
.variant-panel {{
    flex: 0 0 auto; width: 140px; max-width: 140px;
    border: 1px solid #e8e8e8; border-radius: 6px; padding: 10px;
    text-align: center; background: #fff;
    transition: border-color 0.2s, background 0.2s;
}}
.variant-panel:hover {{ border-color: #d9d9d9; }}
.variant-panel.selected {{ border-color: #52c41a; background: #f6ffed; }}
.variant-panel.pua-active {{ border-color: #fa8c16; background: #fff7e6; }}
.variant-panel.in-group {{ border-color: #1890ff; background: #e6f7ff; opacity: 0.7; }}
.variant-panel .svg-container {{ width: 80px; height: 80px; margin: 0 auto 8px; display: flex; align-items: center; justify-content: center; }}
.variant-panel .svg-container svg {{ max-width: 100%; max-height: 100%; }}
.variant-meta {{ font-size: 11px; color: #666; margin-bottom: 8px; word-break: break-all; }}
.variant-meta .name {{ font-weight: 600; color: #333; font-size: 12px; display: block; margin-bottom: 2px; }}
.variant-meta code {{ font-size: 10px; color: #999; }}
.variant-checkbox {{ margin-bottom: 6px; }}

/* Groups area */
.groups-area {{
    padding: 10px 14px; background: #fafafa; border-top: 1px solid #f0f0f0;
    display: flex; flex-wrap: wrap; gap: 8px;
}}
.groups-area:empty {{ display: none; }}
.group-tag {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 10px; border-radius: 4px; font-size: 12px;
}}
.group-tag.keep {{ background: #f6ffed; border: 1px solid #b7eb8f; color: #389e0d; }}
.group-tag.pua {{ background: #fff7e6; border: 1px solid #ffd591; color: #d46b08; }}
.group-tag .group-label {{ font-weight: 600; }}
.group-tag .group-variants {{ color: #666; font-size: 11px; }}
.group-tag .btn-remove {{ background: none; border: none; cursor: pointer; color: #999; font-size: 14px; padding: 0 2px; }}
.group-tag .btn-remove:hover {{ color: #ff4d4f; }}

/* Card footer */
.card-footer {{
    padding: 8px 14px; background: #fafafa; border-top: 1px solid #f0f0f0;
    display: flex; justify-content: space-between; align-items: center;
}}
.btn-manual-merge {{
    padding: 4px 12px; background: #52c41a; color: #fff; border: none;
    border-radius: 4px; cursor: pointer; font-size: 12px;
}}
.btn-manual-merge:hover {{ background: #73d13d; }}
.btn-unmerge {{
    padding: 4px 12px; background: #fff; color: #666; border: 1px solid #d9d9d9;
    border-radius: 4px; cursor: pointer; font-size: 12px;
}}
.btn-unmerge:hover {{ border-color: #ff4d4f; color: #ff4d4f; }}

/* SVG placeholder */
.svg-placeholder {{ width: 80px; height: 80px; margin: 0 auto; background: #f0f0f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #ccc; font-size: 24px; }}

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
    <h1>Phase 7 Conflict Resolution v2 — 分组审核</h1>
    <div class="progress-section">
        <span id="progress-text">Loading...</span>
        <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
    </div>
    <div class="filter-bar" id="filter-bar">
        <button class="filter-btn active" data-filter="all">All</button>
    </div>
    <div class="actions">
        <button id="clear-cache-btn">Clear Cache</button>
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

    const STORAGE_KEY = 'iconfont_conflict_decisions_v2';

    const state = {{
        decisions: {{}},      // recordId -> {{ groups: [{{ type, variants: [] }}] }}
        selections: {{}},     // recordId -> Set(variantIndex)
        totalRecords: 0,
        totalVariants: 0,
        pendingRecords: 0,
        pendingVariants: 0,
        autoMergedRecords: 0,
    }};
    let records = [];

    const container = document.getElementById('card-container');

    // Load data
    fetch('conflict_resolver_data.json')
        .then(function(r) {{ return r.json(); }})
        .then(function(data) {{
            records = data.records || [];
            state.totalRecords = records.length;
            state.totalVariants = records.reduce(function(sum, r) {{ return sum + (r.variants ? r.variants.length : 0); }}, 0);
            state.autoMergedRecords = records.filter(function(r) {{ return r.isFalsePositive; }}).length;
            state.pendingRecords = state.totalRecords - state.autoMergedRecords;
            state.pendingVariants = records.filter(function(r) {{ return !r.isFalsePositive; }}).reduce(function(sum, r) {{ return sum + (r.variants ? r.variants.length : 0); }}, 0);

            // Load cached decisions
            loadFromLocalStorage();

            buildFilterButtons();
            renderCards();
            updateProgress();
        }})
        .catch(function(e) {{
            container.innerHTML = '<div class="loading">Failed to load data: ' + e.message + '<br/>Please serve this page via HTTP server</div>';
        }});

    // ===================== localStorage =====================
    function saveToLocalStorage() {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state.decisions));
    }}

    function loadFromLocalStorage() {{
        try {{
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {{
                state.decisions = JSON.parse(raw);
            }}
        }} catch(e) {{ console.warn('Failed to load cache:', e); }}
    }}

    function clearCache() {{
        localStorage.removeItem(STORAGE_KEY);
        state.decisions = {{}};
        renderCards();
        updateProgress();
    }}

    document.getElementById('clear-cache-btn').addEventListener('click', clearCache);

    // ===================== Filter Buttons =====================
    function buildFilterButtons() {{
        var type_a = records.filter(function(r) {{ return r.type === 'unicode_conflict'; }}).length;
        var type_b = records.filter(function(r) {{ return r.type === 'name_conflict'; }}).length;
        var crit = records.filter(function(r) {{ return r.severity === 'critical'; }}).length;
        var warn = records.filter(function(r) {{ return r.severity === 'warning'; }}).length;
        var info = records.filter(function(r) {{ return r.severity === 'info'; }}).length;
        var fp = records.filter(function(r) {{ return r.isFalsePositive; }}).length;
        var pending = records.filter(function(r) {{ return !r.isFalsePositive; }}).length;
        var total = records.length;
        document.getElementById('filter-bar').innerHTML =
            '<button class="filter-btn active" data-filter="all">All (' + total + ')</button>' +
            '<button class="filter-btn" data-filter="pending" style="color:#1890ff;font-weight:600;">Pending (' + pending + ')</button>' +
            '<button class="filter-btn" data-filter="false_positive" style="color:#52c41a;">Auto-Merged (' + fp + ')</button>' +
            '<button class="filter-btn" data-filter="critical">Critical (' + crit + ')</button>' +
            '<button class="filter-btn" data-filter="warning">Warning (' + warn + ')</button>' +
            '<button class="filter-btn" data-filter="info">Info (' + info + ')</button>' +
            '<button class="filter-btn" data-filter="unicode_conflict">Type A (' + type_a + ')</button>' +
            '<button class="filter-btn" data-filter="name_conflict">Type B (' + type_b + ')</button>';
        document.querySelectorAll('.filter-btn').forEach(function(btn) {{
            btn.addEventListener('click', function() {{
                document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
                btn.classList.add('active');
                var filter = btn.dataset.filter;
                document.querySelectorAll('.conflict-card').forEach(function(card) {{
                    if (filter === 'all') {{
                        card.classList.remove('hidden');
                    }} else if (filter === 'pending') {{
                        card.classList.toggle('hidden', card.dataset.falsePositive === 'true');
                    }} else if (filter === 'false_positive') {{
                        card.classList.toggle('hidden', card.dataset.falsePositive !== 'true');
                    }} else {{
                        var match = card.dataset.severity === filter || card.dataset.type === filter;
                        card.classList.toggle('hidden', !match);
                    }}
                }});
            }});
        }});
    }}

    // ===================== Render Cards =====================
    function renderCards() {{
        container.innerHTML = '';
        var fragment = document.createDocumentFragment();

        // Sort: pending first, auto-merged last
        var sorted = records.slice().sort(function(a, b) {{
            return (a.isFalsePositive ? 1 : 0) - (b.isFalsePositive ? 1 : 0);
        }});

        sorted.forEach(function(record) {{
            fragment.appendChild(buildCard(record));
        }});
        container.appendChild(fragment);
    }}

    function buildCard(record) {{
        var card = document.createElement('div');
        var isUnmerged = state.decisions[record.id] && state.decisions[record.id].unmerge;
        var isFp = record.isFalsePositive && !isUnmerged;
        var hasDecision = !!state.decisions[record.id] && !isUnmerged;
        var isResolved = isFp || (hasDecision && isRecordResolved(record));
        card.className = 'conflict-card' + (isFp ? ' false-positive' : '') + (isResolved ? ' resolved' : '');
        card.dataset.id = record.id;
        card.dataset.type = record.type;
        card.dataset.severity = record.severity;
        card.dataset.falsePositive = isFp ? 'true' : 'false';

        var typeLabel = record.type === 'unicode_conflict' ? 'Unicode: ' + record.key : 'Name: ' + record.key;
        var sevLabel = record.severity.charAt(0).toUpperCase() + record.severity.slice(1);
        var simScore = record.similarityScore !== undefined ? record.similarityScore : null;

        // Header
        var fpBadge = isFp ? '<span class="fp-badge">自动合并</span>' : '';
        var headerHtml =
            '<div class="card-header">'
            + '<span class="key">' + escapeHtml(record.key) + '</span>'
            + '<span class="sev-badge ' + record.severity + '">' + sevLabel + '</span>'
            + '<span class="type-label">' + typeLabel + '</span>'
            + fpBadge
            + '<span class="variant-count">' + record.variantCount + ' variants</span>'
            + '<span class="decision-status">&#10003; Resolved</span>'
            + '</div>';

        // Hint
        var hintHtml;
        if (isFp) {{
            hintHtml = '<div class="card-hint">【已自动合并】' + (record.similarityType === 'visual' ? '视觉相似度' : '几何相似度')
                + (simScore !== null ? ' ' + (simScore * 100).toFixed(1) + '%' : '')
                + ' — 这些变体已自动合并</div>';
        }} else {{
            hintHtml = '<div class="card-hint">'
                + '选中变体后点击"设为保留组"或"添加 PUA 组"进行分组。'
                + (record.type === 'unicode_conflict' ? ' 保留组合并后共享原 unicode。' : ' 保留组合并后共享原名称。')
                + '</div>';
        }}

        // Toolbar + Variants
        var variantsHtml = '';
        record.variants.forEach(function(v, vi) {{
            var svgHtml = v.svg ? '<div class="svg-container">' + v.svg + '</div>' : '<div class="svg-placeholder"></div>';
            var groupInfo = findVariantGroup(record.id, vi);
            var inGroupClass = groupInfo ? ' in-group' : '';
            var checkbox = !isFp ? '<div class="variant-checkbox"><input type="checkbox" data-rid="' + record.id + '" data-vi="' + vi + '" class="var-checkbox"' + (isSelected(record.id, vi) ? ' checked' : '') + '></div>' : '';
            var groupLabel = groupInfo ? '<div style="font-size:10px;color:#1890ff;margin-bottom:4px;">' + groupInfo.label + '</div>' : '';

            variantsHtml += '<div class="variant-panel' + inGroupClass + '" data-variant="' + vi + '">'
                + checkbox
                + groupLabel
                + svgHtml
                + '<div class="variant-meta">'
                + '<span class="name">' + escapeHtml(v.name) + '</span>'
                + '<code>' + escapeHtml(v.glyphHash.substring(0, 12)) + '</code><br/>'
                + '<span class="sources">' + escapeHtml(v.sources) + '</span>'
                + '</div>'
                + '</div>';
        }});

        var toolbarHtml = '';
        if (!isFp) {{
            toolbarHtml = '<div class="variant-toolbar">'
                + '<label><input type="checkbox" class="select-all" data-rid="' + record.id + '"> 全选</label>'
                + '<button class="btn-group-action success" data-rid="' + record.id + '" data-action="keep">设为保留组</button>'
                + '<button class="btn-group-action warning" data-rid="' + record.id + '" data-action="pua">添加 PUA 组</button>'
                + '<button class="btn-group-action" data-rid="' + record.id + '" data-action="clear">取消选择</button>'
                + '</div>';
        }}

        var bodyHtml = '<div class="card-body">' + variantsHtml + '</div>';

        // Groups area
        var groupsHtml = buildGroupsArea(record);

        // Footer
        var footerHtml = '';
        if (!isFp) {{
            footerHtml = '<div class="card-footer">'
                + '<button class="btn-manual-merge" data-rid="' + record.id + '">人工合并（所有变体视为相同）</button>'
                + '<span style="font-size:11px;color:#999;">或：选中部分变体后点击上方按钮分组</span>'
                + '</div>';
        }} else {{
            footerHtml = '<div class="card-footer">'
                + '<button class="btn-unmerge" data-rid="' + record.id + '">取消自动合并（转为人工审核）</button>'
                + '</div>';
        }}

        card.innerHTML = headerHtml + hintHtml + toolbarHtml + bodyHtml + groupsHtml + footerHtml;
        return card;
    }}

    function findVariantGroup(recordId, variantIndex) {{
        var dec = state.decisions[recordId];
        if (!dec || !dec.groups) return null;
        for (var gi = 0; gi < dec.groups.length; gi++) {{
            var g = dec.groups[gi];
            if (g.variants.indexOf(variantIndex) >= 0) {{
                return {{ label: g.type === 'keep' ? '保留组' : ('PUA-' + (gi + 1)), groupIndex: gi }};
            }}
        }}
        return null;
    }}

    function isSelected(recordId, variantIndex) {{
        return state.selections[recordId] && state.selections[recordId].has(variantIndex);
    }}

    function buildGroupsArea(record) {{
        var dec = state.decisions[record.id];
        if (!dec || !dec.groups || dec.groups.length === 0) return '';
        var html = '<div class="groups-area">';
        dec.groups.forEach(function(g, gi) {{
            var cls = g.type === 'keep' ? 'keep' : 'pua';
            var label = g.type === 'keep' ? '保留组' : ('PUA-' + (gi + 1));
            var vnames = g.variants.map(function(vi) {{ return 'v' + (vi + 1); }}).join(', ');
            html += '<div class="group-tag ' + cls + '">'
                + '<span class="group-label">' + label + '</span>'
                + '<span class="group-variants">(' + vnames + ')</span>'
                + '<button class="btn-remove" data-rid="' + record.id + '" data-gi="' + gi + '">&times;</button>'
                + '</div>';
        }});
        html += '</div>';
        return html;
    }}

    function isRecordResolved(record) {{
        var dec = state.decisions[record.id];
        if (!dec || !dec.groups) return false;
        var grouped = new Set();
        dec.groups.forEach(function(g) {{
            g.variants.forEach(function(v) {{ grouped.add(v); }});
        }});
        return grouped.size === record.variants.length;
    }}

    // ===================== Event Delegation =====================
    container.addEventListener('click', function(e) {{
        // Variant checkbox
        var cb = e.target.closest('.var-checkbox');
        if (cb) {{
            var rid = parseInt(cb.dataset.rid);
            var vi = parseInt(cb.dataset.vi);
            toggleSelection(rid, vi);
            var panel = cb.closest('.variant-panel');
            if (panel) panel.classList.toggle('selected', cb.checked);
            return;
        }}

        // Variant panel click (toggle selection)
        var panel = e.target.closest('.variant-panel');
        if (panel && !panel.classList.contains('in-group') && !e.target.closest('.var-checkbox')) {{
            var cb2 = panel.querySelector('.var-checkbox');
            if (cb2) {{
                cb2.checked = !cb2.checked;
                panel.classList.toggle('selected', cb2.checked);
                var rid = parseInt(cb2.dataset.rid);
                var vi = parseInt(cb2.dataset.vi);
                toggleSelection(rid, vi);
            }}
            return;
        }}

        // Select all
        var sa = e.target.closest('.select-all');
        if (sa) {{
            var rid = parseInt(sa.dataset.rid);
            var record = records.find(function(r) {{ return r.id === rid; }});
            if (record) {{
                var allSelected = record.variants.every(function(_, vi) {{ return isSelected(rid, vi); }});
                if (allSelected) {{
                    state.selections[rid] = new Set();
                }} else {{
                    state.selections[rid] = new Set(record.variants.map(function(_, i) {{ return i; }}));
                }}
                updateCard(rid);
            }}
            return;
        }}

        // Group action buttons
        var btn = e.target.closest('.btn-group-action');
        if (btn) {{
            var rid = parseInt(btn.dataset.rid);
            var action = btn.dataset.action;
            if (action === 'clear') {{
                delete state.selections[rid];
            }} else {{
                createGroup(rid, action);
            }}
            updateCard(rid);
            updateProgress();
            saveToLocalStorage();
            return;
        }}

        // Remove group
        var rm = e.target.closest('.btn-remove');
        if (rm) {{
            var rid = parseInt(rm.dataset.rid);
            var gi = parseInt(rm.dataset.gi);
            removeGroup(rid, gi);
            updateCard(rid);
            updateProgress();
            saveToLocalStorage();
            return;
        }}

        // Manual merge
        var mm = e.target.closest('.btn-manual-merge');
        if (mm) {{
            var rid = parseInt(mm.dataset.rid);
            var record = records.find(function(r) {{ return r.id === rid; }});
            if (record) {{
                manualMerge(record);
                updateCard(rid);
                updateProgress();
                saveToLocalStorage();
                scrollNext();
            }}
            return;
        }}

        // Unmerge (cancel auto-merge)
        var um = e.target.closest('.btn-unmerge');
        if (um) {{
            var rid = parseInt(um.dataset.rid);
            unmerge(rid);
            renderCards();  // unmerge may change card ordering
            updateProgress();
            saveToLocalStorage();
            return;
        }}
    }});

    // ===================== Actions =====================
    function toggleSelection(recordId, variantIndex) {{
        if (!state.selections[recordId]) state.selections[recordId] = new Set();
        if (state.selections[recordId].has(variantIndex)) {{
            state.selections[recordId].delete(variantIndex);
        }} else {{
            state.selections[recordId].add(variantIndex);
        }}
    }}

    function createGroup(recordId, type) {{
        var selected = state.selections[recordId];
        if (!selected || selected.size === 0) {{
            alert('请先勾选变体');
            return;
        }}

        // Exclude already grouped variants
        var dec = state.decisions[recordId];
        var grouped = new Set();
        if (dec && dec.groups) {{
            dec.groups.forEach(function(g) {{
                g.variants.forEach(function(v) {{ grouped.add(v); }});
            }});
        }}

        var newVariants = [];
        selected.forEach(function(vi) {{
            if (!grouped.has(vi)) newVariants.push(vi);
        }});

        if (newVariants.length === 0) {{
            alert('选中的变体已全部分组');
            return;
        }}

        if (!state.decisions[recordId]) state.decisions[recordId] = {{ groups: [] }};
        if (!state.decisions[recordId].groups) state.decisions[recordId].groups = [];

        state.decisions[recordId].groups.push({{
            type: type,
            variants: newVariants.sort(function(a,b){{ return a-b; }})
        }});

        // Clear selection for this record
        delete state.selections[recordId];
    }}

    function removeGroup(recordId, groupIndex) {{
        var dec = state.decisions[recordId];
        if (!dec || !dec.groups) return;
        dec.groups.splice(groupIndex, 1);
        if (dec.groups.length === 0) delete state.decisions[recordId];
    }}

    function manualMerge(record) {{
        state.decisions[record.id] = {{
            groups: [{{ type: 'keep', variants: record.variants.map(function(_, i) {{ return i; }}) }}]
        }};
        delete state.selections[record.id];
    }}

    function scrollNext() {{
        var currentCenter = window.innerHeight * 0.5;
        var nextCard = container.querySelector('.conflict-card:not(.resolved):not(.false-positive)');
        if (!nextCard) return;
        var nextTop = nextCard.getBoundingClientRect().top + window.pageYOffset;
        var targetY = nextTop - currentCenter + (nextCard.offsetHeight / 2);
        window.scrollTo({{ top: Math.max(0, targetY), behavior: 'smooth' }});
    }}

    function updateCard(recordId) {{
        var record = records.find(function(r) {{ return r.id === recordId; }});
        if (!record) return;
        var oldCard = container.querySelector('.conflict-card[data-id="' + recordId + '"]');
        if (!oldCard) return;
        var newCard = buildCard(record);
        oldCard.parentNode.replaceChild(newCard, oldCard);
    }}

    function unmerge(recordId) {{
        // Mark this record as unmerged — override the auto-merge status
        state.decisions[recordId] = {{ unmerge: true }};
        delete state.selections[recordId];
        // No alert needed — renderCards will immediately reflect the change
    }}

    // ===================== Progress =====================
    function updateProgress() {{
        var resolvedPending = 0;
        records.forEach(function(r) {{
            if (!r.isFalsePositive && isRecordResolved(r)) resolvedPending++;
        }});
        var pending = state.pendingRecords;
        var pct = pending > 0 ? (resolvedPending / pending * 100).toFixed(1) : 100;
        document.getElementById('progress-text').textContent =
            'Auto-merged: ' + state.autoMergedRecords +
            ' | Pending: ' + state.pendingRecords +
            ' | Resolved: ' + resolvedPending + '/' + pending;
        document.getElementById('progress-fill').style.width = pct + '%';

        var hasDecisions = Object.keys(state.decisions).length > 0;
        document.getElementById('export-btn').disabled = !hasDecisions;
    }}

    // ===================== Export =====================
    document.getElementById('export-btn').addEventListener('click', function() {{
        var resolvedPending = 0;
        records.forEach(function(r) {{
            if (!r.isFalsePositive && isRecordResolved(r)) resolvedPending++;
        }});

        // Build clean export
        var exportDecisions = {{}};
        for (var rid in state.decisions) {{
            var dec = state.decisions[rid];
            if (dec.groups) {{
                exportDecisions[rid] = {{
                    recordKey: records[rid] ? records[rid].key : '',
                    recordType: records[rid] ? records[rid].type : '',
                    groups: dec.groups.map(function(g) {{
                        return {{ type: g.type, variants: g.variants }};
                    }})
                }};
            }}
        }}

        var output = {{
            generatedAt: new Date().toISOString(),
            totalRecords: state.totalRecords,
            autoMergedRecords: state.autoMergedRecords,
            pendingRecords: state.pendingRecords,
            resolvedPending: resolvedPending,
            decisions: exportDecisions,
        }};
        var blob = new Blob([JSON.stringify(output, null, 2)], {{ type: 'application/json' }});
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
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
    print('Phase 7: Conflict Resolution v2 — HTML Generator')
    print('=' * 60)

    if not os.path.exists(CONFLICTS_PATH):
        print(f'\n错误: 未找到冲突数据文件 {CONFLICTS_PATH}')
        print('请先运行 Phase 6.5: python pipeline/06_5_filter_false_positives.py')
        return 1

    with open(CONFLICTS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    total_records = len(data.get('records', []))
    print(f'\n加载冲突数据: {total_records} 条')

    embedded = build_embedded_records(data)
    type_a = sum(1 for r in embedded if r['type'] == 'unicode_conflict')
    type_b = sum(1 for r in embedded if r['type'] == 'name_conflict')
    print(f'过滤后: {len(embedded)} 条 (Type A: {type_a}, Type B: {type_b})')

    svg_count = sum(len(r['variants']) for r in embedded)
    print(f'生成 SVG 预览: {svg_count} 个')

    html_content = generate_html(embedded)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump({'records': embedded}, f, ensure_ascii=False)
    data_size_kb = os.path.getsize(DATA_JSON_PATH) / 1024
    print(f'\n数据: {DATA_JSON_PATH} ({data_size_kb:.1f} KB)')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    html_size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f'输出: {OUTPUT_PATH} ({html_size_kb:.1f} KB)')
    print(f'卡片数: {len(embedded)}')
    print(f'SVG 数: {svg_count}')
    print('\n请通过 HTTP 服务器访问: cd report && python -m http.server 8080')
    print('浏览器打开: http://localhost:8080/conflict_resolver.html')


if __name__ == '__main__':
    sys.exit(main() or 0)
