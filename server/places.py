"""외부 장소 정보 (데이트 플래너용). .env 의 PLACES_PROVIDER 로 kakao / google / none 선택.

- kakao: 카카오 로컬 키워드 검색. 국내 장소가 정확하지만 영업시간은 주지 않아서 장소 링크로 안내
- google: Google Places (New) 텍스트 검색. 영업시간까지 받아옴
- none: 장소 검색 없이 LLM이 장소 종류만 정하고, 지도 검색 링크를 붙임
"""
import math
import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY", "")
GOOGLE_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
PROVIDER = os.getenv("PLACES_PROVIDER", "").lower() or ("kakao" if KAKAO_KEY else "google" if GOOGLE_KEY else "none")

WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def search(keyword: str, lat: float, lng: float, radius_m: int = 2500, size: int = 4) -> list[dict]:
    """중간 지점 근처에서 키워드로 장소 찾기. 실패하면 빈 목록 (코스는 장소 없이도 만들 수 있게)."""
    try:
        if PROVIDER == "kakao" and KAKAO_KEY:
            return _kakao(keyword, lat, lng, radius_m, size)
        if PROVIDER == "google" and GOOGLE_KEY:
            return _google(keyword, lat, lng, radius_m, size)
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"[places] '{keyword}' 검색 실패: {e}")
    return []


def _kakao(keyword, lat, lng, radius_m, size):
    r = requests.get(
        "https://dapi.kakao.com/v2/local/search/keyword.json",
        params={"query": keyword, "x": lng, "y": lat, "radius": min(radius_m, 20000), "size": size, "sort": "accuracy"},
        headers={"Authorization": f"KakaoAK {KAKAO_KEY}"},
        timeout=8,
    )
    r.raise_for_status()
    return [{
        "name": d["place_name"],
        "category": d.get("category_name", "").split(" > ")[-1],
        "address": d.get("road_address_name") or d.get("address_name", ""),
        "lat": float(d["y"]), "lng": float(d["x"]),
        "url": d.get("place_url", ""),
        "phone": d.get("phone", ""),
        "hours": [],   # 카카오 로컬 API는 영업시간을 주지 않음 → 장소 페이지(url)에서 확인
    } for d in r.json().get("documents", [])]


def _google(keyword, lat, lng, radius_m, size):
    r = requests.post(
        "https://places.googleapis.com/v1/places:searchText",
        json={
            "textQuery": keyword, "languageCode": "ko", "regionCode": "KR", "maxResultCount": size,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(min(radius_m, 50000))}},
        },
        headers={
            "X-Goog-Api-Key": GOOGLE_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.googleMapsUri,"
                                "places.primaryTypeDisplayName,places.nationalPhoneNumber,places.regularOpeningHours.weekdayDescriptions",
        },
        timeout=8,
    )
    r.raise_for_status()
    return [{
        "name": p["displayName"]["text"],
        "category": p.get("primaryTypeDisplayName", {}).get("text", ""),
        "address": p.get("formattedAddress", "").replace("대한민국 ", ""),
        "lat": p["location"]["latitude"], "lng": p["location"]["longitude"],
        "url": p.get("googleMapsUri", ""),
        "phone": p.get("nationalPhoneNumber", ""),
        "hours": p.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
    } for p in r.json().get("places", [])]


def hours_on(place: dict, weekday: int | None) -> str:
    """그 요일 영업시간 한 줄 (구글은 '월요일: 오전 11:00~오후 10:00' 모양). 모르면 빈 문자열."""
    hours = place.get("hours") or []
    if weekday is None or not hours:
        return ""
    day = WEEKDAYS[weekday]
    line = next((h for h in hours if h.startswith(day)), "")
    return line.split(":", 1)[1].strip() if ":" in line else line


def dist_km(a: dict, b: dict) -> float:
    """두 좌표 사이 직선거리 (하버사인)."""
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lng"], b["lat"], b["lng"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def leg(a: dict, b: dict) -> dict:
    """이동 예상: 실제 길은 직선보다 30% 정도 길다고 보고, 1.5km까지는 걷고 그보다 멀면 대중교통."""
    km = dist_km(a, b) * 1.3
    if km <= 1.5:
        mode, minutes = "도보", km / 4.5 * 60
    else:
        mode, minutes = "대중교통", km / 20 * 60 + 10
    return {"mode": mode, "min": max(1, round(minutes)), "km": round(km, 1), "url": route_link(a, b)}


def route_link(a: dict, b: dict) -> str:
    if PROVIDER == "google":
        return (f"https://www.google.com/maps/dir/?api=1&origin={a['lat']},{a['lng']}"
                f"&destination={b['lat']},{b['lng']}&travelmode=transit")
    return (f"https://map.kakao.com/link/from/{quote(a['name'])},{a['lat']},{a['lng']}"
            f"/to/{quote(b['name'])},{b['lat']},{b['lng']}")


def search_link(area: str, query: str) -> str:
    q = query if area and area in query else f"{area} {query}"   # LLM이 지역명을 이미 넣었으면 또 붙이지 않음
    return "https://map.naver.com/p/search/" + quote(q.strip())
