import json

reg = json.load(open('registry/glyph_registry.json'))
typea_data = json.load(open('report/conflict_resolver_typea_data.json'))
decisions = json.load(open('report/phase7_typea_decisions.json'))

# Check U+E6E8 in registry
print('=== Registry U+E6E8 ===')
for e in reg:
    if e.get('canonicalUnicodeHex') == 'E6E8':
        print('  gh=' + e['glyphHash'][:16] +
              '... name=' + e.get('name', 'N/A'))

# Check typea ID 629
print('\n=== TypeA ID 629 ===')
r629 = next((r for r in typea_data['records'] if r['id'] == 629), None)
if r629:
    for i, v in enumerate(r629['variants']):
        entry = next(
            (e for e in reg if e['glyphHash'] == v['glyphHash']), None)
        uc = entry.get('canonicalUnicodeHex') if entry else 'NOT FOUND'
        print('  vi=' + str(i) + ' gh=' +
              v['glyphHash'][:16] + '... registry_uc=' + uc)

# Check remaining Type A conflicts
print('\n=== Current Type A conflicts ===')
conflicts = json.load(open('report/conflict_records.json'))
for r in conflicts['records']:
    if r['type'] == 'unicode_conflict':
        print('  ' + r['key'] + ': ' + str(len(r['variants'])) + ' variants')
        match = next(
            (tr for tr in typea_data['records'] if tr['key'] == r['key']), None)
        if match:
            print('    Found in typea_data id=' + str(match['id']))
        else:
            print('    NOT in typea_data')
