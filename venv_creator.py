"""
Python 虛擬環境建立工具 (PySide6)
- 深色模式
- 選擇建立位置
- 自動偵測系統上已安裝的 Python 版本（亦可手動指定 python 執行檔）
- 管理環境：選擇 python.exe 列出已安裝套件，可升級 / 移除 / 匯出 requirements.txt，
  並從常用套件清單勾選安裝（可加入自訂常用套件）
- 記錄上次的設定（venv_creator_settings.json，與執行程式同資料夾）
- 右上角可切換繁體中文 / English

資料夾結構：
    venv_creator.py
    logo/
        venv_creator.png   視窗左上角 / 工作列圖示
        venv_creator.ico   exe 圖示

PyInstaller 打包（在本檔所在資料夾執行，需先 pip install pyinstaller PySide6）：
    pyinstaller --noconfirm --onedir --windowed --name VenvCreator --icon logo\\venv_creator.ico --add-data "logo;logo" venv_creator.py

    產出：dist\\VenvCreator\\VenvCreator.exe（整個 dist\\VenvCreator 資料夾要一起帶走）
          dist\\VenvCreator\\_internal\\   執行所需的函式庫與 logo
          設定檔 venv_creator_settings.json 會建立在 VenvCreator.exe 旁邊
    （macOS / Linux 的 --add-data 分隔符改用冒號："logo:logo"）
"""
import os
import re
import sys
import shutil
import subprocess
from pathlib import Path

import json

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import Qt, QThread, Signal, QProcess, QPoint
from PySide6.QtGui import QPalette, QColor, QIcon, QPixmap, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QPlainTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QScrollArea, QSplitter,
    QButtonGroup, QSizePolicy,
)

IS_WIN = sys.platform.startswith("win")
NO_WINDOW = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
APP_NAME = "VenvCreator"
APP_VERSION = "1.0.0"
APP_AUTHOR = "DeanLin"


