# Re-export functions from 04_normalize_glyphs.py for clean test imports
import importlib
_mod = importlib.import_module('pipeline.04_normalize_glyphs')

scale_contours = _mod.scale_contours
round_contours = _mod.round_contours
normalize_glyph = _mod.normalize_glyph
build_upm_lookup = _mod.build_upm_lookup
load_glyphs = _mod.load_glyphs
load_extraction_summary = _mod.load_extraction_summary
