"""Разбор xlsx-таблицы колледжа (основной источник для автообновления)."""
import re, datetime
import openpyxl
from lessons import build_day, NOTE, TIME


def P_NOTE(v):
    return bool(NOTE.match(v) or TIME.match(v))

LABEL = re.compile(r'^\s*(\d{3})\s*([А-Яа-яA-Za-z]?)\s*$')
DATE = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{4})')


def s(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime('%d.%m.%Y')
    return str(v).strip()


def as_date(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime('%Y-%m-%d')
    m = DATE.search(s(v))
    if m:
        return f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
    return None


def norm_group(a, b):
    lat = {'A': 'А', 'B': 'Б', 'V': 'В'}
    b = lat.get(b.upper(), b.upper())
    return a + b


_fill_cache = {}


def fill_of(ws, r0, c0):
    """Цвет заливки ячейки (r0, c0 — с нуля) или None для белого / без заливки."""
    key = (id(ws), r0, c0)
    if key in _fill_cache:
        return _fill_cache[key]
    v = None
    try:
        f = ws.cell(r0 + 1, c0 + 1).fill
        if f is not None and f.fill_type == 'solid':
            col = f.fgColor
            rgb = col.rgb if col.type == 'rgb' else (f'theme{col.theme}:{col.tint}' if col.type == 'theme' else None)
            if isinstance(rgb, str) and rgb.upper() not in ('FFFFFFFF', '00000000', '00FFFFFF'):
                v = rgb
    except Exception:
        v = None
    _fill_cache[key] = v
    return v


def parse_sheet(ws):
    grid = [list(r) for r in ws.iter_rows(values_only=True)]
    ncols = max((len(r) for r in grid), default=0)
    for r in grid:
        r += [None] * (ncols - len(r))
    headers = []
    for i, row in enumerate(grid):
        labs = []
        for j, v in enumerate(row):
            m = LABEL.match(s(v)) if v is not None else None
            if m:
                labs.append((norm_group(m.group(1), m.group(2)), j))
        if len(labs) >= 8:
            headers.append((i, labs))
    # даты: ячейка в первых столбцах; если она объединена, берём центр объединения
    merged = {}
    for m in ws.merged_cells.ranges:
        if m.min_col <= 3:
            merged[(m.min_row - 1, m.min_col - 1)] = (m.min_row - 1 + m.max_row - 1) / 2
    hrows = [h for h, _ in headers]
    dates_by_header = {}
    for i, row in enumerate(grid):
        for c in range(0, min(3, ncols)):
            d = as_date(row[c])
            if not d:
                continue
            center = merged.get((i, c), i)
            hs = [h for h in hrows if h <= center + 0.5]
            if hs and hs[-1] not in dates_by_header:
                dates_by_header[hs[-1]] = d
    days = {}
    for hi, (hr, labs) in enumerate(headers):
        nxt = headers[hi + 1][0] if hi + 1 < len(headers) else min(len(grid), hr + 16)
        date = dates_by_header.get(hr)
        if not date:
            continue
        block = grid[hr + 1:nxt]
        has_rv = any('разговор' in s(v).lower() for row in block[:2] for v in row)
        start = 3 if has_rv else 1
        if has_rv and len(block) > 1:
            # классный час иногда занимает одну строку: тогда 1 пара начинается со 2-й строки
            row1 = [s(v).lower() for v in block[0]]
            row2 = [s(v) for v in block[1]]
            one_row = any(
                row2[j] and 'разговор' not in row2[j].lower() and not row2[j].replace('.', '').isdigit()
                and 'разговор' in row1[j] and not P_NOTE(row2[j])
                for _, j in labs if j < len(row2))
            if one_row:
                start = 2
        for g, j in labs:
            fills = {}
            for k in range(1, len(block) + 1):
                f = fill_of(ws, hr + k, j)
                if f:
                    fills[k] = f
            rows = {}
            for k, row in enumerate(block, start=1):
                vals = [s(row[j]) if j < ncols else '', s(row[j + 1]) if j + 1 < ncols else '', s(row[j + 2]) if j + 2 < ncols else '']
                if any(vals):
                    rows[k] = vals
            days.setdefault(g, {})[date] = build_day(rows, start, fills=fills)
    return days


def parse(path):
    wb = openpyxl.load_workbook(path, data_only=True, keep_links=False)
    out = {}
    for ws in wb.worksheets:
        for g, d in parse_sheet(ws).items():
            out.setdefault(g, {}).update(d)
    return out
