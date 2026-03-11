"""
AI 離線雙層 PDF 轉換服務 - 主視窗
Main GUI Window using PyQt-Fluent-Widgets
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, Theme,
    FluentIcon as FIF, PushButton, CardWidget, BodyLabel,
    SubtitleLabel, StrongBodyLabel, InfoBar, InfoBarPosition,
    ProgressBar, ComboBox, LineEdit, SwitchButton, FileEdit
)
from qfluentwidgets import FluentIcon

from folder_watcher import FolderWatcher
from ocr_engine import OCREngine
from pdf_builder import PDFBuilder


class ConversionThread(QThread):
    """轉換工作執行緒"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)

    def __init__(self, image_path, ocr_engine, pdf_builder, output_path):
        super().__init__()
        self.image_path = image_path
        self.ocr_engine = ocr_engine
        self.pdf_builder = pdf_builder
        self.output_path = output_path

    def run(self):
        try:
            self.log.emit(f"開始處理: {self.image_path}")
            self.progress.emit(10)

            # 執行 OCR
            ocr_text = self.ocr_engine.process_image(self.image_path)
            if ocr_text is None:
                self.finished.emit(False, "OCR 識別失敗")
                return

            self.progress.emit(60)
            self.log.emit(f"OCR 識別完成，文字長度: {len(ocr_text)}")

            # 建立 PDF
            success = self.pdf_builder.create_dual_layer_pdf(
                self.image_path, ocr_text, self.output_path
            )

            self.progress.emit(100)

            if success:
                self.log.emit(f"PDF 建立成功: {self.output_path}")
                self.finished.emit(True, f"轉換成功: {self.output_path}")
            else:
                self.finished.emit(False, "PDF 建立失敗")

        except Exception as e:
            self.log.emit(f"錯誤: {str(e)}")
            self.finished.emit(False, f"處理失敗: {str(e)}")


