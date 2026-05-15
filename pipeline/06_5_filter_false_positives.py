#!/usr/bin/env python3
"""Phase 6.5: Filter False Positive Conflicts

Reads conflict_records.json + normalized_glyphs.json, computes geometric
similarity between conflict variants, and marks high-similarity pairs as
false positives.

Usage:
    python pipeline/06_5_filter_false_positives.py

Input:
    report/conflict_records.json
    sources/phase4_glyphs/normalized_glyphs.json

Output:
    report/filtered_conflicts.json
"""
import json
import os
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICT_PATH = os.path.join(DATA_DIR, 'report', 'conflict_records.json')
GLYPHS_PATH = os.path.join(
    DATA_DIR, 'sources', 'phase4_glyphs', 'normalized_glyphs.json')
VISUAL_SIM_PATH = os.path.join(
    DATA_DIR, 'report', 'visual_similarity_scores.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'report', 'filtered_conflicts.json')

# Visual similarity is primary; geometric as fallback
VISUAL_SIMILARITY_THRESHOLD = 0.90
GEOMETRIC_SIMILARITY_THRESHOLD = 0.9
BBOX_DIFF_THRESHOLD = 0.05
MAX_COORD_DIFF_THRESHOLD = 2.0


def load_normalized_glyphs():
    """Build lookup: (glyphHash, assetId) -> contours and metrics."""
    lookup = {}
    with open(GLYPHS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for entry in data:
        key = (entry.get('glyphHash', ''), entry.get('assetId', ''))
        lookup[key] = entry
    return lookup


def compute_bbox(contours):
    """Compute bounding box for contours."""
    if not contours:
        return (0, 0, 0, 0)
    all_x = []
    all_y = []
    for contour in contours:
        for pt in contour:
            all_x.append(pt['x'])
            all_y.append(pt['y'])
    if not all_x:
        return (0, 0, 0, 0)
    return (min(all_x), min(all_y), max(all_x), max(all_y))


def bbox_area(bbox):
    """Compute area of bounding box."""
    x1, y1, x2, y2 = bbox
    return max(0, (x2 - x1) * (y2 - y1))


def count_points(contours):
    """Count total points in contours."""
    return sum(len(c) for c in contours)


def compute_contour_similarity(entry_a, entry_b):
    """Compute geometric similarity between two glyph entries (0.0 - 1.0)."""
    contours_a = entry_a.get('contours', [])
    contours_b = entry_b.get('contours', [])

    # 1. Compare contour count
    if len(contours_a) != len(contours_b):
        return 0.0

    # 2. Compare point count
    points_a = count_points(contours_a)
    points_b = count_points(contours_b)
    if points_a != points_b:
        return 0.0

    # 3. Compare bbox area
    bbox_a = compute_bbox(contours_a)
    bbox_b = compute_bbox(contours_b)
    area_a = bbox_area(bbox_a)
    area_b = bbox_area(bbox_b)
    if max(area_a, area_b) > 0:
        bbox_diff = abs(area_a - area_b) / max(area_a, area_b)
        if bbox_diff > BBOX_DIFF_THRESHOLD:
            return 0.0
    elif area_a != area_b:
        return 0.0

    # 4. Per-point coordinate comparison
    max_diff = 0.0
    total_diff = 0.0
    total_points = 0

    for ca, cb in zip(contours_a, contours_b):
        if len(ca) != len(cb):
            return 0.0
        for pa, pb in zip(ca, cb):
            dx = abs(pa['x'] - pb['x'])
            dy = abs(pa['y'] - pb['y'])
            diff = max(dx, dy)
            max_diff = max(max_diff, diff)
            total_diff += diff
            total_points += 1

    if total_points == 0:
        return 1.0 if not contours_a and not contours_b else 0.0

    avg_diff = total_diff / total_points

    # If max coordinate diff is very small, highly similar
    if max_diff < MAX_COORD_DIFF_THRESHOLD:
        return 0.95

    # Weighted similarity based on average diff
    # diff=0 -> 1.0, diff=10 -> ~0.5, diff>=20 -> 0.0
    similarity = max(0.0, 1.0 - avg_diff / 20.0)
    return similarity


def filter_false_positives():
    print("=" * 51)
    print("Phase 6.5: Filter False Positive Conflicts")
    print("=" * 51)
    print()

    # Load data
    print("Loading conflict records...")
    with open(CONFLICT_PATH, 'r', encoding='utf-8') as f:
        conflicts = json.load(f)

    print("Loading normalized glyphs...")
    glyph_lookup = load_normalized_glyphs()
    print(f"  Glyph lookup entries: {len(glyph_lookup)}")

    # Load visual similarity scores (primary metric)
    visual_scores = {}
    if os.path.exists(VISUAL_SIM_PATH):
        print("Loading visual similarity scores...")
        with open(VISUAL_SIM_PATH, 'r', encoding='utf-8') as f:
            visual_scores = json.load(f)
        print(f"  Visual scores: {len(visual_scores)} conflicts")
    print()

    records = conflicts.get('records', [])
    total_conflicts = len(records)
    filtered_records = []
    false_positive_count = 0

    print(f"Processing {total_conflicts} conflict records...")
    for i, record in enumerate(records):
        record_type = record.get('type', '')

        # Only filter Type A (unicode_conflict) and Type B (name_conflict)
        if record_type not in ('unicode_conflict', 'name_conflict'):
            filtered_records.append(record)
            continue

        variants = record.get('variants', [])
        if len(variants) < 2:
            filtered_records.append(record)
            continue

        key = record.get('key', '')
        visual_score = 0.0
        has_visual = False

        # Primary: use visual similarity if available
        # Use minScore: ALL pairs must be similar to mark as false positive
        visual_min_score = 0.0
        visual_avg_score = 0.0
        has_visual = False
        if key in visual_scores:
            visual_min_score = visual_scores[key].get('minScore', 0)
            visual_avg_score = visual_scores[key].get('avgScore', 0)
            has_visual = True

        # Fallback: geometric similarity (also use min across all pairs)
        min_geo_similarity = 1.0
        has_geo = False
        if not has_visual or visual_min_score < VISUAL_SIMILARITY_THRESHOLD:
            geo_scores = []
            for j in range(len(variants)):
                for k in range(j + 1, len(variants)):
                    v_a = variants[j]
                    v_b = variants[k]

                    key_a = None
                    key_b = None
                    for src in v_a.get('sources', []):
                        key_lookup = (v_a.get('glyphHash', ''),
                                      src.get('assetId', ''))
                        if key_lookup in glyph_lookup:
                            key_a = key_lookup
                            break
                    for src in v_b.get('sources', []):
                        key_lookup = (v_b.get('glyphHash', ''),
                                      src.get('assetId', ''))
                        if key_lookup in glyph_lookup:
                            key_b = key_lookup
                            break

                    if key_a and key_b:
                        entry_a = glyph_lookup[key_a]
                        entry_b = glyph_lookup[key_b]
                        sim = compute_contour_similarity(entry_a, entry_b)
                        geo_scores.append(sim)
            if geo_scores:
                min_geo_similarity = min(geo_scores)
                has_geo = True

        # Determine false positive: ALL pairs must meet threshold
        if has_visual and visual_min_score >= VISUAL_SIMILARITY_THRESHOLD:
            false_positive_count += 1
            record['isFalsePositive'] = True
            record['similarityScore'] = round(visual_min_score, 4)
            record['similarityType'] = 'visual'
            record['recommendation'] = 'merge_as_same_glyph'
        elif has_geo and min_geo_similarity >= GEOMETRIC_SIMILARITY_THRESHOLD:
            false_positive_count += 1
            record['isFalsePositive'] = True
            record['similarityScore'] = round(min_geo_similarity, 4)
            record['similarityType'] = 'geometric'
            record['recommendation'] = 'merge_as_same_glyph'
        else:
            record['isFalsePositive'] = False
            record['similarityScore'] = round(
                visual_min_score if has_visual else (min_geo_similarity if has_geo else 0.0), 4)
            record['similarityType'] = 'visual' if has_visual else (
                'geometric' if has_geo else 'none')

        filtered_records.append(record)

        if (i + 1) % 200 == 0:
            print(f"  Processed {i + 1}/{total_conflicts}...")

    print()
    print(
        f"False positives detected: {false_positive_count}/{total_conflicts}")
    print()

    # Build output
    output = {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'totalConflicts': total_conflicts,
            'falsePositives': false_positive_count,
            'visualSimilarityThreshold': VISUAL_SIMILARITY_THRESHOLD,
            'geometricSimilarityThreshold': GEOMETRIC_SIMILARITY_THRESHOLD,
            'visualScoresUsed': len(visual_scores),
        },
        'records': filtered_records,
    }

    print(f"Writing output: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Phase 6.5 complete!")
    return 0


if __name__ == '__main__':
    sys.exit(filter_false_positives())
