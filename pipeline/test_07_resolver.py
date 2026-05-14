#!/usr/bin/env python3
"""Unit tests for Phase 7: Conflict Resolution."""
import json
import os
import sys
import unittest

# Add pipeline dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util

def _load_module(filename):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    spec = importlib.util.spec_from_file_location(os.path.splitext(filename)[0], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_gen = _load_module('07_generate_resolver_ui.py')
_res = _load_module('07_resolve_conflicts.py')

contour_to_path = _gen.contour_to_path
contours_to_svg = _gen.contours_to_svg
PUAAllocator = _res.PUAAllocator
resolve_type_a = _res.resolve_type_a
resolve_type_b = _res.resolve_type_b
resolve_type_c_auto = _res.resolve_type_c_auto


class TestContourToPath(unittest.TestCase):
    """Test TTF contour → SVG path conversion."""

    def test_empty_contour(self):
        self.assertEqual(contour_to_path([]), '')

    def test_single_on_curve_point(self):
        pts = [{'x': 0, 'y': 0, 'on_curve': True}]
        result = contour_to_path(pts)
        self.assertTrue(result.startswith('M'))
        self.assertTrue(result.endswith('Z'))

    def test_simple_rectangle(self):
        pts = [
            {'x': 0, 'y': 0, 'on_curve': True},
            {'x': 100, 'y': 0, 'on_curve': True},
            {'x': 100, 'y': 100, 'on_curve': True},
            {'x': 0, 'y': 100, 'on_curve': True},
        ]
        result = contour_to_path(pts)
        self.assertIn('M', result)
        self.assertIn('L', result)
        self.assertTrue(result.endswith('Z'))

    def test_quadratic_bezier(self):
        """Off-curve + on-curve → Q command."""
        pts = [
            {'x': 0, 'y': 0, 'on_curve': True},
            {'x': 50, 'y': -100, 'on_curve': False},
            {'x': 100, 'y': 0, 'on_curve': True},
        ]
        result = contour_to_path(pts)
        self.assertIn('Q', result)

    def test_two_consecutive_off_curve(self):
        """Two off-curve points → implied midpoint."""
        pts = [
            {'x': 0, 'y': 0, 'on_curve': True},
            {'x': 30, 'y': -50, 'on_curve': False},
            {'x': 70, 'y': -50, 'on_curve': False},
            {'x': 100, 'y': 0, 'on_curve': True},
        ]
        result = contour_to_path(pts)
        # Should have a Q to the implied midpoint (50, -50)
        self.assertIn('Q', result)
        # Midpoint x = (30+70)/2 = 50
        self.assertIn('50.0', result)

    def test_starts_with_off_curve(self):
        """Contour starting with off-curve should rotate to first on-curve."""
        pts = [
            {'x': 50, 'y': -50, 'on_curve': False},
            {'x': 100, 'y': 0, 'on_curve': True},
            {'x': 50, 'y': 50, 'on_curve': False},
            {'x': 0, 'y': 0, 'on_curve': True},
        ]
        result = contour_to_path(pts)
        # Should start at the first on-curve point (100, 0)
        self.assertTrue(result.startswith('M 100.0'))

    def test_all_off_curve_degenerate(self):
        pts = [
            {'x': 0, 'y': 0, 'on_curve': False},
            {'x': 50, 'y': 50, 'on_curve': False},
        ]
        result = contour_to_path(pts)
        self.assertTrue(result.startswith('M'))
        self.assertTrue(result.endswith('Z'))

    def test_wrap_around_last_off_curve(self):
        """Last point off-curve wraps to first on-curve."""
        pts = [
            {'x': 0, 'y': 0, 'on_curve': True},
            {'x': 50, 'y': 50, 'on_curve': True},
            {'x': 25, 'y': 25, 'on_curve': False},
        ]
        result = contour_to_path(pts)
        # Should end with Q to midpoint between last off-curve and first on-curve
        self.assertIn('Q', result)


class TestContoursToSVG(unittest.TestCase):
    """Test contours → inline SVG generation."""

    def test_no_contours(self):
        self.assertIsNone(contours_to_svg([]))
        self.assertIsNone(contours_to_svg(None))

    def test_returns_svg_string(self):
        contours = [[
            {'x': 0, 'y': 0, 'on_curve': True},
            {'x': 100, 'y': 0, 'on_curve': True},
            {'x': 100, 'y': 100, 'on_curve': True},
            {'x': 0, 'y': 100, 'on_curve': True},
        ]]
        result = contours_to_svg(contours, upm=1024, size=80)
        self.assertIsNotNone(result)
        self.assertIn('<svg', result)
        self.assertIn('viewBox', result)
        self.assertIn('</svg>', result)

    def test_y_axis_flip(self):
        """Y should be flipped: svg_y = upm - font_y."""
        contours = [[
            {'x': 100, 'y': 900, 'on_curve': True},
            {'x': 200, 'y': 800, 'on_curve': True},
        ]]
        result = contours_to_svg(contours, upm=1024, size=80)
        self.assertIsNotNone(result)
        # After flip: svg_y = 1024 - 900 = 124
        self.assertIn('124', result)

    def test_custom_size(self):
        contours = [[
            {'x': 0, 'y': 0, 'on_curve': True},
            {'x': 100, 'y': 100, 'on_curve': True},
        ]]
        result = contours_to_svg(contours, upm=1024, size=64)
        self.assertIn('width="64"', result)
        self.assertIn('height="64"', result)


class TestPUAAllocator(unittest.TestCase):
    """Test sequential PUA code allocation."""

    def test_basic_allocation(self):
        pua = PUAAllocator()
        code1 = pua.allocate('hash1', 'test1')
        code2 = pua.allocate('hash2', 'test2')
        self.assertEqual(code1, 0xE000)
        self.assertEqual(code2, 0xE001)
        self.assertNotEqual(code1, code2)

    def test_no_duplicates(self):
        pua = PUAAllocator()
        codes = [pua.allocate(f'hash{i}', f'test{i}') for i in range(100)]
        self.assertEqual(len(set(codes)), 100)

    def test_custom_range(self):
        pua = PUAAllocator(start=0xF000, end=0xF005)
        c1 = pua.allocate('h1', '')
        c2 = pua.allocate('h2', '')
        self.assertEqual(c1, 0xF000)
        self.assertEqual(c2, 0xF001)

    def test_range_exhausted(self):
        pua = PUAAllocator(start=0xF000, end=0xF000)
        pua.allocate('h1', '')
        with self.assertRaises(RuntimeError):
            pua.allocate('h2', '')

    def test_assigned_count(self):
        pua = PUAAllocator()
        pua.allocate('h1', '')
        pua.allocate('h2', '')
        self.assertEqual(pua.assigned_count, 2)

    def test_range_used(self):
        pua = PUAAllocator()
        pua.allocate('h1', '')
        pua.allocate('h2', '')
        self.assertEqual(pua.range_used, 'U+E000-U+E001')

    def test_log(self):
        pua = PUAAllocator()
        pua.allocate('abc123', 'Type A variant')
        log = pua.log
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['glyphHash'], 'abc123')
        self.assertEqual(log[0]['pua'], 'U+E000')


