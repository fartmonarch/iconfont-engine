"""Phase 4 Geometry Normalization 的单元测试"""
import sys
import os
import importlib.util

# 加载 04_normalize_glyphs.py（文件名以数字开头，不能直接作为模块导入）
_pipeline_dir = os.path.dirname(os.path.abspath(__file__))
_module_path = os.path.join(_pipeline_dir, '04_normalize_glyphs.py')
_spec = importlib.util.spec_from_file_location('normalize_glyphs', _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

scale_contours = _mod.scale_contours
round_contours = _mod.round_contours
normalize_glyph = _mod.normalize_glyph
build_upm_lookup = _mod.build_upm_lookup
load_glyphs = _mod.load_glyphs
load_extraction_summary = _mod.load_extraction_summary


def test_scale_contours():
    """UPM 缩放：坐标和 metrics 乘以 scale"""
    contours = [[
        {"x": 512.0, "y": 256.0, "on_curve": True},
        {"x": 0.0, "y": 0.0, "on_curve": True},
    ]]
    new_contours, new_aw, new_lsb = scale_contours(contours, 560.0, 0.0, 1024 / 560)
    # 512 * 1024/560 = 936.228571...
    assert abs(new_contours[0][0]["x"] - 512.0 * 1024 / 560) < 0.0001
    assert abs(new_contours[0][0]["y"] - 256.0 * 1024 / 560) < 0.0001
    assert abs(new_aw - 560.0 * 1024 / 560) < 0.0001
    assert abs(new_lsb - 0.0 * 1024 / 560) < 0.0001


def test_scale_contours_preserves_on_curve():
    """UPM 缩放不改变 on_curve 属性"""
    contours = [[
        {"x": 100.0, "y": 100.0, "on_curve": False},
    ]]
    new_contours, _, _ = scale_contours(contours, 1024, 0, 1.0)
    assert new_contours[0][0]["on_curve"] is False


def test_round_contours():
    """round(6) 精度统一"""
    contours = [[
        {"x": 936.2285714285714, "y": 468.1142857142857, "on_curve": True},
    ]]
    new_contours, new_aw, new_lsb = round_contours(contours, 1024.123456789, 0.987654321)
    assert new_contours[0][0]["x"] == round(936.2285714285714, 6)
    assert new_contours[0][0]["y"] == round(468.1142857142857, 6)
    assert new_aw == round(1024.123456789, 6)


def test_normalize_glyph_upm560():
    """UPM=560 的 glyph 应该被缩放"""
    glyph = {
        "assetId": "1311a7f5b183",  # UPM=560
        "glyphType": "simple",
        "contours": [[
            {"x": 512.0, "y": 256.0, "on_curve": True},
        ]],
        "advanceWidth": 560.0,
        "lsb": 0.0,
    }
    upm_map = {"1311a7f5b183": 560}
    result = normalize_glyph(glyph, upm_map)
    assert result["upmChanged"] is True
    assert result["sourceUpm"] == 560
    assert abs(result["advanceWidth"] - 1024.0) < 0.01


def test_normalize_glyph_upm1024():
    """UPM=1024 的 glyph 不需要缩放"""
    glyph = {
        "assetId": "d737f632f4df",  # UPM=1024
        "glyphType": "simple",
        "contours": [[
            {"x": 512.0, "y": 256.0, "on_curve": True},
        ]],
        "advanceWidth": 1024.0,
        "lsb": 0.0,
    }
    upm_map = {"d737f632f4df": 1024}
    result = normalize_glyph(glyph, upm_map)
    assert result["upmChanged"] is False


def test_normalize_glyph_empty():
    """empty glyph 不做任何处理"""
    glyph = {
        "assetId": "d443fdd5cccb",
        "glyphType": "empty",
        "contours": [],
        "advanceWidth": 1024.0,
        "lsb": 0.0,
    }
    upm_map = {"d443fdd5cccb": 1024}
    result = normalize_glyph(glyph, upm_map)
    assert result["upmChanged"] is False
    assert result["contours"] == []


def test_build_upm_lookup():
    """从 extraction_summary 构建 UPM 映射"""
    summary = {
        "asset_summaries": [
            {"assetId": "aaa", "unitsPerEm": 560},
            {"assetId": "bbb"},  # 没有 unitsPerEm，默认 1024
        ]
    }
    upm_map = build_upm_lookup(summary)
    assert upm_map["aaa"] == 560
    assert upm_map["bbb"] == 1024
