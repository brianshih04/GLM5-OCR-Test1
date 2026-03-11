"""
AI 離線雙層 PDF 轉換服務 - 主視窗
Main GUI Window using PyQt-Fluent-Widgets
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, Theme,
    FluentIcon as FIF, PushButton, PrimaryPushButton, CardWidget,
    BodyLabel, SubtitleLabel, StrongBodyLabel, InfoBar, InfoBarPosition,
    ProgressBar, ComboBox, LineEdit, SwitchButton, TextEdit
)

from folder_watcher import FolderWatcher
from ocr_engine import OCREngine
from pdf_builder import PDFBuilder

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# 預設設定
DEFAULT_MODEL_NAME = "glm-ocr:q8_0"
DEFAULT_FONT_NAME = "NotoSansTC-VariableFont_wght.ttf"
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}


def get_default_font_path() -> Path:
    """取得預設字型路徑"""
    fonts_dir = Path(__file__).parent / 'fonts'
    default_path = fonts_dir / DEFAULT_FONT_NAME

    # 優先使用預設字型
    if default_path.exists():
        return default_path

    # 自動搜尋其他可用字型
    if fonts_dir.exists():
        for ttf_file in fonts_dir.glob('*.ttf'):
            logger.info(f"自動使用字型: {ttf_file.name}")
            return ttf_file

    return default_path  # 回傳預設路徑（可能不存在）


def init_ocr_and_pdf_engines(model_name: str = DEFAULT_MODEL_NAME,
                              font_path: Path = None,
                              dpi: int = 150):
    """
    初始化 OCR 引擎和 PDF 建構器

    Args:
        model_name: Ollama 模型名稱
        font_path: 字型檔案路徑
        dpi: 影像 DPI

    Returns:
        (ocr_engine, pdf_builder) 或 (None, None) 如果初始化失敗
    """
    try:
        # 使用預設字型路徑（如果未指定）
        if font_path is None:
            font_path = get_default_font_path()

        # 初始化 OCR 引擎
        ocr_engine = OCREngine(model_name=model_name)

        # 初始化 PDF 建構器
        pdf_builder = PDFBuilder(font_path)

        return ocr_engine, pdf_builder

    except Exception as e:
        logger.error(f"引擎初始化失敗: {e}")
        return None, None


class ConversionThread(QThread):
    """轉換工作執行緒 - 支援單檔和批次轉換"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)
    file_done = pyqtSignal(str, bool)  # (檔名, 是否成功)

    def __init__(self, image_paths: List[Path], ocr_engine, pdf_builder,
                 output_dir: Optional[Path] = None, dpi: int = 150):
        super().__init__()
        self.image_paths = image_paths
        self.ocr_engine = ocr_engine
        self.pdf_builder = pdf_builder
        self.output_dir = output_dir
        self.dpi = dpi
        self._cancelled = False

    def cancel(self):
        """取消轉換"""
        self._cancelled = True

    def run(self):
        total = len(self.image_paths)
        success_count = 0
        fail_count = 0

        for idx, image_path in enumerate(self.image_paths):
            if self._cancelled:
                self.log.emit("轉換已取消")
                break

            self.log.emit(f"[{idx + 1}/{total}] 處理中: {image_path.name}")

            # 計算整體進度
            base_progress = int((idx / total) * 100)
            self.progress.emit(base_progress)

            try:
                # 執行 OCR
                ocr_text = self.ocr_engine.process_image(image_path)
                if ocr_text is None:
                    self.log.emit(f"  ✗ OCR 識別失敗: {image_path.name}")
                    self.file_done.emit(image_path.name, False)
                    fail_count += 1
                    continue

                self.progress.emit(base_progress + int(60 / total))
                self.log.emit(f"  OCR 完成，文字長度: {len(ocr_text)}")

                # 決定輸出路徑
                if self.output_dir:
                    output_path = self.output_dir / image_path.with_suffix('.pdf').name
                else:
                    output_path = image_path.with_suffix('.pdf')

                # 建立 PDF
                success = self.pdf_builder.create_dual_layer_pdf(
                    image_path, ocr_text, output_path, dpi=self.dpi
                )

                if success:
                    self.log.emit(f"  ✓ 完成: {output_path.name}")
                    self.file_done.emit(image_path.name, True)
                    success_count += 1
                else:
                    self.log.emit(f"  ✗ PDF 建立失敗: {image_path.name}")
                    self.file_done.emit(image_path.name, False)
                    fail_count += 1

            except Exception as e:
                self.log.emit(f"  ✗ 錯誤: {str(e)}")
                self.file_done.emit(image_path.name, False)
                fail_count += 1

        self.progress.emit(100)

        # 彙整結果
        if self._cancelled:
            self.finished.emit(False, f"轉換已取消（成功 {success_count}，失敗 {fail_count}）")
        elif fail_count == 0:
            self.finished.emit(True, f"全部轉換成功！共 {success_count} 個檔案")
        else:
            self.finished.emit(
                success_count > 0,
                f"轉換完成：成功 {success_count}，失敗 {fail_count}"
            )


