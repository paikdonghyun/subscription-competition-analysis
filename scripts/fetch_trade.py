"""
청약랩 ApplyLab — 실거래가 데이터 수집 스크립트
GitHub Actions에서 매일 실행. data/trade/ 에 JSON 저장.

수집 범위:
  - 최근 6개월 데이터
  - 주요 청약 지역(서울·경기·인천·부산·대구·대전·광주 시군구 전체)
  - 아파트 매매 실거래가
"""

import os, json, time, datetime, urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────
API_KEY  = os.environ.get('API_KEY', '')
BASE_URL = 'https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade'
OUT_DIR  = Path('data/trade')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 주요 시군구코드 (법정동 앞 5자리)
# 서울 전 자치구 + 경기 주요 시 + 인천·부산·대구·대전·광주 주요 구
REGIONS = {
    # 서울
    '11110': '서울 종로구', '11140': '서울 중구',    '11170': '서울 용산구',
    '11200': '서울 성동구', '11215': '서울 광진구',  '11230': '서울 동대문구',
    '11260': '서울 중랑구', '11290': '서울 성북구',  '11305': '서울 강북구',
    '11320': '서울 도봉구', '11350': '서울 노원구',  '11380': '서울 은평구',
    '11410': '서울 서대문구','11440': '서울 마포구', '11470': '서울 양천구',
    '11500': '서울 강서구', '11530': '서울 구로구',  '11545': '서울 금천구',
    '11560': '서울 영등포구','11590': '서울 동작구', '11620': '서울 관악구',
    '11650': '서울 서초구', '11680': '서울 강남구',  '11710': '서울 송파구',
    '11740': '서울 강동구',
    # 경기 주요
    '41111': '경기 수원 장안구', '41113': '경기 수원 권선구',
    '41115': '경기 수원 팔달구', '41117': '경기 수원 영통구',
    '41131': '경기 성남 수정구', '41133': '경기 성남 중원구', '41135': '경기 성남 분당구',
    '41150': '경기 의정부시',    '41171': '경기 안양 만안구', '41173': '경기 안양 동안구',
    '41190': '경기 부천시',      '41210': '경기 광명시',      '41220': '경기 평택시',
    '41250': '경기 동두천시',    '41270': '경기 안산 단원구', '41271': '경기 안산 상록구',
    '41281': '경기 고양 덕양구','41285': '경기 고양 일산동구','41287': '경기 고양 일산서구',
    '41290': '경기 과천시',      '41310': '경기 구리시',      '41360': '경기 남양주시',
    '41370': '경기 오산시',      '41390': '경기 시흥시',      '41410': '경기 군포시',
    '41430': '경기 의왕시',      '41450': '경기 하남시',
    '41461': '경기 용인 처인구', '41463': '경기 용인 기흥구', '41465': '경기 용인 수지구',
    '41480': '경기 파주시',      '41500': '경기 이천시',      '41550': '경기 안성시',
    '41570': '경기 김포시',      '41590': '경기 화성시',      '41610': '경기 광주시',
    '41630': '경기 양주시',      '41670': '경기 포천시',
    # 인천
    '28110': '인천 중구',  '28140': '인천 동구',  '28177': '인천 미추홀구',
    '28185': '인천 연수구','28200': '인천 남동구', '28237': '인천 부평구',
    '28245': '인천 계양구','28260': '인천 서구',
    # 부산
    '26110': '부산 중구',  '26140': '부산 서구',  '26170': '부산 동구',
    '26200': '부산 영도구','26215': '부산 부산진구','26230': '부산 동래구',
    '26260': '부산 남구',  '26290': '부산 북구',  '26305': '부산 해운대구',
    '26310': '부산 사하구','26320': '부산 금정구', '26330': '부산 강서구',
    '26350': '부산 연제구','26360': '부산 수영구', '26370': '부산 사상구',
    # 대구
    '27110': '대구 중구',  '27140': '대구 동구',  '27170': '대구 서구',
    '27200': '대구 남구',  '27230': '대구 북구',  '27260': '대구 수성구',
    '27290': '대구 달서구',
    # 대전
    '30110': '대전 동구',  '30140': '대전 중구',  '30170': '대전 서구',
    '30200': '대전 유성구','30230': '대전 대덕구',
    # 광주
    '29110': '광주 동구',  '29140': '광주 서구',  '29155': '광주 남구',
    '29170': '광주 북구',  '29200': '광주 광산구',
}

def get_months(n=6):
    """최근 n개월 YYYYMM 리스트"""
    months = []
    today = datetime.date.today()
    for i in range(n):
        d = today.replace(day=1) - datetime.timedelta(days=i*28)
        months.append(d.strftime('%Y%m'))
    return months

