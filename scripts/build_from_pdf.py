import sys, json, datetime
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from parse_pdf import parse
from lessons import build_day

raw = parse(sys.argv[1])
out = {}
for g, days in raw.items():
    out[g] = {}
    for d, info in days.items():
        rows = {int(k): v for k, v in info['rows'].items()}
        out[g][d] = build_day(rows, info['start'])
json.dump({'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'source': 'pdf', 'groups': out},
          open(sys.argv[2], 'w'), ensure_ascii=False, separators=(',', ':'))
print('groups', len(out))
