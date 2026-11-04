// 둘 서비스워커: 홈 화면 앱으로 쓸 때 빨리 열리고, 인터넷이 끊겨도 마지막 화면은 열리게
// (build_deploy.py가 public/sw.js로 복사하면서 20261104151440에 배포 시각을 넣음 → 새로 배포하면 옛 저장분은 지워짐)
const CACHE = "dul-20261104151440";
const SHELL = ["./", "./demo.html", "./firebase-config.js", "./manifest.webmanifest", "./demo.webmanifest",
  "./icons/icon-180.png", "./icons/icon-192.png", "./icons/icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {}))))   // 하나 없어도 설치는 계속
    .then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const save = (req, res) => { if (res.ok || res.type === "opaque") { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return res; };

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    // AI 서버(/api)와 Firebase Hosting 내부 파일(/__/)은 건드리지 않음
    if (url.pathname.includes("/api/") || url.pathname.startsWith("/__/")) return;
    // 우리 파일: 인터넷 먼저 (새로 배포한 게 바로 보이게), 끊기면 저장해 둔 것
    e.respondWith(fetch(req).then(res => save(req, res))
      .catch(() => caches.match(req, { ignoreSearch: true })
        .then(hit => hit || (req.mode === "navigate" ? caches.match("./") : null))
        .then(hit => hit || Response.error())));
    return;
  }
  // 글꼴: 저장해 둔 것 먼저 (잘 안 바뀌니까)
  if (/(^|\.)fonts\.(googleapis|gstatic)\.com$|^cdn\.jsdelivr\.net$/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => save(req, res))));
  }
  // 나머지(Firebase 로그인·데이터 등)는 브라우저가 알아서
});
