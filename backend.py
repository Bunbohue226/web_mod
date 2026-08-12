"""
backend.py
----------
Lớp bọc (wrapper) quanh package `bcsfe` (Battle Cats Save File Editor).

Mục tiêu: cô lập TOÀN BỘ việc gọi bcsfe ở một chỗ duy nhất, để phần GUI
(gui.py) không bao giờ phải import trực tiếp bcsfe. Nếu sau này bcsfe đổi
API nội bộ, chỉ cần sửa file này.

Kiến trúc mở rộng: mỗi nhóm tính năng bcsfe (currencies, cats, stages, ...)
tương ứng với 1 phương thức get_*/set_* trong class BattleCatsBackend.
Muốn thêm tính năng mới -> thêm 1 phương thức mới ở đây, rồi gọi nó từ gui.py.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bcsfe import core


def get_app_dir() -> Path:
    """Thư mục 'gốc' để lưu DỮ LIỆU NGƯỜI DÙNG (accounts/...) — không phải
    nơi chứa code.

    Khi chạy bằng `python app.py` bình thường: thư mục chứa backend.py.

    Khi chạy dạng .exe đóng gói bằng PyInstaller: `sys.frozen` = True, và
    bắt buộc phải dùng thư mục CHỨA FILE .exe (không phải thư mục giải nén
    tạm `sys._MEIPASS`) — vì thư mục tạm đó bị xoá mỗi khi đóng chương
    trình (--onefile) hoặc không phải chỗ hợp lý để ghi dữ liệu lâu dài
    (--onedir). Dùng nhầm _MEIPASS sẽ khiến account "biến mất" sau khi tắt
    app lần sau mở lại.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# --- FIX QUAN TRỌNG ---
# bcsfe dùng 1 singleton `core.core_data` để giữ config/locale/max-value-data...
# nhưng KHÔNG tự khởi tạo khi import — CLI gốc gọi init_data() ngầm lúc start.
# Nếu bỏ qua bước này, mọi request mạng (RequestHandler.timeout() đọc config)
# sẽ ném AttributeError, và trước đây bị wrap nhầm thành "lỗi kết nối máy chủ".
# Gọi 1 lần duy nhất ở đây, ngay khi module này được import.
core.core_data.init_data()


class BackendError(Exception):
    """Lỗi nghiệp vụ do backend ném ra, GUI sẽ bắt và hiển thị cho người dùng."""


@dataclass
class CatInfo:
    """Thông tin gọn của 1 con mèo, dùng để hiển thị lên bảng trong GUI."""

    id: int
    unlocked: bool
    current_form: int
    unlocked_forms: int
    level_base: int
    level_plus: int

    @property
    def level_total(self) -> int:
        return self.level_base + self.level_plus


