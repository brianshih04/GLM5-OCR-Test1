"""
資料夾監控模組 - 使用 watchdog 實現 Hot Folder 功能
Folder Monitoring Module using watchdog
"""

import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# 常數設定
MAX_FILE_SIZE_MB = 100  # 最大支援 100MB 檔案
MIN_FILE_SIZE_BYTES = 1024  # 最小 1KB（過小可能是損壞檔案）


class ConversionEventHandler(FileSystemEventHandler):
    """檔案系統事件處理器 - 處理新檔案的 OCR 轉換"""

    def __init__(self, callback, supported_extensions=None, 
                 max_size_mb: int = MAX_FILE_SIZE_MB,
                 min_size_bytes: int = MIN_FILE_SIZE_BYTES):
        """
        初始化事件處理器
        
        Args:
            callback: 轉換完成後的回調函數
            supported_extensions: 支援的副檔名列表
            max_size_mb: 最大檔案大小（MB）
            min_size_bytes: 最小檔案大小（bytes）
        """
        super().__init__()
        self.callback = callback
        self.supported_extensions = supported_extensions or [
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'
        ]
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.min_size_bytes = min_size_bytes
        self.processing_files = set()  # 追蹤正在處理的檔案
        self.processed_hashes = set()  # 追蹤已處理檔案的哈希（防止重複處理）

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
        
        # 檢查檔案大小
        size_check = self._check_file_size(file_path)
        if not size_check[0]:
            print(f"跳過檔案 {file_path.name}: {size_check[1]}")
            return
        
        # 計算檔案哈希檢查是否已處理過
        file_hash = self._calculate_file_hash(file_path)
        if file_hash and file_hash in self.processed_hashes:
            print(f"跳過重複檔案: {file_path.name}")
            return

        # 等待檔案寫入完成
        if not self._wait_for_file_ready(file_path):
            print(f"檔案未就緒: {file_path.name}")
            return
        
        # 標記為處理中
        self.processing_files.add(str(file_path))
        
        try:
            # 執行轉換
            self.callback(file_path)
            # 記錄已處理的檔案哈希
            if file_hash:
                self.processed_hashes.add(file_hash)
                # 限制已處理哈希集合的大小（防止記憶體無限增長）
                if len(self.processed_hashes) > 1000:
                    self.processed_hashes.clear()
        finally:
            # 移除處理標記
            self.processing_files.discard(str(file_path))

    def _check_file_size(self, file_path: Path) -> tuple[bool, str]:
        """
        檢查檔案大小是否在允許範圍內
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            (是否合法, 原因)
        """
        try:
            size = file_path.stat().st_size
            if size < self.min_size_bytes:
                return False, f"檔案過小 ({size} bytes)"
            if size > self.max_size_bytes:
                return False, f"檔案過大 ({size / (1024*1024):.1f} MB > {self.max_size_bytes / (1024*1024):.1f} MB)"
            return True, ""
        except Exception as e:
            return False, f"無法檢查檔案大小: {e}"
    
    def _calculate_file_hash(self, file_path: Path, chunk_size: int = 8192) -> Optional[str]:
        """
        計算檔案 MD5 哈希
        
        Args:
            file_path: 檔案路徑
            chunk_size: 讀取區塊大小
            
        Returns:
            MD5 哈希字串，失敗返回 None
        """
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"計算檔案哈希失敗 {file_path}: {e}")
            return None

    def _wait_for_file_ready(self, file_path: Path, timeout: float = 30, check_interval: float = 0.5) -> bool:
        """
        等待檔案寫入完成
        
        Args:
            file_path: 檔案路徑
            timeout: 超時時間（秒）
            check_interval: 檢查間隔（秒）
            
        Returns:
            是否成功等待檔案就緒
        """
        start_time = time.time()
        last_size = -1
        stable_count = 0
        
        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size
                
                # 檔案大小穩定（連續兩次相同）
                if current_size == last_size and current_size > 0:
                    stable_count += 1
                    if stable_count >= 2:
                        return True
                else:
                    stable_count = 0
                    
                last_size = current_size
            except (OSError, FileNotFoundError):
                pass
                
            time.sleep(check_interval)
        
        return False  # 超時


class FolderWatcher:
    """資料夾監控器 - 管理熱資料夾的監控"""

    def __init__(self, watch_path, callback, recursive=True, 
                 max_file_size_mb: int = MAX_FILE_SIZE_MB):
        """
        初始化資料夾監控器
        
        Args:
            watch_path: 要監控的資料夾路徑
            callback: 檔案創建時的回調函數
            recursive: 是否遞歸監控子資料夾
            max_file_size_mb: 最大檔案大小限制（MB）
        """
        self.watch_path = Path(watch_path)
        self.callback = callback
        self.recursive = recursive
        self.max_file_size_mb = max_file_size_mb
        self.observer = None
        self.event_handler = None

    def start(self):
        """開始監控"""
        if not self.watch_path.exists():
            self.watch_path.mkdir(parents=True, exist_ok=True)

        self.event_handler = ConversionEventHandler(
            self.callback, 
            max_size_mb=self.max_file_size_mb
        )
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
