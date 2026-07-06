# research

에코백 주문제작 사업 리서치 + 경쟁사 모니터링 도구 저장소.

## 구성

| 경로 | 내용 |
|---|---|
| `reports/` | 시장·키워드 조사, 사업 전략 보고서 |
| `monitor/` | 네이버 쇼핑 순위 수집 스크립트 (`crawl.py`, `keywords.json`) |
| `docs/` | 경쟁사 모니터 대시보드 (GitHub Pages) + 수집 데이터 (`docs/data/`) |
| `.github/workflows/daily-monitor.yml` | 매일 07:30 KST 자동 수집 |

## 경쟁사 모니터 — 최초 설정 (1회)

1. **네이버 API 키 발급**: [developers.naver.com](https://developers.naver.com/apps/#/register) → 애플리케이션 등록 → 사용 API에 **"검색"** 추가 → Client ID / Client Secret 확보. (무료, 일 25,000회 한도 — 이 도구는 하루 10회 사용)
2. **GitHub Secrets 등록**: 저장소 → Settings → Secrets and variables → Actions → New repository secret
   - `NAVER_CLIENT_ID`
   - `NAVER_CLIENT_SECRET`
3. **GitHub Pages 활성화**: Settings → Pages → Source: `Deploy from a branch`, Branch: `main`, 폴더: `/docs`
4. **첫 실행**: Actions 탭 → `daily-competitor-monitor` → Run workflow (이후 매일 07:30 KST 자동 실행)

첫 실제 수집이 되면 현재 들어있는 샘플(모의) 데이터를 지워도 됩니다:
`docs/data/snapshots/` 안의 `mock` 표시된 파일 삭제 후 커밋. (대시보드 상단에 샘플 데이터 경고 배너가 뜨는 동안은 아직 실데이터가 아니라는 뜻)

## 키워드 추가/변경

`monitor/keywords.json`의 `keywords` 배열을 수정하고 커밋하면 다음 수집부터 반영됩니다.

## 수집하는 것 / 못 하는 것

- ✅ 키워드별 네이버 쇼핑 상위 100개 상품의 **순위, 가격, 판매처(mall), 상품명** — 매일 스냅샷
- ✅ 대시보드에서 업체별 순위 추이, 7일 변화, 신규 진입/이탈, 평균가 추적
- ❌ **리뷰 수·판매량**은 네이버 오픈API가 제공하지 않음. 상품 페이지 직접 크롤링은 차단 위험이 높아 제외 (필요 시 2단계 과제)

## 리뷰 마이닝 (사장님 PC에서 실행)

경쟁사·자사 리뷰를 수집해 불만/칭찬 포인트를 분석하고, 상세페이지에 쓸 "공격 포인트"를 뽑아주는 도구. `review-mining/` 폴더 전체를 PC로 내려받아 사용합니다.

1. **파이썬 설치** (1회): Microsoft Store에서 "Python 3.12" 검색 → 설치
2. `review-mining/targets.json` 열어서 맨 위 "자사" 항목의 URL을 우리 대표 상품 주소로 수정 (경쟁사 12곳은 모니터링 데이터 기준으로 미리 채워져 있음)
3. `run.bat` 더블클릭 → 수집(10~20분) 후 브라우저에 보고서가 자동으로 열림

- 사람이 보는 속도로 천천히 수집합니다(요청 간 2~4초). **주 1회 정도만** 실행하세요.
- 수집된 리뷰(`data/`)와 보고서(`report.html`)는 개인정보가 섞일 수 있어 GitHub에 올라가지 않습니다(.gitignore 처리).
- 네이버 페이지 구조가 바뀌면 수집이 실패할 수 있습니다 — 그때는 화면 메시지를 캡처해서 알려주시면 고쳐드립니다.

## 로컬 실행

```bash
# 실제 수집
NAVER_CLIENT_ID=... NAVER_CLIENT_SECRET=... python3 monitor/crawl.py
# 샘플 데이터 14일치 생성 (대시보드 확인용)
python3 monitor/crawl.py --mock 14
# 대시보드 로컬 확인
cd docs && python3 -m http.server 8000  # → http://localhost:8000
```
