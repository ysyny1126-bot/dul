"""Firebase Hosting 배포 폴더 만들기: deploy/dul/"""
import os, re, shutil, subprocess

# 실제 서비스용: 가상 회원 없이, 가입한 사람끼리만
subprocess.run(["python3", "build_app.py", "--real"], check=True)
app = open("dul_real.html", encoding="utf-8").read()
# 아티팩트 전용 줄(제목, 메타) 빼고 본문만
app = re.sub(r"^<title>.*?</title>\n", "", app)
app = re.sub(r'^<meta name="claude:viewport-fit-sides"[^>]*>\n', "", app)

FB_VER = "10.12.2"
head = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>둘 - 동네친구, 데이트, 새로운 시작</title>
<meta name="description" content="둘 - 동네친구, 데이트, 새로운 시작. 취향이 가까운 사람을 찾아주는 매칭 앱">
<meta name="theme-color" content="#FDE6EE">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z' fill='%23FF6F9C'/%3E%3C/svg%3E">
<style>
:root {{ padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }}
body {{ margin: 0; }}
img {{ max-width: 100%; }}
[hidden] {{ display: none !important; }}
</style>
<!-- Firebase Hosting이 자동으로 넣어주는 SDK와 설정 (API 키를 직접 붙여넣을 필요 없음) -->
<script src="/__/firebase/{FB_VER}/firebase-app-compat.js"></script>
<script src="/__/firebase/{FB_VER}/firebase-auth-compat.js"></script>
<script src="/__/firebase/{FB_VER}/firebase-firestore-compat.js"></script>
<script src="/__/firebase/init.js"></script>
</head>
<body>
'''
import sys
out_dir = sys.argv[1] if len(sys.argv) > 1 else "deploy/dul"
if os.path.exists(out_dir + "/public"):
    shutil.rmtree(out_dir + "/public")   # 빌드 결과(public)만 새로 만듦
os.makedirs(out_dir + "/public")
open(out_dir + "/public/index.html", "w", encoding="utf-8").write(head + app + "\n</body>\n</html>\n")

open(out_dir + "/firebase.json", "w", encoding="utf-8").write('''{
  "hosting": {
    "public": "public",
    "ignore": ["firebase.json", "**/.*"],
    "headers": [
      { "source": "**/*.html", "headers": [{ "key": "Cache-Control", "value": "no-cache" }] }
    ]
  },
  "firestore": {
    "rules": "firestore.rules"
  }
}
''')

open(out_dir + "/firestore.rules", "w", encoding="utf-8").write('''rules_version = '2';
// 둘 보안 규칙 (실제 회원용)
// - 가입한 회원만 다른 회원의 프로필을 볼 수 있어요 (추천 계산에 필요).
// - 프로필은 본인만 만들고 고치고 지울 수 있어요.
// - 좋아요·마음 표현·차단은 주고받은 두 사람만, 채팅과 사진은 대화하는 두 사람만 볼 수 있어요.
// - 신고와 사진 인증 사진은 관리자만 봐요. 관리자도 회원끼리의 대화는 못 봐요.
// - 정해진 컬렉션 말고는 아무것도 못 써요.
service cloud.firestore {
  match /databases/{database}/documents {
    function member() { return request.auth != null && request.auth.token.firebase.sign_in_provider != 'anonymous'; }
    function me() { return request.auth.uid; }
    // 관리자: Firebase 콘솔에서 admins/{회원 번호} 문서를 직접 만든 사람만
    function isAdmin() { return member() && exists(/databases/$(database)/documents/admins/$(request.auth.uid)); }

    match /users/{uid} {
      allow read: if member();
      allow create, update: if member() && me() == uid;
      allow delete: if member() && me() == uid;
    }
    match /likes/{id} {
      allow read: if member() && (resource.data.from == me() || resource.data.to == me());
      allow create, update: if member() && request.resource.data.from == me() && id == me() + '_' + request.resource.data.to;
      allow delete: if member() && resource.data.from == me();
    }
    match /signals/{id} {
      allow read: if member() && (resource.data.from == me() || resource.data.to == me());
      allow create, update: if member() && request.resource.data.from == me() && id == me() + '_' + request.resource.data.to;
      allow delete: if member() && resource.data.from == me();
    }
    match /chats/{id} {
      allow read: if member() && me() in resource.data.pair;
      allow create: if member() && me() in request.resource.data.pair && request.resource.data.pair.size() == 2
                    && id == request.resource.data.pair[0] + '_' + request.resource.data.pair[1];
      allow update: if member() && me() in resource.data.pair && request.resource.data.pair == resource.data.pair;
    }
    match /chatimgs/{id} {
      allow read: if member() && me() in resource.data.pair;
      allow create: if member() && request.resource.data.from == me() && me() in request.resource.data.pair
                    && request.resource.data.src.size() < 400000;
    }
    // 차단: 차단한 사람과 당한 사람만 읽음 (서로 안 보이게 하려고), 만들고 푸는 건 차단한 사람만
    match /blocks/{id} {
      allow read: if member() && (resource.data.from == me() || resource.data.to == me());
      allow create: if member() && request.resource.data.from == me() && id == me() + '_' + request.resource.data.to;
      allow delete: if member() && resource.data.from == me();
    }
    // 신고: 회원은 보내기만, 읽고 처리하는 건 관리자만
    match /reports/{id} {
      allow create: if member() && request.resource.data.from == me() && request.resource.data.status == 'open'
                    && request.resource.data.detail.size() <= 500;
      allow read, update: if isAdmin();
    }
    // 정지·인증 배지: 모든 회원이 읽음(추천에서 빼고 배지를 보여주려고), 쓰기는 관리자만
    match /moderation/{uid} {
      allow read: if member();
      allow write: if isAdmin();
    }
    // 사진 인증 요청: 본인과 관리자만 읽음, 본인은 '대기 중'으로만 올릴 수 있고 승인·반려는 관리자만
    match /verifications/{uid} {
      allow read: if member() && (me() == uid || isAdmin());
      allow create, update: if member() && me() == uid && request.resource.data.status == 'pending'
                            && request.resource.data.src.size() < 400000;
      allow update: if isAdmin();
      allow delete: if member() && me() == uid;
    }
    // 관리자 목록: 본인이 관리자인지만 확인할 수 있고, 앱에서는 아무도 못 씀
    match /admins/{uid} {
      allow read: if member() && me() == uid;
      allow write: if false;
    }
    // 나만 보는 기록 (매일 추천 등)
    match /priv/{uid} {
      allow read, write: if member() && me() == uid;
    }
  }
}
''')

os.makedirs(out_dir + "/docs", exist_ok=True)
GUIDE = out_dir + "/docs/DEPLOY.md"
open(GUIDE, "w", encoding="utf-8").write('''# 둘 배포하기 (Firebase Hosting)

