"""
app.py
------
Flask web app for Battle Cats Save Editor.

Architecture: same as the desktop version — backend.py is the ONLY place
that imports bcsfe. app.py only defines routes.

This is a personal LOCAL tool (localhost) — each browser/device gets its
own independent backend instance (see get_backend() below), so opening
this on your phone AND your PC at the same time no longer means both are
silently editing the exact same in-memory save and overwriting each
other.
This is still NOT a real multi-user login system (no password/account, just
per-browser isolation via cookie) — do NOT deploy this publicly on the
internet.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Kiểm tra & tự động cài module còn thiếu TRƯỚC KHI import — xem bootstrap.py
from bootstrap import ensure_all

ensure_all()

from flask import Flask, render_template, request, redirect, url_for, flash, session

from backend import BattleCatsBackend, BackendError, get_app_dir

# Khi đóng gói bằng PyInstaller (--onefile hoặc --onedir), templates/ và
# static/ được giải nén vào 1 thư mục tạm trỏ bởi sys._MEIPASS lúc chạy —
# PHẢI trỏ Flask vào đúng chỗ đó, nếu không sẽ báo lỗi "template not found"
# dù mọi thứ đóng gói đúng. Chạy `python app.py` bình thường thì dùng thư
# mục chứa app.py như cũ.
if getattr(sys, "frozen", False):
    _resource_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _resource_dir = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(_resource_dir / "templates"),
    static_folder=str(_resource_dir / "static"),
)
app.secret_key = "battle-cats-save-editor-local-tool"  # local-only tool, no real secret needed

import uuid

# ---------------------------------------------------------------------------
# Backend THEO SESSION (mỗi trình duyệt/thiết bị = 1 bản BattleCatsBackend
# riêng biệt trong bộ nhớ server, tách biệt qua cookie session của Flask).
#
# Trước đây có 1 biến `backend` toàn cục dùng chung cho MỌI kết nối — nghĩa
# là mở trên điện thoại và máy tính cùng lúc sẽ cùng sửa 1 save trong bộ
# nhớ, ai bấm sau ghi đè người trước mà không cảnh báo gì. Cách này sửa
# đúng vấn đề đó mà không cần đăng nhập/mật khẩu thật.
#
# Đây vẫn KHÔNG phải bảo mật thật: cookie session không mã hoá mạnh, chỉ đủ
# để tách các thiết bị ra khỏi nhau khi dùng trên cùng 1 mạng LAN tin cậy.
# ---------------------------------------------------------------------------

_session_backends: dict[str, "BattleCatsBackend"] = {}


def get_backend() -> BattleCatsBackend:
    if "bcs_session_id" not in session:
        session["bcs_session_id"] = str(uuid.uuid4())
    sid = session["bcs_session_id"]
    if sid not in _session_backends:
        _session_backends[sid] = BattleCatsBackend()
    return _session_backends[sid]


@app.context_processor
def inject_backend_state():
    return {"backend_loaded": get_backend().is_loaded}


CURRENCY_LABELS = {
    "xp": "XP",
    "catfood": "Cat Food",
    "normal_tickets": "Normal Tickets",
    "rare_tickets": "Rare Tickets",
    "platinum_tickets": "Platinum Tickets",
    "platinum_shards": "Platinum Shards",
    "legend_tickets": "Legend Tickets",
    "np": "NP",
    "leadership": "Leadership",
}

ARRAY_ITEM_DISPLAY = {
    "catamins": "Catamin",
    "catseyes": "Catseye (true form)",
    "treasure_chests": "Treasure Chest",
    "catfruit": "Catfruit",
    "labyrinth_medals": "Labyrinth Medal",
}


def require_loaded():
    if not get_backend().is_loaded:
        flash("No save loaded yet — enter a transfer code or load an account first.", "error")
        return False
    return True


# ---------------- Entry page ----------------


@app.route("/", methods=["GET"])
def index():
    if get_backend().is_loaded:
        return redirect(url_for("dashboard"))
    accounts = get_backend().list_accounts()
    return render_template("account.html", accounts=accounts)


@app.route("/download", methods=["POST"])
def download():
    transfer_code = request.form.get("transfer_code", "")
    confirmation_code = request.form.get("confirmation_code", "")
    country_code = request.form.get("country_code", "en")
    try:
        get_backend().download_from_transfer_code(transfer_code, confirmation_code, country_code)
    except BackendError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    flash("Save downloaded successfully.", "success")
    return redirect(url_for("dashboard"))


# ---------------- Accounts (named save folders) ----------------


@app.route("/accounts")
def accounts_list():
    accounts = get_backend().list_accounts()
    return render_template("accounts.html", accounts=accounts, root_dir=str(get_backend().ACCOUNTS_DIR))


@app.route("/accounts/save", methods=["POST"])
def accounts_save():
    if not require_loaded():
        return redirect(url_for("index"))
    name = request.form.get("account_name", "")
    try:
        path = get_backend().save_to_account(name)
        flash(f"Saved to account '{name}' at: {path}", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("accounts_list"))


@app.route("/accounts/load", methods=["POST"])
def accounts_load():
    name = request.form.get("account_name", "")
    try:
        get_backend().load_account(name)
        flash(f"Loaded account '{name}'.", "success")
    except BackendError as exc:
        flash(str(exc), "error")
        return redirect(url_for("accounts_list"))
    return redirect(url_for("dashboard"))


# ---------------- Main dashboard ----------------


@app.route("/dashboard")
def dashboard():
    if not get_backend().is_loaded:
        return redirect(url_for("index"))
    currencies = get_backend().get_currencies()
    playtime = get_backend().get_playtime()
    return render_template(
        "dashboard.html",
        currencies=currencies,
        currency_labels=CURRENCY_LABELS,
        array_items=ARRAY_ITEM_DISPLAY,
        playtime=playtime,
    )


@app.route("/cats/bulk_unlock", methods=["POST"])
def bulk_unlock_cats():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().bulk_unlock_all_cats()
        flash(f"Unlocked {count} new cat(s).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard"))


@app.route("/cats/bulk_level", methods=["POST"])
def bulk_level_cats():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        base = int(request.form.get("base", "1"))
        plus = int(request.form.get("plus", "0"))
        count = get_backend().bulk_set_all_cats_level(base, plus)
        flash(f"Updated level for {count} unlocked cat(s).", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard"))


@app.route("/playtime/set", methods=["POST"])
def set_playtime():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        hours = int(request.form.get("hours", "0"))
        minutes = int(request.form.get("minutes", "0"))
        seconds = int(request.form.get("seconds", "0"))
        get_backend().set_playtime(hours, minutes, seconds)
        flash(f"Playtime set to {hours}h {minutes}m {seconds}s.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard"))


# ---------------- Story chapters ----------------


@app.route("/story")
def story_list():
    if not get_backend().is_loaded:
        return redirect(url_for("index"))
    chapters = get_backend().get_story_chapters()
    return render_template("story.html", chapters=chapters)


@app.route("/story/complete", methods=["POST"])
def story_complete():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        chapter_index = int(request.form.get("chapter_index", "0"))
        get_backend().clear_story_chapter(chapter_index)
        flash(f"Chapter #{chapter_index + 1} marked as completed.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("story_list"))


@app.route("/story/treasure", methods=["POST"])
def story_treasure():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        chapter_index = int(request.form.get("chapter_index", "0"))
        level = int(request.form.get("level", "3"))
        get_backend().collect_story_treasure(chapter_index, level)
        flash(f"Collected treasure for chapter #{chapter_index + 1}.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("story_list"))


@app.route("/story/complete_all", methods=["POST"])
def story_complete_all():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().clear_all_story_chapters()
        flash(f"Completed all {count} chapters.", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("story_list"))


@app.route("/story/treasure_all", methods=["POST"])
def story_treasure_all():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        level = int(request.form.get("level", "3"))
        count = get_backend().collect_all_story_treasure(level)
        flash(f"Collected treasure for all {count} chapters.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("story_list"))


# ---------------- Ototo / Gamototo ----------------


@app.route("/ototo")
def ototo_page():
    if not get_backend().is_loaded:
        return redirect(url_for("index"))
    engineers = get_backend().get_engineers()
    materials = list(enumerate(get_backend().get_base_materials()))
    cannons = get_backend().get_cannons()
    return render_template(
        "ototo.html", engineers=engineers, materials=materials, cannons=cannons
    )


@app.route("/ototo/engineers", methods=["POST"])
def ototo_engineers():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = int(request.form.get("count", "0"))
        get_backend().set_engineers(count)
        flash(f"Engineers set to {count}.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("ototo_page"))


@app.route("/ototo/materials", methods=["POST"])
def ototo_materials():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        current = get_backend().get_base_materials()
        values = [int(request.form.get(f"value_{i}", "0")) for i in range(len(current))]
        get_backend().set_base_materials(values)
        flash("Base materials updated.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("ototo_page"))


@app.route("/ototo/cannon", methods=["POST"])
def ototo_cannon():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        cannon_id = int(request.form.get("cannon_id", "0"))
        development = int(request.form.get("development", "0"))
        levels = get_backend().get_cannons()
        target = next((c for c in levels if c["id"] == cannon_id), None)
        num_parts = len(target["levels"]) if target else 0
        new_levels = [int(request.form.get(f"level_{i}", "0")) for i in range(num_parts)]
        get_backend().set_cannon(cannon_id, development, new_levels)
        flash(f"Cannon #{cannon_id} updated.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("ototo_page"))


# ---------------- Advanced cat actions ----------------


@app.route("/cats/true_form", methods=["POST"])
def cats_true_form():
    if not require_loaded():
        return redirect(url_for("index"))
    cat_id = int(request.form.get("cat_id", "0"))
    try:
        get_backend().force_true_form([cat_id])
        flash(f"Forced true form for cat #{cat_id}.", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


@app.route("/cats/fourth_form", methods=["POST"])
def cats_fourth_form():
    if not require_loaded():
        return redirect(url_for("index"))
    cat_id = int(request.form.get("cat_id", "0"))
    try:
        get_backend().force_fourth_form([cat_id])
        flash(f"Forced 4th form for cat #{cat_id}.", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


@app.route("/cats/delete", methods=["POST"])
def cats_delete():
    if not require_loaded():
        return redirect(url_for("index"))
    cat_id = int(request.form.get("cat_id", "0"))
    try:
        get_backend().delete_cat(cat_id)
        flash(f"Deleted cat #{cat_id}.", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


@app.route("/cats/bulk_true_form", methods=["POST"])
def cats_bulk_true_form():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().force_true_form(None)
        flash(f"Forced true form for {count} unlocked cat(s).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


@app.route("/cats/bulk_fourth_form", methods=["POST"])
def cats_bulk_fourth_form():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().force_fourth_form(None)
        flash(f"Forced 4th form for {count} unlocked cat(s).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


@app.route("/cats/bulk_talents", methods=["POST"])
def cats_bulk_talents():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().max_all_talents(None)
        flash(f"Maxed talents for {count} cat(s).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


# ---------------- Other map types (simple complete-all) ----------------


@app.route("/other_maps")
def other_maps_page():
    if not get_backend().is_loaded:
        return redirect(url_for("index"))
    return render_template("other_maps.html")


@app.route("/other_maps/gauntlets", methods=["POST"])
def other_maps_gauntlets():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().complete_all_gauntlets()
        flash(f"Completed all Gauntlet stages ({count} stages).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("other_maps_page"))


@app.route("/other_maps/legend_quest", methods=["POST"])
def other_maps_legend_quest():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().complete_all_legend_quest()
        flash(f"Completed all Legend Quest stages ({count} stages).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("other_maps_page"))


@app.route("/other_maps/zero_legends", methods=["POST"])
def other_maps_zero_legends():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().complete_all_zero_legends()
        flash(f"Completed all Zero Legends stages ({count} stages).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("other_maps_page"))


@app.route("/other_maps/event_stages", methods=["POST"])
def other_maps_event_stages():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        count = get_backend().complete_all_event_stages()
        flash(f"Completed all Event Stage groups ({count} groups).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("other_maps_page"))


@app.route("/currency/add", methods=["POST"])
def currency_add():
    if not require_loaded():
        return redirect(url_for("index"))
    key = request.form.get("key", "")
    try:
        amount = int(request.form.get("amount", "0"))
    except ValueError:
        flash("Amount must be a whole number.", "error")
        return redirect(url_for("dashboard"))
    try:
        current = get_backend().get_currencies()
        new_value = current.get(key, 0) + amount
        get_backend().set_currencies({key: new_value})
        sign = "+" if amount >= 0 else ""
        flash(f"{CURRENCY_LABELS.get(key, key)} {sign}{amount:,} (now {new_value:,}).", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard"))


@app.route("/currency/set", methods=["POST"])
def currency_set():
    if not require_loaded():
        return redirect(url_for("index"))
    key = request.form.get("key", "")
    value = request.form.get("value", "0")
    try:
        get_backend().set_currencies({key: int(value)})
        flash(f"{CURRENCY_LABELS.get(key, key)} set to {int(value):,}.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard"))


# ---------------- Array-type items ----------------


@app.route("/items/<key>")
def items_edit(key: str):
    if not get_backend().is_loaded:
        return redirect(url_for("index"))
    try:
        items = get_backend().get_array_item(key)
    except BackendError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    return render_template(
        "items.html",
        key=key,
        title=ARRAY_ITEM_DISPLAY.get(key, key),
        items=list(enumerate(items)),
    )


@app.route("/items/<key>/save", methods=["POST"])
def items_save(key: str):
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        current = get_backend().get_array_item(key)
        new_values = []
        for i in range(len(current)):
            new_values.append(int(request.form.get(f"value_{i}", "0")))
        get_backend().set_array_item(key, new_values)
        flash(f"Updated group '{ARRAY_ITEM_DISPLAY.get(key, key)}'.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("items_edit", key=key))


# ---------------- Cats ----------------


@app.route("/cats")
def cats_list():
    if not get_backend().is_loaded:
        return redirect(url_for("index"))
    cats = get_backend().get_cats()
    return render_template("cats.html", cats=cats)


@app.route("/cats/unlock", methods=["POST"])
def cats_unlock():
    if not require_loaded():
        return redirect(url_for("index"))
    cat_id = int(request.form.get("cat_id", "0"))
    try:
        get_backend().set_cat_unlocked(cat_id, True)
        flash(f"Unlocked cat #{cat_id}.", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


@app.route("/cats/level", methods=["POST"])
def cats_level():
    if not require_loaded():
        return redirect(url_for("index"))
    cat_id = int(request.form.get("cat_id", "0"))
    try:
        base = int(request.form.get("base", "1"))
        plus = int(request.form.get("plus", "0"))
        get_backend().set_cat_level(cat_id, base, plus)
        flash(f"Updated level for cat #{cat_id}.", "success")
    except (BackendError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("cats_list"))


# ---------------- Save / Upload ----------------


@app.route("/save_file", methods=["POST"])
def save_file():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        out_dir = _get_default_save_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "SAVE_DATA_edited"
        get_backend().save_file(str(out_path))
        flash(f"Saved file to: {out_path}", "success")
    except BackendError as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard"))


@app.route("/upload", methods=["POST"])
def upload():
    if not require_loaded():
        return redirect(url_for("index"))
    try:
        transfer_code, confirmation_code = get_backend().upload_and_get_new_codes()
    except BackendError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    return render_template(
        "upload_result.html", transfer_code=transfer_code, confirmation_code=confirmation_code
    )


# ---------------- PWA: service worker phải phục vụ ở scope gốc "/" ----------------
# (nếu để trong /static/, service worker mặc định chỉ kiểm soát được các file
# trong /static/, không kiểm soát được toàn bộ trang -> Android sẽ không coi
# đây là PWA hợp lệ và không hiện nút "Cài đặt ứng dụng").


@app.route("/service-worker.js")
def service_worker():
    from flask import Response

    with open(_resource_dir / "service-worker.js", "r", encoding="utf-8") as f:
        content = f.read()
    response = Response(content, mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


def _is_termux() -> bool:
    """Termux (chạy Python ngay trên Android) đặt biến môi trường PREFIX trỏ
    vào /data/data/com.termux/... — cách phát hiện đáng tin cậy nhất, không
    cần thư viện ngoài."""
    import os

    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or Path("/data/data/com.termux").exists()


def _get_default_save_dir() -> Path:
    """Thư mục mặc định để ghi file save đã sửa. Trên Termux, thư mục HOME
    bị cô lập trong sandbox của Termux — muốn file xuất hiện ở nơi các app
    Android khác (File Manager...) nhìn thấy được, cần dùng thư mục chia sẻ
    qua `termux-setup-storage` (tạo ~/storage/downloads). Nếu người dùng
    chưa chạy lệnh đó, fallback về HOME bình thường để không bị lỗi."""
    if _is_termux():
        shared_downloads = Path.home() / "storage" / "downloads"
        if shared_downloads.exists():
            return shared_downloads
        return Path.home()
    return Path.home() / "Downloads"


def _get_lan_ip() -> str:
    """Đoán địa chỉ IP LAN của máy này để in ra cho người dùng mở trên điện
    thoại. Không kết nối thật ra ngoài internet — chỉ dùng UDP socket để hỏi
    hệ điều hành "nếu tôi gửi gói tin đi, nó sẽ đi qua interface nào"."""
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    BattleCatsBackend.ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)

    # Tắt banner mặc định của Flask/Werkzeug (" * Serving Flask app...",
    # " * Debug mode:...", cảnh báo dev server, và CẢ 2 dòng "Running on"
    # cho 127.0.0.1 lẫn LAN IP) để chỉ còn đúng 1 dòng tự in bên dưới.
    # Server vẫn bind "0.0.0.0" như cũ nên http://127.0.0.1 vẫn truy cập
    # được bình thường — chỉ là không còn hiện dòng log riêng cho nó nữa.
    import logging

    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import flask.cli

    flask.cli.show_server_banner = lambda *a, **k: None

    port = 5000
    lan_ip = _get_lan_ip()
    print(f"🚀 Server running: http://{lan_ip}:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
