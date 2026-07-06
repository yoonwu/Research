#!/usr/bin/env python3
"""네이버 쇼핑 검색 API로 키워드별 상위 상품을 수집해 일별 스냅샷으로 저장한다.

사용법:
  NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수 설정 후:
    python monitor/crawl.py
  API 키 없이 대시보드 확인용 샘플 데이터 생성:
    python monitor/crawl.py --mock [일수]

저장 위치:
  docs/data/snapshots/YYYY-MM-DD.json  (하루 1개)
  docs/data/index.json                 (날짜 목록)
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYWORDS_FILE = os.path.join(ROOT, "monitor", "keywords.json")
DATA_DIR = os.path.join(ROOT, "docs", "data")
SNAP_DIR = os.path.join(DATA_DIR, "snapshots")

API_URL = "https://openapi.naver.com/v1/search/shop.json"
KST = timezone(timedelta(hours=9))


def load_keywords():
    with open(KEYWORDS_FILE, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["keywords"], int(cfg.get("display", 100))


def strip_tags(s):
    return s.replace("<b>", "").replace("</b>", "")


def fetch_keyword(keyword, client_id, client_secret, display):
    params = urllib.parse.urlencode(
        {"query": keyword, "display": display, "sort": "sim"}
    )
    req = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    items = []
    for rank, it in enumerate(body.get("items", []), 1):
        items.append(
            {
                "rank": rank,
                "title": strip_tags(it.get("title", "")),
                "mall": it.get("mallName", ""),
                "price": int(it.get("lprice") or 0),
                "productId": str(it.get("productId", "")),
                "link": it.get("link", ""),
            }
        )
    return items


def mock_items(keyword, day_offset, display):
    """대시보드 확인용 가짜 데이터. 업체별 순위가 날마다 조금씩 움직이는 형태."""
    rng = random.Random(hash(keyword) & 0xFFFF)
    malls = [f"업체{chr(65 + i)}" for i in range(15)]
    base = {m: rng.uniform(1, 60) for m in malls}
    drift = {m: rng.uniform(-1.5, 1.5) for m in malls}
    rows = []
    for m in malls:
        pos = base[m] + drift[m] * day_offset + rng.uniform(-3, 3)
        for j in range(rng.randint(1, 4)):
            rows.append(
                {
                    "mall": m,
                    "score": pos + j * rng.uniform(2, 10),
                    "price": int(rng.uniform(3000, 15000) // 100 * 100),
                    "pid": f"{m}-{j}",
                }
            )
    rows.sort(key=lambda r: r["score"])
    items = []
    for rank, r in enumerate(rows[:display], 1):
        items.append(
            {
                "rank": rank,
                "title": f"{keyword} 샘플상품 {r['pid']}",
                "mall": r["mall"],
                "price": r["price"],
                "productId": f"mock-{keyword}-{r['pid']}",
                "link": "#",
            }
        )
    return items


def write_snapshot(date_str, snapshot):
    os.makedirs(SNAP_DIR, exist_ok=True)
    path = os.path.join(SNAP_DIR, f"{date_str}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))
    index_path = os.path.join(DATA_DIR, "index.json")
    dates = sorted(
        fn[:-5] for fn in os.listdir(SNAP_DIR) if fn.endswith(".json")
    )
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"dates": dates}, f, ensure_ascii=False)
    print(f"saved {path} ({len(snapshot['keywords'])} keywords)")


def main():
    keywords, display = load_keywords()

    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        today = datetime.now(KST).date()
        for offset in range(days - 1, -1, -1):
            date_str = (today - timedelta(days=offset)).isoformat()
            snap = {
                "date": date_str,
                "mock": True,
                "keywords": {
                    kw: mock_items(kw, days - 1 - offset, display)
                    for kw in keywords
                },
            }
            write_snapshot(date_str, snap)
        return

    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 필요합니다. "
            "(developers.naver.com 에서 '검색' API 애플리케이션 등록 후 발급)"
        )

    date_str = datetime.now(KST).date().isoformat()
    result = {}
    for kw in keywords:
        try:
            result[kw] = fetch_keyword(kw, client_id, client_secret, display)
        except Exception as e:  # 한 키워드 실패가 전체를 막지 않도록
            print(f"[warn] '{kw}' 수집 실패: {e}", file=sys.stderr)
            result[kw] = []
        time.sleep(0.3)  # API 예의상 간격

    if not any(result.values()):
        sys.exit("모든 키워드 수집에 실패했습니다. API 키/한도를 확인하세요.")

    write_snapshot(date_str, {"date": date_str, "mock": False, "keywords": result})


if __name__ == "__main__":
    main()
