#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수집된 리뷰를 분석해 불만/칭찬 포인트 보고서(HTML)를 만들어 브라우저로 연다.

사용법: python analyze.py   (data/ 안의 가장 최근 reviews-*.json 을 자동 사용)
"""
import glob
import html
import json
import os
import sys
import webbrowser
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
REPORT = os.path.join(HERE, "report.html")

# 관점(aspect)별 감지 단어 — 에코백 주문제작 업종 맞춤
ASPECTS = {
    "인쇄 품질": ["인쇄", "프린트", "프린팅", "로고", "번짐", "번져", "흐릿", "비뚤", "잉크", "틀어", "선명"],
    "원단/재질": ["원단", "재질", "천이", "두께", "얇", "두껍", "소재", "캔버스", "광목", "빳빳", "하늘하늘"],
    "배송/납기": ["배송", "늦", "지연", "납기", "도착", "택배", "빨리", "느리", "당일", "일정"],
    "색상": ["색상", "색감", "컬러", "색이", "색깔", "누런", "누렇"],
    "마감/봉제": ["마감", "실밥", "박음질", "봉제", "뜯어", "터짐", "올이", "바느질"],
    "냄새": ["냄새", "꼬린", "화학", "쿰쿰"],
    "사이즈": ["사이즈", "크기", "커요", "작아", "작네", "크네", "생각보다 크", "생각보다 작"],
    "끈/손잡이": ["끈이", "끈은", "손잡이", "어깨", "스트랩"],
    "포장": ["포장", "구김", "구겨", "접힌", "접혀"],
    "가격/가성비": ["가격", "가성비", "비싸", "저렴", "싸게", "값"],
    "응대/시안": ["문의", "응대", "상담", "답변", "시안", "수정", "친절", "소통", "카톡"],
}
NEG_CUES = ["아쉬", "별로", "불만", "실망", "그냥", "흠", "안좋", "안 좋", "최악", "다신", "다시는", "환불", "교환"]


def is_complaint(review):
    s = review.get("score")
    if s is not None and s <= 3:
        return True
    text = review.get("text", "")
    if s == 4 and any(c in text for c in NEG_CUES):
        return True
    return False


def find_aspects(text):
    hits = []
    for aspect, words in ASPECTS.items():
        if any(w in text for w in words):
            hits.append(aspect)
    return hits


def snippet(text, limit=90):
    t = text.strip()
    return t[:limit] + ("…" if len(t) > limit else "")


def analyze_store(store):
    reviews = [r for r in store["reviews"] if r.get("text")]
    total = len(reviews)
    complaints = [r for r in reviews if is_complaint(r)]
    scores = [r["score"] for r in reviews if r.get("score")]
    avg = round(sum(scores) / len(scores), 2) if scores else None

    aspect_complaints = Counter()
    aspect_examples = {}
    for r in complaints:
        for a in find_aspects(r["text"]):
            aspect_complaints[a] += 1
            aspect_examples.setdefault(a, [])
            if len(aspect_examples[a]) < 3:
                aspect_examples[a].append(snippet(r["text"]))

    praise = Counter()
    for r in reviews:
        if r.get("score") == 5:
            for a in find_aspects(r["text"]):
                praise[a] += 1

    return {
        "label": store["label"],
        "mall": store["mall"],
        "total": total,
        "avg": avg,
        "complaint_count": len(complaints),
        "complaint_rate": round(len(complaints) / total * 100, 1) if total else 0,
        "aspect_complaints": aspect_complaints,
        "aspect_examples": aspect_examples,
        "praise": praise,
    }


def build_report(stores):
    own = [s for s in stores if s["label"] == "자사"]
    rivals = [s for s in stores if s["label"] != "자사"]

    # 공격 포인트: 경쟁사 전체에서 불만 많은 관점 순위
    rival_total = Counter()
    for s in rivals:
        rival_total.update(s["aspect_complaints"])
    own_aspects = own[0]["aspect_complaints"] if own else Counter()

    css = """
    body{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#f6f7f9;color:#1c2330;margin:0;padding:24px;max-width:1100px;margin:auto}
    h1{font-size:22px}h2{font-size:16px;margin-top:32px}
    table{width:100%;border-collapse:collapse;font-size:13px;background:#fff;border-radius:8px}
    th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #e3e6ec;vertical-align:top}
    th{background:#eef0f4;font-size:12px}
    .bar{display:inline-block;height:10px;background:#c0392b;border-radius:3px;vertical-align:middle;margin-right:6px}
    .good{color:#0a7d4f;font-weight:600}.bad{color:#c0392b;font-weight:600}
    .ex{color:#5b6472;font-size:12px}
    .attack{background:#fff8e6;border:1px solid #e8d9a0;border-radius:10px;padding:14px 18px;margin:10px 0}
    .num{text-align:right}
    """
    p = [f"<meta charset='utf-8'><title>리뷰 마이닝 보고서</title><style>{css}</style>"]
    p.append(f"<h1>리뷰 마이닝 보고서 <small style='color:#5b6472;font-size:13px'>({date.today().isoformat()})</small></h1>")

    # 스토어 요약
    p.append("<h2>1. 스토어별 요약</h2><table><tr><th>구분</th><th>스토어</th><th class='num'>분석 리뷰</th><th class='num'>평균 별점</th><th class='num'>불만 리뷰 비율</th><th>불만 TOP3 관점</th></tr>")
    for s in sorted(stores, key=lambda x: (x["label"] != "자사", x["complaint_rate"])):
        top3 = ", ".join(f"{a}({n})" for a, n in s["aspect_complaints"].most_common(3)) or "-"
        p.append(
            f"<tr><td>{s['label']}</td><td><b>{html.escape(s['mall'])}</b></td>"
            f"<td class='num'>{s['total']}</td><td class='num'>{s['avg'] or '-'}</td>"
            f"<td class='num'>{s['complaint_rate']}%</td><td>{top3}</td></tr>"
        )
    p.append("</table>")

    # 공격 포인트
    p.append("<h2>2. 우리 상세페이지에 쓸 '공격 포인트'</h2>")
    p.append("<p style='font-size:13px;color:#5b6472'>경쟁사 리뷰에서 불만이 많은데 우리는 불만이 적은(또는 없는) 관점 — 상세페이지·광고 카피에서 강조할 순서입니다.</p>")
    maxn = max(rival_total.values()) if rival_total else 1
    for aspect, n in rival_total.most_common(8):
        ours = own_aspects.get(aspect, 0)
        advantage = "✅ 우리가 유리" if (own and ours * 3 < n / max(len(rivals), 1)) else ("⚠️ 우리도 불만 있음" if ours else "")
        examples = []
        for s in rivals:
            for ex in s["aspect_examples"].get(aspect, [])[:1]:
                examples.append(f"<div class='ex'>· [{html.escape(s['mall'])}] \"{html.escape(ex)}\"</div>")
        w = int(n / maxn * 260)
        p.append(
            f"<div class='attack'><b>{aspect}</b> — 경쟁사 불만 {n}건 "
            f"<span class='bar' style='width:{w}px'></span> {advantage}"
            + "".join(examples[:3]) + "</div>"
        )

    # 스토어별 상세
    p.append("<h2>3. 스토어별 불만 상세</h2>")
    for s in stores:
        p.append(f"<h3 style='font-size:14px'>[{s['label']}] {html.escape(s['mall'])} — 불만 {s['complaint_count']}건 / {s['total']}건</h3>")
        if not s["aspect_complaints"]:
            p.append("<p class='ex'>관점별 불만이 감지되지 않았습니다.</p>")
            continue
        p.append("<table><tr><th>관점</th><th class='num'>불만 수</th><th class='num'>칭찬 수(5점)</th><th>불만 리뷰 예시</th></tr>")
        for aspect, n in s["aspect_complaints"].most_common():
            exs = "<br>".join(f"\"{html.escape(e)}\"" for e in s["aspect_examples"].get(aspect, []))
            p.append(f"<tr><td>{aspect}</td><td class='num bad'>{n}</td><td class='num good'>{s['praise'].get(aspect, 0)}</td><td class='ex'>{exs}</td></tr>")
        p.append("</table>")

    p.append("<p style='color:#5b6472;font-size:12px;margin-top:30px'>주의: 단어 기반 자동 분석이라 오분류가 있을 수 있습니다. 인용 전 원문 확인을 권장합니다.</p>")
    return "".join(p)


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "reviews-*.json")))
    if not files:
        sys.exit("data/ 폴더에 리뷰 파일이 없습니다. 먼저 collect_reviews.py를 실행하세요.")
    latest = files[-1]
    print(f"분석 대상: {latest}")
    with open(latest, encoding="utf-8") as f:
        collected = json.load(f)

    stores = [analyze_store(s) for s in collected.values()]
    report_html = build_report(stores)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report_html)
    print(f"보고서 생성 완료: {REPORT}")
    webbrowser.open("file://" + REPORT.replace(os.sep, "/"))


if __name__ == "__main__":
    main()
