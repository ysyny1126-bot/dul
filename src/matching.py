"""
매칭 로직 v1
- 1단계: 거르기 (R1~R6, 양방향)
- 2단계: 점수 (유사도 0~1 × 가중치, 합계 100) + 감점
- 3단계: 최종 점수 = sqrt(A→B × B→A), 이유 기록
"""
import json, math
from datetime import date

TODAY = date(2026, 10, 14)

# ---------------------------------------------------------------------------
# 설정값 (가중치는 여기서만 바꾸면 됨)
# ---------------------------------------------------------------------------
# 만남 목적별 기본 가중치 (합계 100). 동네친구는 거리·관심사, 새로운 시작은 결혼관·소비를 더 봄
PURPOSE_WEIGHTS = {
    "friend":  {"interests": 30, "marriage_view": 0,  "contact_style": 12, "distance": 22, "appearance": 0,
                "chronotype": 8, "weekend": 12, "drinking": 6, "spending": 4, "pet": 6},
    "casual":  {"interests": 22, "marriage_view": 8,  "contact_style": 15, "distance": 12, "appearance": 14,
                "chronotype": 6, "weekend": 8, "drinking": 7, "spending": 4, "pet": 4},
    "serious": {"interests": 16, "marriage_view": 22, "contact_style": 15, "distance": 8, "appearance": 8,
                "chronotype": 6, "weekend": 6, "drinking": 6, "spending": 9, "pet": 4},
}
POP_FREE = 3      # 다른 사람 상위 3명에 이 횟수까지는 그대로
POP_DAMP = 0.03   # 넘는 1회마다 점수를 조금씩 낮춤 (인기 쏠림 완화)

WEIGHTS = {
    "interests": 20, "marriage_view": 15, "contact_style": 15, "distance": 10,
    "appearance": 10, "chronotype": 6, "weekend": 6, "drinking": 6,
    "spending": 6, "pet": 6,
}
PENALTY = {1: -5, 2: -10}           # 중요도 1·2 조건 어김
DIST_PENALTY_PER_5KM = -5           # 거리 중요도 1·2인데 최대 거리 넘었을 때
FAV_BONUS = 1.6                     # (예전 최애 보너스) = 중요도 ★★★ 배율
LEVEL_MULT = {1: 0.6, 2: 1.0, 3: 1.6} # 관심사 중요도 ★ / ★★ / ★★★
MAX_TOP_LEVEL = 2                   # ★★★는 최대 2개
CATEGORY_SIM = 0.25                 # 같은 분류(야구↔축구 = 운동)일 때 태그 유사도

CATEGORIES = {
    "운동": ["헬스", "러닝", "요가", "축구", "야구", "농구", "수영", "클라이밍", "자전거", "테니스", "볼링", "골프"],
    "아웃도어·여행": ["등산", "캠핑", "낚시", "여행", "산책", "사진"],
    "음식·술": ["카페", "맛집", "요리", "베이킹", "와인", "맥주"],
    "영화·책·전시": ["영화", "드라마", "넷플릭스", "전시", "미술", "독서", "글쓰기"],
    "음악·공연": ["음악", "기타", "피아노", "힙합", "공연"],
    "게임·덕질": ["게임", "애니", "굿즈", "보드게임", "코딩"],
    "생활": ["고양이", "강아지", "쇼핑"],
}
CAT_OF = {t: c for c, ts in CATEGORIES.items() for t in ts}

