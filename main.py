# AI 離線雙層 PDF 轉換服務

一個完全離線、本地執行的 Windows 桌面應用程式，將圖片轉換為「雙層可搜尋 PDF」。

## 功能特色

- **單檔轉換**: 支援拖曳或選擇單一影像檔案進行轉換
- **熱資料夾監控**: 自動監控指定資料夾，新加入的影像檔案自動轉換
- **雙層 PDF**: 產生包含原始影像層和透明文字層的 PDF，可搜尋文字
- **極速處理**: 使用 PyTurboJPEG 加速 JPEG 解碼
- **完全離線**: 使用 llama-cpp-python (GGUF) 模型，無需網路連線
- **現代化 UI**: 使用 PyQt-Fluent-Widgets 打造 Windows 11 Fluent Design 質感

## 系統需求

- Windows 10/11
- Python 3.10+
- 4GB+ RAM
- 支援 GPU 加速（選用）

## 安裝步驟

### 1. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

### 2. 下載模型檔案

將 GGUF 模型檔案放置於 `models` 目錄：

- 主模型: `models/model.gguf`
- 視覺投影檔: `models/mmproj.gguf`（多模態模型需要）

### 3. 下載字型檔案

將中文字型檔案放置於 `fonts` 目錄：

- 推薦: `fonts/NotoSansTC.ttf`

### 4. 下載 DLL 檔案

將 `turbojpeg.dll` 放置於 `bin` 目錄：

- 從 [libjpeg-turbo](https://github.com/libjpeg-turbo/libjpeg-turbo/releases) 下載
- 或使用 conda 安裝: `conda install -c conda-forge libjpeg-turbo`

## 使用方法

### 開發模式執行

```bash
python main.py
```

### 打包為執行檔

```bash
python build.py
```

打包後的執行檔位於 `dist/AI_PDF_Converter.exe`

## 專案結構

```
/project_root
  ├── main.py             # GUI 主視窗
  ├── folder_watcher.py   # 資料夾監控
  ├── ocr_engine.py       # OCR 引擎
  ├── pdf_builder.py      # PDF 建構器
  ├── requirements.txt    # 依賴套件
  ├── build.py            # 打包腳本
  ├── /models             # GGUF 模型檔案
  ├── /fonts              # 字型檔案
  └── /bin                # DLL 檔案
```

## 技術棧

- **GUI**: PyQt6 + PyQt-Fluent-Widgets
- **AI 推理**: llama-cpp-python (GGUF)
- **影像處理**: PyTurboJPEG + Pillow
- **資料夾監控**: watchdog
- **PDF 引擎**: PyMuPDF

## 注意事項

1. **模型檔案**: 請確保下載正確的 GGUF 模型檔案
2. **DLL 檔案**: turbojpeg.dll 必須與 PyTurboJPEG 版本匹配
3. **字型檔案**: 確保字型檔案支援中文
4. **GPU 加速**: 如需 GPU 加速，請安裝 CUDA 版本的 llama-cpp-python

## 授權

本專案僅供學習與研究使用。
