"""Скачивает таблицу колледжа, разбирает и обновляет data.json.
Запускается роботом GitHub Actions по расписанию."""
import json, sys, os, datetime, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from parse_xlsx import parse

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
    sys.exit('Не удалось скачать таблицу')


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
    if groups == old.get('groups') and old.get('source') == 'xlsx':
        print('без изменений')
        return
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    json.dump({'updated': now.strftime('%Y-%m-%d %H:%M'), 'source': 'xlsx', 'groups': groups},
              open(DATA, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('обновлено: групп', len(groups))


if __name__ == '__main__':
    main()