# ---------------------------------------------------------------------------
# 취향 좌표 (작은 임베딩): 관심사마다 8개 축의 좌표. 사람 좌표 = Σ(중요도 배율 × 관심사 좌표)
# ---------------------------------------------------------------------------
AXES = ["활동성", "야외", "사교", "문화·감성", "미식", "집콕", "몰입·창작", "새로움"]
TAG_VEC = {
    "헬스": [1, .1, .2, 0, 0, .3, .4, 0], "러닝": [.9, .8, .3, 0, 0, 0, .3, .1], "요가": [.6, .1, .2, .3, 0, .4, .5, 0],
    "축구": [1, .8, .8, 0, 0, 0, .2, 0], "야구": [.4, .6, .8, .1, .4, .2, .1, 0], "농구": [1, .6, .7, 0, 0, .2, .2, 0],
    "수영": [.9, .3, .1, 0, 0, .3, .3, .1], "클라이밍": [.9, .4, .4, 0, 0, .3, .5, .3], "자전거": [.8, .9, .3, 0, 0, 0, .2, .4],
    "테니스": [.9, .7, .6, 0, 0, 0, .3, .1], "볼링": [.5, 0, .8, 0, .2, .4, .1, 0], "골프": [.6, .8, .6, 0, .2, 0, .4, 0],
    "등산": [.8, 1, .3, .1, .1, 0, .2, .4], "캠핑": [.4, 1, .5, .2, .5, 0, .2, .6], "낚시": [.2, .9, .1, .1, .2, 0, .7, .2],
    "여행": [.4, .7, .4, .5, .6, 0, .1, 1], "산책": [.4, .8, .2, .4, .1, 0, .2, .2], "사진": [.2, .7, .2, .8, 0, .1, .7, .6],
    "카페": [0, .2, .5, .6, .7, .3, .2, .3], "맛집": [0, .3, .6, .2, 1, .1, 0, .5], "요리": [0, 0, .3, .3, .9, .9, .6, .2],
    "베이킹": [0, 0, .2, .4, .8, .9, .7, .1], "와인": [0, .1, .6, .6, .9, .3, .2, .4], "맥주": [0, .3, .9, .1, .8, .2, 0, .2],
    "영화": [0, 0, .3, .9, .1, .6, .3, .2], "드라마": [0, 0, .2, .6, .1, 1, .3, 0], "넷플릭스": [0, 0, .1, .6, .1, 1, .3, 0],
    "전시": [.1, .3, .3, 1, .1, 0, .4, .4], "미술": [0, .1, .2, 1, 0, .3, .8, .3], "독서": [0, 0, .1, .8, 0, .8, .8, .2],
    "글쓰기": [0, 0, .1, .8, 0, .7, 1, .1], "음악": [0, 0, .3, .8, 0, .6, .5, .2], "기타": [.1, 0, .3, .7, 0, .6, .9, .1],
    "피아노": [.1, 0, .2, .8, 0, .6, .9, 0], "힙합": [.2, .1, .6, .7, 0, .3, .4, .3], "공연": [.2, .3, .8, .9, .2, 0, .1, .5],
    "게임": [0, 0, .4, .2, 0, 1, .8, .1], "애니": [0, 0, .2, .6, 0, 1, .6, .1], "굿즈": [0, 0, .3, .5, 0, .8, .5, .1],
    "보드게임": [0, 0, .9, .2, .2, .7, .5, .1], "코딩": [0, 0, .1, .1, 0, .9, 1, .2], "고양이": [0, 0, .1, .3, 0, 1, .2, 0],
    "강아지": [.4, .6, .4, .2, 0, .5, .1, 0], "쇼핑": [.2, .3, .5, .3, .3, 0, 0, .4],
}
OVERLAP_SHARE = 0.6        # 관심사 점수 = 0.6 × 태그 겹침 + 0.4 × 좌표 가까움
COS_FLOOR = 0.6            # 코사인 유사도는 0.6~1.0에 몰려서 이 구간을 0~1로 펼침

def person_vec(p):
    v = [0.0] * len(AXES)
    for t in p["interests"]:
        m = LEVEL_MULT[p.get("interest_level", {}).get(t, 2)]
        for i, x in enumerate(TAG_VEC.get(t, [0] * len(AXES))):
            v[i] += m * x
    return v

