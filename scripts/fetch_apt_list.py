"""
청약랩 ApplyLab — 단지 목록 전체 수집 스크립트
GitHub Actions에서 하루 2회(00시·12시) 실행.
data/apt/ 에 JSON 저장 → search.html에서 API 대신 JSON 직접 로드.

저장 파일:
  data/apt/list.json     — 전체 단지 목록 (검색·필터용)
  data/apt/meta.json     — 수집 메타정보 (건수·시각)
"""

import os, json, time, datetime, urllib.request, urllib.parse

API_KEY  = os.environ.get('API_KEY', '')
BASE_URL = 'https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail'
OUT_DIR  = 'data/apt'
os.makedirs(OUT_DIR, exist_ok=True)

# 오늘 날짜 (KST)
NOW     = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
NOW_STR = NOW.strftime('%Y-%m-%d %H:%M')
TODAY   = NOW.strftime('%Y%m%d')

def fetch_page(page, per=100, retry=3):
    params = urllib.parse.urlencode({
        'serviceKey': API_KEY,
        'page':       page,
        'perPage':    per,
    })
    url = f'{BASE_URL}?{params}'
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                d = json.loads(r.read())
            return d.get('data', []), d.get('totalCount', 0)
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2)
            else:
                print(f'  ⚠ 페이지 {page} 실패: {e}')
                return [], 0

def slim(row):
    """필요한 필드만 추출 → 파일 크기 최소화"""
    def d(k): return str(row.get(k) or '').strip()
    return {
        'no':   d('HOUSE_MANAGE_NO'),
        'pbno': d('PBLANC_NO'),
        'nm':   d('HOUSE_NM'),
        'area': d('SUBSCRPT_AREA_CODE_NM'),
        'addr': d('HSSPLY_ADRES'),
        'type': d('HOUSE_DTL_SECD_NM'),
        'tot':  d('TOT_SUPLY_HSHLDCO'),
        'co':   d('CNSTRCT_ENTRPS_NM'),
        # 청약 일정 (상태 계산용)
        'r1s':  d('GNRL_RNK1_CRSPAREA_RCPTDE') or d('SPSPLY_RCEPT_BGNDE'),
        'r2e':  d('GNRL_RNK2_CRSPAREA_ENDDE'),
        'ann':  d('RCRIT_PBLANC_DE'),
        'win':  d('PRZWNER_PRESNATN_DE'),
        'cnt':  d('CNTRCT_CNCLS_BGNDE'),
        'mv':   d('MVN_PREARNGE_YM'),
        'url':  d('PBLANC_URL'),
    }

def main():
    if not API_KEY:
        print('ERROR: API_KEY 환경변수 없음')
        return

    print(f'[{NOW_STR} KST] 단지 목록 수집 시작')

    # 1페이지로 총 건수 파악
    first, total = fetch_page(1)
    if not total:
        print('ERROR: 총 건수 조회 실패')
        return

    total_pages = (total + 99) // 100
    print(f'총 {total:,}건 / {total_pages}페이지')

    all_rows = [slim(r) for r in first]

    # 나머지 페이지 수집
    for pg in range(2, total_pages + 1):
        rows, _ = fetch_page(pg)
        all_rows.extend(slim(r) for r in rows)
        if pg % 5 == 0:
            print(f'  {pg}/{total_pages} 페이지 완료 ({len(all_rows):,}건)')
        time.sleep(0.2)

    print(f'수집 완료: {len(all_rows):,}건')

    # list.json 저장
    list_path = f'{OUT_DIR}/list.json'
    with open(list_path, 'w', encoding='utf-8') as f:
        json.dump(all_rows, f, ensure_ascii=False, separators=(',', ':'))
    size_kb = os.path.getsize(list_path) // 1024
    print(f'list.json 저장: {size_kb:,}KB')

    # meta.json 저장
    meta = {
        'updated':  NOW_STR,
        'date':     TODAY,
        'count':    len(all_rows),
        'size_kb':  size_kb,
    }
    with open(f'{OUT_DIR}/meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

    print('완료')

if __name__ == '__main__':
    main()
