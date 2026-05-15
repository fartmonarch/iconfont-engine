#!/usr/bin/env python3
"""Task 6: Rebuild Conflict Resolver Data with Usage + TTF Info

Reads filtered_conflicts.json + lineage_resolved.json + phase7_resolution.json,
generates enhanced conflict_resolver_data.json for the review UI.

Usage:
    python pipeline/15_rebuild_resolver_data.py

Output:
    report/conflict_resolver_data.json
"""
import json
import os
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICTS_PATH = os.path.join(DATA_DIR, 'report', 'filtered_conflicts.json')
LINEAGE_PATH = os.path.join(DATA_DIR, 'registry', 'lineage_resolved.json')
RESOLUTION_PATH = os.path.join(DATA_DIR, 'report', 'phase7_resolution.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'report', 'conflict_resolver_data.json')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print('=' * 51)
    print('Task 6: Rebuild Conflict Resolver Data')
    print('=' * 51)
    print()

    conflicts = load_json(CONFLICTS_PATH)
    lineage_data = load_json(LINEAGE_PATH)
    resolution = load_json(RESOLUTION_PATH)

    lineage_map = {e['glyphHash']: e for e in lineage_data.get('entries', [])}
    resolution_map = {g['glyphHash']: g for g in resolution['glyphs']}

    enhanced_records = []
    for record in conflicts.get('records', []):
        variants = record.get('variants', [])
        enhanced_variants = []

        for v in variants:
            glyph_hash = v['glyphHash']
            lineage_entry = lineage_map.get(glyph_hash, {})
            res_entry = resolution_map.get(glyph_hash, {})

            # Build usage summary per project
            usages = lineage_entry.get('usages', {})
            usage_summary = {}
            for project, proj_data in usages.items():
                static_count = sum(1 for u in proj_data.get(
                    'iconUsageFiles', []) if u['canAutoReplace'])
                dynamic_count = sum(1 for u in proj_data.get(
                    'iconUsageFiles', []) if not u['canAutoReplace'])
                files = [f"{u['file']}:{u['line']}" for u in proj_data.get(
                    'iconUsageFiles', [])]
                usage_summary[project] = {
                    'staticCount': static_count,
                    'dynamicCount': dynamic_count,
                    'files': files[:10],  # Limit to avoid huge JSON
                }

            enhanced_variants.append({
                'glyphHash': glyph_hash,
                'previewUnicode': res_entry.get('finalUnicodeHex', ''),
                'sources': v.get('sources', []),
                'usages': usage_summary,
                'inFinalTTF': bool(res_entry),
                'finalTTFGlyphName': res_entry.get('finalName', ''),
                'similarityScore': record.get('similarityScore'),
            })

        enhanced_records.append({
            'id': record.get('id', len(enhanced_records)),
            'type': record.get('type', ''),
            'severity': record.get('severity', ''),
            'key': record.get('key', ''),
            'variantCount': len(variants),
            'isFalsePositive': record.get('isFalsePositive', False),
            'similarityScore': record.get('similarityScore'),
            'recommendation': record.get('recommendation', ''),
            'resolution_hint': record.get('resolution_hint', ''),
            'variants': enhanced_variants,
            'decision': None,  # To be filled by reviewer
        })

    output = {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'totalRecords': len(enhanced_records),
            'falsePositives': sum(1 for r in enhanced_records if r['isFalsePositive']),
            'sources': ['filtered_conflicts.json', 'lineage_resolved.json', 'phase7_resolution.json'],
        },
        'records': enhanced_records,
    }

    print(f'Enhanced records: {len(enhanced_records)}')
    print(f'False positives included: {output["metadata"]["falsePositives"]}')
    print(f'Writing output: {OUTPUT_PATH}')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print('Task 6 complete!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
