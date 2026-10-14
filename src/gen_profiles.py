"""가상 회원 480명 생성 → 기존 20명과 합쳐 profiles_500.json (항상 같은 결과가 나오게 시드 고정)"""
import json, random
from matching import load, CATEGORIES

random.seed(20261014)

REGIONS = [
    ("서울 강서구", 37.5509, 126.8495, 5), ("서울 양천구", 37.5170, 126.8665, 4), ("서울 마포구", 37.5663, 126.9019, 7),
    ("서울 영등포구", 37.5264, 126.8963, 5), ("서울 서대문구", 37.5791, 126.9368, 4), ("서울 은평구", 37.6027, 126.9291, 4),
    ("서울 종로구", 37.5735, 126.9790, 3), ("서울 용산구", 37.5326, 126.9905, 4), ("서울 동작구", 37.5124, 126.9393, 4),
    ("서울 관악구", 37.4784, 126.9516, 6), ("서울 성동구", 37.5634, 127.0369, 4), ("서울 광진구", 37.5385, 127.0823, 5),
    ("서울 강남구", 37.5172, 127.0473, 7), ("서울 송파구", 37.5145, 127.1059, 6), ("서울 노원구", 37.6542, 127.0568, 4),
    ("경기 고양시", 37.6584, 126.8320, 4), ("경기 성남시 분당구", 37.3826, 127.1189, 4), ("경기 수원시", 37.2636, 127.0286, 4),
    ("인천 연수구", 37.4100, 126.6783, 3),
]
# 성향(페르소나)별로 관심사와 생활 패턴을 묶어서, 그럴듯한 사람이 나오게
PERSONAS = {
    "운동파":   dict(tags=["헬스", "러닝", "요가", "축구", "야구", "농구", "수영", "클라이밍", "자전거", "테니스", "볼링", "골프"], chrono=.7, out=.85, drink=[.3, .5, .2], extra=["맛집", "등산", "여행"]),
    "아웃도어": dict(tags=["등산", "캠핑", "낚시", "여행", "산책", "사진"], chrono=.65, out=.9, drink=[.2, .6, .2], extra=["자전거", "러닝", "맛집", "강아지"]),
    "미식가":   dict(tags=["카페", "맛집", "요리", "베이킹", "와인", "맥주"], chrono=.35, out=.75, drink=[.1, .5, .4], extra=["여행", "사진", "쇼핑", "전시"]),
    "문화인":   dict(tags=["영화", "드라마", "넷플릭스", "전시", "미술", "독서", "글쓰기"], chrono=.45, out=.45, drink=[.35, .5, .15], extra=["카페", "공연", "음악", "산책"]),
    "음악인":   dict(tags=["음악", "기타", "피아노", "힙합", "공연"], chrono=.25, out=.55, drink=[.2, .5, .3], extra=["카페", "영화", "맥주"]),
    "집순집돌": dict(tags=["게임", "애니", "굿즈", "보드게임", "코딩", "넷플릭스", "드라마"], chrono=.15, out=.15, drink=[.45, .45, .1], extra=["고양이", "요리", "음악"]),
    "반려인":   dict(tags=["고양이", "강아지", "산책"], chrono=.55, out=.5, drink=[.35, .5, .15], extra=["카페", "사진", "드라마", "베이킹"]),
}
PERSONA_W = [16, 12, 16, 16, 9, 16, 8]
FIRST = ["말랑", "포근", "반짝", "느긋", "새벽", "노을", "봄날", "바람", "몽글", "푸른", "달빛", "햇살", "보송", "산뜻", "조용", "씩씩", "다정", "엉뚱",
         "소소", "느릿", "또롱", "코코", "단단", "살랑", "초코", "딸기", "레몬", "우유", "호두", "구름", "별빛", "꿀잠", "주말", "퇴근", "동네", "골목"]
