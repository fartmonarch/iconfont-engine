#!/usr/bin/env python3
"""Task 4: Enhance Lineage with Usage Data + Replacement Info

Merges lineage.json + icon_usage_index.json + phase7_resolution.json
into a comprehensive traceability chain.

Usage:
    python pipeline/13_enhance_lineage.py

Input:
    registry/lineage.json
    report/icon_usage_index.json
    report/phase7_resolution.json

Output:
    registry/lineage_resolved.json
"""
import json
import os
import sys
from datetime import datetime, timezone

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINEAGE_PATH = os.path.join(DATA_DIR, 'registry', 'lineage.json')
USAGE_PATH = os.path.join(DATA_DIR, 'report', 'icon_usage_index.json')
RESOLUTION_PATH = os.path.join(DATA_DIR, 'report', 'phase7_resolution.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'registry', 'lineage_resolved.json')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print('=' * 51)
    print('Task 4: Enhance Lineage with Usage + Replacement')
    print('=' * 51)
    print()

    # Load inputs
    print('Loading lineage...')
    lineage = load_json(LINEAGE_PATH)
    lineage_map = {entry['glyphHash']: entry for entry in lineage}
    print(f'  Entries: {len(lineage)}')

    print('Loading icon usage index...')
    usage_data = load_json(USAGE_PATH)
    print(f'  Projects: {len(usage_data.get("projects", {}))}')

    print('Loading phase7 resolution...')
    resolution = load_json(RESOLUTION_PATH)
    resolution_map = {g['glyphHash']: g for g in resolution['glyphs']}
    print(f'  Resolved glyphs: {len(resolution_map)}')
    print()

    # Build usage lookup: project -> iconName -> [usages]
    usage_lookup = {}
    for project_name, project_data in usage_data.get('projects', {}).items():
        usage_lookup[project_name] = {}
        for icon_entry in project_data.get('iconUsages', []):
            usage_lookup[project_name][icon_entry['iconName']
                                       ] = icon_entry.get('usages', [])

    # Build CSS link lookup: project -> [cssLink entries]
    css_link_lookup = {}
    for project_name, project_data in usage_data.get('projects', {}).items():
        css_link_lookup[project_name] = project_data.get('cssLinks', [])

    enhanced = []
    for entry in lineage:
        glyph_hash = entry['glyphHash']
        res = resolution_map.get(glyph_hash, {})

        # Build usages per project
        usages = {}
        for source in entry.get('sources', []):
            for project in source.get('projects', []):
                if project not in usage_lookup:
                    continue
                icon_name = entry.get('canonicalName', '')
                project_usages = usage_lookup[project].get(icon_name, [])
                if project not in usages:
                    usages[project] = {
                        'cssLinkFiles': css_link_lookup.get(project, []),
                        'iconUsageFiles': [],
                    }
                for u in project_usages:
                    usages[project]['iconUsageFiles'].append({
                        'file': u['file'],
                        'line': u['line'],
                        'iconName': u['iconName'],
                        'canAutoReplace': u['canAutoReplace'],
                        'usageType': u['usageType'],
                    })

        # Build replacement info
        replacement = None
        if res:
            old_names = [entry.get('canonicalName', '')]
            old_names.extend(entry.get('aliases', []))
            old_names = list(set(n for n in old_names if n))

            replacement = {
                'newUnicode': res.get('finalUnicodeHex', ''),
                'newName': res.get('finalName', ''),
                'nameChanged': res.get('finalName', '') != entry.get('canonicalName', ''),
                'unicodeChanged': res.get('finalUnicodeHex', '') != entry.get('canonicalUnicodeHex', ''),
                'oldNames': old_names,
                'autoReplaceReady': True,
                'manualCheckRequired': [],
            }

            # Check for dynamic usages
            for project, proj_usages in usages.items():
                for u in proj_usages['iconUsageFiles']:
                    if not u['canAutoReplace']:
                        replacement['manualCheckRequired'].append(
                            f"{project}/{u['file']} 第{u['line']}行: 动态拼接无法自动替换"
                        )

        # Build version history
        version_history = [
            {
                'phase': 'phase4',
                'unicode': entry.get('canonicalUnicodeHex', ''),
                'name': entry.get('canonicalName', ''),
                'glyphHash': 'original',
            }
        ]
        if res and replacement and replacement['unicodeChanged']:
            version_history.append({
                'phase': 'phase7',
                'unicode': res.get('finalUnicodeHex', ''),
                'name': res.get('finalName', ''),
                'changeReason': entry.get('conflictType', 'resolved'),
            })

        enhanced_entry = {
            'glyphHash': glyph_hash,
            'canonicalName': entry.get('canonicalName', ''),
            'aliases': entry.get('aliases', []),
            'sources': entry.get('sources', []),
            'usages': usages,
            'replacement': replacement,
            'versionHistory': version_history,
        }
        enhanced.append(enhanced_entry)

    output = {
        'metadata': {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'totalEntries': len(enhanced),
            'totalProjects': len(usage_data.get('projects', {})),
            'totalUsages': usage_data.get('totalUsages', 0),
            'sources': ['lineage.json', 'icon_usage_index.json', 'phase7_resolution.json'],
        },
        'entries': enhanced,
    }

    print(f'Writing output: {OUTPUT_PATH}')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print('Task 4 complete!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
