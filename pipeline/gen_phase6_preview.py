#!/usr/bin/env python3
"""Phase 6 Conflict Detection Decision Preview HTML Generator v2"""
import json
import html as htmlmod
import os
import math

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(DATA_DIR, 'registry', 'glyph_registry.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'report', 'phase6_conflict_preview.html')

with open(REGISTRY_PATH, 'r') as f:
    data = json.load(f)

# --- unicode conflicts ---
uc_map = {}
for entry in data:
    uc = entry.get('canonicalUnicodeHex', '')
    if not uc:
        continue
    if uc not in uc_map:
        uc_map[uc] = []
    uc_map[uc].append(entry)

uc_conflicts = {uc: entries for uc, entries in uc_map.items() if len(entries) > 1}
uc_conflict_list = sorted(uc_conflicts.items(), key=lambda x: len(x[1]), reverse=True)

# --- name conflicts ---
name_map = {}
for entry in data:
    name = entry.get('canonicalName', '')
    if not name:
        continue
    if name not in name_map:
        name_map[name] = []
    name_map[name].append(entry)

name_conflicts = {n: entries for n, entries in name_map.items() if len(entries) > 1}
name_conflict_list = sorted(name_conflicts.items(), key=lambda x: len(x[1]), reverse=True)


def contour_to_path(contour):
    """Convert TTF contour points to SVG path data.

    TTF uses quadratic B-splines: on-curve points are explicit knots,
    off-curve points are control points. Two consecutive off-curve points
    have an implied on-curve midpoint between them.
    """
    if not contour:
        return ''

    n = len(contour)

    # If contour starts with off-curve, rotate so it starts with on-curve
    # (TTF convention: first on-curve point after trailing off-curves)
    pts = list(contour)

    # Find first on-curve point
    first_on = None
    for i, pt in enumerate(pts):
        if pt['on_curve']:
            first_on = i
            break

    if first_on is None:
        # All off-curve - degenerate case, just draw lines
        d = f'M {pts[0]["x"]:.1f} {pts[0]["y"]:.1f} '
        for pt in pts[1:]:
            d += f'L {pt["x"]:.1f} {pt["y"]:.1f} '
        d += 'Z'
        return d

    # Rotate so first point is on-curve
    pts = pts[first_on:] + pts[:first_on]

    d = f'M {pts[0]["x"]:.1f} {pts[0]["y"]:.1f} '
    i = 1
    while i < len(pts):
        pt = pts[i]
        if pt['on_curve']:
            d += f'L {pt["x"]:.1f} {pt["y"]:.1f} '
            i += 1
        else:
            # Off-curve control point
            if i + 1 < len(pts) and pts[i + 1]['on_curve']:
                # Q control endpoint
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {pts[i+1]["x"]:.1f} {pts[i+1]["y"]:.1f} '
                i += 2
            elif i + 1 < len(pts) and not pts[i + 1]['on_curve']:
                # Two consecutive off-curve: implied midpoint
                mid_x = (pt['x'] + pts[i + 1]['x']) / 2
                mid_y = (pt['y'] + pts[i + 1]['y']) / 2
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {mid_x:.1f} {mid_y:.1f} '
                i += 1
            else:
                # Last point is off-curve, wrap around to first point
                first = pts[0]
                mid_x = (pt['x'] + first['x']) / 2
                mid_y = (pt['y'] + first['y']) / 2
                d += f'Q {pt["x"]:.1f} {pt["y"]:.1f} {mid_x:.1f} {mid_y:.1f} '
                i += 1

    d += 'Z'
    return d


def contours_to_svg(contours, upm=1024):
    """Convert contours to SVG with auto-fit viewBox."""
    if not contours:
        return '<div class="no-icon">✗</div>'

    # Collect all points
    all_x = []
    all_y = []
    for contour in contours:
        for pt in contour:
            all_x.append(pt['x'])
            all_y.append(upm - pt['y'])  # Flip Y

    if not all_x:
        return '<div class="no-icon">✗</div>'

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    # Add padding
    pad = max(max_x - min_x, max_y - min_y) * 0.1
    vx = min_x - pad
    vy = min_y - pad
    vw = (max_x - min_x) + 2 * pad
    vh = (max_y - min_y) + 2 * pad

    if vw < 1 or vh < 1:
        return '<div class="no-icon">✗</div>'

    paths = []
    for contour in contours:
        # Build path with flipped Y
        flipped = [{'x': p['x'], 'y': upm - p['y'], 'on_curve': p['on_curve']} for p in contour]
        d = contour_to_path(flipped)
        if d:
            paths.append(f'<path d="{d}" fill="currentColor"/>')

    if not paths:
        return '<div class="no-icon">✗</div>'

    svg_content = ''.join(paths)
    return f'<svg viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" width="48" height="48" xmlns="http://www.w3.org/2000/svg">{svg_content}</svg>'


parts = []
parts.append(f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Phase 6 冲突检测决策面板</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f0f2f5; padding: 20px; }}
h1 {{ text-align: center; margin-bottom: 8px; font-size: 22px; }}
.stats {{ text-align: center; margin-bottom: 24px; color: #666; font-size: 14px; }}
.stats b {{ margin: 0 12px; }}

.section {{ background: #fff; border-radius: 8px; margin-bottom: 20px; padding: 20px; }}
.section h2 {{ font-size: 18px; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #eee; }}

.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.summary-card {{ background: #fafafa; border-radius: 6px; padding: 16px; text-align: center; }}
.summary-card .label {{ font-size: 12px; color: #999; margin-bottom: 4px; }}
.summary-card .value {{ font-size: 28px; font-weight: 700; }}
.summary-card .value.red {{ color: #ff4d4f; }}
.summary-card .value.orange {{ color: #fa8c16; }}
.summary-card .value.blue {{ color: #1890ff; }}

.conflict-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.conflict-table th {{ background: #fafafa; padding: 8px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #eee; }}
.conflict-table td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
.conflict-table tr:hover {{ background: #e6f7ff; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.badge.critical {{ background: #fff1f0; color: #cf1322; }}
.badge.warning {{ background: #fff7e6; color: #d46b08; }}
.badge.info {{ background: #e6f7ff; color: #096dd9; }}

.variants-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }}
.variant-card {{ border: 1px solid #e8e8e8; border-radius: 6px; padding: 10px; min-width: 140px; max-width: 200px; background: #fafafa; }}
.variant-card .icon-preview {{ text-align: center; margin-bottom: 6px; color: #333; }}
.variant-card .icon-preview svg {{ display: inline-block; }}
.variant-card .meta {{ font-size: 11px; color: #666; line-height: 1.6; }}
.variant-card .meta code {{ background: #eee; padding: 1px 4px; border-radius: 3px; font-size: 10px; }}
.no-icon {{ width: 48px; height: 48px; margin: 0 auto; background: #f0f0f0; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #ccc; font-size: 24px; }}

.question-box {{ background: #fffbe6; border: 1px solid #ffe58f; border-radius: 8px; padding: 16px; margin-bottom: 20px; }}
.question-box h3 {{ font-size: 14px; color: #d46b08; margin-bottom: 8px; }}
.question-box p {{ font-size: 13px; color: #666; line-height: 1.6; }}

.option {{ background: #f0f5ff; border: 1px solid #d6e4ff; border-radius: 6px; padding: 12px; margin: 8px 0; }}
.option.recommended {{ border-color: #52c41a; background: #f6ffed; }}
.option .title {{ font-weight: 600; font-size: 13px; }}
.option .desc {{ font-size: 12px; color: #666; margin-top: 4px; }}
</style>
</head>
<body>
<h1>Phase 6 冲突检测决策面板</h1>
<div class="stats">
  <span>Registry Entry: <b style="color:#1890ff">{len(data)}</b></span>
  <span>Unicode 冲突: <b style="color:#ff4d4f">{len(uc_conflicts)}</b></span>
  <span>Name 冲突: <b style="color:#fa8c16">{len(name_conflicts)}</b></span>
</div>

<div class="section">
<h2>总览</h2>
<div class="summary-grid">
<div class="summary-card"><div class="label">Unicode 冲突总数</div><div class="value red">{len(uc_conflicts)}</div></div>
<div class="summary-card"><div class="label">Name 冲突总数</div><div class="value orange">{len(name_conflicts)}</div></div>
<div class="summary-card"><div class="label">最严重 Unicode</div><div class="value blue">U+{uc_conflict_list[0][0]}</div></div>
<div class="summary-card"><div class="label">最严重 Name</div><div class="value blue" style="font-size:16px">{htmlmod.escape(name_conflict_list[0][0])}</div></div>
</div>
</div>

<div class="section">
<h2>Unicode 冲突 Top 10</h2>
<table class="conflict-table">
<tr><th>Unicode</th><th>冲突数</th><th>严重程度</th><th>变体预览</th></tr>''')

for uc, entries in uc_conflict_list[:10]:
    sev = 'critical' if len(entries) >= 5 else ('warning' if len(entries) >= 3 else 'info')
    sev_label = 'Critical' if len(entries) >= 5 else ('Warning' if len(entries) >= 3 else 'Info')
    variants_html = '<div class="variants-row">'
    for e in entries[:4]:
        svg = contours_to_svg(e.get('contours'), 1024)
        src_names = [s.get('projects', ['?'])[0] for s in e.get('sources', [])[:3]]
        variants_html += f'''<div class="variant-card">
<div class="icon-preview">{svg}</div>
<div class="meta">
Hash: <code>{e["glyphHash"][:12]}...</code><br/>
Name: <code>{htmlmod.escape(e.get("canonicalName","?"))}</code><br/>
Sources: <code>{htmlmod.escape(", ".join(src_names))}</code>
</div>
</div>'''
    variants_html += '</div>'
    parts.append(f'''<tr>
<td><b>U+{uc}</b></td>
<td>{len(entries)}</td>
<td><span class="badge {sev}">{sev_label}</span></td>
<td>{variants_html}</td>
</tr>''')

parts.append(f'''</table>
</div>

<div class="section">
<h2>Name 冲突 Top 10</h2>
<table class="conflict-table">
<tr><th>Icon Name</th><th>冲突数</th><th>严重程度</th><th>变体预览</th></tr>''')

for name, entries in name_conflict_list[:10]:
    sev = 'critical' if len(entries) >= 5 else ('warning' if len(entries) >= 3 else 'info')
    sev_label = 'Critical' if len(entries) >= 5 else ('Warning' if len(entries) >= 3 else 'Info')
    variants_html = '<div class="variants-row">'
    for e in entries[:4]:
        svg = contours_to_svg(e.get('contours'), 1024)
        src_names = [s.get('projects', ['?'])[0] for s in e.get('sources', [])[:3]]
        variants_html += f'''<div class="variant-card">
<div class="icon-preview">{svg}</div>
<div class="meta">
Hash: <code>{e["glyphHash"][:12]}...</code><br/>
Unicode: <code>U+{e.get("canonicalUnicodeHex","?")}</code><br/>
Sources: <code>{htmlmod.escape(", ".join(src_names))}</code>
</div>
</div>'''
    variants_html += '</div>'
    parts.append(f'''<tr>
<td><b>{htmlmod.escape(name)}</b></td>
<td>{len(entries)}</td>
<td><span class="badge {sev}">{sev_label}</span></td>
<td>{variants_html}</td>
</tr>''')

# Decision questions
crit_count = sum(1 for _, e in uc_conflict_list if len(e) >= 5)
warn_count = sum(1 for _, e in uc_conflict_list if 3 <= len(e) < 5)
info_count = sum(1 for _, e in uc_conflict_list if len(e) == 2)

parts.append(f'''</table>
</div>

<div class="section">
<h2>需要你做的决策</h2>

<div class="question-box">
<h3>Q1: 冲突检测范围</h3>
<p>Type A (Unicode 冲突): {len(uc_conflicts)} 个 — 同 unicode 不同字形，必须解决</p>
<p>Type B (Name 冲突): {len(name_conflicts)} 个 — 同名不同形，必须解决</p>
<p>Type C (Duplicate Glyph): 同 glyphHash 多来源 905 个 — 是正常合并情况</p>
<p><b>问题</b>：Type C 是否需要列入 Phase 6 报告？</p>
<div class="option recommended">
<div class="title">A: 只报告 Type A + Type B（推荐）</div>
<div class="desc">Type C 是正常情况，不需要关注，减少噪音</div>
</div>
<div class="option">
<div class="title">B: 全部三种都报告</div>
<div class="desc">完整记录所有冲突类型，便于后续追溯</div>
</div>
</div>

<div class="question-box">
<h3>Q2: 报告输出形式</h3>
<div class="option recommended">
<div class="title">A: JSON + Markdown（推荐）</div>
<div class="desc">JSON 供 Phase 7 程序消费，Markdown 给人看，足够清晰</div>
</div>
<div class="option">
<div class="title">B: JSON + Markdown + HTML 可视化</div>
<div class="desc">额外生成带 SVG 预览的 HTML，方便视觉对比</div>
</div>
</div>

<div class="question-box">
<h3>Q3: 严重性分级阈值</h3>
<p>分布：5+ 变体有 {crit_count} 个，3-4 变体有 {warn_count} 个，2 变体有 {info_count} 个</p>
<div class="option recommended">
<div class="title">A: 三级分级（推荐）: Critical(5+) / Warning(3-4) / Info(2)</div>
</div>
<div class="option">
<div class="title">B: 两级分级: High(3+) / Low(2)</div>
</div>
</div>

<div class="question-box">
<h3>Q4: PUA 分配策略（Phase 7 预判）</h3>
<p>Phase 7 需要为 Type A 冲突分配新的 PUA 码位（E000-F8FF）</p>
<div class="option recommended">
<div class="title">A: 按严重程度顺序分配（推荐）: Critical 先分配低 PUA</div>
</div>
<div class="option">
<div class="title">B: 按 glyphHash 字母序分配: 确定性更高</div>
</div>
</div>

<div class="question-box">
<h3>Q5: 脚本语言</h3>
<p>plan.md 指定 Python，已收集参考脚本是 Node.js</p>
<div class="option recommended">
<div class="title">A: Python（推荐）</div>
<div class="desc">与 Phase 3-5 保持一致，直接消费 registry JSON</div>
</div>
<div class="option">
<div class="title">B: Node.js</div>
<div class="desc">复用已收集的 iconfont_compare.js 模式</div>
</div>
</div>

</div>

</body>
</html>''')

html_content = '\n'.join(parts)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f'HTML 已生成: {OUTPUT_PATH}')
print(f'大小: {len(html_content) / 1024:.1f} KB')
