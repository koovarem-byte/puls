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
sys.exit(1 if bad else 0)
