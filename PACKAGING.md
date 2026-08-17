# Đóng gói thành .exe (Windows)

Đã kiểm chứng cách làm này thật sự chạy được (build + chạy thử + gọi tất cả
route chính, xác nhận 86/86 file dữ liệu của `bcsfe` được gộp đúng, xác
nhận thư mục `accounts/` lưu đúng cạnh file .exe không mất dữ liệu giữa các
lần chạy) — không phải hướng dẫn suông chưa thử.

⚠️ Việc build PHẢI làm trên Windows (không build trên Mac/Linux ra được
.exe Windows — PyInstaller không hỗ trợ build chéo giữa các hệ điều hành).

## Cách 1 — dùng script có sẵn (khuyên dùng)

1. Cài Python (nếu chưa có): https://www.python.org/downloads/ — nhớ tick
   "Add python.exe to PATH" lúc cài.
2. Mở thư mục project này, double-click `build_exe.bat`.
3. Đợi build xong (1-2 phút). Kết quả nằm trong `dist\BattleCatsSaveEditor\`.
4. Gửi **cả thư mục** `dist\BattleCatsSaveEditor\` cho người dùng cuối
   (không chỉ file .exe — nó cần các file đi kèm trong `_internal\`).
   Chạy được bằng cách double-click `BattleCatsSaveEditor.exe` bên trong.

## Cách 2 — chạy tay từng lệnh

```
pip install flask==3.1.3 bcsfe==3.6.0 zeroconf pyinstaller

pyinstaller --name BattleCatsSaveEditor --onedir --console ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "service-worker.js;." ^
    --collect-data bcsfe ^
    --hidden-import bcsfe ^
    app.py
```

## Vì sao dùng đúng các tham số này (không phải PyInstaller mặc định)

- `--add-data "templates;templates"` / `"static;static"` / `service-worker.js` —
  PyInstaller mặc định CHỈ gộp code Python nó dò được qua `import`, không
  tự động biết templates HTML / CSS / icon / service worker cần thiết. Bỏ
  qua bước này → build "thành công" nhưng mở lên báo lỗi "template not
  found".
- `--collect-data bcsfe` — package `bcsfe` có 86 file dữ liệu không phải
  `.py` (locale text, theme...) nằm trong chính package của nó. Không có
  cờ này, tool build xong nhưng nhiều tính năng (tên chapter, item...) sẽ
  lỗi ngầm hoặc hiện tên chung chung vì thiếu dữ liệu.
- `app.py` đã tự code sẵn phần "biết mình đang chạy dạng .exe hay chạy
  bằng `python app.py`" (`sys.frozen`), để: (1) tìm đúng chỗ templates/
  static khi đã đóng gói, (2) lưu thư mục `accounts/` CẠNH file .exe thay
  vì trong thư mục giải nén tạm (nếu không, account sẽ "biến mất" mỗi lần
  tắt mở lại app).

## `--onedir` (thư mục) hay `--onefile` (1 file duy nhất)?

Script dùng `--onedir` (khuyên dùng):
- Khởi động nhanh hơn hẳn `--onefile` (không phải tự giải nén lại mỗi lần
  chạy).
- **Ít bị Windows Defender / diệt virus báo nhầm là đáng ngờ hơn.**
  `--onefile` là kiểu file rất hay bị chặn nhầm (false positive) vì cách
  nó tự giải nén lúc chạy giống hành vi của malware — đây là vấn đề rất
  phổ biến với PyInstaller, không phải do code có vấn đề gì.
- Nhược điểm: phải gửi cả thư mục thay vì 1 file duy nhất.

Muốn đổi sang `--onefile`, chỉ cần đổi `--onedir` thành `--onefile` trong
lệnh trên — mọi tham số khác giữ nguyên.

## Ẩn cửa sổ terminal đen?

Script dùng `--console` (giữ cửa sổ đen hiện dòng "Server running..." +
log lỗi nếu có — hữu ích khi có sự cố). Muốn ẩn hẳn, đổi `--console`
thành `--windowed`, nhưng lúc đó người dùng sẽ KHÔNG thấy được URL để mở
— nên cân nhắc thêm bước tự mở trình duyệt nếu chọn hướng này (báo tôi
nếu muốn, tôi thêm `webbrowser.open()` vào `app.py`).

## requirements.txt

Đã bỏ theo yêu cầu — bản .exe không cần nó (mọi thư viện đã gộp sẵn vào
trong lúc build). Muốn build lại hoặc chạy bằng `python app.py` (không
đóng gói), dùng đúng 2 lệnh pip ở trên (`flask==3.1.3 bcsfe==3.6.0`).