class TestResolveTypeA(unittest.TestCase):
    """Test Unicode conflict resolution."""

    def _make_record(self, num_variants=2, record_id=0):
        return {
            'id': record_id,
            'type': 'unicode_conflict',
            'severity': 'info',
            'key': f'U+E{record_id:X}',
            'variantCount': num_variants,
            'variants': [
                {
                    'glyphHash': f'hash_{record_id}_{i}',
                    'canonicalName': f'icon-test_{record_id}',
                    'sources': [{'assetId': f'asset_{i}', 'projects': [f'proj_{i}']}],
                }
                for i in range(num_variants)
            ],
        }

    def test_keep_one_variant(self):
        record = self._make_record(3, record_id=0)
        decisions = {
            '0': {'recordType': 'unicode_conflict', 'key': 'U+E0', 'action': 'keep', 'variantIndex': 1, 'keptGlyphHash': 'hash_0_1'},
        }
        pua = PUAAllocator()
        resolved, stats = resolve_type_a([record], decisions, pua)
        self.assertEqual(len(resolved), 3)
        self.assertEqual(stats['kept'], 1)
        self.assertEqual(stats['pua_assigned'], 2)
        # The kept variant should have the original unicode
        kept = [r for r in resolved if r['glyphHash'] == 'hash_0_1'][0]
        self.assertEqual(kept['resolution'], 'kept_original')
        self.assertEqual(kept['finalUnicode'], 0xE0)

    def test_all_pua_no_decision(self):
        record = self._make_record(2, record_id=1)
        pua = PUAAllocator()
        resolved, stats = resolve_type_a([record], {}, pua)
        self.assertEqual(len(resolved), 2)
        self.assertEqual(stats['auto_resolved'], 2)
        # All should have PUA codes
        for r in resolved:
            self.assertTrue(r['finalUnicode'] >= 0xE000)

    def test_pua_action(self):
        record = self._make_record(2, record_id=2)
        decisions = {
            '2': {'recordType': 'unicode_conflict', 'key': 'U+E2', 'action': 'pua', 'variantIndex': 0, 'keptGlyphHash': 'hash_2_0'},
        }
        pua = PUAAllocator()
        resolved, stats = resolve_type_a([record], decisions, pua)
        # PUA action → all variants get PUA (different from keep)
        self.assertEqual(len(resolved), 2)


