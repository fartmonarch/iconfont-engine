"""
Phase 4: Geometry Normalization（几何标准化）

技术：Python + numpy（批量坐标运算加速）
输入：
  - sources/phase3_glyphs/raw_glyphs.json
  - sources/phase3_glyphs/extraction_summary.json
输出：
  - sources/phase4_glyphs/normalized_glyphs.json
  - sources/phase4_glyphs/normalization_summary.json

标准化步骤：
  1. UPM 缩放（1024 为目标）
  2. round(6) 精度统一
  3. contour 起点统一（min x+y）
  4. contour 排序（bbox 面积降序 + min x+y 升序）
  5. winding direction 统一（CW）
  6. glyphHash 生成（sha256）
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from copy import deepcopy
import numpy as np


def load_glyphs():
    with open('sources/phase3_glyphs/raw_glyphs.json', encoding='utf-8') as f:
        return json.load(f)


def load_extraction_summary():
    with open('sources/phase3_glyphs/extraction_summary.json', encoding='utf-8') as f:
        return json.load(f)


def build_upm_lookup(summary):
    """从 extraction_summary 构建 assetId -> unitsPerEm 映射"""
    upm_map = {}
    for asset in summary['asset_summaries']:
        upm_map[asset['assetId']] = asset.get('unitsPerEm', 1024)
    return upm_map


def scale_contours(contours, advance_width, lsb, scale):
    """UPM 缩放：使用 numpy 批量处理所有坐标"""
    if not contours:
        return contours, advance_width * scale, lsb * scale

    # 展平所有点
    all_points = []
    contour_lengths = []
    for c in contours:
        contour_lengths.append(len(c))
        all_points.extend([(p['x'], p['y'], p['on_curve']) for p in c])

    # numpy 批量缩放
    arr = np.array(all_points, dtype=np.float64)
    arr[:, 0] *= scale
    arr[:, 1] *= scale

    # 重新构建 contours
    new_contours = []
    idx = 0
    for length in contour_lengths:
        new_contour = []
        for j in range(length):
            new_contour.append({
                'x': float(arr[idx + j, 0]),
                'y': float(arr[idx + j, 1]),
                'on_curve': bool(arr[idx + j, 2]),
            })
        new_contours.append(new_contour)
        idx += length

    return new_contours, advance_width * scale, lsb * scale


def round_contours(contours, advance_width, lsb, decimals=6):
    """坐标精度统一到指定小数位，使用 numpy 批量处理"""
    if not contours:
        return contours, round(advance_width, decimals), round(lsb, decimals)

    # 展平所有点
    all_points = []
    contour_lengths = []
    for c in contours:
        contour_lengths.append(len(c))
        all_points.extend([(p['x'], p['y'], p['on_curve']) for p in c])

    # numpy 批量 round
    arr = np.array(all_points, dtype=np.float64)
    arr[:, 0] = np.round(arr[:, 0], decimals)
    arr[:, 1] = np.round(arr[:, 1], decimals)

    # 重新构建 contours
    new_contours = []
    idx = 0
    for length in contour_lengths:
        new_contour = []
        for j in range(length):
            new_contour.append({
                'x': float(arr[idx + j, 0]),
                'y': float(arr[idx + j, 1]),
                'on_curve': bool(arr[idx + j, 2]),
            })
        new_contours.append(new_contour)
        idx += length

    return new_contours, round(advance_width, decimals), round(lsb, decimals)


def normalize_contour_start(contour):
    """将 contour 旋转到 min(x+y) 点作为起点，保证确定性"""
    if not contour:
        return contour

    min_idx = 0
    min_sum = contour[0]['x'] + contour[0]['y']
    for i, p in enumerate(contour[1:], 1):
        s = p['x'] + p['y']
        if s < min_sum:
            min_sum = s
            min_idx = i

    return contour[min_idx:] + contour[:min_idx]


def contour_bbox(contour):
    """计算 contour 的 bbox"""
    xs = [p['x'] for p in contour]
    ys = [p['y'] for p in contour]
    return min(xs), min(ys), max(xs), max(ys)


def contour_area(contour):
    """计算 contour 的 bbox 面积（用于排序）"""
    x0, y0, x1, y1 = contour_bbox(contour)
    return (x1 - x0) * (y1 - y0)


def sort_contours(contours):
    """按 bbox 面积降序排序，面积相同按 min(x+y) 升序排序"""
    def sort_key(c):
        area = contour_area(c)
        min_xy = min(p['x'] + p['y'] for p in c)
        return (-area, min_xy)
    return sorted(contours, key=sort_key)


def signed_area(contour):
    """计算 contour 的 signed area（shoelace formula）"""
    area = 0.0
    n = len(contour)
    for i in range(n):
        j = (i + 1) % n
        area += contour[i]['x'] * contour[j]['y']
        area -= contour[j]['x'] * contour[i]['y']
    return area / 2.0


def ensure_cw(contour):
    """确保 contour 是顺时针方向（CW）"""
    if len(contour) < 3:
        return contour
    area = signed_area(contour)
    # signed area < 0 = CW, > 0 = CCW
    if area > 0:
        return list(reversed(contour))
    return contour


def compute_glyph_hash(contours):
    """
    SHA-256 hash of canonical contours。
    contours 已经是标准化的（起点统一、排序、CW），
    序列化时 sort_keys 保证确定性。
    """
    data = json.dumps(contours, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]


def normalize_glyph(glyph, upm_map):
    """对单个 glyph 应用完整标准化（Step 1-5 + glyphHash）"""
    result = deepcopy(glyph)
    asset_id = glyph['assetId']
    source_upm = upm_map.get(asset_id, 1024)

    if glyph['glyphType'] == 'empty':
        result['glyphHash'] = 'empty'
        result['upmChanged'] = False
        return result

    # Step 1: UPM 缩放
    if source_upm != 1024:
        scale = 1024 / source_upm
        scaled_contours, scaled_aw, scaled_lsb = \
            scale_contours(glyph['contours'], glyph['advanceWidth'], glyph['lsb'], scale)
        result['contours'] = scaled_contours
        result['advanceWidth'] = scaled_aw
        result['lsb'] = scaled_lsb
        result['upmChanged'] = True
        result['sourceUpm'] = source_upm
    else:
        result['upmChanged'] = False

    # Step 2: round(6)
    result['contours'], result['advanceWidth'], result['lsb'] = \
        round_contours(result['contours'], result['advanceWidth'], result['lsb'])

    # Step 3: 每个 contour 起点统一
    result['contours'] = [normalize_contour_start(c) for c in result['contours']]

    # Step 4: contour 排序
    result['contours'] = sort_contours(result['contours'])

    # Step 5: winding direction 统一（CW）
    result['contours'] = [ensure_cw(c) for c in result['contours']]

    # Step 6: glyphHash
    result['glyphHash'] = compute_glyph_hash(result['contours'])

    return result
