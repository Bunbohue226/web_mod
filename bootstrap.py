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
    ensure_installed("flask")
    ensure_installed("bcsfe")


if __name__ == "__main__":
    ensure_all()
    print("Tất cả module cần thiết đã sẵn sàng.")