def fetch_trade(lawd_cd, deal_ymd, retry=3):
    """실거래가 API 호출 → 거래 리스트 반환"""
    params = urllib.parse.urlencode({
        'serviceKey': API_KEY,
        'LAWD_CD':    lawd_cd,
        'DEAL_YMD':   deal_ymd,
        'numOfRows':  '100',
        'pageNo':     '1',
    })
    url = f'{BASE_URL}?{params}'

    for attempt in range(retry):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            items = []
            for item in root.iter('item'):
                apt_nm  = (item.findtext('aptNm') or '').strip()
                area    = item.findtext('excluUseAr') or ''
                amount  = (item.findtext('dealAmount') or '').replace(',','')
                floor   = item.findtext('floor') or ''
                year    = item.findtext('dealYear') or ''
                month   = item.findtext('dealMonth') or ''
                dong    = (item.findtext('umdNm') or '').strip()
                build_y = item.findtext('buildYear') or ''
                try:
                    amt_man = int(amount)   # 만원 단위
                    area_f  = float(area)   # ㎡
                    if apt_nm and amt_man > 0 and area_f > 0:
                        items.append({
                            'nm':  apt_nm,
                            'amt': amt_man,         # 만원
                            'ar':  round(area_f, 1),# ㎡
                            'fl':  floor,
                            'ym':  f'{year}{str(month).zfill(2)}',
                            'dg':  dong,
                            'by':  build_y,
                        })
                except (ValueError, TypeError):
                    continue
            return items
        except Exception as e:
            if attempt < retry - 1:
                time.sleep(2)
            else:
                print(f'  ⚠ 실패 {lawd_cd} {deal_ymd}: {e}')
                return []
    return []

def calc_stats(trades, area_min=59, area_max=100):
    """전용면적 기준(기본 59~100㎡) 통계 산출"""
    filtered = [t for t in trades if area_min <= t['ar'] <= area_max]
    if not filtered:
        filtered = trades  # 없으면 전체
    if not filtered:
        return None
    amts = sorted(t['amt'] for t in filtered)
    n = len(amts)
    avg = int(sum(amts) / n)
    med = amts[n // 2]
    hi  = amts[-1]
    lo  = amts[0]
    # 최근 3건 평균 (최신 동향)
    recent = sorted(filtered, key=lambda x: x['ym'], reverse=True)[:5]
    recent_avg = int(sum(t['amt'] for t in recent) / len(recent)) if recent else avg
    return {
        'cnt':    n,
        'avg':    avg,
        'med':    med,
        'hi':     hi,
        'lo':     lo,
        'recent': recent_avg,  # 최근 5건 평균
        'samples': [{'nm':t['nm'],'amt':t['amt'],'ar':t['ar'],'ym':t['ym']} for t in recent[:3]],
    }

def main():
    if not API_KEY:
        print('ERROR: API_KEY 환경변수 없음')
        return

    months = get_months(6)
    print(f'수집 기간: {months[-1]} ~ {months[0]}')
    print(f'수집 지역: {len(REGIONS)}개 시군구')

    # 지역별로 수집·저장
    summary = {}  # 지역코드 → 통계

    for lawd_cd, region_nm in REGIONS.items():
        all_trades = []
        for ym in months:
            trades = fetch_trade(lawd_cd, ym)
            all_trades.extend(trades)
            time.sleep(0.3)  # API 부하 방지

        if not all_trades:
            print(f'  {region_nm}: 데이터 없음')
            continue

        stats = calc_stats(all_trades)
        if stats:
            summary[lawd_cd] = {
                'nm':    region_nm,
                **stats,
                'updated': datetime.date.today().isoformat(),
            }
            print(f'  ✓ {region_nm}: {stats["cnt"]}건 / 평균 {stats["avg"]:,}만원')

        # 지역별 상세 파일 저장 (단지명 검색용)
        # 단지명별로 그룹화
        apts = {}
        for t in all_trades:
            nm = t['nm']
            if nm not in apts:
                apts[nm] = []
            apts[nm].append(t)

        apt_stats = {}
        for nm, tlist in apts.items():
            st = calc_stats(tlist)
            if st:
                apt_stats[nm] = {
                    'cnt':    st['cnt'],
                    'avg':    st['avg'],
                    'recent': st['recent'],
                    'hi':     st['hi'],
                    'lo':     st['lo'],
                }

        detail_path = OUT_DIR / f'{lawd_cd}.json'
        detail_data = {
            'lawd_cd':  lawd_cd,
            'region':   region_nm,
            'updated':  datetime.date.today().isoformat(),
            'stats':    stats,
            'apts':     apt_stats,   # 단지명 → 통계
        }
        with open(detail_path, 'w', encoding='utf-8') as f:
            json.dump(detail_data, f, ensure_ascii=False, separators=(',',':'))

    # 전체 요약 파일 저장 (빠른 지역 조회용)
    summary_path = OUT_DIR / 'summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'updated': datetime.date.today().isoformat(),
            'months':  months,
            'regions': summary,
        }, f, ensure_ascii=False, separators=(',',':'))

    print(f'\n완료: {len(summary)}개 지역 / summary.json 저장')

if __name__ == '__main__':
    main()
