// service-worker.js
// Mục đích DUY NHẤT: cho trình duyệt (đặc biệt Android/Chrome) coi đây là
// PWA hợp lệ để hiện nút "Cài đặt ứng dụng" / "Thêm vào màn hình chính".
//
// KHÔNG cache các trang có dữ liệu save (dashboard, cats, story...) vì save
// data thay đổi liên tục — cache nhầm sẽ khiến điện thoại hiện dữ liệu cũ.
// Chỉ cache vài tài nguyên tĩnh không đổi (CSS, icon, manifest).

const CACHE_NAME = "bcs-static-v1";
const STATIC_ASSETS = [
  "/static/style.css",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isStaticAsset = STATIC_ASSETS.some((path) => url.pathname === path);

  if (!isStaticAsset) {
    // Moi request khac (trang HTML, form POST, du lieu save...) -> luon
    // di thang mang, khong bao gio lay tu cache.
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