class BattleCatsBackend:
    """API mà GUI sẽ gọi. Không có Tkinter/print/input nào ở đây."""

    def __init__(self) -> None:
        self._save_file: Optional[core.SaveFile] = None
        self._loaded_path: Optional[Path] = None

    # ---------- Quản lý file save ----------

    @property
    def is_loaded(self) -> bool:
        return self._save_file is not None

    @property
    def loaded_path(self) -> Optional[Path]:
        return self._loaded_path

    def load_file(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            raise BackendError(f"Không tìm thấy file: {p}")
        try:
            data = core.Data.from_file(core.Path(str(p)))
            self._save_file = core.SaveFile(data)
        except Exception as exc:  # bcsfe ném nhiều loại exception khác nhau
            raise BackendError(f"Không đọc được save file (sai định dạng?): {exc}") from exc
        self._loaded_path = p

    def save_file(self, path: Optional[str] = None) -> None:
        self._require_loaded()
        target = Path(path) if path else self._loaded_path
        if target is None:
            raise BackendError("Chưa có đường dẫn để lưu.")
        try:
            self._save_file.set_hash(add=True)
            data = self._save_file.to_data()
            data.to_file(core.Path(str(target)))
        except Exception as exc:
            raise BackendError(f"Lưu file thất bại: {exc}") from exc
        self._loaded_path = target

    def _require_loaded(self) -> None:
        if self._save_file is None:
            raise BackendError("Chưa load save file nào.")

    # ---------- Tải save bằng mã Transfer / Confirmation (nhập mã lấy tài khoản) ----------
    # Đây chính là cơ chế "Chuyển dữ liệu sang máy mới" mà game Battle Cats cung cấp
    # sẵn (Settings -> Data Transfer -> Begin Data Transfer). Ta chỉ gọi lại đúng
    # API công khai đó, KHÔNG khai thác lỗ hổng gì cả. Lưu ý: mã transfer chỉ
    # dùng được 1 lần và hết hạn sau một thời gian ngắn.

    VALID_COUNTRY_CODES = ("en", "jp", "kr", "tw")

    def download_from_transfer_code(
        self, transfer_code: str, confirmation_code: str, country_code: str
    ) -> None:
        transfer_code = transfer_code.strip()
        confirmation_code = confirmation_code.strip()
        country_code = country_code.strip().lower()

        if not transfer_code or not confirmation_code:
            raise BackendError("Cần nhập cả Transfer Code và Confirmation Code.")
        if country_code not in self.VALID_COUNTRY_CODES:
            raise BackendError(
                f"Mã quốc gia không hợp lệ. Chọn một trong: {', '.join(self.VALID_COUNTRY_CODES)}"
            )

        cc = core.CountryCode(country_code)
        gv = core.GameVersion(120200)  # giá trị này không ảnh hưởng tới việc tải save

        try:
            server_handler, result = core.ServerHandler.from_codes(
                transfer_code, confirmation_code, cc, gv, print=False
            )
        except Exception as exc:
            raise BackendError(f"Lỗi kết nối tới máy chủ game: {exc}") from exc

        if server_handler is None:
            hint = ""
            if country_code == "jp":
                hint = " (lưu ý: dễ nhầm giữa server JP và TW, thử lại với mã quốc gia khác nếu cần)"
            raise BackendError(
                "Mã transfer/confirmation không hợp lệ, đã hết hạn, hoặc sai mã quốc gia." + hint
            )

        self._save_file = server_handler.save_file
        self._loaded_path = None  # chưa có đường dẫn file cho tới khi người dùng bấm Lưu

    def upload_and_get_new_codes(self) -> tuple[str, str]:
        """Upload save hiện tại lên server game, trả về (transfer_code, confirmation_code)
        MỚI để người dùng nhập lại vào game (Data Transfer -> Recover Data) và nhận
        lại đúng save đã chỉnh sửa. Đây là cách chính thức đưa save sửa xong
        trở lại tài khoản, không cần root/adb.
        """
        self._require_loaded()
        server_handler = core.ServerHandler(self._save_file, print=False)
        try:
            result = server_handler.get_codes(upload_managed_items=False, tries=1)
        except Exception as exc:
            raise BackendError(f"Lỗi khi upload save lên máy chủ: {exc}") from exc

        if result is None:
            raise BackendError(
                "Upload thất bại. Có thể do mất mạng, hoặc save này chưa từng được "
                "tải bằng mã transfer (server cần biết tài khoản để ghi đè)."
            )
        return result

    # ---------- Story of Cats: unlock map / auto-complete chapter / lấy hết treasure ----------
    # save_file.story là core.StoryChapters. get_real_chapters() bỏ qua đúng 1 vị trí
    # không dùng trong danh sách gốc, khớp 1-1 với get_chapter_names() (Empire of Cats
    # I/II/III, Into the Future I/II/III, Cats of the Cosmos I/II/III = 9 chapter).
    # Object trả về là THAM CHIẾU thật tới dữ liệu save -> gọi thẳng method trên đó
    # là ghi trực tiếp vào save, không cần gán ngược lại.
    #
    # (Bản trước có ghi chú "chưa rõ encoding của treasure nên không động vào" —
    # giờ đã đọc kỹ core/game/map/story.py và xác nhận: Stage.set_treasure(level)
    # với level 0=không có, 1..3=các mốc hiển thị trong game, tối đa kỹ thuật 9999.
    # Nên tính năng treasure ở đây AN TOÀN để dùng.)

    TREASURE_MIN = 0
    TREASURE_MAX_DISPLAY = 3  # 0=không có, 1..3=các mốc treasure hiển thị trong game

    def _get_real_story_chapters(self):
        self._require_loaded()
        return self._save_file.story.get_real_chapters()

    def get_story_chapters(self) -> list[dict]:
        chapters = self._get_real_story_chapters()
        try:
            names = core.StoryChapters.get_chapter_names(self._save_file)
        except Exception:
            names = None
        if not names or len(names) != len(chapters):
            names = [f"Chapter {i + 1}" for i in range(len(chapters))]

        result = []
        for i, chapter in enumerate(chapters):
            valid_stages = chapter.get_valid_treasure_stages()
            cleared = sum(1 for s in valid_stages if s.is_cleared())
            treasured = sum(1 for s in valid_stages if s.treasure > 0)
            result.append(
                {
                    "index": i,
                    "name": names[i],
                    "cleared_stages": cleared,
                    "total_stages": len(valid_stages),
                    "treasured_stages": treasured,
                }
            )
        return result

    def clear_story_chapter(self, index: int) -> None:
        """Tự động hoàn thành (clear) toàn bộ chapter — tương đương chơi thắng hết stage."""
        chapters = self._get_real_story_chapters()
        if index < 0 or index >= len(chapters):
            raise BackendError("Chapter không hợp lệ.")
        chapters[index].clear_chapter()

    def collect_story_treasure(self, index: int, level: int = 3) -> None:
        """Lấy hết treasure (kho báu) của mọi stage trong 1 chapter, đặt cùng 1 mức.
        level: 0=xoá treasure, 1..3=mức treasure tăng dần (3=cao nhất, phổ biến nhất
        khi muốn "lấy hết")."""
        chapters = self._get_real_story_chapters()
        if index < 0 or index >= len(chapters):
            raise BackendError("Chapter không hợp lệ.")
        if level < self.TREASURE_MIN:
            raise BackendError("Mức treasure không hợp lệ.")
        for stage in chapters[index].get_valid_treasure_stages():
            stage.set_treasure(level)

    def clear_all_story_chapters(self) -> int:
        """Auto-complete TẤT CẢ chapter Story of Cats cùng lúc. Trả về số chapter đã xử lý."""
        chapters = self._get_real_story_chapters()
        for chapter in chapters:
            chapter.clear_chapter()
        return len(chapters)

    def collect_all_story_treasure(self, level: int = 3) -> int:
        """Lấy hết treasure ở TẤT CẢ chapter cùng lúc. Trả về số chapter đã xử lý."""
        chapters = self._get_real_story_chapters()
        for chapter in chapters:
            for stage in chapter.get_valid_treasure_stages():
                stage.set_treasure(level)
        return len(chapters)

    # ---------- Ototo / Gamototo (căn cứ Ototo: engineers, base materials, pháo) ----------

    def get_engineers(self) -> dict:
        self._require_loaded()
        try:
            max_engineers = core.Ototo.get_max_engineers(self._save_file)
        except Exception:
            max_engineers = 5
        return {"current": self._save_file.ototo.engineers, "max": max_engineers}

    def set_engineers(self, count: int) -> None:
        self._require_loaded()
        if count < 0:
            raise BackendError("Số kỹ sư không được âm.")
        self._save_file.ototo.engineers = count

    def get_base_materials(self) -> list[int]:
        self._require_loaded()
        return [m.amount for m in self._save_file.ototo.base_materials.materials]

    def set_base_materials(self, values: list[int]) -> None:
        self._require_loaded()
        materials = self._save_file.ototo.base_materials.materials
        if len(values) != len(materials):
            raise BackendError("Số lượng giá trị không khớp số loại nguyên liệu.")
        for m, v in zip(materials, values):
            m.amount = int(v)

    def get_cannons(self) -> list[dict]:
        self._require_loaded()
        cannons = self._save_file.ototo.cannons
        if cannons is None:
            return []
        result = []
        for cannon_id, cannon in sorted(cannons.cannons.items()):
            result.append(
                {
                    "id": cannon_id,
                    "development": cannon.development,
                    "levels": list(cannon.levels),
                }
            )
        return result

    def set_cannon(self, cannon_id: int, development: int, levels: list[int]) -> None:
        self._require_loaded()
        cannons = self._save_file.ototo.cannons
        if cannons is None or cannon_id not in cannons.cannons:
            raise BackendError(f"Không tìm thấy pháo id={cannon_id}.")
        cannon = cannons.cannons[cannon_id]
        cannon.development = development
        if len(levels) != len(cannon.levels):
            raise BackendError("Số lượng part level không khớp.")
        cannon.levels = [int(v) for v in levels]

    # ---------- Mèo nâng cao: talent / force true form / force 4th form / xoá mèo ----------

    def force_true_form(self, cat_ids: list[int] | None = None) -> int:
        """Ép true form (form thứ 3) cho danh sách id mèo, hoặc TẤT CẢ mèo đã mở
        khoá nếu cat_ids=None. force=True bỏ qua yêu cầu đã sưu tầm hình ảnh mèo."""
        self._require_loaded()
        cats = self._resolve_cats(cat_ids)
        self._save_file.cats.true_form_cats(self._save_file, cats, force=True)
        return len(cats)

    def force_fourth_form(self, cat_ids: list[int] | None = None) -> int:
        self._require_loaded()
        cats = self._resolve_cats(cat_ids)
        self._save_file.cats.fourth_form_cats(self._save_file, cats, force=True)
        return len(cats)

    def max_all_talents(self, cat_ids: list[int] | None = None) -> int:
        """Đẩy toàn bộ talent của các mèo chỉ định (hoặc tất cả mèo có talent)
        lên mức tối đa theo dữ liệu game thật. Cần internet để tải dữ liệu
        talent; nếu không tải được sẽ báo lỗi rõ ràng thay vì âm thầm bỏ qua."""
        self._require_loaded()
        talent_data = self._save_file.cats.read_talent_data(self._save_file)
        if talent_data is None:
            raise BackendError(
                "Không tải được dữ liệu talent từ game (cần internet). Thử lại sau."
            )
        cats = self._resolve_cats(cat_ids)
        count = 0
        for cat in cats:
            if cat.talents is None:
                continue
            data = talent_data.get_cat_talents(cat)
            if data is None:
                continue
            _names, max_levels, _current, ids = data
            for i, talent_id in enumerate(ids):
                talent = cat.get_talent_from_id(talent_id)
                if talent is not None:
                    talent.level = max_levels[i]
            count += 1
        return count

    def delete_cat(self, cat_id: int) -> None:
        """Xoá 1 mèo khỏi save (khoá lại và reset toàn bộ dữ liệu form/level/talent)."""
        self._require_loaded()
        cat = self._get_cat(cat_id)
        cat.remove(reset=True, save_file=self._save_file)

    def _resolve_cats(self, cat_ids: list[int] | None):
        all_cats = self._save_file.cats.cats
        if cat_ids is None:
            return [c for c in all_cats if c.unlocked]
        wanted = set(cat_ids)
        return [c for c in all_cats if c.id in wanted]

    # ---------- Bản đồ khác: Gauntlet / Legend Quest / Zero Legends / Event Stages ----------
    # Xử lý ĐƠN GIẢN theo đúng yêu cầu: chỉ có nút "Complete toàn bộ" cho mỗi loại,
    # không làm treasure/theo từng chapter riêng như Story of Cats.
    #
    # Gauntlet/LegendQuest/ZeroLegends dùng chung 1 cấu trúc 3 lớp
    # (map -> star -> stage) với top_level.clear_stage(map, star, stage, ...),
    # nên dùng 1 hàm generic. Event Stages có sẵn hàm clear_group(type) riêng,
    # hiệu quả hơn nên dùng thẳng thay vì lặp tay.

    def _clear_entire_chapter_group(self, group) -> int:
        """Generic: clear toàn bộ stage của 1 nhóm dạng map/star/stage
        (Gauntlet, Legend Quest, Zero Legends đều cùng interface này)."""
        cleared = 0
        total_maps = len(group.chapters)
        for map_i in range(total_maps):
            total_stars = group.get_total_stars(map_i)
            for star_i in range(total_stars):
                total_stages = group.get_total_stages(map_i, star_i)
                for stage_i in range(total_stages):
                    group.clear_stage(map_i, star_i, stage_i, 1, True)
                    cleared += 1
        return cleared

    def complete_all_gauntlets(self) -> int:
        self._require_loaded()
        return self._clear_entire_chapter_group(self._save_file.gauntlets)

    def complete_all_legend_quest(self) -> int:
        self._require_loaded()
        return self._clear_entire_chapter_group(self._save_file.legend_quest)

    def complete_all_zero_legends(self) -> int:
        self._require_loaded()
        return self._clear_entire_chapter_group(self._save_file.dojo_chapters)

    def complete_all_event_stages(self) -> int:
        self._require_loaded()
        event_stages = self._save_file.event_stages
        num_types = len(event_stages.chapters)
        for t in range(num_types):
            event_stages.clear_group(t, True)
        return num_types

    # ---------- Accounts folder management ----------
    # Save/load save files into named subfolders under ACCOUNTS_DIR, e.g.
    # accounts/my_main_account/SAVE_DATA. Lets the user keep several accounts
    # side by side and switch between them by folder name.

    ACCOUNTS_DIR = get_app_dir() / "accounts"
    SAVE_FILENAME = "SAVE_DATA"

    def list_accounts(self) -> list[dict]:
        """Return [{name, path, has_save, modified}] for every saved account folder."""
        self.ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
        result = []
        for entry in sorted(self.ACCOUNTS_DIR.iterdir()):
            if entry.is_dir():
                save_path = entry / self.SAVE_FILENAME
                has_save = save_path.exists()
                modified = ""
                if has_save:
                    import datetime

                    ts = save_path.stat().st_mtime
                    modified = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                result.append(
                    {
                        "name": entry.name,
                        "path": str(save_path if has_save else entry),
                        "has_save": has_save,
                        "modified": modified,
                    }
                )
        return result

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise BackendError("Account name cannot be empty.")
        invalid = set('<>:"/\\|?*')
        if any(ch in invalid for ch in name):
            raise BackendError('Account name cannot contain: < > : " / \\ | ? *')
        return name

    def save_to_account(self, name: str) -> str:
        """Save the currently loaded save file into accounts/<name>/SAVE_DATA.
        Returns the full path it was written to."""
        self._require_loaded()
        folder_name = self._sanitize_folder_name(name)
        target_dir = self.ACCOUNTS_DIR / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / self.SAVE_FILENAME
        self.save_file(str(target_path))
        return str(target_path)

    def load_account(self, name: str) -> None:
        """Load a previously saved account back into memory by folder name."""
        folder_name = self._sanitize_folder_name(name)
        target_path = self.ACCOUNTS_DIR / folder_name / self.SAVE_FILENAME
        if not target_path.exists():
            raise BackendError(f"No save file found for account '{folder_name}'.")
        self.load_file(str(target_path))
    # Đây là nhóm tính năng bcsfe expose sẵn dạng get_x()/set_x() thuần,
    # nên bọc lại 1-1 rất đơn giản.

    def get_currencies(self) -> dict:
        self._require_loaded()
        sf = self._save_file
        return {
            "xp": sf.get_xp(),
            "catfood": sf.get_catfood(),
            "normal_tickets": sf.get_normal_tickets(),
            "rare_tickets": sf.get_rare_tickets(),
            "platinum_tickets": sf.get_platinum_tickets(),
            "platinum_shards": sf.get_platinum_shards(),
            "legend_tickets": sf.get_legend_tickets(),
            "np": sf.get_np(),
            "leadership": sf.get_leadership(),
        }

    def set_currencies(self, values: dict) -> None:
        self._require_loaded()
        sf = self._save_file
        setters = {
            "xp": sf.set_xp,
            "catfood": sf.set_catfood,
            "normal_tickets": sf.set_normal_tickets,
            "rare_tickets": sf.set_rare_tickets,
            "platinum_tickets": sf.set_platinum_tickets,
            "platinum_shards": sf.set_platinum_shards,
            "legend_tickets": sf.set_legend_tickets,
            "np": sf.set_np,
            "leadership": sf.set_leadership,
        }
        for key, val in values.items():
            if key not in setters:
                continue
            try:
                setters[key](int(val))
            except (TypeError, ValueError) as exc:
                raise BackendError(f"Giá trị không hợp lệ cho {key}: {val}") from exc

    # ---------- Cats ----------
    # save_file.cats.cats là list các đối tượng Cat (core.game.catbase.cat.Cat)

    def get_cats(self) -> list[CatInfo]:
        self._require_loaded()
        result = []
        for cat in self._save_file.cats.cats:
            result.append(
                CatInfo(
                    id=cat.id,
                    unlocked=bool(cat.unlocked),
                    current_form=cat.current_form,
                    unlocked_forms=cat.unlocked_forms,
                    level_base=cat.upgrade.get_base(),
                    level_plus=cat.upgrade.get_plus(),
                )
            )
        return result

    def set_cat_unlocked(self, cat_id: int, unlocked: bool) -> None:
        self._require_loaded()
        cat = self._get_cat(cat_id)
        cat.unlocked = 1 if unlocked else 0

    def set_cat_level(self, cat_id: int, base: int, plus: int) -> None:
        self._require_loaded()
        cat = self._get_cat(cat_id)
        if base < 1:
            raise BackendError("Level cơ bản (base) tối thiểu là 1.")
        cat.upgrade.base = base - 1  # nội bộ bcsfe lưu base - 1 (get_base() = base+1)
        cat.upgrade.plus = max(0, plus)

    def _get_cat(self, cat_id: int):
        self._require_loaded()
        for cat in self._save_file.cats.cats:
            if cat.id == cat_id:
                return cat
        raise BackendError(f"Không tìm thấy mèo id={cat_id}")

    # ---------- Bulk actions cho mèo (áp dụng cùng lúc cho TẤT CẢ) ----------

    def bulk_unlock_all_cats(self) -> int:
        """Mở khoá toàn bộ mèo, trả về số lượng mèo vừa được mở khoá thêm."""
        self._require_loaded()
        count = 0
        for cat in self._save_file.cats.cats:
            if not cat.unlocked:
                cat.unlocked = 1
                count += 1
        return count

    def bulk_set_all_cats_level(self, base: int, plus: int) -> int:
        """Đặt level base+plus cho TẤT CẢ mèo đã mở khoá. Trả về số mèo bị ảnh hưởng."""
        self._require_loaded()
        if base < 1:
            raise BackendError("Level cơ bản (base) tối thiểu là 1.")
        count = 0
        for cat in self._save_file.cats.cats:
            if not cat.unlocked:
                continue
            cat.upgrade.base = base - 1
            cat.upgrade.plus = max(0, plus)
            count += 1
        return count

    # ---------- Playtime ----------

    FPS = 30

    def get_playtime(self) -> dict:
        self._require_loaded()
        frames = self._save_file.officer_pass.play_time
        total_seconds = frames // self.FPS
        return {
            "hours": total_seconds // 3600,
            "minutes": (total_seconds % 3600) // 60,
            "seconds": total_seconds % 60,
            "frames": frames,
        }

    def set_playtime(self, hours: int, minutes: int, seconds: int) -> None:
        self._require_loaded()
        try:
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        except (TypeError, ValueError) as exc:
            raise BackendError(f"Giá trị thời gian không hợp lệ: {exc}") from exc
        if total_seconds < 0:
            raise BackendError("Thời gian chơi không thể âm.")
        self._save_file.officer_pass.play_time = total_seconds * self.FPS

    # ---------- Story chapters: xem thêm get_story_chapters()/clear_story_chapter()/
    # collect_story_treasure() ở phía trên (đã gộp về đúng 1 bản logic, dùng
    # get_real_chapters() + clear_chapter()/set_treasure() thay vì thao tác tay). ----------

    # ---------- Items dạng mảng (mỗi item có nhiều loại, mỗi loại 1 số lượng) ----------
    # Ví dụ: Catamin có 3 loại (đỏ/xanh/vàng), Catfruit có hàng chục loại theo mèo...
    # save_file.<attr> là list[int] số lượng, ta cố lấy tên hiển thị cho từng vị trí,
    # nếu bcsfe không lấy được tên (do chưa có dữ liệu game tải về) thì dùng tên
    # chung "Loại #i" để không bị vỡ chức năng.

    ARRAY_ITEM_ATTRS = {
        "catamins": "Catamin",
        "catseyes": "Catseye",
        "treasure_chests": "Rương kho báu (Treasure Chest)",
        "catfruit": "Catfruit",
        "labyrinth_medals": "Huy chương mê cung (Labyrinth Medal)",
    }

    def list_array_items(self) -> list[str]:
        """Trả về danh sách khoá (key) các nhóm item dạng mảng đang khả dụng."""
        self._require_loaded()
        return [
            key for key in self.ARRAY_ITEM_ATTRS if hasattr(self._save_file, key)
        ]

    def get_array_item(self, key: str) -> list[tuple[str, int]]:
        """Trả về list (tên hiển thị, số lượng hiện tại) cho 1 nhóm item dạng mảng."""
        self._require_loaded()
        if key not in self.ARRAY_ITEM_ATTRS:
            raise BackendError(f"Nhóm item không hợp lệ: {key}")
        values = getattr(self._save_file, key, None)
        if values is None:
            raise BackendError(f"Save file này không có dữ liệu cho nhóm: {key}")

        names = self._try_get_names(key, len(values))
        return list(zip(names, values))

    def set_array_item(self, key: str, values: list[int]) -> None:
        self._require_loaded()
        if key not in self.ARRAY_ITEM_ATTRS:
            raise BackendError(f"Nhóm item không hợp lệ: {key}")
        current = getattr(self._save_file, key, None)
        if current is None:
            raise BackendError(f"Save file này không có dữ liệu cho nhóm: {key}")
        if len(values) != len(current):
            raise BackendError("Số lượng giá trị không khớp với số loại item.")
        try:
            setattr(self._save_file, key, [int(v) for v in values])
        except (TypeError, ValueError) as exc:
            raise BackendError(f"Giá trị không hợp lệ: {exc}") from exc

    def _try_get_names(self, key: str, count: int) -> list[str]:
        """Cố gắng lấy tên vật phẩm thật từ dữ liệu game (cần dữ liệu game đã tải).
        Nếu thất bại (chưa có dữ liệu / lỗi mạng...), trả về tên chung để không
        chặn người dùng chỉnh số lượng."""
        generic_label = self.ARRAY_ITEM_ATTRS.get(key, key)
        fallback = [f"{generic_label} #{i}" for i in range(count)]
        try:
            names_obj = core.core_data.get_gatya_item_names(self._save_file)
            category_map = {
                "catamins": 6,
                "catseyes": 5,
                "treasure_chests": None,  # lấy qua GatyaItemCategory riêng, bỏ qua fallback
                "labyrinth_medals": 11,
            }
            if key == "catfruit":
                names = core.Matatabi(self._save_file).get_names()
                if not names:
                    return fallback
                result = [n if n else fallback[i] for i, n in enumerate(names)]
                return (result + fallback)[:count]
            cat_id = category_map.get(key)
            if cat_id is None:
                return fallback
            items = core.core_data.get_gatya_item_buy(self._save_file).get_by_category(cat_id)
            if not items:
                return fallback
            result = []
            for i in range(count):
                if i < len(items):
                    name = names_obj.get_name(items[i].id)
                    result.append(name if name else fallback[i])
                else:
                    result.append(fallback[i])
            return result
        except Exception:
            return fallback
    # Gợi ý các nhóm tiếp theo (chưa làm ở bản này):
    #   - Stages / clear progress   -> self._save_file.stage_data...
    #   - Talents                   -> self._save_file.cats.read_talent_data(...)
    #   - Gatya / banners           -> self._save_file.gatya...
    #   - Item packs / basic items  -> bcsfe.cli.edits.basic_items để tham khảo logic
    # Cách làm: mở file tương ứng trong
    #   .../site-packages/bcsfe/cli/edits/<ten>.py để xem nó đọc/ghi
    #   thuộc tính nào trên save_file, rồi thêm 1 phương thức get_*/set_*
    #   mới ở class này theo đúng mẫu trên.
