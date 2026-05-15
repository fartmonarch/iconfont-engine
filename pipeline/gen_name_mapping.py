#!/usr/bin/env python3
"""Generate name resolution mapping table after Type B resolution."""
import json
import os

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(
    DATA_DIR, 'registry', 'glyph_registry_resolved.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'report', 'name_resolution_mapping.md')

with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
    registry = json.load(f)

mapping = []
for entry in registry:
    name = entry.get('canonicalName', '')
    unicode_hex = entry.get('canonicalUnicodeHex', '') or ''
    sources = entry.get('sources', [])
    mapping.append({
        'name': name,
        'unicode': unicode_hex,
        'sourceCount': len(sources),
    })

# Sort by unicode, None/empty last
mapping.sort(key=lambda x: (x['unicode'] == '', x['unicode']))

lines = []
lines.append('# Type B 解决后溯源映射表')
lines.append('')
lines.append(f'总条目: {len(mapping)}')
lines.append('')
lines.append('| 名称 | Unicode | 来源数 |')
lines.append('|------|---------|--------|')
for m in mapping[:100]:
    lines.append(f"| {m['name']} | {m['unicode']} | {m['sourceCount']} |")

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f'映射表已生成: {OUTPUT_PATH}')
print(f'总条目: {len(mapping)}')
pua = sum(1 for m in mapping if m['unicode'].startswith(
    'E') and len(m['unicode']) == 4)
print(f'PUA分配: {pua}')