SECOND = {"운동파": ["러너", "헬린이", "슈터", "스윙", "스매시", "덩크"], "아웃도어": ["산악인", "캠퍼", "여행자", "산책러", "찍사"],
          "미식가": ["미식가", "카페인", "빵순이", "와인잔", "맥주잔", "요리사"], "문화인": ["책갈피", "관객", "필름", "독서가", "전시회"],
          "음악인": ["기타맨", "플레이리스트", "건반", "리스너", "래퍼"], "집순집돌": ["게이머", "덕후", "집순이", "집돌이", "코더"],
          "반려인": ["집사", "댕댕맘", "냥냥", "멍멍", "산책꾼"]}
JOBS = ["회사원", "대학생", "대학원생", "개발자", "디자이너", "간호사", "교사", "공무원", "마케터", "회계사", "연구원", "프리랜서", "자영업", "PD", "기획자", "영업직", "약사", "사무직", "엔지니어", "바리스타"]
BIOS = {"운동파": ["운동 같이 할 사람 찾아요.", "주말엔 무조건 땀 흘려요.", "건강한 습관 공유해요."],
        "아웃도어": ["주말마다 밖으로 나가요.", "좋은 풍경 보러 다니는 게 취미.", "같이 걸을 사람 구해요."],
        "미식가": ["맛있는 거 먹으러 다녀요.", "새로 생긴 가게는 꼭 가봐요.", "집에서 요리하는 것도 좋아해요."],
        "문화인": ["영화 끝나고 이야기 나누는 걸 좋아해요.", "전시 같이 볼 사람.", "책 추천 주고받아요."],
        "음악인": ["공연장에서 자주 만나요.", "플레이리스트 공유해요.", "악기 연습하는 중이에요."],
        "집순집돌": ["집이 제일 좋아요.", "같이 게임하실 분.", "주말엔 정주행이죠."],
        "반려인": ["반려동물이랑 살아요.", "산책 메이트 구해요.", "동물 좋아하는 분이면 좋겠어요."]}
OPP = {"M": "F", "F": "M"}

def pick(weights_by_value):
    vals, ws = zip(*weights_by_value)
    return random.choices(vals, ws)[0]

