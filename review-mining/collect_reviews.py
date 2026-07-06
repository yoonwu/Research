#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""네이버 스마트스토어 상품 리뷰 수집기 (사장님 PC에서 실행용).

targets.json에 적힌 상품들의 리뷰를 수집해 data/ 폴더에 저장한다.
외부 라이브러리 설치 없이 파이썬 기본 기능만 사용.

사용법:
  python collect_reviews.py            # 전체 수집 (상품당 최대 30페이지 = 600개)
  python collect_reviews.py --pages 5  # 상품당 5페이지만 (빠른 테스트)

주의: 사람이 보는 것과 비슷한 속도로 천천히 수집합니다(요청 간 2~4초).
      너무 자주 돌리지 마세요. 주 1회 정도면 충분합니다.
"""
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS_FILE = os.path.join(HERE, "targets.json")
DATA_DIR = os.path.join(HERE, "data")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REVIEW_API = "https://smartstore.naver.com/i/v1/contents/reviews/query-pages"


def polite_sleep():
    time.sleep(random.uniform(2.0, 4.0))


def http_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def http_post_json(url, payload, referer):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": referer,
            "Origin": "https://smartstore.naver.com",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def extract_ids(html):
    """상품 페이지 HTML에서 리뷰 API 호출에 필요한 번호들을 찾는다."""
    ids = {}
    m = re.search(r'"originProductNo"\s*:\s*"?(\d+)', html)
    if m:
        ids["originProductNo"] = m.group(1)
    m = re.search(r'"merchantNo"\s*:\s*"?(\d+)', html)
    if m:
        ids["merchantNo"] = m.group(1)
    m = re.search(r'"payReferenceKey"\s*:\s*"?(\d+)', html)
    if m and "merchantNo" not in ids:
        ids["merchantNo"] = m.group(1)
    return ids


def parse_reviews(api_response):
    """API 응답에서 리뷰 목록을 최대한 유연하게 뽑아낸다 (구조가 바뀌어도 견디도록)."""
    contents = None
    if isinstance(api_response, dict):
        for key in ("contents", "content", "reviews", "items"):
            v = api_response.get(key)
            if isinstance(v, list):
                contents = v
                break
        if contents is None:
            # 한 단계 안쪽도 탐색
            for v in api_response.values():
                if isinstance(v, dict):
                    for key in ("contents", "content", "reviews", "items"):
                        vv = v.get(key)
                        if isinstance(vv, list):
                            contents = vv
                            break
                if contents is not None:
                    break
    if contents is None:
        return None
    out = []
    for c in contents:
        if not isinstance(c, dict):
            continue
        text = (
            c.get("reviewContent")
            or c.get("content")
            or c.get("reviewText")
            or ""
        )
        score = c.get("reviewScore") or c.get("score") or c.get("rating")
        created = c.get("createDate") or c.get("createdDate") or c.get("date") or ""
        out.append(
            {
                "text": re.sub(r"\s+", " ", str(text)).strip(),
                "score": int(score) if score else None,
                "date": str(created)[:10],
            }
        )
    return out


def collect_product(target, max_pages):
    url = target["url"]
    print(f"\n[{target['label']}] {target['mall']} — 페이지 접속 중...")
    try:
        html = http_get(url)
    except Exception as e:
        print(f"  !! 상품 페이지 접속 실패: {e}")
        print("  -> 네이버가 접속을 막았거나 URL이 잘못됐을 수 있습니다. 다음 상품으로 넘어갑니다.")
        return None

    ids = extract_ids(html)
    if "originProductNo" not in ids or "merchantNo" not in ids:
        print(f"  !! 상품 번호를 찾지 못했습니다 (찾은 것: {list(ids.keys())})")
        print("  -> 네이버 페이지 구조가 바뀌었을 수 있습니다. 이 메시지를 캡처해서 알려주세요.")
        # 디버깅용으로 HTML 앞부분 저장
        os.makedirs(DATA_DIR, exist_ok=True)
        debug_path = os.path.join(DATA_DIR, "debug_page.html")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(html[:200000])
        print(f"  -> 분석용 파일 저장됨: {debug_path}")
        return None

    reviews = []
    for page in range(1, max_pages + 1):
        polite_sleep()
        payload = {
            "page": page,
            "pageSize": 20,
            "merchantNo": ids["merchantNo"],
            "originProductNo": ids["originProductNo"],
            "sortType": "REVIEW_CREATE_DATE_DESC",
        }
        try:
            resp = http_post_json(REVIEW_API, payload, url)
        except urllib.error.HTTPError as e:
            if page == 1:
                print(f"  !! 리뷰 API 호출 실패 (HTTP {e.code})")
                print("  -> 네이버가 API 주소를 바꿨거나 차단했을 수 있습니다. 캡처해서 알려주세요.")
                return None
            break
        except Exception as e:
            print(f"  !! 통신 오류: {e}")
            break
        batch = parse_reviews(resp)
        if batch is None:
            if page == 1:
                print("  !! 리뷰 응답 형식을 해석하지 못했습니다. 원본을 저장합니다.")
                os.makedirs(DATA_DIR, exist_ok=True)
                raw_path = os.path.join(DATA_DIR, "debug_api_response.json")
                with open(raw_path, "w", encoding="utf-8") as f:
                    json.dump(resp, f, ensure_ascii=False, indent=2)
                print(f"  -> 저장됨: {raw_path} (이 파일을 알려주세요)")
                return None
            break
        if not batch:
            break
        reviews.extend(batch)
        print(f"  {page}페이지 수집 — 누적 {len(reviews)}개")
    return reviews


def main():
    max_pages = 30
    if "--pages" in sys.argv:
        max_pages = int(sys.argv[sys.argv.index("--pages") + 1])

    with open(TARGETS_FILE, encoding="utf-8") as f:
        targets = json.load(f)["targets"]

    os.makedirs(DATA_DIR, exist_ok=True)
    collected = {}
    for t in targets:
        if "여기에" in t["url"]:
            print(f"\n[건너뜀] {t['mall']} — URL이 아직 입력되지 않았습니다 (targets.json 수정 필요)")
            continue
        reviews = collect_product(t, max_pages)
        if reviews:
            collected[t["mall"]] = {
                "label": t["label"],
                "mall": t["mall"],
                "url": t["url"],
                "collected_at": date.today().isoformat(),
                "reviews": reviews,
            }
            print(f"  => {t['mall']}: 총 {len(reviews)}개 저장")

    if not collected:
        print("\n수집된 리뷰가 없습니다. 위의 오류 메시지를 확인해주세요.")
        sys.exit(1)

    out_path = os.path.join(DATA_DIR, f"reviews-{date.today().isoformat()}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False)
    print(f"\n완료! {len(collected)}개 스토어 리뷰 저장: {out_path}")
    print("이제 analyze.py를 실행하면 분석 보고서가 열립니다.")


if __name__ == "__main__":
    main()