이 폴더를 그대로 Firebase에 올리면 `https://<프로젝트ID>.web.app` 주소로 열려요.
기존 with-6a75a 프로젝트와 섞이지 않도록 **새 프로젝트**를 만들어 쓰세요.

## 1. Firebase 콘솔에서 준비 (처음 한 번)

1. https://console.firebase.google.com 에서 **프로젝트 추가** → 이름 예: `dul-app`
2. **빌드 → Authentication → 시작하기 → 로그인 방법**에서 두 개를 켜기
   - 이메일/비밀번호
3. **빌드 → Firestore Database → 데이터베이스 만들기**
   - 위치: `asia-northeast3 (서울)`
   - 프로덕션 모드로 시작 (보안 규칙은 배포할 때 같이 올라가요)

## 2. 터미널에서 배포

이 폴더(`dul`)에서 실행:

```bash
npm install -g firebase-tools   # 이미 있으면 생략
firebase login                  # 브라우저에서 구글 로그인
firebase use --add              # 방금 만든 프로젝트 고르고, 별칭은 default
firebase deploy                 # 사이트 + 보안 규칙 같이 배포
```

끝나면 `Hosting URL: https://<프로젝트ID>.web.app` 이 나와요.

## 3. 기존 데이터 지우고 새로 배포 (권장)

이 폴더에서 아래 중 하나를 실행하면, **Firestore 데이터를 전부 지운 뒤** 새로 배포해요.

- Mac / Linux: `./deploy.sh`
- Windows: `deploy.bat` 더블클릭

지워지는 것: 회원 프로필, 좋아요, 채팅, 사진, 마음 표현 (되돌릴 수 없어요)
남는 것: 사이트 주소, 보안 규칙

로그인 계정(Authentication)은 이 명령으로 지워지지 않아요. 예전에 가입한 사람이 로그인하면 앱이 알아서 옛 계정을 정리하고 다시 가입하도록 안내해요.
계정까지 한 번에 비우고 싶으면 Firebase 콘솔 → Authentication → 사용자에서 전체 선택 후 삭제하세요.

## 4. 나를 관리자로 지정하기 (처음 한 번)

관리자 화면에서 신고 처리, 이용 정지, 사진 인증 승인, 가입 현황을 볼 수 있어요.

