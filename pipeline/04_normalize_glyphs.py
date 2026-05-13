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


def normalize_glyph(glyph, upm_map):
    """对单个 glyph 应用标准化 Step 1-2（UPM 缩放 + round）"""
    result = deepcopy(glyph)
    asset_id = glyph['assetId']
    source_upm = upm_map.get(asset_id, 1024)

    if glyph['glyphType'] == 'empty':
        result['upmChanged'] = False
    elif source_upm != 1024:
        scale = 1024 / source_upm
        # Step 1: UPM 缩放
        scaled_contours, scaled_aw, scaled_lsb = \
            scale_contours(glyph['contours'], glyph['advanceWidth'], glyph['lsb'], scale)
        # Step 2: round(6)
        result['contours'], result['advanceWidth'], result['lsb'] = \
            round_contours(scaled_contours, scaled_aw, scaled_lsb)
        result['upmChanged'] = True
        result['sourceUpm'] = source_upm
        result['scale'] = scale
    else:
        # 已经是 UPM=1024，跳过缩放，只做 round
        result['contours'], result['advanceWidth'], result['lsb'] = \
            round_contours(glyph['contours'], glyph['advanceWidth'], glyph['lsb'])
        result['upmChanged'] = False

    return result
