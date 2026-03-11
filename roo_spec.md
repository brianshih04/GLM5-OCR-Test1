# 專案名稱：AI 離線雙層 PDF 轉換服務 (GGUF + Win11 UI + 極速 JPEG 引擎)
**Roo Code 開發規格書 (Development Specification for Roo Code)**

## 1. 專案概觀 (Project Overview)
你是一個資深的 Python 桌面應用開發專家與 AI 工程師。
請幫我開發一個「完全離線、本地執行的 Windows 桌面應用程式」。
該程式包含單檔轉換與自動化資料夾監控 (Hot Folder) 功能，負責將圖片轉為「雙層可搜尋 PDF」。
**【架構核心要求】**：
1. **AI 輕量化**: 嚴禁使用 `torch` 與 `transformers`。使用 `llama-cpp-python` (GGUF)。
2. **UI 現代化**: 嚴格使用 `PyQt-Fluent-Widgets` 打造 Windows 11 Fluent Design 質感。
3. **極速影像解碼 (新增)**: 為了應付大量高解析度掃描檔，必須使用 `PyTurboJPEG` (`libjpeg-turbo`) 作為 JPEG 檔案的優先解碼器，加速影像預處理流程。

## 2. Roo Code 執行策略 (Execution Strategy)
- **階段一 (Architect 模式)**: 建立專案資料夾架構、空白 Python 檔案，以及 `/models`, `/fonts`, `/bin` 等外部資源資料夾。
- **階段二 (Coder 模式)**: 依序實作各個模組，特別注意影像解碼的 Fallback 機制與打包腳本。

## 3. 系統架構與技術棧 (Tech Stack)
- **語言**: Python 3.10+
- **GUI 框架**: `PyQt6` + `PyQt-Fluent-Widgets`
- **資料夾監聽**: `watchdog` 
- **極速影像引擎**: `PyTurboJPEG` (處理 `.jpg`, `.jpeg`) + `Pillow` (Fallback 處理 PNG/BMP/TIFF 等)
- **AI 推理引擎**: `llama-cpp-python` 
- **PDF 引擎**: `PyMuPDF` (`fitz`)

## 4. 目錄結構設計 (Directory Structure)
```text
/project_root
  ├── main.py             # GUI 主視窗與進入點
  ├── folder_watcher.py   # watchdog 資料夾監聽
  ├── ocr_engine.py       # 包含影像解碼與 llama-cpp-python 推理邏輯
  ├── pdf_builder.py      # 產生透明文字的雙層 PDF
  ├── requirements.txt    # 依賴套件清單
  ├── build.py            # PyInstaller 打包腳本
  ├── /models             # 放置 .gguf 主模型與 mmproj 視覺投影檔
  ├── /fonts              # 放置中文字型檔 (如 NotoSansTC.ttf)
  └── /bin                # 放置 turbojpeg.dll 檔案 (極度重要！)