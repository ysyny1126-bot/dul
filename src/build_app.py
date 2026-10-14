"""앱 페이지 생성: 엔진 + 화면 + 가상 프로필 20명 데이터"""
import json
from matching import load, run, age, WEIGHTS, PENALTY, DIST_PENALTY_PER_5KM, FAV_BONUS, RARITY_CAP, RELATED, CATEGORIES, CATEGORY_SIM, LEVEL_MULT, MAX_TOP_LEVEL, AXES, TAG_VEC, OVERLAP_SHARE, COS_FLOOR

import sys
SRC = sys.argv[1] if len(sys.argv) > 1 else "profiles_500.json"
people = load(SRC)
results, _ = run(people)
profiles = []
for p in people:
    profiles.append({
        "id": str(p["id"]), "login_id": f"user{p['id']:03d}", "nickname": p["nickname"], "gender": p["gender"],
        "birth_date": p["birth_date"], "age": age(p),
        "region": p["location"]["region"], "lat": p["location"]["lat"], "lng": p["location"]["lng"],
        "has_photo": True, "searchable": p.get("searchable", p["id"] not in (3, 12, 18)), "job": p["job"], "height": p["height"], "bio": p["bio"],
        "interests": p["interests"], "favorite_tag": p["favorite_tag"], "interest_level": p["interest_level"], "mbti": p["mbti"],
        "smoking": p["smoking"], "drinking": p["drinking"], "religion": p["religion"],
        "chronotype": p["chronotype"], "contact_style": p["contact_style"], "weekend": p["weekend"],
        "pet": p["pet"], "purpose": p["purpose"], "marriage_view": p["marriage_view"],
        "spending": p["spending"], "appearance": p["appearance"], "preference": p["preference"],
    })
cfg = {"weights": WEIGHTS, "penalty": PENALTY, "dist_penalty": DIST_PENALTY_PER_5KM,
       "fav_bonus": FAV_BONUS, "rarity_cap": RARITY_CAP, "related": RELATED,
       "categories": CATEGORIES, "category_sim": CATEGORY_SIM,
       "level_mult": {str(k): v for k, v in LEVEL_MULT.items()}, "max_top_level": MAX_TOP_LEVEL,
       "axes": AXES, "tag_vec": TAG_VEC, "overlap_share": OVERLAP_SHARE, "cos_floor": COS_FLOOR, "auto_top_n": 3}
data = {"profiles": profiles, "cfg": cfg}
json.dump({"data": data, "py": results}, open("app_data.json", "w", encoding="utf-8"), ensure_ascii=False)

import os
if os.path.exists("app_template.html"):
    tpl = open("app_template.html", encoding="utf-8").read()
    eng = open("app_engine.js", encoding="utf-8").read()
    out = tpl.replace("/*__ENGINE__*/", eng).replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    open("gyeol_app.html", "w", encoding="utf-8").write(out)
    print("built gyeol_app.html", len(out))
