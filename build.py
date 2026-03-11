"""
PyInstaller 打包腳本
Packaging Script for PyInstaller
"""

import os
import sys
from pathlib import Path
import PyInstaller.__main__


def build():
    """執行打包流程"""
    
    # 專案根目錄
    project_root = Path(__file__).parent
    
    # 設定路徑
    bin_path = project_root / 'bin'
    models_path = project_root / 'models'
    fonts_path = project_root / 'fonts'
    
    # 檢查必要目錄
    if not bin_path.exists():
        print(f"警告：bin 目錄不存在，請確保 libturbojpeg.dll 已放置於 {bin_path}")
    
    # PyInstaller 參數
    pyinstaller_args = [
        'main.py',
        '--name=AI_PDF_Converter',
        '--windowed',  # 無控制台視窗
        '--onefile',   # 單一執行檔
        '--clean',     # 清理暫存檔案
        
        # 添加資料檔案
        f'--add-data={bin_path};bin' if bin_path.exists() else '',
        f'--add-data={models_path};models' if models_path.exists() else '',
        f'--add-data={fonts_path};fonts' if fonts_path.exists() else '',
        
        # 隱藏導入
        '--hidden-import=ollama',
        '--hidden-import=PyTurboJPEG',
        '--hidden-import=watchdog',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=qfluentwidgets',
        
        # 排除不需要的模組（減小體積）
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=IPython',
        
        # 圖標（如果有的話）
        # '--icon=assets/icon.ico',
        
        # 輸出目錄
        '--distpath=dist',
        '--workpath=build',
        '--specpath=.',
    ]
    
    # 過濾空參數
    pyinstaller_args = [arg for arg in pyinstaller_args if arg]
    
    print("開始打包...")
    print(f"專案根目錄: {project_root}")
    print(f"PyInstaller 參數: {' '.join(pyinstaller_args)}")
    
    # 執行打包
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\n打包完成！")
    print(f"執行檔位置: {project_root / 'dist' / 'AI_PDF_Converter.exe'}")
    print("\n注意事項：")
    print("1. 請確保 Ollama 服務正在運行")
    print("2. 請確保已下載 GLM-OCR 模型: ollama pull glm-ocr:q8_0")
    print("3. 請確保 fonts 目錄中有中文字型檔案")
    print("4. 請確保 bin 目錄中有 libturbojpeg.dll 檔案")


def build_with_dll():
    """打包並包含 DLL 檔案"""
    
    # 專案根目錄
    project_root = Path(__file__).parent
    bin_path = project_root / 'bin'
    
    # 檢查 DLL 檔案
    dll_files = list(bin_path.glob('*.dll')) if bin_path.exists() else []
    
    if not dll_files:
        print(f"警告：未在 {bin_path} 中找到 DLL 檔案")
        print("請將 libturbojpeg.dll 放置於 bin 目錄中")
        return
    
    print(f"找到 DLL 檔案: {[f.name for f in dll_files]}")
    
    # 執行標準打包
    build()
    
    # 複製 DLL 到輸出目錄
    dist_path = project_root / 'dist'
    if dist_path.exists():
        import shutil
        for dll_file in dll_files:
            shutil.copy2(dll_file, dist_path / dll_file.name)
            print(f"已複製 {dll_file.name} 到輸出目錄")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--with-dll':
        build_with_dll()
    else:
        build()
