"""Скачивает таблицу колледжа, разбирает и обновляет data.json.
Запускается роботом GitHub Actions по расписанию."""
import json, sys, os, datetime, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from parse_xlsx import parse
import difflib, collections

FILE_ID = '15gLO2V6V3jxHgYROBl3S_fxmZk7YYMOV'
URLS = [
    f'https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx',
    f'https://drive.google.com/uc?export=download&id={FILE_ID}',
]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data.json')


def download():
    import time
    for attempt in range(3):
        p = try_download()
        if p:
            return p
        time.sleep(20)
    local = os.path.join(ROOT, 'rasp.xlsx')
    if os.path.exists(local):
        print('скачать не вышло, беру загруженный вручную rasp.xlsx')
        return local
    sys.exit('Не удалось скачать таблицу. Загрузи её вручную в репозиторий как rasp.xlsx')


def try_download():
    for u in URLS:
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            body = urllib.request.urlopen(req, timeout=60).read()
            if body[:2] == b'PK':  # xlsx = zip
                open('/tmp/rasp.xlsx', 'wb').write(body)
                print('downloaded from', u, len(body))
                return '/tmp/rasp.xlsx'
            print('not xlsx from', u)
        except Exception as e:
            print('fail', u, e)
    return None


def fix_typos(groups):
    """Редкие написания с опечатками заменяем на частое правильное (Неарология -> Неврология)."""
    cnt = collections.Counter(l['s'] for g in groups.values() for v in g.values() for l in v)
    common = [s for s, n in cnt.items() if n >= 8]
    for g in groups.values():
        for v in g.values():
            for l in v:
                if cnt[l['s']] < 4 and len(l['s']) > 5:
                    m = difflib.get_close_matches(l['s'], common, n=1, cutoff=0.82)
                    if m:
                        l['s'] = m[0]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else download()
    if len(sys.argv) == 1:
        import shutil
        os.makedirs(os.path.join(ROOT, 'cache'), exist_ok=True)
        shutil.copy(src, os.path.join(ROOT, 'cache', 'latest.xlsx'))
    new = parse(src)
    total = sum(len(v) for v in new.values())
    if len(new) < 5 or total < 20:
        sys.exit(f'Подозрительно мало данных: групп {len(new)}, дней {total}. data.json не трогаю')
    old = json.load(open(DATA)) if os.path.exists(DATA) else {'groups': {}}
    import copy
    groups = copy.deepcopy(old.get('groups', {}))
    for g, days in new.items():
        groups.setdefault(g, {}).update(days)
    fix_typos(groups)
    # защита: если новая таблица разобралась подозрительно плохо (колледж поменял вёрстку), ничего не портим
    old_n = new_n = 0
    for g, days in new.items():
        for d, v in days.items():
            if d in old.get('groups', {}).get(g, {}):
                old_n += len(old['groups'][g][d]); new_n += len(v)
    if old_n > 50 and new_n < 0.6 * old_n:
        sys.exit(f'Разбор выглядит сломанным: пар было {old_n}, стало {new_n}. data.json не трогаю')
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    same = groups == old.get('groups') and old.get('source') == 'xlsx' and len(sys.argv) == 1
    status_path = os.path.join(ROOT, 'status.json')
    # Каждый коммит запускает выкладку сайта (GitHub Pages, 4-6 минут), и новый коммит отменяет незаконченную.
    # Поэтому без изменений в расписании время проверки сохраняем не чаще раза в 20 минут.
    try:
        prev = datetime.datetime.strptime(json.load(open(status_path))['checked'], '%Y-%m-%d %H:%M')
        fresh = (now.replace(tzinfo=None) - prev) < datetime.timedelta(minutes=19)
    except Exception:
        fresh = False
    if not (same and fresh):
        json.dump({'checked': now.strftime('%Y-%m-%d %H:%M')}, open(status_path, 'w'))
    if same:
        print('без изменений' + (' (время проверки обновлю в следующий раз)' if fresh else ''))
        return
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    json.dump({'updated': now.strftime('%Y-%m-%d %H:%M'), 'source': 'xlsx', 'groups': groups},
              open(DATA, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('обновлено: групп', len(groups))


if __name__ == '__main__':
    main()
