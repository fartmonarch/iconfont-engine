"""
Phase 4: Geometry Normalization（几何标准化）

技术：Python + 标准库（无 numpy）
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
    """UPM 缩放：所有坐标和 metrics 乘以 scale"""
    new_contours = []
    for contour in contours:
        new_contour = []
        for point in contour:
            new_contour.append({
                'x': point['x'] * scale,
                'y': point['y'] * scale,
                'on_curve': point['on_curve'],
            })
        new_contours.append(new_contour)
    return new_contours, advance_width * scale, lsb * scale


def round_contours(contours, advance_width, lsb, decimals=6):
    """坐标精度统一到 6 位小数"""
    new_contours = []
    for contour in contours:
        new_contour = []
        for point in contour:
            new_contour.append({
                'x': round(point['x'], decimals),
                'y': round(point['y'], decimals),
                'on_curve': point['on_curve'],
            })
        new_contours.append(new_contour)
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
