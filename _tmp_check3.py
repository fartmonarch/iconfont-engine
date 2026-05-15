import json
cr = json.load(open('report/conflict_records.json'))
type_a = [r for r in cr['records'] if r['type'] == 'unicode_conflict']
print('Type A conflicts:', len(type_a))
for r in type_a[:20]:
    print(f"  {r['key']}: {r['variantCount']} variants")
