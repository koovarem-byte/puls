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
    local = os.path.join(ROOT, 'rasp.xlsx')
    if os.path.exists(local):
        print('скачать не вышло, беру загруженный вручную rasp.xlsx')
        return local
    sys.exit('Не удалось скачать таблицу. Загрузи её вручную в репозиторий как rasp.xlsx')


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
    new = parse(src)
    total = sum(len(v) for v in new.values())
    if len(new) < 5 or total < 20:
        sys.exit(f'Подозрительно мало данных: групп {len(new)}, дней {total}. data.json не трогаю')
    old = json.load(open(DATA)) if os.path.exists(DATA) else {'groups': {}}
    groups = old.get('groups', {})
    for g, days in new.items():
        groups.setdefault(g, {}).update(days)
    fix_typos(groups)
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    json.dump({'checked': now.strftime('%Y-%m-%d %H:%M')}, open(os.path.join(ROOT, 'status.json'), 'w'))
    if groups == old.get('groups') and old.get('source') == 'xlsx' and len(sys.argv) == 1:
        print('без изменений')
        return
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    json.dump({'updated': now.strftime('%Y-%m-%d %H:%M'), 'source': 'xlsx', 'groups': groups},
              open(DATA, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('обновлено: групп', len(groups))


if __name__ == '__main__':
    main()
