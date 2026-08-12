"""
bootstrap.py
------------
Kiểm tra xem các thư viện cần thiết (flask, bcsfe) đã được cài trên máy
chưa; nếu chưa, TỰ ĐỘNG chạy pip install giúp người dùng, để chỉ cần
`python app.py` là chạy được ngay, không cần nhớ chạy
`pip install -r requirements.txt` trước.

Phải import và gọi ensure_all() TRƯỚC bất kỳ import nào của flask/bcsfe
trong app.py (đặt ở dòng đầu file), vì lúc đó các thư viện đó có thể
chưa tồn tại trên máy.
"""

from __future__ import annotations

import importlib
import subprocess
import sys


def ensure_installed(import_name: str, pip_name: str | None = None) -> None:
    """Kiểm tra `import_name` import được chưa; nếu chưa, cài `pip_name`
    (mặc định trùng import_name) bằng đúng python đang chạy file này,
    rồi thử import lại."""
    pip_name = pip_name or import_name
    try:
        importlib.import_module(import_name)
        return
    except ImportError:
        pass

    print(f"[setup] Module '{import_name}' chưa được cài. Đang tự động cài '{pip_name}'...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
    except subprocess.CalledProcessError:
        # Một số hệ điều hành (Debian/Ubuntu mới, Homebrew Python trên Mac...)
        # chặn pip install thẳng vào python hệ thống ("externally-managed-environment").
        # Thử lại với --break-system-packages cho các máy đó; Windows thường
        # không cần bước này nhưng thử lại không gây hại gì.
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--break-system-packages", pip_name]
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"Không tự cài được '{pip_name}'. Hãy chạy tay: "
                f"{sys.executable} -m pip install {pip_name}"
            ) from exc

    importlib.invalidate_caches()
    importlib.import_module(import_name)  # nếu vẫn lỗi, ném exception rõ ràng ở đây
    print(f"[setup] Đã cài xong '{pip_name}'.")


def ensure_all() -> None:
    if getattr(sys, "frozen", False):
        # Đang chạy trong .exe đóng gói (PyInstaller) — mọi thư viện đã được
        # gộp sẵn vào exe từ lúc build, không cần (và không thể) pip install
        # gì thêm lúc chạy. sys.executable lúc này trỏ vào chính file .exe,
        # không phải python.exe thật, nên gọi pip ở đây sẽ chỉ gây lỗi khó
        # hiểu — bỏ qua hẳn bước này.
        return
    # Ghim đúng version đã test kỹ trong dự án này (không có requirements.txt
    # làm nguồn tham chiếu riêng nữa — xem PACKAGING.md để đóng gói .exe).
    ensure_installed("flask", "flask==3.1.3")
    ensure_installed("bcsfe", "bcsfe==3.6.0")


if __name__ == "__main__":
    ensure_all()
    print("Tất cả module cần thiết đã sẵn sàng.")