def resource_path(rel: str) -> Path:
    """取得資源路徑；PyInstaller 打包後資源會解壓到 sys._MEIPASS。"""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def app_dir() -> Path:
    """執行程式所在資料夾：打包後為 exe 所在位置，未打包為 .py 所在位置。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def settings_file() -> Path:
    """設定檔與執行程式放在同一個資料夾。"""
    return app_dir() / "venv_creator_settings.json"


def load_settings() -> dict:
    try:
        return json.loads(settings_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(data: dict):
    try:
        settings_file().write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------- 語系
# 介面文字以繁體中文為鍵值，EN 為對應的英文翻譯；新增文字時要一併加入 EN。
LANGUAGES = [("zh", "中文"), ("en", "EN")]

EN = {
    # 主視窗
    "Python 虛擬環境建立工具": "Python Virtual Environment Creator",
    "建立環境": "Create Environment",
    "管理環境": "Manage Environments",
    "可到「管理環境」分頁安裝套件。": "Go to the \"Manage Environments\" tab to install packages.",
    # 建立環境
    "Python 版本": "Python Version",
    "重新偵測": "Re-detect",
    "手動指定…": "Specify Manually…",
    "建立位置": "Location",
    "瀏覽…": "Browse…",
    "資料夾：": "Folder:",
    "環境名稱：": "Environment name:",
    "選項": "Options",
    "升級 pip / setuptools": "Upgrade pip / setuptools",
    "包含系統 site-packages": "Include system site-packages",
    "建立 Code 資料夾": "Create Code folder",
    "在虛擬環境資料夾內建立 Code 子資料夾（例如 .venv/Code）":
        "Create a Code subfolder inside the virtual environment folder (e.g. .venv/Code)",
    "安裝 requirements.txt：": "Install requirements.txt:",
    "開啟資料夾": "Open Folder",
    "建立中…": "Creating…",
    "偵測中…": "Detecting…",
    "偵測到 {n} 個 Python 版本。": "Detected {n} Python version(s).",
    "找不到 Python，請手動指定": "No Python found, please specify one manually",
    "⚠ 找不到任何 Python，請按「手動指定…」選擇 python 執行檔。":
        "⚠ No Python found. Click \"Specify Manually…\" to choose a python executable.",
    "已載入上次的設定。": "Loaded your previous settings.",
    "所有檔案 (*)": "All files (*)",
    "選擇 python 執行檔": "Select python executable",
    "無效": "Invalid",
    "這不是可執行的 Python。": "This is not a runnable Python.",
    "選擇資料夾": "Select folder",
    "選擇 requirements 檔": "Select requirements file",
    "文字檔 (*.txt);;所有檔案 (*)": "Text files (*.txt);;All files (*)",
    "缺少 Python": "Python Required",
    "請先選擇 Python 版本。": "Please select a Python version first.",
    "資料夾無效": "Invalid Folder",
    "請選擇存在的資料夾。": "Please select an existing folder.",
    "名稱無效": "Invalid Name",
    "請輸入有效的環境名稱。": "Please enter a valid environment name.",
    "{target}\n已存在且非空，要覆寫（--clear）嗎？":
        "{target}\nalready exists and is not empty. Overwrite it (--clear)?",
    "\n\n⚠ 注意：裡面的 Code 資料夾有檔案，覆寫會一併刪除！":
        "\n\n⚠ Warning: the Code folder inside contains files, and overwriting will delete them too!",
    "已存在": "Already Exists",
    "requirements 無效": "Invalid requirements",
    "找不到指定的 requirements 檔。": "The specified requirements file was not found.",
    "建立虛擬環境": "Create virtual environment",
    "升級 pip": "Upgrade pip",
    "安裝 requirements": "Install requirements",
    "✖ 失敗，結束代碼 {code}": "✖ Failed with exit code {code}",
    "✖ 無法啟動程序": "✖ Could not start the process",
    "📁 Code 資料夾已存在：{path}": "📁 Code folder already exists: {path}",
    "📁 Code 資料夾已建立：{path}": "📁 Code folder created: {path}",
    "✖ 無法建立 Code 資料夾：{error}": "✖ Could not create the Code folder: {error}",
    "✔ 完成！\n啟用方式：{act}": "✔ Done!\nTo activate: {act}",
    # 常用套件分類
    "常用工具": "Utilities",
    "資料處理": "Data Processing",
    "GUI / 打包": "GUI / Packaging",
    "網頁 / API": "Web / API",
    "資料庫": "Databases",
    "硬體 / 通訊": "Hardware / Communication",
    "影像": "Imaging",
    "開發工具": "Developer Tools",
    "自訂（右鍵可移除）": "Custom (right-click to remove)",
    # 管理環境
    "目標環境（python.exe 或虛擬環境資料夾）": "Target Environment (python.exe or virtual environment folder)",
    "重新整理": "Refresh",
    "尚未選擇環境": "No environment selected",
    "已安裝套件": "Installed Packages",
    "已安裝套件（讀取中…）": "Installed Packages (loading…)",
    "已安裝套件（{n}）": "Installed Packages ({n})",
    "搜尋套件…": "Search packages…",
    "套件": "Package",
    "版本": "Version",
    "升級選取": "Upgrade Selected",
    "移除選取": "Remove Selected",
    "匯出 requirements.txt": "Export requirements.txt",
    "常用套件（勾選後安裝，綠色勾為已安裝）": "Common Packages (check to install, green check = installed)",
    "其他套件，空白分隔，可加版本，如 django==5.1":
        "Other packages, space-separated, versions allowed, e.g. django==5.1",
    "加入常用": "Add to Common",
    "把左邊輸入的套件加入「自訂」分類，下次也會出現":
        "Add the packages typed on the left to the \"Custom\" category; they will appear next time too",
    "匯入 requirements.txt…": "Import requirements.txt…",
    "讀取 requirements.txt，把套件加入「自訂」分類並勾選未安裝的":
        "Read requirements.txt, add its packages to the \"Custom\" category, and check those not yet installed",
    "取消勾選": "Clear Checks",
    "安裝": "Install",
    "已安裝 {name} {ver}": "Installed: {name} {ver}",
    "匯入 requirements.txt": "Import requirements.txt",
    "匯入失敗": "Import Failed",
    "匯入": "Import",
    "檔案裡沒有找到套件。": "No packages were found in the file.",
    "📄 匯入 {path}\n   共 {total} 個套件，新加入常用 {added} 個，已勾選未安裝 {todo} 個":
        "📄 Imported {path}\n   {total} package(s): {added} added to Common, {todo} not installed and now checked",
    "，按「安裝」即可安裝。": ". Click \"Install\" to install them.",
    "。": ".",
    "移除": "Remove",
    "從常用清單移除「{pkg}」？": "Remove \"{pkg}\" from the Common list?",
    "Python (python.exe);;所有檔案 (*)": "Python (python.exe);;All files (*)",
    "⚠ 無法執行這個 Python": "⚠ Could not run this Python",
    "虛擬環境": "Virtual environment",
    "⚠ 系統 Python（不是虛擬環境，安裝會影響全域）":
        "⚠ System Python (not a virtual environment; installs affect it globally)",
    "這個環境可能沒有 pip": "this environment may not have pip",
    "✖ 讀取套件失敗：{error}": "✖ Failed to read packages: {error}",
    "請勾選或輸入要安裝的套件。": "Please check or enter the packages to install.",
    "安裝 {pkgs}": "Install {pkgs}",
    "升級": "Upgrade",
    "請先在左邊表格選取套件（可 Ctrl / Shift 多選）。":
        "Please select packages in the table on the left first (Ctrl / Shift for multiple).",
    "升級 {pkgs}": "Upgrade {pkgs}",
    "請先在左邊表格選取套件（pip 本身不能移除）。":
        "Please select packages in the table on the left first (pip itself cannot be removed).",
    "確定移除以下套件？\n\n{pkgs}": "Remove the following packages?\n\n{pkgs}",
    "移除 {pkgs}": "Remove {pkgs}",
    "文字檔 (*.txt)": "Text files (*.txt)",
    "✖ 匯出失敗：{error}": "✖ Export failed: {error}",
    "✔ 已匯出 {n} 個套件到 {path}": "✔ Exported {n} package(s) to {path}",
    "未選擇環境": "No Environment Selected",
    "請先選擇 python.exe。": "Please select python.exe first.",
    "✔ 完成": "✔ Done",
    "執行中…": "Running…",
    # 關於
    "關於": "About",
    "Python 虛擬環境圖形化管理工具 — 建立環境、管理套件與匯出 requirements.txt。":
        "A graphical tool for Python virtual environments — create environments, manage packages, and export requirements.txt.",
    "版本 {v}": "Version {v}",
    "環境資訊": "Environment",
    "作者": "Author",
    "設定檔": "Settings file",
    "相關連結": "Links",
    "Python 官方網站": "Python Website",
    "venv 說明文件": "venv Documentation",
    "pip 說明文件": "pip Documentation",
    "Python 下載": "Download Python",
}

_language = "zh"


def set_language(lang):
    global _language
    _language = "en" if lang == "en" else "zh"


def current_language() -> str:
    return _language


def tr(text: str, **kw) -> str:
    """回傳目前語系的文字；kw 會填入文字中的 {欄位}。"""
    s = EN.get(text, text) if _language == "en" else text
    return s.format(**kw) if kw else s


# ---------------------------------------------------------------- 偵測 Python
def probe_python(exe: str):
    """執行指定的 python，回傳 (版本, 真實路徑)；失敗回傳 None。"""
    try:
        out = subprocess.run(
            [exe, "-c", "import sys;print(sys.version.split()[0]);print(sys.executable)"],
            capture_output=True, text=True, timeout=5, creationflags=NO_WINDOW,
        )
        if out.returncode != 0:
            return None
        lines = out.stdout.strip().splitlines()
        if len(lines) >= 2 and lines[1]:
            return lines[0], lines[1]
    except Exception:
        pass
    return None


def find_candidates():
    """收集可能的 python 執行檔路徑。"""
    cands = []

    # Windows: py launcher 會列出所有已註冊的版本
    if IS_WIN and shutil.which("py"):
        try:
            out = subprocess.run(["py", "-0p"], capture_output=True, text=True,
                                 timeout=5, creationflags=NO_WINDOW).stdout
            for line in out.splitlines():
                m = re.search(r"([A-Za-z]:\\.*?python[w]?\.exe)", line, re.I)
                if m:
                    cands.append(m.group(1).strip())
        except Exception:
            pass

    # 掃描 PATH 中的 python / python3 / python3.x
    pattern = re.compile(r"^python(3(\.\d+)?)?(\.exe)?$", re.I)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        if IS_WIN and "WindowsApps" in d:  # 跳過 Microsoft Store 假捷徑
            continue
        try:
            for name in os.listdir(d):
                if pattern.match(name):
                    cands.append(os.path.join(d, name))
        except OSError:
            pass

    # 常見安裝位置
    if IS_WIN:
        roots = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
                 Path("C:/"), Path(os.environ.get("ProgramFiles", "C:/Program Files"))]
        for r in roots:
            if r.is_dir():
                for p in r.glob("Python3*/python.exe"):
                    cands.append(str(p))
    else:
        for r in ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin",
                  str(Path.home() / ".pyenv" / "shims")]:
            if os.path.isdir(r):
                for p in Path(r).glob("python3*"):
                    if pattern.match(p.name):
                        cands.append(str(p))
    return cands


def version_key(v: str):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.]", re.sub(r"[^\d.]", "", v)))


class DetectWorker(QThread):
    found = Signal(list)  # [(version, path), ...]

    def run(self):
        seen, result = set(), []
        for c in find_candidates():
            info = probe_python(c)
            if not info:
                continue
            ver, real = info
            key = os.path.normcase(os.path.realpath(real))
            if key in seen:
                continue
            seen.add(key)
            result.append((ver, real))
        result.sort(key=lambda x: version_key(x[0]), reverse=True)
        self.found.emit(result)


# ---------------------------------------------------------------- 深色主題
def make_check_image() -> str:
    """畫一個白色勾勾 PNG（Qt 樣式表的勾選格需要圖檔路徑）。"""
    import tempfile
    path = Path(tempfile.gettempdir()) / "venv_creator_check.png"
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    qp = QPainter(pm)
    qp.setRenderHint(QPainter.Antialiasing)
    pen = QPen(Qt.white, 4.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    qp.setPen(pen)
    qp.drawPolyline([QPoint(7, 17), QPoint(13, 23), QPoint(25, 9)])
    qp.end()
    pm.save(str(path))
    return path.as_posix()


def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    check = make_check_image()
    p = QPalette()
    bg, base, text = QColor(30, 31, 34), QColor(43, 45, 48), QColor(223, 225, 229)
    accent = QColor(77, 144, 254)
    p.setColor(QPalette.Window, bg)
    p.setColor(QPalette.WindowText, text)
    p.setColor(QPalette.Base, base)
    p.setColor(QPalette.AlternateBase, bg)
    p.setColor(QPalette.ToolTipBase, base)
    p.setColor(QPalette.ToolTipText, text)
    p.setColor(QPalette.Text, text)
    p.setColor(QPalette.Button, QColor(54, 57, 61))
    p.setColor(QPalette.ButtonText, text)
    p.setColor(QPalette.Highlight, accent)
    p.setColor(QPalette.HighlightedText, Qt.white)
    p.setColor(QPalette.PlaceholderText, QColor(120, 124, 130))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        p.setColor(QPalette.Disabled, role, QColor(110, 112, 118))
    app.setPalette(p)
    app.setStyleSheet("""
        QWidget { font-size: 10pt; }
        QGroupBox { border: 1px solid #3c3f44; border-radius: 6px;
                    margin-top: 10px; padding-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px;
                           color: #9aa0a6; }
        QLineEdit, QComboBox, QPlainTextEdit {
            border: 1px solid #3c3f44; border-radius: 4px; padding: 5px;
            background: #2b2d30; }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #4d90fe; }
        QPushButton { border: 1px solid #45484d; border-radius: 4px;
                      padding: 6px 14px; background: #36393d; }
        QPushButton:hover { background: #41454a; }
        QPushButton:disabled { color: #6e7076; background: #2b2d30; }
        QPushButton#primary { background: #2f6fde; border: 1px solid #2f6fde;
                              color: white; font-weight: bold; }
        QPushButton#primary:hover { background: #3d7ef0; }
        QPushButton#primary:disabled { background: #2b3a55; border-color: #2b3a55; }
        QPushButton#lang_zh, QPushButton#lang_en { padding: 3px 12px; min-width: 24px;
                                                   background: #2b2d30; color: #9aa0a6; }
        QPushButton#lang_zh { border-top-right-radius: 0; border-bottom-right-radius: 0; }
        QPushButton#lang_en { border-top-left-radius: 0; border-bottom-left-radius: 0;
                              border-left: none; }
        QPushButton#lang_zh:hover, QPushButton#lang_en:hover { background: #36393d; }
        QPushButton#lang_zh:checked, QPushButton#lang_en:checked {
            background: #2f6fde; border-color: #2f6fde; color: white; }
        QPlainTextEdit { font-family: Consolas, "Cascadia Mono", Menlo, monospace; }
        QTabWidget::pane { border: 1px solid #3c3f44; border-radius: 6px; top: -1px; }
        QTabBar::tab { background: #2b2d30; border: 1px solid #3c3f44; border-bottom: none;
                       padding: 7px 18px; margin-right: 2px;
                       border-top-left-radius: 6px; border-top-right-radius: 6px; color: #9aa0a6; }
        QTabBar::tab:selected { background: #1e1f22; color: #dfe1e5; border-bottom: 2px solid #4d90fe; }
        QTabBar::tab:hover:!selected { background: #36393d; }
        QTableWidget { background: #2b2d30; border: 1px solid #3c3f44; border-radius: 4px;
                       gridline-color: #3c3f44; alternate-background-color: #26282b; }
        QHeaderView::section { background: #36393d; color: #9aa0a6; border: none;
                               border-right: 1px solid #3c3f44; padding: 5px; }
        QScrollArea { background: transparent; border: none; }
        QScrollArea > QWidget > QWidget { background: transparent; }
        QLabel#category { color: #4d90fe; font-weight: bold; margin-top: 6px; }
        QLabel#aboutTitle { font-size: 24pt; font-weight: 600; color: #4d90fe; }
        QLabel#aboutVersion { font-size: 12pt; }
        QLabel#aboutMuted { color: #9aa0a6; }
        QGroupBox#aboutGroup::title { color: #4d90fe; }
        QSplitter::handle { background: transparent; }
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #5a5e66;
                               border-radius: 3px; background: #2b2d30; }
        QCheckBox::indicator:hover { border-color: #4d90fe; }
        QCheckBox::indicator:checked { background: #2f6fde; border-color: #2f6fde;
                                       image: url(CHECK); }
        QCheckBox::indicator:checked:disabled { background: #2e8b57; border-color: #2e8b57;
                                                image: url(CHECK); }
        QCheckBox::indicator:disabled:!checked { background: #26282b; border-color: #3c3f44; }
    """.replace("CHECK", check))


# ---------------------------------------------------------------- 主視窗
class TranslatablePage(QWidget):
    """可在執行中切換語系的分頁：記住各元件的文字，retranslate() 時重新套用。"""

    def __init__(self):
        super().__init__()
        self._bindings = []   # 固定文字：(setter, 中文鍵值)
        self._live = {}       # 依狀態變動的文字：名稱 -> (setter, render)

    def make(self, cls, text):
        """建立帶文字的元件（QLabel / QPushButton / QCheckBox / QGroupBox）。"""
        w = cls(tr(text))
        self._bindings.append((w.setTitle if isinstance(w, QGroupBox) else w.setText, text))
        return w

    def bind(self, setter, text):
        """設定固定文字（提示字、tooltip 等）。"""
        setter(tr(text))
        self._bindings.append((setter, text))

    def live(self, name, setter, render):
        """設定依狀態變動的文字；render 會在切換語系時重新呼叫。"""
        self._live[name] = (setter, render)
        setter(render())

    def retranslate(self):
        for setter, text in self._bindings:
            setter(tr(text))
        for setter, render in self._live.values():
            setter(render())


class CreatePage(TranslatablePage):
    """分頁一：建立虛擬環境"""
    env_created = Signal(str)  # 建立成功後送出新環境的 python 路徑

    def __init__(self, settings: dict):
        super().__init__()
        self.proc = None
        self.steps = []
        self.settings = settings
        self._build_ui()
        self.apply_settings()
        self.detect_pythons()

    # 設定 ------------------------------------------------------------
    def apply_settings(self):
        """套用上次成功建立時的設定（Python 版本在偵測完成後才套用）。"""
        s = self.settings
        if not s:
            return
        if s.get("base_dir") and os.path.isdir(s["base_dir"]):
            self.ed_dir.setText(s["base_dir"])
        if s.get("name"):
            self.ed_name.setText(s["name"])
        self.chk_upgrade.setChecked(s.get("upgrade", True))
        self.chk_site.setChecked(s.get("system_site", False))
        self.chk_code.setChecked(s.get("code_dir", True))
        self.chk_req.setChecked(s.get("use_req", False))
        self.ed_req.setText(s.get("req_path", ""))

    def store_settings(self):
        self.settings.update({
            "python": self.cmb_py.currentData(),
            "base_dir": self.ed_dir.text().strip(),
            "name": self.ed_name.text().strip(),
            "upgrade": self.chk_upgrade.isChecked(),
            "system_site": self.chk_site.isChecked(),
            "code_dir": self.chk_code.isChecked(),
            "use_req": self.chk_req.isChecked(),
            "req_path": self.ed_req.text().strip(),
        })
        save_settings(self.settings)

    def select_saved_python(self):
        saved = self.settings.get("python")
        if not saved:
            return
        idx = self.cmb_py.findData(saved)
        if idx < 0 and os.path.isfile(saved):  # 不在偵測清單（例如手動指定的）
            info = probe_python(saved)
            if info:
                if not self.cmb_py.itemData(0):
                    self.cmb_py.clear()
                self.cmb_py.addItem(f"Python {info[0]}    —    {info[1]}", info[1])
                idx = self.cmb_py.count() - 1
                self.btn_create.setEnabled(True)
        if idx >= 0:
            self.cmb_py.setCurrentIndex(idx)

    # UI ------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Python 版本
        g1 = self.make(QGroupBox, "Python 版本")
        l1 = QHBoxLayout(g1)
        self.cmb_py = QComboBox()
        self.cmb_py.setMinimumWidth(420)
        btn_refresh = self.make(QPushButton, "重新偵測")
        btn_refresh.clicked.connect(self.detect_pythons)
        btn_custom = self.make(QPushButton, "手動指定…")
        btn_custom.clicked.connect(self.pick_python)
        l1.addWidget(self.cmb_py, 1)
        l1.addWidget(btn_refresh)
        l1.addWidget(btn_custom)
        root.addWidget(g1)

        # 位置 & 名稱
        g2 = self.make(QGroupBox, "建立位置")
        l2 = QGridLayout(g2)
        self.ed_dir = QLineEdit(str(Path.cwd()))
        btn_dir = self.make(QPushButton, "瀏覽…")
        btn_dir.clicked.connect(self.pick_dir)
        self.ed_name = QLineEdit(".venv")
        self.lbl_full = QLabel()
        self.lbl_full.setStyleSheet("color:#9aa0a6;")
        self.ed_dir.textChanged.connect(self.update_full_path)
        self.ed_name.textChanged.connect(self.update_full_path)
        l2.addWidget(self.make(QLabel, "資料夾："), 0, 0)
        l2.addWidget(self.ed_dir, 0, 1)
        l2.addWidget(btn_dir, 0, 2)
        l2.addWidget(self.make(QLabel, "環境名稱："), 1, 0)
        l2.addWidget(self.ed_name, 1, 1, 1, 2)
        l2.addWidget(self.lbl_full, 2, 1, 1, 2)
        root.addWidget(g2)

        # 選項
        g3 = self.make(QGroupBox, "選項")
        l3 = QGridLayout(g3)
        self.chk_upgrade = self.make(QCheckBox, "升級 pip / setuptools")
        self.chk_upgrade.setChecked(True)
        self.chk_site = self.make(QCheckBox, "包含系統 site-packages")
        self.chk_code = self.make(QCheckBox, "建立 Code 資料夾")
        self.chk_code.setChecked(True)
        self.bind(self.chk_code.setToolTip, "在虛擬環境資料夾內建立 Code 子資料夾（例如 .venv/Code）")
        self.chk_req = self.make(QCheckBox, "安裝 requirements.txt：")
        self.ed_req = QLineEdit()
        self.ed_req.setEnabled(False)
        btn_req = self.make(QPushButton, "瀏覽…")
        btn_req.setEnabled(False)
        btn_req.clicked.connect(self.pick_req)
        self.chk_req.toggled.connect(self.ed_req.setEnabled)
        self.chk_req.toggled.connect(btn_req.setEnabled)
        l3.addWidget(self.chk_upgrade, 0, 0)
        l3.addWidget(self.chk_site, 0, 1)
        l3.addWidget(self.chk_code, 0, 2)
        l3.addWidget(self.chk_req, 1, 0)
        l3.addWidget(self.ed_req, 1, 1)
        l3.addWidget(btn_req, 1, 2)
        root.addWidget(g3)

        # 按鈕列
        hb = QHBoxLayout()
        self.btn_open = self.make(QPushButton, "開啟資料夾")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_folder)
        self.btn_create = QPushButton()
        self.live("btn_create", self.btn_create.setText, lambda: tr("建立環境"))
        self.btn_create.setObjectName("primary")
        self.btn_create.clicked.connect(self.create_env)
        hb.addStretch()
        hb.addWidget(self.btn_open)
        hb.addWidget(self.btn_create)
        root.addLayout(hb)

        # 紀錄
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

        self.update_full_path()

    # 偵測 ------------------------------------------------------------
    def detect_pythons(self):
        self.cmb_py.clear()
        self.show_python_hint("偵測中…")
        self.cmb_py.setEnabled(False)
        self.btn_create.setEnabled(False)
        self.worker = DetectWorker()
        self.worker.found.connect(self.on_detected)
        self.worker.start()

    def show_python_hint(self, text):
        """在下拉選單顯示提示項目（沒有 Python 路徑資料的第一項）。"""
        self.cmb_py.addItem("")
        self.live("py_hint", self._set_python_hint, lambda: tr(text))

    def _set_python_hint(self, s):
        if not self.cmb_py.itemData(0):   # 提示項目已被實際的 Python 取代時不動作
            self.cmb_py.setItemText(0, s)

    def on_detected(self, items):
        self.cmb_py.clear()
        for ver, path in items:
            self.cmb_py.addItem(f"Python {ver}    —    {path}", path)
        self.cmb_py.setEnabled(True)
        self.btn_create.setEnabled(bool(items))
        if items:
            self.append(tr("偵測到 {n} 個 Python 版本。", n=len(items)))
        else:
            self.show_python_hint("找不到 Python，請手動指定")
            self.append(tr("⚠ 找不到任何 Python，請按「手動指定…」選擇 python 執行檔。"))
        self.select_saved_python()
        if self.settings.get("python"):
            self.append(tr("已載入上次的設定。"))

    def pick_python(self):
        flt = "Python (python*.exe)" if IS_WIN else tr("所有檔案 (*)")
        path, _ = QFileDialog.getOpenFileName(self, tr("選擇 python 執行檔"), "", flt)
        if not path:
            return
        info = probe_python(path)
        if not info:
            QMessageBox.warning(self, tr("無效"), tr("這不是可執行的 Python。"))
            return
        ver, real = info
        idx = self.cmb_py.findData(real)
        if idx < 0:
            if not self.cmb_py.itemData(0):  # 移除「找不到」提示
                self.cmb_py.clear()
            self.cmb_py.addItem(f"Python {ver}    —    {real}", real)
            idx = self.cmb_py.count() - 1
        self.cmb_py.setCurrentIndex(idx)
        self.btn_create.setEnabled(True)

    # 路徑 ------------------------------------------------------------
    def pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("選擇資料夾"), self.ed_dir.text())
        if d:
            self.ed_dir.setText(d)

    def pick_req(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("選擇 requirements 檔"),
                                           self.ed_dir.text(), tr("文字檔 (*.txt);;所有檔案 (*)"))
        if f:
            self.ed_req.setText(f)

    def target_path(self) -> Path:
        return Path(self.ed_dir.text().strip()) / self.ed_name.text().strip()

    def update_full_path(self):
        self.lbl_full.setText(f"→ {self.target_path()}")

    def env_python(self) -> Path:
        t = self.target_path()
        return t / "Scripts" / "python.exe" if IS_WIN else t / "bin" / "python"

    def open_folder(self):
        p = str(self.target_path())
        if IS_WIN:
            os.startfile(p)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])

    # 建立 ------------------------------------------------------------
    def create_env(self):
        py = self.cmb_py.currentData()
        base = self.ed_dir.text().strip()
        name = self.ed_name.text().strip()
        if not py:
            QMessageBox.warning(self, tr("缺少 Python"), tr("請先選擇 Python 版本。"))
            return
        if not base or not os.path.isdir(base):
            QMessageBox.warning(self, tr("資料夾無效"), tr("請選擇存在的資料夾。"))
            return
        if not name or re.search(r'[<>:"/\\|?*]', name):
            QMessageBox.warning(self, tr("名稱無效"), tr("請輸入有效的環境名稱。"))
            return
        target = self.target_path()
        if target.exists() and any(target.iterdir()):
            msg = tr("{target}\n已存在且非空，要覆寫（--clear）嗎？", target=target)
            code_dir = target / "Code"
            if code_dir.is_dir() and any(code_dir.iterdir()):
                msg += tr("\n\n⚠ 注意：裡面的 Code 資料夾有檔案，覆寫會一併刪除！")
            r = QMessageBox.question(self, tr("已存在"), msg)
            if r != QMessageBox.Yes:
                return
            clear = True
        else:
            clear = False
        req = self.ed_req.text().strip()
        if self.chk_req.isChecked() and not os.path.isfile(req):
            QMessageBox.warning(self, tr("requirements 無效"), tr("找不到指定的 requirements 檔。"))
            return

        # 組步驟
        args = ["-m", "venv", str(target)]
        if self.chk_site.isChecked():
            args.append("--system-site-packages")
        if clear:
            args.append("--clear")
        self.steps = [(tr("建立虛擬環境"), py, args)]
        env_py = str(self.env_python())
        if self.chk_upgrade.isChecked():
            self.steps.append((tr("升級 pip"), env_py,
                               ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"]))
        if self.chk_req.isChecked():
            self.steps.append((tr("安裝 requirements"), env_py,
                               ["-m", "pip", "install", "-r", req]))

        self.log.clear()
        self.set_busy(True)
        self.run_next_step()

    def run_next_step(self):
        if not self.steps:
            self.finish(True)
            return
        title, prog, args = self.steps.pop(0)
        self.append(f"\n▶ {title}\n$ {prog} {' '.join(args)}")
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.read_output)
        self.proc.finished.connect(self.step_finished)
        self.proc.errorOccurred.connect(self.proc_error)
        self.proc.start(prog, args)

    def read_output(self):
        data = bytes(self.proc.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        if IS_WIN and "\ufffd" in text:
            text = data.decode("cp950", errors="replace")
        self.log.insertPlainText(text)
        self.log.ensureCursorVisible()

    def step_finished(self, code, _status):
        if code == 0:
            self.run_next_step()
        else:
            self.append(tr("✖ 失敗，結束代碼 {code}", code=code))
            self.finish(False)

    def proc_error(self, err):
        if err == QProcess.FailedToStart:
            self.append(tr("✖ 無法啟動程序"))
            self.finish(False)

    def finish(self, ok):
        self.steps = []
        self.set_busy(False)
        if ok:
            t = self.target_path()
            # 在虛擬環境內建立 Code 資料夾（需在 venv 建好後才做，避免被 --clear 清掉）
            if self.chk_code.isChecked():
                code_dir = t / "Code"
                try:
                    existed = code_dir.exists()
                    code_dir.mkdir(parents=True, exist_ok=True)
                    self.append("\n" + tr("📁 Code 資料夾已存在：{path}" if existed else "📁 Code 資料夾已建立：{path}",
                                          path=code_dir))
                except OSError as e:
                    self.append("\n" + tr("✖ 無法建立 Code 資料夾：{error}", error=e))
            act = (rf"{t}\Scripts\activate" if IS_WIN else f"source {t}/bin/activate")
            self.append("\n" + tr("✔ 完成！\n啟用方式：{act}", act=act))
            self.btn_open.setEnabled(True)
            self.store_settings()
            self.env_created.emit(str(self.env_python()))

    def set_busy(self, busy):
        self.btn_create.setEnabled(not busy)
        self.live("btn_create", self.btn_create.setText, lambda: tr("建立中…" if busy else "建立環境"))
        self.cmb_py.setEnabled(not busy)

    def append(self, s):
        self.log.appendPlainText(s)


# ---------------------------------------------------------------- 管理環境
COMMON_PACKAGES = {
    "常用工具": ["requests", "python-dotenv", "tqdm", "rich", "pyyaml"],
    "資料處理": ["numpy", "pandas", "scipy", "openpyxl", "matplotlib"],
    "GUI / 打包": ["PySide6", "pyinstaller", "pillow"],
    "網頁 / API": ["flask", "fastapi", "uvicorn", "beautifulsoup4", "lxml"],
    "資料庫": ["sqlalchemy", "psycopg2-binary"],
    "硬體 / 通訊": ["pyserial", "paho-mqtt"],
    "影像": ["opencv-python"],
    "開發工具": ["pytest", "black", "ruff", "ipykernel"],
}


def norm_pkg(name: str) -> str:
    """套件名稱正規化（PEP 503）：大小寫、底線、點都視為相同。"""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(path: str) -> list:
    """讀取 requirements.txt，回傳套件名稱（去掉版本、extras、註解與 pip 選項）。"""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp950"):   # PowerShell 的 pip freeze > 會產生 UTF-16
        try:
            text = raw.decode(enc)
            if "\x00" not in text:
                break
        except UnicodeDecodeError:
            continue
    names, seen = [], set()
    for line in text.splitlines():
        line = line.split(" #")[0].split("\t#")[0].strip()
        # 略過 pip 選項（-r、-e、--index-url…）、本機路徑、網址與「套件 @ 網址」直接參照
        if not line or line.startswith(("#", "-", ".", "/", "\\")) or "://" in line or "@" in line:
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if m and norm_pkg(m.group(1)) not in seen:
            seen.add(norm_pkg(m.group(1)))
            names.append(m.group(1))
    return names


def resolve_python(path: str) -> str:
    """接受 python 執行檔或虛擬環境資料夾，回傳 python 執行檔路徑。"""
    p = Path(path.strip().strip('"'))
    if p.is_dir():
        for cand in (p / "Scripts" / "python.exe", p / "bin" / "python", p / "python.exe"):
            if cand.is_file():
                return str(cand)
    return str(p)


class ManagePage(TranslatablePage):
    """分頁二：管理既有環境的 pip 套件"""

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.proc = None
        self.installed = {}      # 正規化名稱 -> (原名, 版本)
        self.pkg_checks = {}     # 正規化名稱 -> QCheckBox
        self._build_ui()
        saved = self.settings.get("manage_python")
        if saved and os.path.isfile(saved):
            self.set_python(saved)

    # UI ------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # 目標環境
        g1 = self.make(QGroupBox, "目標環境（python.exe 或虛擬環境資料夾）")
        l1 = QGridLayout(g1)
        self.ed_py = QLineEdit()
        self.ed_py.returnPressed.connect(lambda: self.set_python(self.ed_py.text()))
        btn_browse = self.make(QPushButton, "瀏覽…")
        btn_browse.clicked.connect(self.pick_python)
        self.btn_reload = self.make(QPushButton, "重新整理")
        self.btn_reload.clicked.connect(lambda: self.set_python(self.ed_py.text()))
        self.lbl_info = QLabel()
        self.set_info(lambda: tr("尚未選擇環境"), "#9aa0a6")
        l1.addWidget(self.ed_py, 0, 0)
        l1.addWidget(btn_browse, 0, 1)
        l1.addWidget(self.btn_reload, 0, 2)
        l1.addWidget(self.lbl_info, 1, 0, 1, 3)
        root.addWidget(g1)

        split = QSplitter(Qt.Horizontal)

        # 左：已安裝套件
        g2 = QGroupBox()
        self.g_installed = g2
        self.set_installed_title(lambda: tr("已安裝套件"))
        l2 = QVBoxLayout(g2)
        self.ed_filter = QLineEdit()
        self.bind(self.ed_filter.setPlaceholderText, "搜尋套件…")
        self.ed_filter.textChanged.connect(self.apply_filter)
        self.table = QTableWidget(0, 2)
        self.live("table_headers", self.table.setHorizontalHeaderLabels, lambda: [tr("套件"), tr("版本")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        hb2 = QHBoxLayout()
        self.btn_upgrade = self.make(QPushButton, "升級選取")
        self.btn_upgrade.clicked.connect(self.upgrade_selected)
        self.btn_uninstall = self.make(QPushButton, "移除選取")
        self.btn_uninstall.clicked.connect(self.uninstall_selected)
        self.btn_freeze = self.make(QPushButton, "匯出 requirements.txt")
        self.btn_freeze.clicked.connect(self.export_requirements)
        hb2.addWidget(self.btn_upgrade)
        hb2.addWidget(self.btn_uninstall)
        hb2.addStretch()
        hb2.addWidget(self.btn_freeze)
        l2.addWidget(self.ed_filter)
        l2.addWidget(self.table, 1)
        l2.addLayout(hb2)
        split.addWidget(g2)

        # 右：常用套件
        g3 = self.make(QGroupBox, "常用套件（勾選後安裝，綠色勾為已安裝）")
        l3 = QVBoxLayout(g3)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        l3.addWidget(self.scroll, 1)
        hb3 = QHBoxLayout()
        self.ed_extra = QLineEdit()
        self.bind(self.ed_extra.setPlaceholderText, "其他套件，空白分隔，可加版本，如 django==5.1")
        btn_add = self.make(QPushButton, "加入常用")
        self.bind(btn_add.setToolTip, "把左邊輸入的套件加入「自訂」分類，下次也會出現")
        btn_add.clicked.connect(self.add_custom)
        btn_import = self.make(QPushButton, "匯入 requirements.txt…")
        self.bind(btn_import.setToolTip, "讀取 requirements.txt，把套件加入「自訂」分類並勾選未安裝的")
        btn_import.clicked.connect(self.import_requirements)
        hb3.addWidget(self.ed_extra, 1)
        hb3.addWidget(btn_add)
        l3.addLayout(hb3)
        hb4 = QHBoxLayout()
        btn_clear = self.make(QPushButton, "取消勾選")
        btn_clear.clicked.connect(self.clear_checks)
        self.btn_install = QPushButton()
        self.btn_install.setObjectName("primary")
        self.btn_install.clicked.connect(self.install_selected)
        hb4.addWidget(btn_import)
        hb4.addStretch()
        hb4.addWidget(btn_clear)
        hb4.addWidget(self.btn_install)
        l3.addLayout(hb4)
        split.addWidget(g3)
        split.setSizes([420, 420])
        root.addWidget(split, 3)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

        self.build_common_list()
        self.set_busy(False)

    def retranslate(self):
        super().retranslate()
        for lbl, cat in self.category_labels:
            lbl.setText(tr(cat))
        self.mark_installed()   # 更新「已安裝」提示

    def set_info(self, render, color):
        self.live("info", self.lbl_info.setText, render)
        self.lbl_info.setStyleSheet(f"color:{color};")

    def set_installed_title(self, render):
        self.live("installed_title", self.g_installed.setTitle, render)

    def build_common_list(self):
        """建立常用套件勾選清單（含使用者自訂）。"""
        checked = {k for k, c in self.pkg_checks.items() if c.isChecked() and c.isEnabled()}
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(4, 0, 4, 4)
        self.pkg_checks = {}
        self.category_labels = []
        groups = dict(COMMON_PACKAGES)
        custom = self.settings.get("custom_packages", [])
        if custom:
            groups["自訂（右鍵可移除）"] = custom
        row = 0
        for cat, pkgs in groups.items():
            lbl = QLabel(tr(cat))
            lbl.setObjectName("category")
            self.category_labels.append((lbl, cat))
            grid.addWidget(lbl, row, 0, 1, 2)
            row += 1
            for i, pkg in enumerate(pkgs):
                cb = QCheckBox(pkg)
                cb.setProperty("pkg", pkg)
                if pkg in custom:
                    cb.setContextMenuPolicy(Qt.CustomContextMenu)
                    cb.customContextMenuRequested.connect(
                        lambda _pos, p=pkg: self.remove_custom(p))
                key = norm_pkg(re.split(r"[<>=!~\[ ]", pkg)[0])
                self.pkg_checks[key] = cb
                if key in checked:
                    cb.setChecked(True)
                grid.addWidget(cb, row + i // 2, i % 2)
            row += (len(pkgs) + 1) // 2
        grid.setRowStretch(row, 1)
        self.scroll.setWidget(w)
        self.mark_installed()

    def mark_installed(self):
        for key, cb in self.pkg_checks.items():
            pkg = cb.property("pkg")
            if key in self.installed:
                name, ver = self.installed[key]
                cb.setText(f"{pkg}  ({ver})")
                cb.setChecked(True)          # 勾選格顯示綠色 ✓
                cb.setEnabled(False)
                cb.setToolTip(tr("已安裝 {name} {ver}", name=name, ver=ver))
            else:
                if not cb.isEnabled():       # 原本是已安裝（例如剛被移除）
                    cb.setChecked(False)
                cb.setText(pkg)
                cb.setEnabled(True)
                cb.setToolTip("")

    # 自訂常用 ------------------------------------------------------------
    def add_custom(self):
        pkgs = self.ed_extra.text().split()
        if not pkgs:
            return
        custom = self.settings.setdefault("custom_packages", [])
        existing = set(self.pkg_checks)
        for p in pkgs:
            if norm_pkg(re.split(r"[<>=!~\[ ]", p)[0]) not in existing and p not in custom:
                custom.append(p)
        save_settings(self.settings)
        self.ed_extra.clear()
        self.build_common_list()

    def import_requirements(self):
        start = str(Path(self.python()).parent.parent) if self.python() else ""
        path, _ = QFileDialog.getOpenFileName(self, tr("匯入 requirements.txt"), start,
                                              tr("文字檔 (*.txt);;所有檔案 (*)"))
        if not path:
            return
        try:
            names = parse_requirements(path)
        except OSError as e:
            QMessageBox.warning(self, tr("匯入失敗"), str(e))
            return
        if not names:
            QMessageBox.information(self, tr("匯入"), tr("檔案裡沒有找到套件。"))
            return
        custom = self.settings.setdefault("custom_packages", [])
        known = set(self.pkg_checks)
        added = []
        for n in names:
            if norm_pkg(n) not in known:
                custom.append(n)
                known.add(norm_pkg(n))
                added.append(n)
        save_settings(self.settings)
        self.build_common_list()
        # 勾選檔案中尚未安裝的套件，按「安裝」即可一次裝好
        todo = []
        for n in names:
            cb = self.pkg_checks.get(norm_pkg(n))
            if cb and cb.isEnabled():
                cb.setChecked(True)
                todo.append(n)
        self.append("\n" + tr("📄 匯入 {path}\n   共 {total} 個套件，新加入常用 {added} 個，已勾選未安裝 {todo} 個",
                              path=path, total=len(names), added=len(added), todo=len(todo))
                    + tr("，按「安裝」即可安裝。" if todo else "。"))

    def remove_custom(self, pkg):
        if QMessageBox.question(self, tr("移除"), tr("從常用清單移除「{pkg}」？", pkg=pkg)) != QMessageBox.Yes:
            return
        custom = self.settings.get("custom_packages", [])
        if pkg in custom:
            custom.remove(pkg)
            save_settings(self.settings)
            self.build_common_list()

    def clear_checks(self):
        for cb in self.pkg_checks.values():
            if cb.isEnabled():
                cb.setChecked(False)

    # 環境 ------------------------------------------------------------
    def pick_python(self):
        start = os.path.dirname(self.ed_py.text()) if self.ed_py.text() else ""
        flt = tr("Python (python.exe);;所有檔案 (*)") if IS_WIN else tr("所有檔案 (*)")
        path, _ = QFileDialog.getOpenFileName(self, tr("選擇 python 執行檔"), start, flt)
        if path:
            self.set_python(path)

    def python(self) -> str:
        return self.ed_py.text().strip()

    def set_python(self, path: str):
        path = resolve_python(path)
        self.ed_py.setText(path)
        info = probe_python(path) if path else None
        if not info:
            self.set_info(lambda: tr("⚠ 無法執行這個 Python"), "#e0a030")
            self.installed = {}
            self.table.setRowCount(0)
            self.mark_installed()
            self.set_busy(False)
            return
        ver, _real = info
        is_venv = (Path(path).parent.parent / "pyvenv.cfg").is_file()
        kind = "虛擬環境" if is_venv else "⚠ 系統 Python（不是虛擬環境，安裝會影響全域）"
        self.set_info(lambda: f"Python {ver}  ·  {tr(kind)}", "#9aa0a6" if is_venv else "#e0a030")
        self.settings["manage_python"] = path
        save_settings(self.settings)
        self.refresh_list()

    def refresh_list(self):
        """用 pip list 讀取已安裝套件（非同步）。"""
        if not self.python():
            return
        self.set_busy(True)
        self.set_installed_title(lambda: tr("已安裝套件（讀取中…）"))
        p = QProcess(self)
        p.finished.connect(lambda code, _s, p=p: self.on_list_done(p, code))
        p.start(self.python(), ["-m", "pip", "list", "--format=json",
                                "--disable-pip-version-check"])
        self.list_proc = p

    def on_list_done(self, p, code):
        out = bytes(p.readAllStandardOutput()).decode("utf-8", errors="replace")
        err = bytes(p.readAllStandardError()).decode("utf-8", errors="replace")
        self.installed = {}
        try:
            for item in json.loads(out) if code == 0 else []:
                self.installed[norm_pkg(item["name"])] = (item["name"], item["version"])
        except ValueError:
            pass
        if code != 0:
            self.append(tr("✖ 讀取套件失敗：{error}", error=err.strip() or tr("這個環境可能沒有 pip")))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.installed))
        for r, (name, ver) in enumerate(sorted(self.installed.values(), key=lambda x: x[0].lower())):
            self.table.setItem(r, 0, QTableWidgetItem(name))
            self.table.setItem(r, 1, QTableWidgetItem(ver))
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.AscendingOrder)
        count = len(self.installed)
        self.set_installed_title(lambda: tr("已安裝套件（{n}）", n=count))
        self.apply_filter()
        self.mark_installed()
        self.set_busy(False)

    def apply_filter(self):
        kw = self.ed_filter.text().strip().lower()
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            self.table.setRowHidden(r, bool(kw) and kw not in it.text().lower())

    def selected_packages(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        return [self.table.item(r, 0).text() for r in sorted(rows)]

    # pip 動作 ------------------------------------------------------------
    def install_selected(self):
        pkgs = [cb.property("pkg") for cb in self.pkg_checks.values()
                if cb.isChecked() and cb.isEnabled()]
        pkgs += self.ed_extra.text().split()
        if not pkgs:
            QMessageBox.information(self, tr("安裝"), tr("請勾選或輸入要安裝的套件。"))
            return
        self.run_pip(["install", *pkgs], tr("安裝 {pkgs}", pkgs=" ".join(pkgs)))
        self.ed_extra.clear()

    def upgrade_selected(self):
        pkgs = self.selected_packages()
        if not pkgs:
            QMessageBox.information(self, tr("升級"), tr("請先在左邊表格選取套件（可 Ctrl / Shift 多選）。"))
            return
        self.run_pip(["install", "--upgrade", *pkgs], tr("升級 {pkgs}", pkgs=" ".join(pkgs)))

    def uninstall_selected(self):
        pkgs = [p for p in self.selected_packages() if norm_pkg(p) != "pip"]
        if not pkgs:
            QMessageBox.information(self, tr("移除"), tr("請先在左邊表格選取套件（pip 本身不能移除）。"))
            return
        if QMessageBox.question(self, tr("移除"), tr("確定移除以下套件？\n\n{pkgs}", pkgs="\n".join(pkgs))) != QMessageBox.Yes:
            return
        self.run_pip(["uninstall", "-y", *pkgs], tr("移除 {pkgs}", pkgs=" ".join(pkgs)))

    def export_requirements(self):
        if not self.python():
            return
        start = str(Path(self.python()).parent.parent / "requirements.txt")
        path, _ = QFileDialog.getSaveFileName(self, tr("匯出 requirements.txt"), start,
                                              tr("文字檔 (*.txt)"))
        if not path:
            return
        r = subprocess.run([self.python(), "-m", "pip", "freeze", "--disable-pip-version-check"],
                           capture_output=True, text=True, creationflags=NO_WINDOW)
        if r.returncode != 0:
            self.append(tr("✖ 匯出失敗：{error}", error=r.stderr.strip()))
            return
        Path(path).write_text(r.stdout, encoding="utf-8")
        self.append(tr("✔ 已匯出 {n} 個套件到 {path}", n=len(r.stdout.splitlines()), path=path))

    def run_pip(self, args, title):
        if not self.python():
            QMessageBox.warning(self, tr("未選擇環境"), tr("請先選擇 python.exe。"))
            return
        args = ["-m", "pip", *args, "--disable-pip-version-check"]
        self.append(f"\n▶ {title}\n$ {self.python()} {' '.join(args)}")
        self.set_busy(True)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.read_output)
        self.proc.finished.connect(self.on_pip_done)
        self.proc.errorOccurred.connect(
            lambda e: e == QProcess.FailedToStart and self.on_pip_done(-1, None))
        self.proc.start(self.python(), args)

    def read_output(self):
        data = bytes(self.proc.readAllStandardOutput())
        text = data.decode("utf-8", errors="replace")
        if IS_WIN and "\ufffd" in text:
            text = data.decode("cp950", errors="replace")
        self.log.moveCursor(self.log.textCursor().MoveOperation.End)
        self.log.insertPlainText(text)
        self.log.ensureCursorVisible()

    def on_pip_done(self, code, _status):
        self.append(tr("✔ 完成") if code == 0 else tr("✖ 失敗，結束代碼 {code}", code=code))
        self.refresh_list()

    def set_busy(self, busy):
        has_py = bool(self.python())
        for b in (self.btn_install, self.btn_upgrade, self.btn_uninstall,
                  self.btn_freeze, self.btn_reload):
            b.setEnabled(not busy and has_py)
        self.live("btn_install", self.btn_install.setText, lambda: tr("執行中…" if busy else "安裝"))

    def append(self, s):
        self.log.appendPlainText(s)


# ---------------------------------------------------------------- 關於
class AboutPage(TranslatablePage):
    """分頁三：程式資訊"""
    LOGO_SIZE = 112
    LINKS = (("Python 官方網站", "https://www.python.org/"),
             ("venv 說明文件", "https://docs.python.org/3/library/venv.html"),
             ("pip 說明文件", "https://pip.pypa.io/"),
             ("PyPI", "https://pypi.org/"),
             ("Python 下載", "https://www.python.org/downloads/"))

    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)
        root.addLayout(self._build_header())
        root.addWidget(self._build_info())
        root.addWidget(self._build_links())
        root.addStretch(1)

    def _build_header(self):
        """左邊圖示，右邊名稱、版本與簡介。"""
        header = QHBoxLayout()
        header.setSpacing(24)
        logo = self._logo_label()
        if logo:
            header.addWidget(logo)
        text = QVBoxLayout()
        text.setSpacing(6)
        title = QLabel(APP_NAME)
        title.setObjectName("aboutTitle")
        version = QLabel()
        version.setObjectName("aboutVersion")
        self.live("version", version.setText, lambda: tr("版本 {v}", v=APP_VERSION))
        desc = self.make(QLabel, "Python 虛擬環境圖形化管理工具 — 建立環境、管理套件與匯出 requirements.txt。")
        desc.setObjectName("aboutMuted")
        desc.setWordWrap(True)
        text.addStretch(1)
        text.addWidget(title)
        text.addWidget(version)
        text.addWidget(desc)
        text.addStretch(1)
        header.addLayout(text, 1)
        return header

    def _build_info(self):
        box = self.make(QGroupBox, "環境資訊")
        box.setObjectName("aboutGroup")
        grid = QGridLayout(box)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        rows = (("作者", APP_AUTHOR),
                ("Python", sys.version.split()[0]),
                ("PySide6", PYSIDE_VERSION),
                ("設定檔", str(settings_file())))
        for r, (name, value) in enumerate(rows):
            val = QLabel(value)
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # 路徑過長時不撐寬視窗
            val.setToolTip(value)
            grid.addWidget(self.make(QLabel, name), r, 0)
            grid.addWidget(val, r, 1)
        return box

    def _build_links(self):
        box = self.make(QGroupBox, "相關連結")
        box.setObjectName("aboutGroup")
        lay = QVBoxLayout(box)
        lay.setSpacing(8)
        for i, (name, url) in enumerate(self.LINKS):
            lbl = QLabel()
            lbl.setOpenExternalLinks(True)
            self.live(f"link{i}", lbl.setText, lambda n=name, u=url: (
                f'<a href="{u}" style="color:#4d90fe; text-decoration:none;">{tr(n)}</a>'
                f'&nbsp;&nbsp;<a href="{u}" style="color:#9aa0a6; text-decoration:none;">{u}</a>'))
            lay.addWidget(lbl)
        return box

    def _logo_label(self):
        pm = QPixmap(str(resource_path("logo/venv_creator.png")))
        if pm.isNull():
            return None
        ratio = self.devicePixelRatioF()
        pm = pm.scaled(int(self.LOGO_SIZE * ratio), int(self.LOGO_SIZE * ratio),
                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(ratio)
        lbl = QLabel()
        lbl.setPixmap(pm)
        lbl.setAlignment(Qt.AlignCenter)
        return lbl


# ---------------------------------------------------------------- 主視窗
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(str(resource_path("logo/venv_creator.png"))))
        self.resize(900, 680)
        self.settings = load_settings()
        set_language(self.settings.get("language"))
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.create_page = CreatePage(self.settings)
        self.manage_page = ManagePage(self.settings)
        self.tabs.addTab(self.create_page, "")
        self.tabs.addTab(self.manage_page, "")
        self.about_page = AboutPage()
        self.tabs.addTab(self.about_page, "")
        self.tabs.setCornerWidget(self._build_language_switch(), Qt.TopRightCorner)
        lay.addWidget(self.tabs)
        self.create_page.env_created.connect(self.on_env_created)
        self.retranslate()

    def _build_language_switch(self) -> QWidget:
        """分頁列右上角的語系切換按鈕。"""
        corner = QWidget()
        lay = QHBoxLayout(corner)
        lay.setContentsMargins(0, 0, 0, 3)
        lay.setSpacing(0)
        group = QButtonGroup(corner)   # 同一時間只會有一個按鈕被選取
        self.lang_buttons = {}
        for code, label in LANGUAGES:
            btn = QPushButton(label)
            btn.setObjectName(f"lang_{code}")
            btn.setCheckable(True)
            btn.setChecked(code == current_language())
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, c=code: self.change_language(c))
            group.addButton(btn)
            lay.addWidget(btn)
            self.lang_buttons[code] = btn
        return corner

    def change_language(self, code):
        if code == current_language():
            return
        set_language(code)
        self.settings["language"] = current_language()
        save_settings(self.settings)
        self.retranslate()

    def retranslate(self):
        self.setWindowTitle(tr("Python 虛擬環境建立工具"))
        self.tabs.setTabText(0, tr("建立環境"))
        self.tabs.setTabText(1, tr("管理環境"))
        self.tabs.setTabText(2, tr("關於"))
        self.create_page.retranslate()
        self.manage_page.retranslate()
        self.about_page.retranslate()

    def on_env_created(self, py):
        self.manage_page.set_python(py)
        self.create_page.append(tr("可到「管理環境」分頁安裝套件。"))

    def closeEvent(self, e):
        save_settings(self.settings)
        super().closeEvent(e)


if __name__ == "__main__":
    if IS_WIN:
        # 讓工作列顯示自己的圖示，而不是 python.exe 的
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DeanLin.VenvCreator")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(resource_path("logo/venv_creator.png"))))
    apply_dark_theme(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