1. 배포한 사이트에서 직접 회원가입해요.
2. **내 정보** 맨 아래의 `회원 번호`를 복사해요.
3. Firebase 콘솔 → **Firestore Database → 컬렉션 시작** → 컬렉션 ID `admins`
4. 문서 ID에 회원 번호를 붙여넣고, 필드는 아무거나 하나 (예: `name` = `상윤`) → 저장
5. 사이트를 새로고침하면 **내 정보 → 관리자 화면 열기**가 생겨요.

관리자 목록은 앱에서 바꿀 수 없고 콘솔에서만 추가·삭제할 수 있어요.

## 5. 문의 연락처 넣기 (권장)

`src/app_template.html`의 `const CONTACT_EMAIL = "";`에 운영자 이메일을 넣고 다시 빌드하면, 이용약관·개인정보 처리방침·정지 안내에 연락처가 표시돼요. 비워두면 "앱 안의 신고하기로 알려주세요"라고 나와요.

## 6. 데이터는 두고 고친 화면만 올릴 때

`firebase deploy --only hosting`

## 알아둘 점

- 배포판에는 **가상 회원이 없어요.** 가입한 실제 회원끼리만 추천·매칭돼요. 첫 회원은 "아직 가입한 사람이 적어요" 화면을 보게 돼요.
  (가상 회원 500명이 들어간 시연판은 `src`에서 `python3 build_app.py`로 만든 `gyeol_app.html`이에요.)
- 회원가입한 사람은 Firebase 인증 계정이 만들어지고, 비밀번호는 Firebase가 관리해요 (6자 이상). 아이디는 프로필에 저장하지 않아서 다른 회원에게 보이지 않아요.
- 보안 규칙: 가입한 회원만 다른 회원 프로필을 볼 수 있고, 좋아요·마음 표현은 주고받은 두 사람만, 채팅과 사진은 대화하는 두 사람만 읽을 수 있어요.
- 회원은 "내 정보 → 회원 탈퇴"로 프로필·사진·보낸 좋아요·마음 표현·차단·인증 사진을 지우고 계정을 없앨 수 있어요.
- 알림은 둘이 열려 있거나 다른 탭에 있을 때 브라우저 알림으로 와요. 앱을 완전히 닫았을 때도 휴대폰으로 보내려면 Firebase Cloud Functions(유료 Blaze 요금제)와 Cloud Messaging을 추가로 설정해야 해요.
- 사진은 줄여서 Firestore에 저장해요. 사람이 많아지면 Cloud Storage로 옮기는 게 좋아요.
- 실제 사람의 개인정보를 받으니, 공개 전에 개인정보 처리방침(무엇을 모으고 어디에 쓰는지, 탈퇴 방법)을 사이트에 적어두세요.
''')
open(out_dir + "/deploy.sh", "w", encoding="utf-8", newline="\n").write('''#!/usr/bin/env bash
# 둘: 기존 데이터를 모두 지우고 새로 배포 (Mac / Linux)
set -e
cd "$(dirname "$0")"
echo "기존 데이터(회원 프로필, 좋아요, 채팅, 사진, 마음 표현)를 모두 지우고 새로 배포해요."
read -r -p "계속할까요? (y/N) " ans
if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then echo "취소했어요."; exit 1; fi
echo "[1/2] 기존 데이터 지우는 중..."
firebase firestore:delete --all-collections --force || echo "  (지울 데이터가 없거나 처음 배포예요)"
echo "[2/2] 사이트와 보안 규칙 배포 중..."
firebase deploy
echo "끝! 위에 나온 Hosting URL로 들어가 보세요."
''')
os.chmod(out_dir + "/deploy.sh", 0o755)
open(out_dir + "/deploy.bat", "w", encoding="utf-8", newline="\r\n").write('''@echo off
chcp 65001 > nul
rem 둘: 기존 데이터를 모두 지우고 새로 배포 (Windows)
cd /d "%~dp0"
echo 기존 데이터(회원 프로필, 좋아요, 채팅, 사진, 마음 표현)를 모두 지우고 새로 배포해요.
set /p ans=계속할까요? (y/N)
if /i not "%ans%"=="y" (echo 취소했어요. & exit /b 1)
echo [1/2] 기존 데이터 지우는 중...
call firebase firestore:delete --all-collections --force
echo [2/2] 사이트와 보안 규칙 배포 중...
call firebase deploy
echo 끝! 위에 나온 Hosting URL로 들어가 보세요.
pause
''')
if not os.path.exists(out_dir + "/README.md"):
    shutil.copy(GUIDE, out_dir + "/README.md")
print("built", out_dir)
for root, _, files in os.walk(out_dir):
    for f in files:
        path = os.path.join(root, f)
        print(f"  {path}  {os.path.getsize(path):,} bytes")
