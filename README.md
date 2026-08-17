# Battle Cats Save Editor — Web (Flask, hacker green-on-black terminal UI)

## Run

```
python app.py
```

Không hỏi gì cả — server tự host luôn, chỉ in đúng 1 dòng:

```
🚀 Server running: http://127.0.0.1:5000 | http://<LAN-IP>:5000
```

Mở URL nào cũng được, từ máy nào cũng được — **giao diện tự thích nghi
theo bề rộng màn hình** (responsive CSS thuần): trên điện thoại, sidebar
ẩn mặc định, chỉ còn nút hamburger (☰, 3 gạch) góc trên trái, bấm vào để
trượt menu ra; trên máy tính/tablet, sidebar hiện sẵn như bình thường.
Không cần chọn "máy tính hay điện thoại" gì cả.

Muốn đóng gói thành file `.exe` chạy được mà không cần cài Python — xem
**`PACKAGING.md`** (đã kiểm chứng thật, không phải hướng dẫn suông).

`app.py` auto-installs `flask`/`bcsfe` if missing (see `bootstrap.py`).

Do not deploy this publicly on the internet — it's a personal tool for
localhost/LAN only. There is no multi-user login system.

## Tự host ngay trên điện thoại (Termux, Android)

1. Cài **Termux** từ F-Droid (không dùng bản Google Play, đã ngừng cập
   nhật lâu rồi): https://f-droid.org/packages/com.termux/
2. Trong Termux:
   ```
   pkg update
   pkg install python git
   termux-setup-storage   # cấp quyền để lưu file ra thư mục Downloads chung
   ```
3. Copy project này vào điện thoại (git clone hoặc giải nén zip), `cd` vào
   thư mục đó.
4. `python app.py`.
5. Mở `http://127.0.0.1:5000` bằng Chrome ngay trên điện thoại đó.

Một số gói Python có phần biên dịch C có thể cần thêm bước trên Termux; nếu
`pip install` báo lỗi, thử `pkg install clang make` rồi chạy lại.

## What's new in this version

- **Không còn hỏi "máy tính hay điện thoại"** khi khởi động — chạy
  `python app.py` là xong, server tự host, không cần chọn gì.
- **Sidebar tự thích nghi bằng CSS thuần** (không còn server đoán thiết bị
  qua User-Agent): dưới 768px, sidebar ẩn mặc định, chỉ còn nút hamburger
  (☰) góc trên trái; bấm vào để trượt menu ra, có lớp nền mờ phía sau,
  bấm ra ngoài hoặc chọn 1 mục là tự đóng lại. Trên màn hình rộng hơn,
  sidebar hiện sẵn như bình thường — không cần cấu hình gì thêm.
- **Banner ASCII "SKITTLE"** ở trang Home, kèm dòng chữ ký "tool made by
  skittle".
- Previous session's terminal-chrome, PWA install, and sharp-corner theme
  are all still here — see below.

## Install on your phone (PWA)

1. Make sure your phone is on the **same wifi** as the computer running
   `python app.py`.
2. Open the "Trên điện thoại" URL printed in the terminal, in Chrome
   (Android) or Safari (iOS).
3. **Android (Chrome)**: tap the menu (⋮) → "Install app" / "Add to Home
   screen".
   **iOS (Safari)**: tap the Share icon → "Add to Home Screen".
4. Launch it from the home screen icon — it opens full-screen, no address
   bar, like a real app.

This is a real PWA (`manifest.json` + `service-worker.js` + custom app
icon), not just a bookmark — but it's still 100% the same Flask app, no
separate mobile codebase to maintain.

## What's new in this version

- **Sharp corners everywhere** — `border-radius: 0` on every element
  (buttons, cards, inputs, alerts), including Bootstrap's own components
  via its CSS variables.
- **Terminal window chrome** — every card now has a fake terminal title
  bar with red/yellow/green traffic-light dots, done purely in CSS (no
  template changes), so it applies consistently across the whole app.
- **Command-center stat strip** — a row of large live stats (Catfood, XP,
  Rare Tickets, Leadership) at the top of the Overview page.
- **Scanline overlay** — a faint CRT-style texture across the whole page.
- **Pulsing status dot** next to the app name in the sidebar.
- **Mobile-responsive layout** — sidebar becomes an off-canvas menu behind
  a hamburger button below 768px width, tables scroll horizontally instead
  of overflowing, inputs are sized to avoid iOS auto-zoom, touch targets
  are enlarged.
- **Installable PWA** — manifest, service worker (caches only static
  assets, never save data, so you never see stale data on your phone),
  and a generated app icon.
- Server now binds to `0.0.0.0` (was `127.0.0.1`) so your phone can reach
  it over LAN, and prints both URLs on startup.

## Previous features (all still here)

Transfer-code login, currencies (free-form add/set, no fixed preset
buttons), array items (Catamin/Catseye/Treasure Chest/Catfruit/Labyrinth
Medal), Cats (unlock/level individually or in bulk, force true form, force
4th form, max talents, delete), Story Chapters (per-chapter or bulk
complete + treasure collection), Ototo/Gamototo (engineers, base
materials, cannons), Other Maps (Gauntlets/Legend Quest/Zero
Legends/Event Stages complete-all), named Accounts folders, Save File,
Upload & Get New Codes.

## Still not covered (future work)

Gatya seeds, unlocked equip slots, rare ticket trade, restart pack, Enemy
Guide, Aku Realm, Other/Fixes (medals, missions, gold pass, user rank,
clear tutorial).

