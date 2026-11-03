"""Превращает строки таблицы (по группе и дню) в список пар."""
import re

NOTE = re.compile(r'^(\d+\s*(пар[аы]?|ч\.?|час(а|ов)?)\b.*|[св]\s*\d{1,2}([.:]\d{2})?|\(?\d\s*пара\)?|\d\s*и\s*\d\s*пар[аы]?|\d{1,2}\.\d{1,2}\.\d{4}|[.,]+)$', re.I)
NAME = re.compile(r'^[А-ЯЁ][а-яё]+(\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?|,)$')
ROOMS = {
    'бол': 'больница', 'д.бол': 'детская больница', 'дет.б.': 'детская больница', 'дет.б': 'детская больница',
    'дет. б.': 'детская больница', 'дет.бол': 'детская больница', 'акт.з': 'актовый зал', 'акт.з.': 'актовый зал',
    'актз': 'актовый зал', 'чит.з': 'читальный зал', 'чит.з.': 'читальный зал', 'онк': 'онкодиспансер',
    'инф.б.': 'инфекционная больница', 'инф.б': 'инфекционная больница', 'дет. п.': 'детская поликлиника',
    'дет.п.': 'детская поликлиника', 'д.бол.': 'детская больница', 'д.б.': 'детская больница', 'д.б': 'детская больница',
    'гор.б.': 'городская больница', 'гор.б': 'городская больница', 'акт.зал': 'актовый зал', 'цз': 'центр здоровья',
    'онк.д.': 'онкодиспансер', 'сз': 'спортзал', 'квд': 'КВД', 'дет. пол': 'детская поликлиника', 'дет.пол': 'детская поликлиника',
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


FULL = [
    (r'^(информ|тинфор|инфориац)[а-я]*\.?\s*те', 'Информационные технологии'),
    (r'^экстр(\.|енная)\s*пом', 'Экстренная помощь'),
    (r'^(ин[фф]о[рр]?[а-я]*ц|тинфор|инфориац)[а-я]*\.?\s*тех', 'Информационные технологии'),
    (r'^инфекц[а-я]*\.?\s*бол', 'Инфекционные болезни'),
    (r'^(основы\s*)?фин[а-я]*\.?\s*гр', 'Основы финансовой грамотности'),
    (r'^торж\.?\s*собр', 'Торжественное собрание'),
    (r'^здор[а-я]*\.?\s*чел', 'Здоровый человек'),
    (r'^медици[а-я]*\.?\s*реаб', 'Медицинская реабилитация'),
    (r'^акушерство и гинек\.?$', 'Акушерство и гинекология'),
    (r'^физ-?ра$', 'Физкультура'),
    (r'^англ(ийский)?\.?\s*яз\.?$', 'Английский язык'),
    (r'^русский яз\.?$', 'Русский язык'),
    (r'^основы лат\.?\s*яз\.?$', 'Основы латинского языка'),
]


def nice(s):
    s = clean(s)
    if len(s) > 2 and s[0].isupper() and s[1].isupper() and s[2].islower():
        s = s[0] + s[1].lower() + s[2:]  # КУльтура -> Культура
    if s[:1].islower():
        s = s[0].upper() + s[1:]
    low = s.lower()
    for pat, full in FULL:
        if re.match(pat, low):
            return full
    s = re.sub(r'^(УП|ПП)[\s\-–]+(\w)', lambda m: m.group(1) + ' ' + m.group(2).upper(), s)
    return re.sub(r'\.(?=[А-ЯЁа-яё])', '. ', s)


def parse_subject(s):
    s = clean(s)
    out = {}
    m = re.match(r'^(\d)(?=[А-ЯЁ])', s)
    if m:
        s = m.group(1) + '-' + s[1:]
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
    out['s'] = nice(s) if s else s
    return out


def merge_color_blocks(lessons, start, fills):
    """Практика/занятие одним цветным блоком: 4 строки = 4 ч (2 пары), 6 строк = 6 ч (3 пары).
    Если внутри блока один и тот же предмет — показываем одним блоком на все его пары."""
    out = []
    used = set()
    for i, L in enumerate(lessons):
        if i in used:
            continue
        if L['a'] == 0:
            out.append(L)
            continue
        o = start + 2 * (L['a'] - 1)
        color = fills.get(o)
        if color and fills.get(o - 1) == color:
            color = None  # пара не в начале цветного блока — не объединяем
        run = 0
        while color and fills.get(o + run) == color:
            run += 1
        if run >= 4:
            n = (run + 1) // 2
            last = min(6, L['a'] + n - 1)
            inside = [j for j in range(i, len(lessons)) if L['a'] <= lessons[j]['a'] <= last and lessons[j]['a'] > 0]
            if all(lessons[j]['s'] == L['s'] for j in inside):
                M = {'a': L['a'], 's': L['s']}
                if last > L['a']:
                    M['b'] = last
                ts, gs = [], set()
                for j in inside:
                    x = lessons[j]
                    gs.add(x.get('g'))
                    if x.get('t'):
                        lab = x['t'] + (f" ({x['g']} подгр.)" if x.get('g') and len(inside) > 1 else '')
                        if lab not in ts:
                            ts.append(lab)
                    if x.get('r') and not M.get('r'):
                        M['r'] = x['r']
                    if x.get('last'):
                        M['last'] = 1
                    used.add(j)
                if ts:
                    M['t'] = ', '.join(ts)
                if len(inside) == 1 and L.get('g'):
                    M['g'] = L['g']
                M['note'] = f'{run} ч.'
                out.append(M)
                continue
        out.append(L)
    return out


def note_pairs(note):
    """'3 пары' -> 3, '6 ч.' -> 3 (пара = 2 часа)."""
    m = re.match(r'^(\d+)\s*(пар|ч)', (note or '').lower())
    if not m:
        return None
    n = int(m.group(1))
    return n if m.group(2) == 'пар' else max(1, n // 2)


def merge_subgroups(lessons):
    """«1-ЗОЖ» в одной паре и «2-ЗОЖ» в следующей = вся группа на этом предмете блоком
    (1 подгр. у одного преподавателя, 2 подгр. у другого). Длина блока — из пометки «3 пары» / «6 ч.», иначе 2 пары."""
    out = []
    i = 0
    while i < len(lessons):
        A = lessons[i]
        B = lessons[i + 1] if i + 1 < len(lessons) else None
        if (B and A.get('g') == '1' and B.get('g') == '2' and A['s'] == B['s'] and B['a'] == A['a'] + 1):
            n = note_pairs(B.get('note')) or note_pairs(A.get('note')) or 2
            M = {'a': A['a'], 'b': min(6, A['a'] + n - 1), 's': A['s']}
            t = [f"{x.get('t')} (1 подгр.)" if x is A else f"{x.get('t')} (2 подгр.)" for x in (A, B) if x.get('t')]
            if t:
                M['t'] = ', '.join(t)
            r = A.get('r') or B.get('r')
            if r:
                M['r'] = r
            for k in ('last',):
                if A.get(k) or B.get(k):
                    M[k] = 1
            out.append(M)
            # пропускаем пары, которые перекрыл блок
            i += 2
            while i < len(lessons) and lessons[i]['a'] <= M['b'] and lessons[i]['s'] == M['s']:
                i += 1
            continue
        out.append(A)
        i += 1
    return out


def build_day(rows, start, max_pairs=6, fills=None):
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
            if subj.lower() in ('нет', '-', '—') or NAME.match(subj):
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
    if fills:
        lessons = merge_color_blocks(lessons, start, fills)
    lessons = merge_subgroups(lessons)
    for L in lessons:
        if L['s'].upper() == 'ЗОЖ':
            L['r'] = 'центр здоровья'
            if L['a'] == 1:
                L['start'] = '09:00'
            L['hint'] = 'Время и место уточняйте в чате группы'
    return lessons