def make(pid, used_names):
    persona = random.choices(list(PERSONAS), PERSONA_W)[0]
    P = PERSONAS[persona]
    gender = random.choice("MF")
    age = max(20, min(39, int(random.gauss(28, 4))))
    birth = f"{2026 - age - (1 if random.random() < .6 else 0)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
    reg = random.choices(REGIONS, [r[3] for r in REGIONS])[0]
    lat, lng = reg[1] + random.uniform(-.012, .012), reg[2] + random.uniform(-.012, .012)
    n = random.choices([2, 3, 4, 5], [15, 40, 30, 15])[0]
    main = random.sample(P["tags"], min(len(P["tags"]), max(1, n - random.randint(0, 2))))
    pool = [t for t in P["extra"] + random.sample([t for ts in CATEGORIES.values() for t in ts], 6) if t not in main]
    interests = (main + random.sample(pool, max(0, n - len(main))))[:n]
    tops = random.sample(interests, random.choice([1, 1, 2]))
    level = {t: (3 if t in tops else random.choices([2, 1], [75, 25])[0]) for t in interests}
    fav = tops[0]
    while True:
        name = random.choice(FIRST) + random.choice(SECOND[persona])
        if name not in used_names:
            used_names.add(name); break
        if random.random() < .3:
            name += str(random.randint(1, 99))
            if name not in used_names:
                used_names.add(name); break
    want = "both" if random.random() < .03 else ("same" if random.random() < .04 else "other")
    pref_gender = [OPP[gender]] if want == "other" else ([gender] if want == "same" else ["M", "F"])
    lo, hi = max(20, age - random.randint(2, 6)), min(45, age + random.randint(2, 7))
    if age not in range(lo, hi + 1): lo, hi = min(lo, age), max(hi, age)
    conditions = {}
    smoking = pick([("no", 78), ("sometimes", 12), ("yes", 10)])
    if random.random() < .35: conditions["smoking"] = {"value": "no", "importance": random.choice([2, 3, 3])}
    religion = pick([("none", 65), ("christian", 17), ("catholic", 9), ("buddhist", 9)])
    if religion != "none" and random.random() < .3: conditions["religion"] = {"value": religion, "importance": random.choice([1, 2, 3])}
    pet = pick([("has", 18), ("likes", 62), ("dislikes", 20)]) if persona != "반려인" else "has"
    if pet in ("has", "likes") and random.random() < .15: conditions["pet"] = {"value": "likes", "importance": random.choice([2, 3])}
    drinking = random.choices(["none", "sometimes", "often"], P["drink"])[0]
    if random.random() < .12: conditions["drinking"] = {"value": drinking, "importance": random.choice([1, 2])}
    app_pref = {}
    if random.random() < .45: app_pref["hair"] = random.sample(["short", "medium", "long"], random.choice([1, 2]))
    if random.random() < .3: app_pref["style"] = random.sample(["casual", "dandy", "street", "minimal"], random.choice([1, 2]))
    if random.random() < .15: app_pref["eyelid"] = [random.choice(["double", "single"])]
    return {
        "id": pid, "nickname": name, "photos": [f"https://picsum.photos/seed/u{pid:03d}/400/500"],
        "gender": gender, "birth_date": birth,
        "location": {"region": reg[0], "lat": round(lat, 4), "lng": round(lng, 4)},
        "job": random.choice(JOBS) if age > 23 or random.random() < .5 else "대학생",
        "height": int(random.gauss(176 if gender == "M" else 163, 5)),
        "bio": random.choice(BIOS[persona]), "interests": interests, "mbti": "".join(random.choice(p) for p in ["EI", "NS", "TF", "JP"]),
        "smoking": smoking, "drinking": drinking, "religion": religion,
        "chronotype": "morning" if random.random() < P["chrono"] else "night",
        "contact_style": pick([("frequent", 55), ("occasional", 45)]),
        "weekend": "out" if random.random() < P["out"] else "home", "pet": pet,
        "purpose": pick([("friend", 25), ("casual", 35), ("serious", 40)]),
        "marriage_view": pick([("positive", 45), ("neutral", 40), ("negative", 15)]),
        "spending": pick([("saver", 35), ("balanced", 45), ("spender", 20)]),
        "preference": {"gender": pref_gender, "age_min": lo, "age_max": hi,
                       "max_distance_km": random.choice([5, 10, 10, 15, 15, 20, 20, 30, 40]),
                       "distance_importance": random.choices([1, 2, 3], [20, 50, 30])[0],
                       "conditions": conditions, "appearance": app_pref},
        "appearance": {"hair": random.choice(["short", "medium", "long"]) if gender == "F" else random.choices(["short", "medium", "long"], [70, 25, 5])[0],
                       "eyelid": random.choice(["double", "single"]), "glasses": random.random() < .3,
                       "style": random.choice(["casual", "dandy", "street", "minimal"])},
        "favorite_tag": fav, "interest_level": level, "searchable": random.random() < .8, "persona": persona,
    }

base = json.load(open("profiles.json", encoding="utf-8"))
used = {p["nickname"] for p in base}
gen = [make(i, used) for i in range(21, 501)]
json.dump(base + gen, open("profiles_500.json", "w", encoding="utf-8"), ensure_ascii=False)

from collections import Counter
print("총", len(base) + len(gen), "명 | 성별", Counter(p["gender"] for p in gen), "| 목적", Counter(p["purpose"] for p in gen))
print("성향", Counter(p["persona"] for p in gen))
print("지역 상위", Counter(p["location"]["region"] for p in gen).most_common(5))
print("예시:", [(p["nickname"], p["interests"], p["purpose"]) for p in gen[:3]])
