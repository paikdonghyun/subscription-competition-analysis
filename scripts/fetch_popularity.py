"""
청약랩 ApplyLab — 네이버 언급량(인기도) 수집 스크립트
GitHub Actions에서 하루 2회(00시·12시) 실행. data/apt/list.json의
단지 목록을 기반으로 블로그+카페 검색 총건수를 조회해 popularity.json 저장.

※ 네이버 검색 API는 무료 일 25,000건. 약 2,800개 단지 × 2(블로그+카페) = 5,600건
   → 여유 있게 사용 가능.
"""

import os, json, time, datetime, urllib.request, urllib.parse, urllib.error

CLIENT_ID     = os.environ.get('NAVER_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET', '')
OUT_DIR       = 'data/popularity'
APT_LIST_PATH = 'data/apt/list.json'

os.makedirs(OUT_DIR, exist_ok=True)

NOW     = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
NOW_STR = NOW.strftime('%Y-%m-%d %H:%M')

def naver_search(api, query, retry=3, debug=False):
    """blog 또는 cafearticle 검색 → total(검색결과 총건수) 반환"""
    url = f'https://openapi.naver.com/v1/search/{api}.json?' + urllib.parse.urlencode({
        'query': query, 'display': 1,
    })
    req = urllib.request.Request(url, headers={
        'X-Naver-Client-Id':     CLIENT_ID,
        'X-Naver-Client-Secret': CLIENT_SECRET,
    })
    for attempt in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                d = json.loads(r.read())
            return d.get('total', 0)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')
            if debug:
                print(f'  [HTTPError {e.code}] {api} "{query}": {body[:200]}')
            if e.code == 429:  # 쿼터 초과
                time.sleep(3)
                continue
            return 0
        except Exception as ex:
            if debug:
                print(f'  [Exception] {api} "{query}": {ex}')
            if attempt < retry - 1:
                time.sleep(1)
            else:
                return 0
    return 0

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print('ERROR: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음')
        return

    if not os.path.exists(APT_LIST_PATH):
        print('ERROR: data/apt/list.json 없음 (먼저 fetch_apt_list.py 실행 필요)')
        return

    with open(APT_LIST_PATH, encoding='utf-8') as f:
        apts = json.load(f)

    print(f'[{NOW_STR} KST] 단지 {len(apts):,}건 언급량 수집 시작')

    # ── 1순위: 청약 진행 중이거나 최근 단지만 수집 (전체 수집 시 시간 과다) ──
    # r1s(1순위 접수일) 기준 최근 60일 이내 + 향후 60일 이내 단지만 대상
    today = NOW.strftime('%Y%m%d')
    cutoff_past   = (NOW - datetime.timedelta(days=60)).strftime('%Y%m%d')
    cutoff_future = (NOW + datetime.timedelta(days=60)).strftime('%Y%m%d')

    targets = []
    for apt in apts:
        r1s = (apt.get('r1s') or '').replace('-', '')
        if not r1s:
            continue
        if cutoff_past <= r1s <= cutoff_future:
            targets.append(apt)

    print(f'수집 대상(최근±60일 단지): {len(targets):,}건')

    results = {}
    for i, apt in enumerate(targets):
        no = apt.get('no')
        nm = apt.get('nm', '').strip()
        area = apt.get('area', '').strip()
        if not no or not nm:
            continue

        # 검색어: "단지명 지역명" 조합으로 정확도 향상
        query = f'{nm} {area}'.strip()

        blog_cnt = naver_search('blog', query, debug=(i < 5))
        time.sleep(0.05)
        cafe_cnt = naver_search('cafearticle', query, debug=(i < 5))
        time.sleep(0.05)

        results[no] = {
            'nm': nm,
            'blog': blog_cnt,
            'cafe': cafe_cnt,
            'total': blog_cnt + cafe_cnt,
        }

        if (i + 1) % 50 == 0:
            print(f'  {i+1}/{len(targets)} 완료')

    print(f'수집 완료: {len(results):,}건')

    # ── 백분위 산출을 위한 분포 계산 ──
    totals = sorted(r['total'] for r in results.values())
    n = len(totals)

    def percentile(value):
        if n == 0:
            return 50
        # value 이하인 개수 비율
        cnt = sum(1 for t in totals if t <= value)
        return round(cnt / n * 100)

    for no, r in results.items():
        r['percentile'] = percentile(r['total'])

    # ── 저장 ──
    out_path = f'{OUT_DIR}/list.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

    meta = {
        'updated': NOW_STR,
        'count':   len(results),
        'method':  '블로그+카페 검색 총건수 → 동기간 단지 대비 백분위',
    }
    with open(f'{OUT_DIR}/meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(out_path) // 1024
    print(f'popularity/list.json 저장 완료: {size_kb}KB')

if __name__ == '__main__':
    main()