class ConversionInterface(CardWidget):
    """單檔轉換介面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.ocr_engine = None
        self.pdf_builder = None
        self.conversion_thread = None
        self.initUI()

    def initUI(self):
        """初始化 UI"""
        self.setFixedHeight(500)

        # 標題
        self.title_label = SubtitleLabel("單檔轉換", self)
        self.title_label.move(30, 20)

        # 選擇檔案按鈕
        self.select_file_btn = PushButton("選擇影像檔案", self)
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.move(30, 70)

        # 檔案路徑顯示
        self.file_path_edit = LineEdit(self)
        self.file_path_edit.setPlaceholderText("請選擇要轉換的影像檔案")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setGeometry(30, 110, 400, 35)

        # 輸出路徑
        self.output_path_edit = LineEdit(self)
        self.output_path_edit.setPlaceholderText("輸出 PDF 路徑（自動生成）")
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setGeometry(30, 160, 400, 35)

        # 轉換按鈕
        self.convert_btn = PushButton("開始轉換", self)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        self.convert_btn.move(30, 210)

        # 進度條
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setGeometry(30, 260, 400, 20)

        # 狀態標籤
        self.status_label = BodyLabel("準備就緒", self)
        self.status_label.move(30, 300)

    def select_file(self):
        """選擇檔案"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇影像檔案",
            "",
            "影像檔案 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"
        )

        if file_path:
            self.file_path_edit.setText(file_path)
            # 自動生成輸出路徑
            output_path = Path(file_path).with_suffix('.pdf')
            self.output_path_edit.setText(str(output_path))
            self.convert_btn.setEnabled(True)
            self.status_label.setText("已選擇檔案，準備轉換")

    def start_conversion(self):
        """開始轉換"""
        image_path = self.file_path_edit.text()
        output_path = self.output_path_edit.text()

        if not image_path or not output_path:
            InfoBar.error(
                title="錯誤",
                content="請選擇影像檔案",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
            return

        # 初始化 OCR 引擎和 PDF 建構器
        if self.ocr_engine is None:
            self.init_engines()

        if not self.ocr_engine.is_ready():
            InfoBar.error(
                title="錯誤",
                content="OCR 引擎未初始化，請檢查模型檔案",
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
            return

        # 建立轉換執行緒
        self.conversion_thread = ConversionThread(
            Path(image_path),
            self.ocr_engine,
            self.pdf_builder,
            Path(output_path)
        )
        self.conversion_thread.progress.connect(self.progress_bar.setValue)
        self.conversion_thread.finished.connect(self.on_conversion_finished)
        self.conversion_thread.log.connect(self.status_label.setText)
        self.conversion_thread.start()

        self.convert_btn.setEnabled(False)
        self.status_label.setText("轉換中...")

    def init_engines(self):
        """初始化 OCR 引擎和 PDF 建構器"""
        try:
            # 初始化 OCR 引擎（使用 Ollama GLM-OCR 模型）
            self.ocr_engine = OCREngine(model_name="glm-ocr:q8_0")

            # 初始化 PDF 建構器
            fonts_dir = Path(__file__).parent / 'fonts'
            font_path = fonts_dir / 'NotoSansTC.ttf'

            self.pdf_builder = PDFBuilder(font_path)

        except Exception as e:
            InfoBar.error(
                title="初始化失敗",
                content=str(e),
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )

    def on_conversion_finished(self, success, message):
        """轉換完成回調"""
        self.convert_btn.setEnabled(True)

        if success:
            InfoBar.success(
                title="成功",
                content=message,
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.error(
                title="失敗",
                content=message,
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )


class HotFolderInterface(CardWidget):
    """熱資料夾監控介面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.folder_watcher = None
        self.ocr_engine = None
        self.pdf_builder = None
        self.is_watching = False
        self.initUI()

    def initUI(self):
        """初始化 UI"""
        self.setFixedHeight(500)

        # 標題
        self.title_label = SubtitleLabel("熱資料夾監控", self)
        self.title_label.move(30, 20)

        # 選擇資料夾按鈕
        self.select_folder_btn = PushButton("選擇監控資料夾", self)
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.select_folder_btn.move(30, 70)

        # 資料夾路徑顯示
        self.folder_path_edit = LineEdit(self)
        self.folder_path_edit.setPlaceholderText("請選擇要監控的資料夾")
        self.folder_path_edit.setReadOnly(True)
        self.folder_path_edit.setGeometry(30, 110, 400, 35)

        # 輸出資料夾
        self.output_folder_edit = LineEdit(self)
        self.output_folder_edit.setPlaceholderText("輸出資料夾（自動生成）")
        self.output_folder_edit.setReadOnly(True)
        self.output_folder_edit.setGeometry(30, 160, 400, 35)

        # 開始/停止監控按鈕
        self.toggle_watch_btn = PushButton("開始監控", self)
        self.toggle_watch_btn.clicked.connect(self.toggle_watching)
        self.toggle_watch_btn.setEnabled(False)
        self.toggle_watch_btn.move(30, 210)

        # 狀態標籤
        self.status_label = BodyLabel("準備就緒", self)
        self.status_label.move(30, 260)

        # 統計資訊
        self.stats_label = StrongBodyLabel("已處理: 0 個檔案", self)
        self.stats_label.move(30, 300)

        self.processed_count = 0

    def select_folder(self):
        """選擇資料夾"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "選擇監控資料夾"
        )

        if folder_path:
            self.folder_path_edit.setText(folder_path)
            # 自動生成輸出資料夾
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

        if not self.ocr_engine.is_ready():
            InfoBar.error(
                title="錯誤",
                content="OCR 引擎未初始化，請檢查模型檔案",
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

    def stop_watching(self):
        """停止監控"""
        if self.folder_watcher:
            self.folder_watcher.stop()
            self.folder_watcher = None

        self.is_watching = False
        self.toggle_watch_btn.setText("開始監控")
        self.status_label.setText("監控已停止")
        self.select_folder_btn.setEnabled(True)

    def init_engines(self):
        """初始化 OCR 引擎和 PDF 建構器"""
        try:
            # 初始化 OCR 引擎（使用 Ollama GLM-OCR 模型）
            self.ocr_engine = OCREngine(model_name="glm-ocr:q8_0")

            # 初始化 PDF 建構器
            fonts_dir = Path(__file__).parent / 'fonts'
            font_path = fonts_dir / 'NotoSansTC.ttf'

            self.pdf_builder = PDFBuilder(font_path)

        except Exception as e:
            InfoBar.error(
                title="初始化失敗",
                content=str(e),
                parent=self.parent_window,
                position=InfoBarPosition.TOP
            )

    def process_file(self, file_path):
        """處理檔案"""
        try:
            # 執行 OCR
            ocr_text = self.ocr_engine.process_image(file_path)
            if ocr_text is None:
                return

            # 生成輸出路徑
            output_folder = Path(self.output_folder_edit.text())
            output_path = output_folder / file_path.with_suffix('.pdf').name

            # 建立 PDF
            success = self.pdf_builder.create_dual_layer_pdf(
                file_path, ocr_text, output_path
            )

            if success:
                self.processed_count += 1
                self.stats_label.setText(f"已處理: {self.processed_count} 個檔案")

        except Exception as e:
            print(f"處理檔案失敗 {file_path}: {e}")


class SettingsInterface(CardWidget):
    """設定介面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.initUI()

    def initUI(self):
        """初始化 UI"""
        self.setFixedHeight(500)

        # 標題
        self.title_label = SubtitleLabel("設定", self)
        self.title_label.move(30, 20)

        # 模型路徑設定
        self.model_path_label = BodyLabel("模型路徑:", self)
        self.model_path_label.move(30, 70)

        self.model_path_edit = LineEdit(self)
        self.model_path_edit.setText(str(Path(__file__).parent / 'models' / 'model.gguf'))
        self.model_path_edit.setGeometry(30, 100, 400, 35)

        # 字型路徑設定
        self.font_path_label = BodyLabel("字型路徑:", self)
        self.font_path_label.move(30, 150)

        self.font_path_edit = LineEdit(self)
        self.font_path_edit.setText(str(Path(__file__).parent / 'fonts' / 'NotoSansTC.ttf'))
        self.font_path_edit.setGeometry(30, 180, 400, 35)

        # DPI 設定
        self.dpi_label = BodyLabel("影像 DPI:", self)
        self.dpi_label.move(30, 230)

        self.dpi_combo = ComboBox(self)
        self.dpi_combo.addItems(["150", "200", "300", "600"])
        self.dpi_combo.setCurrentIndex(0)
        self.dpi_combo.move(30, 260)

        # GPU 加速開關
        self.gpu_label = BodyLabel("GPU 加速:", self)
        self.gpu_label.move(30, 310)

        self.gpu_switch = SwitchButton(self)
        self.gpu_switch.setChecked(True)
        self.gpu_switch.move(30, 340)


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
        self.addSubInterface(
            self.conversion_interface,
            FIF.DOCUMENT,
            '單檔轉換'
        )

        self.hot_folder_interface = HotFolderInterface(self)
        self.addSubInterface(
            self.hot_folder_interface,
            FIF.FOLDER,
            '熱資料夾監控'
        )

        self.settings_interface = SettingsInterface(self)
        self.addSubInterface(
            self.settings_interface,
            FIF.SETTING,
            '設定',
            position=NavigationItemPosition.BOTTOM
        )


def main():
    """應用程式進入點"""
    # 啟用高 DPI 縮放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    # 設定 Fluent 主題
    setTheme(Theme.AUTO)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
