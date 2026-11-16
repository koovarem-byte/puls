"""Проверка разбора на сохранённой таблице: python3 tests/check_parse.py
Каждый случай — день, который раньше разбирался неправильно и был исправлен вручную по таблице."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
from parse_xlsx import parse

got = parse(os.path.join(HERE, 'fixture_2026-11-12.xlsx'))
exp = json.load(open(os.path.join(HERE, 'expected.json')))
bad = 0
for key, want in exp.items():
    g, d = key.split('|')
    have = [[l['a'], l.get('b'), l.get('g'), l['s'], l.get('start')] for l in got.get(g, {}).get(d, [])]
    # опечатки правит update.py (fix_typos), здесь сравниваем без неё — по номерам пар и подгруппам
    norm = lambda xs: [(x[0], x[1], x[2], x[4]) for x in xs]
    if norm(have) != norm(want):
        bad += 1
        print('ОШИБКА', key, '\n  ждали ', want, '\n  вышло ', have)
print(f'проверено {len(exp)}, ошибок {bad}')
if bad:
    sys.exit(1)

# формат дат «Среда\n18 ноября» и дата строкой выше групп (с 15.11): все дни недели на месте
import parse_xlsx
parse_xlsx.WARN.clear()
got2 = parse(os.path.join(HERE, 'fixture_2026-11-15.xlsx'))
miss = [d for d in ['2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20', '2026-11-21']
        if sum(d in v for v in got2.values()) != 23]
print('даты 16–21.11:', 'ок' if not miss else f'ОШИБКА, нет {miss}', '| предупреждений:', len(parse_xlsx.WARN))
if miss or parse_xlsx.WARN:
    sys.exit(1)

# названия: склейка «ЭКЗАМЕН / по / АНАТОМИИ», капс, «ПМ0;4», время в названии
def names(got, g, d):
    return [(l['a'], l['s'], l.get('note')) for l in got.get(g, {}).get(d, [])]
checks = [
    (got, '211', '2026-11-06', lambda x: x[0][1] == 'Экзамен по анатомии'),
    (got, '305В', '2026-10-22', lambda x: x[0][1] == 'Зачет по хирургии'),
    (got, '205А', '2026-10-21', lambda x: all(';' not in s for _, s, _ in x)),
    (got2, '205А', '2026-11-18', lambda x: x[-1][1] == 'ПМ04' and (x[-1][2] or '').startswith('с 14:30')),
]
nbad = sum(1 for G, g, d, ok in checks if not ok(names(G, g, d)) and not print('ОШИБКА названия', g, d, names(G, g, d)))
print('названия:', 'ок' if not nbad else f'ошибок {nbad}')
if nbad:
    sys.exit(1)
