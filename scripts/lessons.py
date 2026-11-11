"""Превращает строки таблицы (по группе и дню) в список пар."""
import re

NOTE = re.compile(r'^(\d+\s*(пар[аы]?|ч\.?|час(а|ов)?)\b.*|[св]\s*\d{1,2}([.:]\d{2})?|\(?\d\s*пара\)?|\d\s*[,и]\s*\d\s*пар[аы]?|\d{1,2}\.\d{1,2}\.\d{4}|[.,]+)$', re.I)
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
            inside = [j for j in range(i, len(lessons)) if L['a'] <= lessons[j]['a'] <= last and lessons[j]['a'] > 0
                      and o <= lessons[j].get('_o', o) < o + run]  # только строки внутри цветного блока
            if all(lessons[j]['s'] == L['s'] for j in inside):
                M = {'a': L['a'], 's': L['s']}
                if last > L['a']:
                    M['b'] = last
                ts = []
                gs = {lessons[j].get('g') for j in inside}
                one_g = len(gs) == 1 and None not in gs
                for j in inside:
                    x = lessons[j]
                    if x.get('t'):
                        lab = x['t'] + (f" ({x['g']} подгр.)" if x.get('g') and len(inside) > 1 and not one_g else '')
                        if lab not in ts:
                            ts.append(lab)
                    if x.get('r') and not M.get('r'):
                        M['r'] = x['r']
                    if x.get('last'):
                        M['last'] = 1
                    if x.get('start') and not M.get('start'):
                        M['start'] = x['start']
                    used.add(j)
                if ts:
                    M['t'] = ', '.join(ts)
                if one_g:
                    M['g'] = L['g']
                M['note'] = f'{run} ч.'
                out.append(M)
                continue
            if all(lessons[j].get('g') in ('1', '2') for j in inside):
                # «1- ПМ06» и «2- ПМ05» друг под другом в одном цветном блоке = подгруппы занимаются
                # одновременно, каждая весь блок (а не 1 подгр. на 3 паре, 2 подгр. на 4-й)
                # подряд одинаковые записи одной подгруппы считаем одной
                ent, prev = [], {}
                for j in inside:
                    x = lessons[j]
                    used.add(j)
                    if prev.get(x['g']) == x['s']:
                        continue
                    prev[x['g']] = x['s']
                    ent.append(x)
                # куски «1-…, 2-…»: новый кусок, когда подгруппа повторяется (1-Реаб, 2-Тер, 1-Тер, 2-Реаб = смена)
                chunks, cur = [], []
                for x in ent:
                    if any(y['g'] == x['g'] for y in cur):
                        chunks.append(cur); cur = []
                    cur.append(x)
                if cur:
                    chunks.append(cur)
                total = last - L['a'] + 1
                per = max(1, total // len(chunks))
                for ci, ch in enumerate(chunks):
                    a0 = L['a'] + ci * per
                    b0 = last if ci == len(chunks) - 1 else min(last, a0 + per - 1)
                    if a0 > last:
                        a0 = b0 = last
                    for x in ch:
                        M = {k: v for k, v in x.items() if k not in ('a', 'b', 'note')}
                        M['a'] = a0
                        if b0 > a0:
                            M['b'] = b0
                        if PAIRNOTE.match((x.get('note') or '').strip()) or note_pairs(x.get('note')):
                            M['note'] = x['note']  # «2 пара» / «6 ч.» под предметом важнее размера блока
                        elif b0 > a0:
                            M['note'] = f'{run} ч.' if len(chunks) == 1 else f'{2 * (b0 - a0 + 1)} ч.'
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


PAIRNOTE = re.compile(r'^(\d)(?:\s*[,и]\s*(\d))?\s*пара$', re.I)
TAILPAIR = re.compile(r'^(.*\S)\s+(\d(?:\s*[,и]\s*\d)?\s*пара)$', re.I)
BELL_MIN = [(1, 510, 605), (2, 615, 710), (3, 740, 835), (4, 845, 940), (5, 970, 1065), (6, 1075, 1170)]


def pair_of_time(t):
    """'16:15' -> 5 (пара, в которую попадает время, с запасом 10 минут до начала)."""
    h, m = map(int, t.split(':'))
    x = h * 60 + m
    for n, a, b in BELL_MIN:
        if a - 10 <= x < b:
            return n
    return None


def apply_pair_notes(lessons):
    """Пометка «2 пара» / «1, 2 пара» под предметом = явный номер пары."""
    for L in lessons:
        m = PAIRNOTE.match((L.get('note') or '').strip())
        if not m or not L.get('a'):
            continue
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else None
        if not 1 <= a <= 6:
            continue
        L['a'] = a
        if b and b > a:
            L['b'] = min(6, b)
        else:
            L.pop('b', None)
        L.pop('note', None)
    lessons.sort(key=lambda L: (L['a'], L.get('g') or ''))
    return lessons


def realign_blocks(rows, fills, start, max_pairs=6):
    """Цветной блок, начатый с нижней строки пары (составитель сдвинул его на строку вниз),
    поднимаем на строку вверх, если строка над ним пустая и не закрашена."""
    rows, fills = dict(rows), dict(fills)
    end = start + 2 * max_pairs
    o = start
    while o < end:
        c = fills.get(o)
        if not c or fills.get(o - 1) == c:
            o += 1
            continue
        run = 0
        while fills.get(o + run) == c:
            run += 1
        if (o - start) % 2 == 1 and run % 2 == 0 and o - 1 >= start and not fills.get(o - 1) \
                and not any(rows.get(o - 1, [''])) and any(any(rows.get(o + k, [''])) for k in range(run)):
            for k in range(run):
                v = rows.pop(o + k, None)
                if v is not None:
                    rows[o + k - 1] = v
                fills[o + k - 1] = c
            fills.pop(o + run - 1, None)
        o += run
    return rows, fills


def build_day(rows, start, max_pairs=6, fills=None):
    """rows: {offset: [subject, teacher, room]} offsets from header row (header = 0)."""
    if fills:
        rows, fills = realign_blocks(rows, fills, start, max_pairs)
    lessons = []
    rv = any('разговор' in (rows.get(o, ['', '', ''])[0] or '').lower() for o in range(1, start))
    if rv:
        lessons.append({'a': 0, 's': 'Разговоры о важном'})
    last = None
    pending = None
    for p in range(1, max_pairs + 1):
        halves = {}
        for half in (0, 1):
            o = start + 2 * (p - 1) + half
            subj, tch, room = [clean(x) for x in (rows.get(o) or ['', '', ''])]
            if not (subj or tch or room):
                continue
            nxt = clean((rows.get(o + 1) or [''])[0])
            same_block = (fills or {}).get(o) == (fills or {}).get(o + 1)
            if subj and TIME.match(subj) and not tch and not room and nxt and same_block \
                    and not NOTE.match(nxt) and not TIME.match(nxt) and nxt.lower() not in ('нет', '-', '—'):
                pending = subj.replace('.', ':').zfill(5)  # «16.15» над предметом = начало
                continue
            if (subj and half == 1 and not tch and not room and subj[0].islower() and last is not None
                    and last['a'] == p and not NOTE.match(subj) and len(subj.strip('. ')) >= 4
                    and subj.lower().strip('. ') not in ('нет', 'дист', 'дистант')):
                m = TAILPAIR.match(subj)  # «фельдшера 5 пара» = продолжение названия
                last['s'] = last['s'] + ' ' + (m.group(1) if m else subj)
                if m:
                    last['note'] = m.group(2)
                continue
            if subj and (NOTE.match(subj) or TIME.match(subj)):
                if last is not None:
                    last['note'] = ('в ' + subj.replace('.', ':')) if TIME.match(subj) else subj
                continue
            if subj.lower() in ('нет', '-', '—'):
                halves[half] = 'нет'
                continue
            if NAME.match(subj):
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
                L['_o'] = o
                if pending:
                    L['start'] = pending
                    tp = pair_of_time(pending)
                    c = (fills or {}).get(o)
                    if tp:
                        run, k = 0, o
                        while c and fills.get(k - 1) == c:
                            k -= 1
                        while c and fills.get(k + run) == c:
                            run += 1
                        L['a'] = tp
                        n = max((run + 1) // 2, 1) if c else 1
                        if n > 1:
                            L['b'] = min(6, tp + n - 1)
                    pending = None
                lessons.append(L)
                last = L
                if tt or rr:
                    halves[half] = L
            elif last is not None and last['a'] == p:
                # строка без предмета: доп. преподаватель / кабинет к текущей паре
                if t:
                    last['t'] = (last.get('t', '') + ', ' + t).strip(', ') if t not in last.get('t', '') else last['t']
                if r and not last.get('r'):
                    last['r'] = room_label(r)
        # пара из двух строк без «1-/2-»: верхняя = 1 подгруппа, нижняя = 2 («нет» = у подгруппы пары нет)
        h0, h1 = halves.get(0), halves.get(1)
        if h0 and h1 and (isinstance(h0, dict) or isinstance(h1, dict)):
            if not any(isinstance(h, dict) and h.get('g') for h in (h0, h1)):
                if isinstance(h0, dict):
                    h0['g'] = '1'
                if isinstance(h1, dict):
                    h1['g'] = '2'
    if fills:
        lessons = merge_color_blocks(lessons, start, fills)
    lessons = merge_subgroups(lessons)
    lessons = apply_pair_notes(lessons)
    for L in lessons:
        L.pop('_o', None)
    for L in lessons:
        if L['s'].upper() == 'ЗОЖ':
            L['r'] = 'центр здоровья'
            if L['a'] == 1:
                L['start'] = '09:00'
            L['hint'] = 'Время и место уточняйте в чате группы'
    return lessons
