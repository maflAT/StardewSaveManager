# %%
import os
import xml.etree.ElementTree as ET
from datetime import date
from datetime import timedelta
from pathlib import Path
from typing import ClassVar
from typing import Self
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from PySide6.QtCore import QTimer
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QListWidget
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QStyle
from PySide6.QtWidgets import QToolButton
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget


# %%
class GameTime:
    SEASONS: ClassVar = ["Spring", "Summer", "Fall", "Winter"]

    def __init__(self, year: int | str, season_no: int | str, day: int | str) -> None:
        self.year = int(year)
        self.season_no = int(season_no)  # 1 - 4
        self.season = self.SEASONS[self.season_no]
        self.day = int(day)
        self.short = f"{self.year:02d}-{self.season_no + 1}-{self.day:02d}"
        self.long = f"Day {self.day} of {self.season}, Year {self.year}"

    def __str__(self) -> str:
        return self.short

    @classmethod
    def from_savegame(cls, save_game_info: Path) -> Self:
        root = ET.parse(save_game_info).getroot()
        year = root.find("yearForSaveGame").text
        season_number = root.find("seasonForSaveGame").text
        day = root.find("dayOfMonthForSaveGame").text
        return cls(year, season_number, day)


# %%
def played_time(save_game_info: Path) -> timedelta:
    root = ET.parse(save_game_info).getroot()
    ms = int(root.find("millisecondsPlayed").text)
    return timedelta(seconds=round(ms / 1000))


# %%
class Farm:
    def __init__(self, path: Path) -> None:
        self.save_dir = path.resolve()
        self.full_name = path.stem
        self.name = self.full_name.split("_", 1)[0]
        self.save_file = (self.save_dir / self.full_name).resolve()
        self.game_info = (self.save_dir / "SaveGameInfo").resolve()
        self.backup_dir = (path.parents[1] / "Backup" / self.full_name).resolve()

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.save_dir!r})"

    def __str__(self) -> str:
        return self.name

    @property
    def game_date(self) -> GameTime:
        return GameTime.from_savegame(self.game_info)

    @property
    def play_time(self) -> timedelta:
        return played_time(self.game_info)

    @property
    def backups(self) -> list[Path]:
        return list(self.backup_dir.glob("*.zip"))

    def save(self, target_dir: Path | None = None, file_name: str = "") -> Path:
        target_dir = self.backup_dir if target_dir is None else target_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = file_name or f"{date.today().isoformat()} {self.game_date}.zip"
        file_path = target_dir / file_name
        file_path.touch()
        with ZipFile(file_path, mode="w", compression=ZIP_DEFLATED) as zf:
            zf.write(self.save_file, self.save_file.relative_to(self.save_dir))
            zf.write(self.game_info, self.game_info.relative_to(self.save_dir))
        return file_path


# %%
class Save:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.name = self.path.stem

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self.path!r})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Save):
            return NotImplemented
        return self.path == other.path

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Save):
            return NotImplemented
        return self.path < other.path

    @property
    def farm(self) -> Farm:
        return Farm(self.path.parents[2] / "Saves" / self.path.parts[-2])

    def restore(self) -> None:
        with ZipFile(self.path, mode="r") as zf:
            zf.extractall(self.farm.save_dir)


# %%
class PathSelector(QWidget):
    sig_path_changed = Signal(object)  # Path | None

    def __init__(self) -> None:
        super().__init__()
        # -------------------------------- Attributes -------------------------------- #
        self.path: Path | None = None
        self._path_str: str = ""
        # ---------------------------------- Actions --------------------------------- #
        icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self.browse_action = QAction(icon, "...", self)
        self.browse_action.setToolTip("Select folder...")
        # ---------------------------------- Widgets --------------------------------- #
        self.path_edit = QLineEdit()
        self.path_edit.setMinimumWidth(300)
        # adjust height so that it matches a QToolButton with default font
        m = self.path_edit.textMargins()
        self.path_edit.setTextMargins(m.left(), m.top() - 1, m.right(), m.bottom() - 1)
        self.browse_btn = QToolButton()
        self.browse_btn.setDefaultAction(self.browse_action)
        # ---------------------------------- Layout ---------------------------------- #
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.browse_btn)
        # ---------------------------- Connect GUI events ---------------------------- #
        self.browse_btn.clicked.connect(self._on_browse_click)
        self.path_edit.returnPressed.connect(self._on_return_press)
        self.path_edit.editingFinished.connect(self._on_edit_finished)

    # ---------------------------------- Public API ---------------------------------- #
    def set_path(self, path: Path | None) -> None:
        if path is not None and not path.is_dir():
            raise ValueError(path)
        self._set_path(path)

    # -------------------------------- Private Methods ------------------------------- #
    def _set_path(self, path: Path | None) -> None:
        self.path = None if path is None else path.resolve()
        self._path_str = "" if path is None else str(self.path)
        self.path_edit.setText(self._path_str)
        self.sig_path_changed.emit(self.path)

    # ----------------------------------- Callbacks ---------------------------------- #
    def _on_browse_click(self) -> None:
        title = "Select save file location"
        return_path = QFileDialog.getExistingDirectory(self, title, dir=self._path_str)
        if return_path:
            self._set_path(Path(return_path))

    def _on_return_press(self) -> None:
        text = self.path_edit.text()
        if text == "":
            self._set_path(None)
        elif (path := Path(text)).is_dir():
            self._set_path(path)

    def _on_edit_finished(self) -> None:
        self.path_edit.setText(self._path_str)