class TestResolveTypeB(unittest.TestCase):
    """Test Name conflict resolution."""

    def _make_record(self, num_variants=2, record_id=0):
        return {
            'id': record_id,
            'type': 'name_conflict',
            'severity': 'info',
            'key': f'icon-conflict_{record_id}',
            'variantCount': num_variants,
            'variants': [
                {
                    'glyphHash': f'namehash_{record_id}_{i}',
                    'canonicalName': f'icon-conflict_{record_id}',
                    'sources': [{
                        'assetId': f'asset_{i}',
                        'projects': [f'proj_{i}'],
                        'originalUnicode': 0xE600 + i,
                    }],
                }
                for i in range(num_variants)
            ],
        }

    def test_keep_one_variant(self):
        record = self._make_record(3, record_id=5)
        decisions = {
            '5': {'recordType': 'name_conflict', 'key': 'icon-conflict_5', 'action': 'keep', 'variantIndex': 0, 'keptGlyphHash': 'namehash_5_0'},
        }
        pua = PUAAllocator()
        resolved, stats = resolve_type_b([record], decisions, pua)
        self.assertEqual(len(resolved), 3)
        self.assertEqual(stats['kept'], 1)
        kept = [r for r in resolved if r['glyphHash'] == 'namehash_5_0'][0]
        self.assertEqual(kept['finalName'], 'icon-conflict_5')
        self.assertEqual(kept['resolution'], 'kept_original')

    def test_suffix_naming(self):
        record = self._make_record(2, record_id=6)
        pua = PUAAllocator()
        resolved, stats = resolve_type_b([record], {}, pua)
        names = [r['finalName'] for r in resolved]
        self.assertIn('icon-conflict_6_v1', names)
        self.assertIn('icon-conflict_6_v2', names)


class TestResolveTypeC(unittest.TestCase):
    """Test Type C auto-resolution (alias merge)."""

    def test_merge_multi_source_entries(self):
        registry = [
            {
                'glyphHash': 'shared_hash',
                'canonicalUnicode': 0xE700,
                'canonicalUnicodeHex': 'E700',
                'canonicalName': 'icon-shared',
                'aliases': ['alias1'],
                'sources': [
                    {'assetId': 'a1', 'projects': ['proj1']},
                    {'assetId': 'a2', 'projects': ['proj2']},
                ],
            },
            {
                'glyphHash': 'unique_hash',
                'canonicalUnicode': 0xE701,
                'canonicalUnicodeHex': 'E701',
                'canonicalName': 'icon-unique',
                'aliases': [],
                'sources': [{'assetId': 'a3', 'projects': ['proj3']}],
            },
        ]
        resolved, stats = resolve_type_c_auto(registry)
        # Only multi-source entries should be resolved
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]['glyphHash'], 'shared_hash')
        self.assertEqual(resolved[0]['resolution'], 'alias_merged')
        self.assertEqual(stats['merged'], 1)

    def test_no_multi_source(self):
        registry = [
            {
                'glyphHash': 'unique',
                'sources': [{'assetId': 'a1', 'projects': ['p1']}],
            },
        ]
        resolved, stats = resolve_type_c_auto(registry)
        self.assertEqual(len(resolved), 0)
        self.assertEqual(stats['merged'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
