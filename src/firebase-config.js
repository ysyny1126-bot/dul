// GitHub Pages처럼 Firebase Hosting이 아닌 곳에서 둘을 열 때 쓰는 Firebase 설정이에요.
// Firebase Hosting(*.web.app)으로 배포하면 이 파일은 쓰지 않아요.
//
// 채우는 법: Firebase 콘솔 → 프로젝트 설정(톱니바퀴) → 일반 → 내 앱 → 웹 앱(</>) 추가
//           → 나오는 firebaseConfig 값을 아래 null 자리에 붙여넣기
// 예: window.DUL_FIREBASE_CONFIG = { apiKey: "...", authDomain: "dul-app.firebaseapp.com", projectId: "dul-app", appId: "..." };
// 이 값들은 공개돼도 괜찮은 값이에요 (데이터는 firestore.rules가 지켜요).
window.DUL_FIREBASE_CONFIG = null;