# %%
class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        # -------------------------------- Attributes -------------------------------- #
        self._saves: list[Save] = []
        # ---------------------------------- Widgets --------------------------------- #
        game_folder_label = QLabel("Game Folder:")
        self.path_selector = PathSelector()
        farm_label = QLabel("Farm:")
        self.farm_cb = QComboBox()
        save_date_label = QLabel("In-Game Date:")
        self.game_date_disp = QLabel()
        play_time_label = QLabel("Played Time:")
        self.play_time_disp = QLabel()
        self.save_list = QListWidget()
        self.save_btn = QPushButton("Save")
        self.save_btn.setEnabled(False)
        self.restore_btn = QPushButton("Restore")
        self.restore_btn.setEnabled(False)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setEnabled(False)
        # ---------------------------------- Layout ---------------------------------- #
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.delete_btn)

        saves_layout = QHBoxLayout()
        saves_layout.addWidget(self.save_list)
        saves_layout.addLayout(btn_layout)
        saves_box = QGroupBox("Backups:")
        saves_box.setLayout(saves_layout)

        main_layout = QGridLayout()
        main_layout.setContentsMargins(9, 9, 9, 9)
        main_layout.addWidget(game_folder_label, 0, 0)
        main_layout.addWidget(self.path_selector, 0, 1)
        main_layout.addWidget(farm_label, 1, 0)
        main_layout.addWidget(self.farm_cb, 1, 1)
        main_layout.addWidget(save_date_label, 2, 0)
        main_layout.addWidget(self.game_date_disp, 2, 1)
        main_layout.addWidget(play_time_label, 3, 0)
        main_layout.addWidget(self.play_time_disp, 3, 1)
        main_layout.addWidget(saves_box, 4, 0, 1, 2)

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(main_layout)
        self.statusBar()
        # -------------------------------- Connections ------------------------------- #
        self.path_selector.sig_path_changed.connect(self._on_game_dir_change)
        self.farm_cb.currentIndexChanged.connect(self._on_farm_change)
        self.save_list.currentRowChanged.connect(self._on_backup_select)
        self.save_btn.clicked.connect(self._on_save_click)
        self.restore_btn.clicked.connect(self._on_restore_click)
        self.delete_btn.clicked.connect(self._on_delete_click)

    # -------------------------------------------------------------------------------- #
    #                                    Public API                                    #
    # -------------------------------------------------------------------------------- #
    @property
    def game_dir(self) -> Path | None:
        return self.path_selector.path

    @property
    def save_dir(self) -> Path | None:
        return self.game_dir and self.game_dir / "Saves"

    @property
    def backup_dir(self) -> Path | None:
        return self.game_dir and self.game_dir / "Backup"

    @property
    def current_farm(self) -> Farm | None:
        return self.farm_cb.currentData()

    @property
    def current_save(self) -> Save | None:
        return None if (row := self.save_list.currentRow()) < 0 else self._saves[row]

    def set_game_folder(self, path: Path | None):
        self.path_selector.set_path(path)

    # -------------------------------------------------------------------------------- #
    #                                     Callbacks                                    #
    # -------------------------------------------------------------------------------- #
    def _on_game_dir_change(self):
        self._populate_farms()
        self._show_status(f"Game data loaded from '{self.game_dir}'")

    def _on_farm_change(self):
        self.save_btn.setEnabled(self.current_farm is not None)
        self._update_game_info()
        self._populate_backups()

    def _on_backup_select(self):
        self.restore_btn.setEnabled(self.current_save is not None)
        self.delete_btn.setEnabled(self.current_save is not None)

    def _on_save_click(self):
        assert self.current_farm is not None
        file = self.current_farm.save()
        self._show_status(f"Successfully backed up '{file}'")
        self._populate_backups()

    def _on_restore_click(self):
        assert self.current_save is not None
        self.current_save.restore()
        self._show_status(f"Successfully restored backup '{self.current_save.path}'")
        self._update_game_info()

    def _on_delete_click(self):
        assert self.current_save is not None
        self.current_save.path.unlink()
        self._show_status(f"Deleted backup '{self.current_save.path}'")
        self.save_list.setFocus()
        self._populate_backups()

    # -------------------------------------------------------------------------------- #
    #                                  Private Methods                                 #
    # -------------------------------------------------------------------------------- #
    def _populate_farms(self):
        self.farm_cb.clear()
        if (d := self.save_dir) is not None:
            for farm in (Farm(p) for p in d.glob(r"*_*") if p.is_dir()):
                self.farm_cb.addItem(farm.name, farm)

    def _populate_backups(self):
        self._saves.clear()
        self.save_list.clear()
        if (f := self.current_farm) is not None:
            self._saves = sorted((Save(p) for p in f.backups), reverse=True)
            self.save_list.addItems([str(s) for s in self._saves])

    def _update_game_info(self):
        if self.current_farm is None:
            self.game_date_disp.clear()
            self.play_time_disp.clear()
        else:
            self.game_date_disp.setText(self.current_farm.game_date.long)
            self.play_time_disp.setText(str(self.current_farm.play_time))

    def _show_status(self, message: str, timeout: int = 6000):
        self.statusBar().showMessage(message, timeout)


# ------------------------------------------------------------------------------------ #
#                                         Test                                         #
# ------------------------------------------------------------------------------------ #
# %%
if __name__ == "__main__":
    appdata = os.getenv("APPDATA")
    GAME_DIR = None if appdata is None else Path(appdata) / "StardewValley"

    app = QApplication.instance() or QApplication()
    app.setApplicationName("Stardew Save Manager")
    app.setApplicationVersion("1.0.0")
    mw = MainWindow()
    mw.show()
    QTimer.singleShot(100, lambda: mw.set_game_folder(GAME_DIR))
    app.exec()