class ConversionInterface(QWidget):
    """單檔/批次轉換介面 - 支援拖放"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.ocr_engine = None
        self.pdf_builder = None
        self.conversion_thread = None
        self.selected_files: List[Path] = []
        self.setAcceptDrops(True)
        self.initUI()

    def initUI(self):
        """初始化 UI（使用佈局管理器）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        # 標題
        self.title_label = SubtitleLabel("影像轉換")
        layout.addWidget(self.title_label)

        # 按鈕列
        btn_layout = QHBoxLayout()
        self.select_file_btn = PushButton("選擇檔案")
        self.select_file_btn.clicked.connect(self.select_files)
        btn_layout.addWidget(self.select_file_btn)

        self.select_folder_btn = PushButton("選擇資料夾內所有圖片")
        self.select_folder_btn.clicked.connect(self.select_folder_images)
        btn_layout.addWidget(self.select_folder_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 拖放提示 & 檔案列表
        self.file_list_label = BodyLabel("拖放影像檔案到此處，或使用上方按鈕選擇")
        self.file_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_list_label.setMinimumHeight(60)
        self.file_list_label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 8px; padding: 16px; color: #888;"
        )
        layout.addWidget(self.file_list_label)

        # 輸出路徑
        output_layout = QHBoxLayout()
        output_layout.addWidget(BodyLabel("輸出目錄:"))
        self.output_path_edit = LineEdit()
        self.output_path_edit.setPlaceholderText("與原檔同目錄（留空）或指定輸出目錄")
        output_layout.addWidget(self.output_path_edit, stretch=1)
        self.browse_output_btn = PushButton("瀏覽")
        self.browse_output_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.browse_output_btn)
        layout.addLayout(output_layout)

        # 轉換按鈕
        action_layout = QHBoxLayout()
        self.convert_btn = PrimaryPushButton("開始轉換")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        action_layout.addWidget(self.convert_btn)

        self.cancel_btn = PushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setEnabled(False)
        action_layout.addWidget(self.cancel_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # 進度條
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 狀態標籤
        self.status_label = StrongBodyLabel("準備就緒")
        layout.addWidget(self.status_label)

        # 日誌輸出
        self.log_edit = TextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText("轉換日誌將顯示在這裡...")
        self.log_edit.setMinimumHeight(120)
        layout.addWidget(self.log_edit, stretch=1)

    # --- 拖放支援 ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 檢查是否有支援的影像檔案
            for url in event.mimeData().urls():
                if Path(url.toLocalFile()).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                    event.acceptProposedAction()
                    self.file_list_label.setStyleSheet(
                        "border: 2px solid #0078d4; border-radius: 8px; "
                        "padding: 16px; background-color: rgba(0, 120, 212, 0.05);"
                    )
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.file_list_label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 8px; padding: 16px; color: #888;"
        )

    def dropEvent(self, event: QDropEvent):
        self.file_list_label.setStyleSheet(
            "border: 2px dashed #888; border-radius: 8px; padding: 16px; color: #888;"
        )

        files = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                files.append(path)
            elif path.is_dir():
                for ext in SUPPORTED_IMAGE_EXTENSIONS:
                    files.extend(path.glob(f'*{ext}'))

        if files:
            self._set_selected_files(files)
            event.acceptProposedAction()

    # --- 檔案選擇 ---
    def select_files(self):
        """選擇一或多個檔案"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "選擇影像檔案",
            "",
            "影像檔案 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;所有檔案 (*)"
        )
        if file_paths:
            self._set_selected_files([Path(p) for p in file_paths])

    def select_folder_images(self):
        """選擇資料夾中所有圖片"""
        folder = QFileDialog.getExistingDirectory(self, "選擇包含影像的資料夾")
        if folder:
            folder_path = Path(folder)
            files = []
            for ext in SUPPORTED_IMAGE_EXTENSIONS:
                files.extend(folder_path.glob(f'*{ext}'))
                files.extend(folder_path.glob(f'*{ext.upper()}'))
            files = sorted(set(files))
            if files:
                self._set_selected_files(files)
            else:
                InfoBar.warning(
                    title="未找到影像",
                    content=f"資料夾中沒有支援的影像檔案",
                    parent=self.parent_window,
                    position=InfoBarPosition.TOP
                )

    def browse_output_dir(self):
        """瀏覽輸出目錄"""
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出目錄")
        if folder:
            self.output_path_edit.setText(folder)

    def _set_selected_files(self, files: List[Path]):
        """設定已選擇的檔案"""
        self.selected_files = files
        count = len(files)
        names = [f.name for f in files[:5]]
        display = ', '.join(names)
        if count > 5:
            display += f' ... (共 {count} 個檔案)'
        else:
            display = f'{display} (共 {count} 個檔案)'

        self.file_list_label.setText(display)
        self.file_list_label.setStyleSheet(
            "border: 2px solid #28a745; border-radius: 8px; padding: 16px;"
        )
        self.convert_btn.setEnabled(True)
        self.status_label.setText(f"已選擇 {count} 個檔案，準備轉換")

    # --- 轉換控制 ---
    def start_conversion(self):
        """開始轉換"""
        if not self.selected_files:
            InfoBar.error(
                title="錯誤",
                content="請選擇影像檔案",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
            return

        # 從設定頁面取得參數
        settings = self._get_settings()

        # 初始化 OCR 引擎和 PDF 建構器
        if self.ocr_engine is None or self.pdf_builder is None:
            self.init_engines(settings['model_name'], settings['font_path'])

        if self.ocr_engine is None or not self.ocr_engine.is_ready():
            InfoBar.error(
                title="引擎未就緒",
                content="OCR 引擎未初始化，請檢查 Ollama 服務和模型設定",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
            return

        # 決定輸出目錄
        output_dir = None
        output_text = self.output_path_edit.text().strip()
        if output_text:
            output_dir = Path(output_text)
            output_dir.mkdir(parents=True, exist_ok=True)

        # 清空日誌
        self.log_edit.clear()

        # 建立轉換執行緒
        self.conversion_thread = ConversionThread(
            self.selected_files,
            self.ocr_engine,
            self.pdf_builder,
            output_dir=output_dir,
            dpi=settings['dpi']
        )
        self.conversion_thread.progress.connect(self.progress_bar.setValue)
        self.conversion_thread.finished.connect(self.on_conversion_finished)
        self.conversion_thread.log.connect(self._append_log)
        self.conversion_thread.start()

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.select_file_btn.setEnabled(False)
        self.select_folder_btn.setEnabled(False)
        self.status_label.setText("轉換中...")

    def cancel_conversion(self):
        """取消轉換"""
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.cancel()
            self.status_label.setText("正在取消...")

    def init_engines(self, model_name: str = None, font_path: Path = None):
        """初始化 OCR 引擎和 PDF 建構器"""
        model_name = model_name or DEFAULT_MODEL_NAME
        self.ocr_engine, self.pdf_builder = init_ocr_and_pdf_engines(
            model_name=model_name, font_path=font_path
        )

        if self.ocr_engine is None:
            InfoBar.error(
                title="初始化失敗",
                content="OCR 引擎初始化失敗，請檢查 Ollama 服務和模型",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )

    def on_conversion_finished(self, success, message):
        """轉換完成回調"""
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.select_file_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(True)
        self.status_label.setText(message)

        if success:
            InfoBar.success(
                title="完成",
                content=message,
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.warning(
                title="完成（有錯誤）",
                content=message,
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )

    def _append_log(self, text: str):
        """追加日誌文字"""
        self.log_edit.append(text)

    def _get_settings(self) -> dict:
        """從設定介面取得目前設定"""
        settings = {
            'model_name': DEFAULT_MODEL_NAME,
            'font_path': get_default_font_path(),
            'dpi': 150,
        }

        # 嘗試從 MainWindow 的設定介面取得值
        if self.parent_window and hasattr(self.parent_window, 'settings_interface'):
            si = self.parent_window.settings_interface
            try:
                model_name = si.model_combo.currentText().strip()
                if model_name:
                    settings['model_name'] = model_name

                font_text = si.font_path_edit.text().strip()
                if font_text:
                    settings['font_path'] = Path(font_text)

                dpi_text = si.dpi_combo.currentText().strip()
                if dpi_text.isdigit():
                    settings['dpi'] = int(dpi_text)

            except Exception as e:
                logger.warning(f"讀取設定失敗，使用預設值: {e}")

        return settings


class HotFolderInterface(QWidget):
    """熱資料夾監控介面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.folder_watcher = None
        self.ocr_engine = None
        self.pdf_builder = None
        self.is_watching = False
        self.processed_count = 0
        self.initUI()

    def initUI(self):
        """初始化 UI（使用佈局管理器）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        # 標題
        self.title_label = SubtitleLabel("熱資料夾監控")
        layout.addWidget(self.title_label)

        # 監控資料夾選擇
        input_layout = QHBoxLayout()
        input_layout.addWidget(BodyLabel("監控資料夾:"))
        self.folder_path_edit = LineEdit()
        self.folder_path_edit.setPlaceholderText("請選擇要監控的資料夾")
        self.folder_path_edit.setReadOnly(True)
        input_layout.addWidget(self.folder_path_edit, stretch=1)
        self.select_folder_btn = PushButton("瀏覽")
        self.select_folder_btn.clicked.connect(self.select_folder)
        input_layout.addWidget(self.select_folder_btn)
        layout.addLayout(input_layout)

        # 輸出資料夾
        output_layout = QHBoxLayout()
        output_layout.addWidget(BodyLabel("輸出資料夾:"))
        self.output_folder_edit = LineEdit()
        self.output_folder_edit.setPlaceholderText("輸出資料夾（自動生成）")
        self.output_folder_edit.setReadOnly(True)
        output_layout.addWidget(self.output_folder_edit, stretch=1)
        layout.addLayout(output_layout)

        # 控制按鈕
        ctrl_layout = QHBoxLayout()
        self.toggle_watch_btn = PrimaryPushButton("開始監控")
        self.toggle_watch_btn.clicked.connect(self.toggle_watching)
        self.toggle_watch_btn.setEnabled(False)
        ctrl_layout.addWidget(self.toggle_watch_btn)
        ctrl_layout.addStretch()

        self.stats_label = StrongBodyLabel("已處理: 0 個檔案")
        ctrl_layout.addWidget(self.stats_label)
        layout.addLayout(ctrl_layout)

        # 狀態標籤
        self.status_label = BodyLabel("準備就緒")
        layout.addWidget(self.status_label)

        # 日誌面板
        self.log_edit = TextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setPlaceholderText("監控日誌...")
        self.log_edit.setMinimumHeight(150)
        layout.addWidget(self.log_edit, stretch=1)

    def select_folder(self):
        """選擇資料夾"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "選擇監控資料夾"
        )

        if folder_path:
            self.folder_path_edit.setText(folder_path)
            # 自動產生輸出資料夾
            output_folder = Path(folder_path) / 'output'
            self.output_folder_edit.setText(str(output_folder))
            self.toggle_watch_btn.setEnabled(True)
            self.status_label.setText("已選擇資料夾，準備監控")

    def toggle_watching(self):
        """切換監控狀態"""
        if self.is_watching:
            self.stop_watching()
        else:
            self.start_watching()

    def start_watching(self):
        """開始監控"""
        folder_path = self.folder_path_edit.text()
        output_folder = self.output_folder_edit.text()

        if not folder_path or not output_folder:
            InfoBar.error(
                title="錯誤",
                content="請選擇監控資料夾",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
            return

        # 初始化 OCR 引擎和 PDF 建構器
        if self.ocr_engine is None:
            self.init_engines()

        if self.ocr_engine is None or not self.ocr_engine.is_ready():
            InfoBar.error(
                title="錯誤",
                content="OCR 引擎未初始化，請檢查 Ollama 服務和模型",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
            return

        # 建立輸出資料夾
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        # 建立資料夾監控器
        self.folder_watcher = FolderWatcher(
            folder_path,
            self.process_file,
            recursive=True
        )
        self.folder_watcher.start()

        self.is_watching = True
        self.toggle_watch_btn.setText("停止監控")
        self.status_label.setText("監控中...")
        self.select_folder_btn.setEnabled(False)
        self.log_edit.append(f"✓ 開始監控: {folder_path}")

    def stop_watching(self):
        """停止監控"""
        if self.folder_watcher:
            self.folder_watcher.stop()
            self.folder_watcher = None

        self.is_watching = False
        self.toggle_watch_btn.setText("開始監控")
        self.status_label.setText("監控已停止")
        self.select_folder_btn.setEnabled(True)
        self.log_edit.append("■ 監控已停止")

    def init_engines(self):
        """初始化 OCR 引擎和 PDF 建構器"""
        # 從設定介面取得模型名稱
        model_name = DEFAULT_MODEL_NAME
        if self.parent_window and hasattr(self.parent_window, 'settings_interface'):
            try:
                model_name = self.parent_window.settings_interface.model_combo.currentText().strip() or DEFAULT_MODEL_NAME
            except Exception:
                pass

        self.ocr_engine, self.pdf_builder = init_ocr_and_pdf_engines(model_name=model_name)

        if self.ocr_engine is None:
            InfoBar.error(
                title="初始化失敗",
                content="OCR 引擎初始化失敗，請檢查 Ollama 服務和模型",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )

    def process_file(self, file_path):
        """處理檔案（由 FolderWatcher 回調呼叫）"""
        try:
            self.log_edit.append(f"處理: {file_path.name}")

            # 執行 OCR
            ocr_text = self.ocr_engine.process_image(file_path)
            if ocr_text is None:
                self.log_edit.append(f"  ✗ OCR 失敗: {file_path.name}")
                return

            # 生成輸出路徑
            output_folder = Path(self.output_folder_edit.text())
            output_path = output_folder / file_path.with_suffix('.pdf').name

            # 取得 DPI 設定
            dpi = 150
            if self.parent_window and hasattr(self.parent_window, 'settings_interface'):
                try:
                    dpi_text = self.parent_window.settings_interface.dpi_combo.currentText()
                    dpi = int(dpi_text)
                except Exception:
                    pass

            # 建立 PDF
            success = self.pdf_builder.create_dual_layer_pdf(
                file_path, ocr_text, output_path, dpi=dpi
            )

            if success:
                self.processed_count += 1
                self.stats_label.setText(f"已處理: {self.processed_count} 個檔案")
                self.log_edit.append(f"  ✓ 完成: {output_path.name}")

        except Exception as e:
            self.log_edit.append(f"  ✗ 錯誤: {file_path.name} - {e}")
            logger.error(f"處理檔案失敗 {file_path}: {e}")


class SettingsInterface(QWidget):
    """設定介面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.initUI()

    def initUI(self):
        """初始化 UI（使用佈局管理器）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)

        # 標題
        self.title_label = SubtitleLabel("設定")
        layout.addWidget(self.title_label)

        # --- Ollama 模型設定 ---
        layout.addWidget(StrongBodyLabel("Ollama 模型"))

        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("模型名稱:"))
        self.model_combo = ComboBox()
        self.model_combo.addItems([
            "glm-ocr:q8_0",
            "glm-ocr:q4_k_m",
            "glm-ocr:q4_0",
        ])
        self.model_combo.setCurrentIndex(0)
        self.model_combo.setEditable(True)
        model_layout.addWidget(self.model_combo, stretch=1)
        layout.addLayout(model_layout)

        # Ollama 狀態檢查
        status_layout = QHBoxLayout()
        self.check_status_btn = PushButton("檢查 Ollama 狀態")
        self.check_status_btn.clicked.connect(self.check_ollama_status)
        status_layout.addWidget(self.check_status_btn)

        self.ollama_status_label = BodyLabel("")
        status_layout.addWidget(self.ollama_status_label, stretch=1)
        layout.addLayout(status_layout)

        # --- 字型設定 ---
        layout.addWidget(StrongBodyLabel("字型設定"))

        font_layout = QHBoxLayout()
        font_layout.addWidget(BodyLabel("字型路徑:"))
        self.font_path_edit = LineEdit()
        self.font_path_edit.setText(str(get_default_font_path()))
        font_layout.addWidget(self.font_path_edit, stretch=1)
        self.browse_font_btn = PushButton("瀏覽")
        self.browse_font_btn.clicked.connect(self.browse_font)
        font_layout.addWidget(self.browse_font_btn)
        layout.addLayout(font_layout)

        # --- 影像設定 ---
        layout.addWidget(StrongBodyLabel("影像設定"))

        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(BodyLabel("影像 DPI:"))
        self.dpi_combo = ComboBox()
        self.dpi_combo.addItems(["150", "200", "300", "600"])
        self.dpi_combo.setCurrentIndex(0)
        dpi_layout.addWidget(self.dpi_combo)
        dpi_layout.addStretch()
        layout.addLayout(dpi_layout)

        # 填充底部空間
        layout.addStretch()

    def browse_font(self):
        """瀏覽字型檔案"""
        font_file, _ = QFileDialog.getOpenFileName(
            self,
            "選擇字型檔案",
            str(Path(__file__).parent / 'fonts'),
            "字型檔案 (*.ttf *.otf);;所有檔案 (*)"
        )
        if font_file:
            self.font_path_edit.setText(font_file)

    def check_ollama_status(self):
        """檢查 Ollama 服務狀態"""
        model_name = self.model_combo.currentText().strip() or DEFAULT_MODEL_NAME
        engine = OCREngine(model_name=model_name)
        status = engine.check_service_status()
        self.ollama_status_label.setText(status['message'])

        if status['service_available'] and status['model_available']:
            InfoBar.success(
                title="連線成功",
                content=status['message'],
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
        elif status['service_available']:
            InfoBar.warning(
                title="模型未安裝",
                content=status['message'],
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.error(
                title="連線失敗",
                content=status['message'],
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )


class MainWindow(FluentWindow):
    """主視窗類別 - 使用 Fluent Design"""

    def __init__(self):
        super().__init__()
        self.initWindow()
        self.initNavigation()

    def initWindow(self):
        """初始化視窗設定"""
        self.setWindowTitle("AI 離線雙層 PDF 轉換服務")
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)

    def initNavigation(self):
        """初始化導航介面"""
        # 添加子介面
        self.conversion_interface = ConversionInterface(self)
        self.conversion_interface.setObjectName("conversionInterface")
        self.addSubInterface(
            self.conversion_interface,
            FIF.DOCUMENT,
            '影像轉換'
        )

        self.hot_folder_interface = HotFolderInterface(self)
        self.hot_folder_interface.setObjectName("hotFolderInterface")
        self.addSubInterface(
            self.hot_folder_interface,
            FIF.FOLDER,
            '熱資料夾監控'
        )

        self.settings_interface = SettingsInterface(self)
        self.settings_interface.setObjectName("settingsInterface")
        self.addSubInterface(
            self.settings_interface,
            FIF.SETTING,
            '設定',
            position=NavigationItemPosition.BOTTOM
        )


def main():
    """應用程式進入點"""
    # 高 DPI 縮放（PyQt6 預設已啟用，僅需設定捨入策略）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 設定 Fluent 主題
    setTheme(Theme.AUTO)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