def cosine(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0

def spread(c):
    return min(1.0, max(0.0, (c - COS_FLOOR) / (1 - COS_FLOOR)))
RARITY_CAP = 2.0                    # 희귀도 상한

ORDINAL = {
    "marriage_view": ["negative", "neutral", "positive"],
    "drinking": ["none", "sometimes", "often"],
    "spending": ["saver", "balanced", "spender"],
}

# 임베딩 대용: "관련 있음(0.70~0.85)" 쌍. 실제 서비스에선 임베딩 유사도로 대체
RELATED = [
    ("등산", "캠핑"), ("러닝", "헬스"), ("요가", "헬스"), ("산책", "러닝"),
    ("카페", "맛집"), ("와인", "맥주"), ("공연", "음악"), ("기타", "음악"),
    ("독서", "글쓰기"), ("전시", "미술"), ("영화", "드라마"), ("애니", "게임"),
    ("여행", "사진"), ("러닝", "축구"),
]
RELATED_SET = {frozenset(p) for p in RELATED}

LABEL = {
    "marriage_view": "결혼관", "contact_style": "연락 스타일", "chronotype": "활동 시간대",
    "weekend": "주말 방식", "drinking": "음주", "spending": "소비 성향", "pet": "반려동물",
    "smoking": "흡연", "religion": "종교",
}

# ---------------------------------------------------------------------------
# 가상 보충 데이터: 외모, 원하는 외모, 최애 태그, 거리 중요도
# ---------------------------------------------------------------------------
SUPPLEMENT = {
    1:  dict(app=("short", "double", False, "casual"),  want={"hair": ["medium", "long"], "eyelid": "any"}, fav="산책", dist_imp=3),
    2:  dict(app=("medium", "single", True, "street"),  want={"hair": ["long"], "style": ["casual", "street"]}, fav="기타", dist_imp=2),
    3:  dict(app=("short", "double", False, "dandy"),   want={"hair": ["long"]}, fav="헬스", dist_imp=3),
    4:  dict(app=("short", "single", False, "casual"),  want={"eyelid": ["double"]}, fav="야구", dist_imp=2),
    5:  dict(app=("medium", "single", True, "minimal"), want={"glasses": [True], "style": ["minimal"]}, fav="독서", dist_imp=2),
    6:  dict(app=("short", "single", False, "casual"),  want={}, fav="캠핑", dist_imp=2),
    7:  dict(app=("medium", "single", True, "casual"),  want={"hair": ["medium", "long"]}, fav="게임", dist_imp=3),
    8:  dict(app=("short", "double", False, "dandy"),   want={"style": ["dandy", "minimal"]}, fav="여행", dist_imp=2),
    9:  dict(app=("short", "double", False, "casual"),  want={}, fav="낚시", dist_imp=3),
    10: dict(app=("short", "double", False, "street"),  want={"hair": ["medium", "long"]}, fav="러닝", dist_imp=2),
    11: dict(app=("medium", "single", False, "minimal"), want={"hair": ["short"], "style": ["casual", "dandy"]}, fav="카페", dist_imp=3),
    12: dict(app=("long", "double", True, "casual"),    want={"glasses": [False]}, fav="고양이", dist_imp=3),
    13: dict(app=("long", "double", False, "minimal"),  want={"hair": ["short"], "eyelid": ["double"]}, fav="요가", dist_imp=3),
    14: dict(app=("medium", "single", False, "street"), want={"style": ["street", "casual"]}, fav="맥주", dist_imp=2),
    15: dict(app=("long", "single", True, "minimal"),   want={"glasses": [True]}, fav="독서", dist_imp=2),
    16: dict(app=("medium", "double", False, "casual"), want={"hair": ["short"]}, fav="등산", dist_imp=2),
    17: dict(app=("medium", "single", True, "casual"),  want={}, fav="애니", dist_imp=3),
    18: dict(app=("long", "double", False, "minimal"),  want={"style": ["dandy"]}, fav="와인", dist_imp=3),
    19: dict(app=("long", "double", False, "casual"),   want={"eyelid": ["double"]}, fav="맛집", dist_imp=2),
    20: dict(app=("long", "single", False, "casual"),   want={"hair": ["short"]}, fav="러닝", dist_imp=2),
}

def load(path="profiles.json"):
    people = json.load(open(path, encoding="utf-8"))
    for p in people:
        s = SUPPLEMENT.get(p["id"])
        if s:   # 처음 20명은 보충 데이터로 외모·최애 등을 채움
            hair, eyelid, glasses, style = s["app"]
            p["appearance"] = {"hair": hair, "eyelid": eyelid, "glasses": glasses, "style": style}
            p["preference"]["appearance"] = s["want"]
            p["favorite_tag"] = s["fav"]
            p["preference"]["distance_importance"] = s["dist_imp"]
            # 관심사 중요도: 최애는 ★★★, 나머지는 ★★
            p["interest_level"] = {t: (3 if t == s["fav"] else 2) for t in p["interests"]}
    return people

# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def age(p):
    y, m, d = map(int, p["birth_date"].split("-"))
    return TODAY.year - y - ((TODAY.month, TODAY.day) < (m, d))

def distance_km(a, b):
    R = 6371.0
    la1, lo1 = math.radians(a["location"]["lat"]), math.radians(a["location"]["lng"])
    la2, lo2 = math.radians(b["location"]["lat"]), math.radians(b["location"]["lng"])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def build_rarity(people):
    """희귀도(IDF): 가장 흔한 태그 = 1.0, 상한 2.0"""
    n = len(people)
    count = {}
    for p in people:
        for t in p["interests"]:
            count[t] = count.get(t, 0) + 1
    idf = {t: math.log(n / c) for t, c in count.items()}
    base = min(idf.values())
    return {t: min(v / base, RARITY_CAP) for t, v in idf.items()}

def tag_sim(t1, t2):
    if t1 == t2:
        return 1.0
    if frozenset((t1, t2)) in RELATED_SET:
        return 0.5
    if CAT_OF.get(t1) and CAT_OF.get(t1) == CAT_OF.get(t2):
        return CATEGORY_SIM
    return 0.0

def ordinal_sim(field, x, y):
    order = ORDINAL[field]
    gap = abs(order.index(x) - order.index(y))
    return {0: 1.0, 1: 0.5}.get(gap, 0.0)

def satisfies(field, actual, wanted):
    """조건 충족 여부. 반려동물은 '키움(has)'도 '좋아함(likes)'을 만족"""
    if field == "pet" and wanted == "likes":
        return actual in ("has", "likes")
    return actual == wanted

def pet_sim(x, y):
    fond = {"has", "likes"}
    if (x in fond and y in fond) or (x == "dislikes" and y == "dislikes"):
        return 1.0
    if "has" in (x, y) and "dislikes" in (x, y):
        return 0.0
    return 0.5

# ---------------------------------------------------------------------------
# 1단계: 거르기 (A 입장에서 B를 볼 때). 통과면 None, 탈락이면 사유
# ---------------------------------------------------------------------------
def filter_one_way(a, b, d):
    pref = a["preference"]
    if not b.get("nickname") or not b.get("photos"):
        return "R1 프로필 미완성"
    if b["gender"] not in pref["gender"]:
        return "R2 성별"
    if not (pref["age_min"] <= age(b) <= pref["age_max"]):
        return f"R3 나이 ({a['nickname']}의 조건 {pref['age_min']}~{pref['age_max']}세, 상대 {age(b)}세)"
    if d > pref["max_distance_km"]:
        if pref["distance_importance"] == 3 or d > pref["max_distance_km"] * 2:
            return f"R4 거리 ({a['nickname']}의 최대 {pref['max_distance_km']}km, 실제 {d:.1f}km)"
    if a["purpose"] != b["purpose"]:
        return f"R5 목적 ({a['purpose']} ≠ {b['purpose']})"
    for field, cond in pref["conditions"].items():
        if cond["importance"] == 3 and not satisfies(field, b.get(field), cond["value"]):
            return f"R6 딜브레이커 ({a['nickname']}: {LABEL.get(field, field)}={cond['value']} 필수)"
    return None

# ---------------------------------------------------------------------------
# 2단계: 점수 (A가 B를 볼 때)
# ---------------------------------------------------------------------------
def score_one_way(a, b, d, rarity):
    W = PURPOSE_WEIGHTS.get(a["purpose"], WEIGHTS)
    reasons = []   # (점수, 설명)
    total = 0.0
    parts = []     # 화면용 항목별 내역: (key, 점수, 설명)

    # 관심사: 희귀도 × 최애 보너스 × 태그 유사도 → 1 - 0.5^k
    k, hits = 0.0, []
    for t in a["interests"]:
        best_tag, best = None, 0.0
        for u in b["interests"]:
            s = tag_sim(t, u)
            if s > best:
                best_tag, best = u, s
        if best > 0:
            bonus = LEVEL_MULT[a.get("interest_level", {}).get(t, 3 if t == a.get("favorite_tag") else 2)]
            k += best * rarity[t] * bonus
            hits.append(t if best == 1.0 else f"{t}≈{best_tag}")
    cos = cosine(person_vec(a), person_vec(b))
    pts = (OVERLAP_SHARE * (1 - 0.5 ** k) + (1 - OVERLAP_SHARE) * spread(cos)) * W["interests"]
    total += pts
    parts.append(("interests", pts, (", ".join(hits) if hits else "겹침 없음") + f" · 좌표 유사도 {cos:.2f}"))
    if hits:
        reasons.append((pts, f"관심사 통함 ({', '.join(hits)})"))

    # 순서형·일치형 항목
    for field in ["marriage_view", "drinking", "spending"]:
        s = ordinal_sim(field, a[field], b[field])
        pts = s * W[field]
        total += pts
        parts.append((field, pts, f"{a[field]} / {b[field]}"))
        if s == 1.0:
            reasons.append((pts, f"{LABEL[field]} 같음"))
    for field in ["contact_style", "chronotype", "weekend"]:
        s = 1.0 if a[field] == b[field] else 0.0
        pts = s * W[field]
        total += pts
        parts.append((field, pts, f"{a[field]} / {b[field]}"))
        if s:
            reasons.append((pts, f"{LABEL[field]} 같음"))

    s = pet_sim(a["pet"], b["pet"])
    total += s * W["pet"]
    parts.append(("pet", s * W["pet"], f"{a['pet']} / {b['pet']}"))

    # 거리
    max_d = min(a["preference"]["max_distance_km"], b["preference"]["max_distance_km"])
    s = max(0.0, 1 - d / max_d)
    pts = s * W["distance"]
    total += pts
    parts.append(("distance", pts, f"{d:.1f}km / 기준 {max_d}km"))
    if s >= 0.5:
        reasons.append((pts, f"가까움 ({d:.1f}km)"))

    # 외모 (A가 원하는 것 vs B의 외모)
    want = a["preference"].get("appearance", {})
    wanted = {k2: v for k2, v in want.items() if v != "any"}
    if wanted:
        matched = [k2 for k2, v in wanted.items() if b["appearance"][k2] in v]
        s = len(matched) / len(wanted)
    else:
        s, matched = 1.0, []
    pts = s * W["appearance"]
    total += pts
    parts.append(("appearance", pts, f"원하는 {len(wanted)}개 중 {len(matched)}개 일치" if wanted else "상관없음"))
    if wanted and s > 0:
        reasons.append((pts, "선호 외모와 일치"))

    # 감점
    penalties = []
    for field, cond in a["preference"]["conditions"].items():
        imp = cond["importance"]
        if imp in PENALTY and not satisfies(field, b.get(field), cond["value"]):
            total += PENALTY[imp]
            penalties.append((PENALTY[imp], f"{LABEL.get(field, field)} 조건 어김"))
    over = d - a["preference"]["max_distance_km"]
    if over > 0:
        p = DIST_PENALTY_PER_5KM * math.ceil(over / 5)
        total += p
        penalties.append((p, f"최대 거리 {over:.1f}km 초과"))

    return max(total, 0.0), reasons, penalties, parts

# ---------------------------------------------------------------------------
# 3단계: 전체 실행
# ---------------------------------------------------------------------------
def run(people):
    rarity = build_rarity(people)
    results = {}
    for a in people:
        recs, rejected = [], []
        for b in people:
            if a["id"] == b["id"]:
                continue
            d = distance_km(a, b)
            why = filter_one_way(a, b, d) or filter_one_way(b, a, d)
            if why:
                if b["gender"] in a["preference"]["gender"]:
                    rejected.append({"id": b["id"], "nickname": b["nickname"], "reason": why})
                continue
            ab, reasons, pen_ab, parts_ab = score_one_way(a, b, d, rarity)
            ba, _, pen_ba, parts_ba = score_one_way(b, a, d, rarity)
            final = math.sqrt(ab * ba)
            Wa = PURPOSE_WEIGHTS.get(a["purpose"], WEIGHTS)
            reasons.sort(key=lambda x: -x[0])
            recs.append({
                "id": b["id"], "nickname": b["nickname"], "age": age(b),
                "region": b["location"]["region"], "distance_km": round(d, 1),
                "score": round(final, 1), "raw": final, "a_to_b": round(ab, 1), "b_to_a": round(ba, 1),
                "top_reasons": [f"{r} (+{p:.0f})" for p, r in reasons[:3]],
                "penalties": [f"{r} ({p})" for p, r in pen_ab],
                "penalties_b": [f"{r} ({p})" for p, r in pen_ba],
                "breakdown": [
                    {"key": k1, "label": LABEL.get(k1, {"interests": "관심사", "distance": "거리", "appearance": "외모"}.get(k1, k1)),
                     "weight": Wa[k1], "a": round(p1, 1), "b": round(p2, 1), "a_note": n1, "b_note": n2}
                    for (k1, p1, n1), (_, p2, n2) in zip(parts_ab, parts_ba)
                ],
            })
        recs.sort(key=lambda r: (-r["raw"], r["distance_km"]))
        results[a["id"]] = {"nickname": a["nickname"], "recommendations": recs, "rejected": rejected}
    # 인기 쏠림 완화: 여러 사람의 상위 3명에 자주 드는 사람은 점수를 조금 낮춤
    pop = {}
    for r in results.values():
        for rec in r["recommendations"][:3]:
            pop[rec["id"]] = pop.get(rec["id"], 0) + 1
    for r in results.values():
        for rec in r["recommendations"]:
            f = 1 / (1 + POP_DAMP * max(0, pop.get(rec["id"], 0) - POP_FREE))
            rec["pop"] = round(f, 3)
            rec["score"] = round(rec["raw"] * f, 1)
            rec["_adj"] = rec["raw"] * f
        r["recommendations"].sort(key=lambda x: (-x["_adj"], x["distance_km"]))
        for rec in r["recommendations"]:
            del rec["_adj"]; del rec["raw"]
    return results, rarity

if __name__ == "__main__":
    people = load()
    results, rarity = run(people)
    json.dump(results, open("match_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("== 희귀도 ==")
    print(", ".join(f"{t}:{v:.2f}" for t, v in sorted(rarity.items(), key=lambda x: x[1])))
    for pid, r in results.items():
        print(f"\n## {pid}번 {r['nickname']}  (후보 {len(r['recommendations'])}명)")
        for i, rec in enumerate(r["recommendations"], 1):
            print(f"  {i}위 {rec['id']}번 {rec['nickname']} {rec['score']}점 "
                  f"[A→B {rec['a_to_b']} / B→A {rec['b_to_a']}] {rec['distance_km']}km")
            print(f"      이유: {' / '.join(rec['top_reasons'])}")
            if rec["penalties"]:
                print(f"      감점: {' / '.join(rec['penalties'])}")
        for rj in r["rejected"]:
            print(f"  ✕ {rj['id']}번 {rj['nickname']}: {rj['reason']}")
