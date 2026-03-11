"""
資料夾監控模組 - 使用 watchdog 實現 Hot Folder 功能
Folder Monitoring Module using watchdog
"""

import os
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent


class ConversionEventHandler(FileSystemEventHandler):
    """檔案系統事件處理器 - 處理新檔案的 OCR 轉換"""

    def __init__(self, callback, supported_extensions=None):
        """
        初始化事件處理器
        
        Args:
            callback: 轉換完成後的回調函數
            supported_extensions: 支援的副檔名列表
        """
        super().__init__()
        self.callback = callback
        self.supported_extensions = supported_extensions or [
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'
        ]
        self.processing_files = set()  # 追蹤正在處理的檔案

    def on_created(self, event):
        """當檔案被創建時觸發"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        
        # 檢查副檔名是否支援
        if file_path.suffix.lower() not in self.supported_extensions:
            return

        # 避免重複處理
        if str(file_path) in self.processing_files:
            return

        # 等待檔案寫入完成
        self._wait_for_file_ready(file_path)
        
        # 標記為處理中
        self.processing_files.add(str(file_path))
        
        try:
            # 執行轉換
            self.callback(file_path)
        finally:
            # 移除處理標記
            self.processing_files.discard(str(file_path))

    def _wait_for_file_ready(self, file_path, timeout=30, check_interval=0.5):
        """
        等待檔案寫入完成
        
        Args:
            file_path: 檔案路徑
            timeout: 超時時間（秒）
            check_interval: 檢查間隔（秒）
        """
        start_time = time.time()
        last_size = 0
        
        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size
                if current_size > 0 and current_size == last_size:
                    # 檔案大小穩定，認為寫入完成
                    time.sleep(check_interval * 2)  # 再等待一下確保
                    return
                last_size = current_size
            except (OSError, FileNotFoundError):
                pass
            time.sleep(check_interval)


class FolderWatcher:
    """資料夾監控器 - 管理熱資料夾的監控"""

    def __init__(self, watch_path, callback, recursive=True):
        """
        初始化資料夾監控器
        
        Args:
            watch_path: 要監控的資料夾路徑
            callback: 檔案創建時的回調函數
            recursive: 是否遞歸監控子資料夾
        """
        self.watch_path = Path(watch_path)
        self.callback = callback
        self.recursive = recursive
        self.observer = None
        self.event_handler = None

    def start(self):
        """開始監控"""
        if not self.watch_path.exists():
            self.watch_path.mkdir(parents=True, exist_ok=True)

        self.event_handler = ConversionEventHandler(self.callback)
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.watch_path),
            recursive=self.recursive
        )
        self.observer.start()

    def stop(self):
        """停止監控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def is_running(self):
        """檢查監控是否正在運行"""
        return self.observer and self.observer.is_alive()

    def __enter__(self):
        """上下文管理器進入"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
