"""
청약랩 ApplyLab — 지역별 최근 1년 청약 경쟁률 캐시 수집 스크립트
GitHub Actions에서 하루 1회 실행. data/apt/list.json(단지목록)을 기반으로
청약홈 경쟁률 API 전체를 수집해 "지역(area)별 최근 1년 평균 경쟁률"을
data/region_rate/list.json 으로 저장.

용도: apt.html 인기도 산출 시 "단지 인근 최근 1년 청약 온도" 지표로 사용.
"""

import os, json, time, datetime, urllib.request, urllib.parse

API_KEY     = os.environ.get('API_KEY', '')
CMPET_BASE  = 'https://api.odcloud.kr/api/ApplyhomeInfoCmpetRtSvc/v1/getAPTLttotPblancCmpet'
APT_LIST    = 'data/apt/list.json'
OUT_DIR     = 'data/region_rate'

os.makedirs(OUT_DIR, exist_ok=True)

NOW     = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
NOW_STR = NOW.strftime('%Y-%m-%d %H:%M')
CUTOFF  = (NOW - datetime.timedelta(days=365)).strftime('%Y-%m-%d')  # 최근 1년

def fetch_page(page, per=300, retry=3):
    params = urllib.parse.urlencode({
        'serviceKey': API_KEY, 'page': page, 'perPage': per,
    })
    url = f'{CMPET_BASE}?{params}'
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

def parse_rate(s):
    if not s:
        return None
    import re
    m = re.search(r'[\d.]+', str(s))
    return float(m.group()) if m else None

def main():
    if not API_KEY:
        print('ERROR: API_KEY 없음')
        return

    if not os.path.exists(APT_LIST):
        print('ERROR: data/apt/list.json 없음')
        return

    with open(APT_LIST, encoding='utf-8') as f:
        apts = json.load(f)

    # 단지번호 → (지역, 공고일) 매핑, 최근 1년 공고만 필터
    apt_meta = {}
    for a in apts:
        no  = a.get('no')
        ann = (a.get('ann') or '').strip()
        area = (a.get('area') or '').strip()
        if no and area and ann and ann >= CUTOFF:
            apt_meta[no] = area

    print(f'[{NOW_STR} KST] 최근 1년 공고 단지: {len(apt_meta):,}건')
    print(f'기준일(1년 전): {CUTOFF}')

    # 경쟁률 전체 수집 (1순위 해당지역만 사용 — 가장 일반적인 경쟁률 지표)
    first, total = fetch_page(1)
    total_pages = (total + 299) // 300
    print(f'경쟁률 전체: {total:,}건 / {total_pages}페이지')

    region_rates = {}  # area -> [rate, rate, ...]
    matched = 0

    def process(rows):
        nonlocal matched
        for r in rows:
            no = r.get('HOUSE_MANAGE_NO')
            if no not in apt_meta:
                continue
            # 1순위 해당지역만 대표값으로 사용
            if str(r.get('SUBSCRPT_RANK_CODE')) != '1':
                continue
            rate = parse_rate(r.get('CMPET_RATE'))
            if rate is None or rate <= 0:
                continue
            area = apt_meta[no]
            region_rates.setdefault(area, []).append(rate)
            matched += 1

    process(first)
    for pg in range(2, total_pages + 1):
        rows, _ = fetch_page(pg)
        process(rows)
        if pg % 50 == 0:
            print(f'  {pg}/{total_pages} 페이지 완료 (매칭 {matched:,}건)')
        time.sleep(0.05)

    print(f'매칭 완료: {matched:,}건 / {len(region_rates)}개 지역')

    # 지역별 평균·중앙값 산출
    result = {}
    for area, rates in region_rates.items():
        rates_sorted = sorted(rates)
        n = len(rates_sorted)
        avg = sum(rates_sorted) / n
        med = rates_sorted[n // 2]
        result[area] = {
            'avg': round(avg, 2),
            'median': round(med, 2),
            'count': n,
        }

    # 전국 분포 대비 백분위 계산
    all_avgs = sorted(v['avg'] for v in result.values())
    n_all = len(all_avgs)
    for area, v in result.items():
        cnt = sum(1 for x in all_avgs if x <= v['avg'])
        v['percentile'] = round(cnt / n_all * 100) if n_all else 50

    out_path = f'{OUT_DIR}/list.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    meta = {
        'updated': NOW_STR,
        'cutoff': CUTOFF,
        'region_count': len(result),
        'matched_count': matched,
    }
    with open(f'{OUT_DIR}/meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

    print(f'\n저장 완료: {out_path}')
    for area, v in sorted(result.items(), key=lambda x: -x[1]['avg'])[:10]:
        print(f'  {area}: 평균 {v["avg"]}:1 (백분위 {v["percentile"]}, {v["count"]}건)')

if __name__ == '__main__':
    main()
