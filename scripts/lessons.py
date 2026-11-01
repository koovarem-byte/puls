"""Превращает строки таблицы (по группе и дню) в список пар."""
import re

NOTE = re.compile(r'^\d+\s*(пар[аы]?|ч\.?|час(а|ов)?)$', re.I)
ROOMS = {
    'бол': 'больница', 'д.бол': 'детская больница', 'дет.б.': 'детская больница', 'дет.б': 'детская больница',
    'дет. б.': 'детская больница', 'дет.бол': 'детская больница', 'акт.з': 'актовый зал', 'акт.з.': 'актовый зал',
    'актз': 'актовый зал', 'чит.з': 'читальный зал', 'чит.з.': 'читальный зал', 'онк': 'онкодиспансер',
    'инф.б.': 'инфекционная больница', 'инф.б': 'инфекционная больница', 'дет. п.': 'детская поликлиника',
    'дет.п.': 'детская поликлиника', 'дет. пол': 'детская поликлиника', 'дет.пол': 'детская поликлиника',
}
TIME = re.compile(r'^\d{1,2}[.:]\d{2}$')
TEACH = re.compile(r'^[А-ЯЁ]{1,4}-?$')


def clean(s):
    return re.sub(r'\s+', ' ', (s or '').strip())


def split_teacher(s):
    """'БОД 31' -> ('БОД','31'), 'С ИВ 11' -> ('СИВ','11'), 'ОСП бол' -> ('ОСП','бол')."""
    toks = clean(s).split(' ')
    t = []
    while toks and toks[0] and TEACH.match(toks[0]):
        t.append(toks.pop(0).rstrip('-'))
    t = ''.join(t) if len(''.join(t)) <= 4 else ' '.join(t)
    return t, ' '.join(toks).strip()


def room_label(r):
    r = clean(r)
    if not r or r.lower() == 'нет' or re.match(r'^[А-ЯЁ][а-яё]{4,}', r):
        return ''
    return ROOMS.get(r.lower(), r)


def parse_subject(s):
    s = clean(s)
    out = {}
    # прилипший преподаватель: 'ПропедевтикаХАВ'
    m = re.match(r'^(.*[а-яё.)])([А-ЯЁ]{3})$', s)
    if m:
        s, out['t'] = m.group(1), m.group(2)
    m = re.match(r'^(\d)\s*[-=]\s*(.*)$', s)
    if m:
        out['g'] = m.group(1)
        s = m.group(2).strip()
    if s.endswith('+'):
        out['last'] = 1
        s = s.rstrip('+').strip()
    m = re.match(r'^(.*\D)\s(\d{1,3}[а-я]?)$', s)
    if m and len(m.group(1)) > 3:
        s, out['r'] = m.group(1).strip(), m.group(2)
    out['s'] = s
    return out


def build_day(rows, start, max_pairs=6):
    """rows: {offset: [subject, teacher, room]} offsets from header row (header = 0)."""
    lessons = []
    rv = any('разговор' in (rows.get(o, ['', '', ''])[0] or '').lower() for o in range(1, start))
    if rv:
        lessons.append({'a': 0, 's': 'Разговоры о важном'})
    last = None
    for p in range(1, max_pairs + 1):
        for half in (0, 1):
            o = start + 2 * (p - 1) + half
            subj, tch, room = [clean(x) for x in (rows.get(o) or ['', '', ''])]
            if not (subj or tch or room):
                continue
            if subj and (NOTE.match(subj) or TIME.match(subj)):
                if last is not None:
                    last['note'] = ('в ' + subj.replace('.', ':')) if TIME.match(subj) else subj
                continue
            if subj.lower() in ('нет', '-', '—'):
                continue
            t, r2 = split_teacher(tch)
            r = room or r2
            if subj:
                info = parse_subject(subj)
                if not info['s']:
                    continue  # '1-' без предмета
                L = {'a': p, 's': info['s']}
                if info.get('g'):
                    L['g'] = info['g']
                if info.get('last'):
                    L['last'] = 1
                tt = t or info.get('t', '')
                if tt:
                    L['t'] = tt
                rr = room_label(r or info.get('r', ''))
                if rr:
                    L['r'] = rr
                lessons.append(L)
                last = L
            elif last is not None and last['a'] == p:
                # строка без предмета: доп. преподаватель / кабинет к текущей паре
                if t:
                    last['t'] = (last.get('t', '') + ', ' + t).strip(', ') if t not in last.get('t', '') else last['t']
                if r and not last.get('r'):
                    last['r'] = room_label(r)
    return lessons
