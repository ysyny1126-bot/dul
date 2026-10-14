# 둘 배포하기 (Firebase Hosting)

이 폴더를 그대로 Firebase에 올리면 `https://<프로젝트ID>.web.app` 주소로 열려요.
기존 with-6a75a 프로젝트와 섞이지 않도록 **새 프로젝트**를 만들어 쓰세요.

## 1. Firebase 콘솔에서 준비 (처음 한 번)

1. https://console.firebase.google.com 에서 **프로젝트 추가** → 이름 예: `dul-app`
2. **빌드 → Authentication → 시작하기 → 로그인 방법**에서 두 개를 켜기
   - 이메일/비밀번호
   - 익명
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
남는 것: 사이트 주소, 보안 규칙, 가상 회원 500명(앱 안에 들어 있어서 그대로예요)

로그인 계정(Authentication)은 이 명령으로 지워지지 않아요. 예전에 가입한 사람이 로그인하면 앱이 알아서 옛 계정을 정리하고 다시 가입하도록 안내해요.
계정까지 한 번에 비우고 싶으면 Firebase 콘솔 → Authentication → 사용자에서 전체 선택 후 삭제하세요.

## 4. 데이터는 두고 고친 화면만 올릴 때

`firebase deploy --only hosting`

## 알아둘 점

- 가상 회원 500명(user001~user500 / 1234)은 시연용이라 누구나 들어가서 좋아요·메시지를 보낼 수 있어요. 실제 서비스로 열 때는 가상 회원을 빼세요.
- 회원가입한 사람은 Firebase 인증 계정이 만들어지고, 비밀번호는 Firebase가 관리해요 (6자 이상).
- 사진은 줄여서 Firestore에 저장해요. 사람이 많아지면 Cloud Storage로 옮기는 게 좋아요.
- 지금 보안 규칙은 시연용이라 로그인한 사람이면 좋아요·채팅 문서를 읽을 수 있어요. 실제 서비스 전에는 채팅을 두 사람만 읽게 규칙을 좁혀야 해요.
