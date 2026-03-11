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

**推薦模型：**
- [Llava-1.5](https://huggingface.co/mys/ggml_llava-v1.5-7b) - 視覺語言模型
- [BakLLaVA-1](https://huggingface.co/SkunkworksAI/BakLLaVA-1) - 輕量級視覺模型

### 3. 下載字型檔案

將中文字型檔案放置於 `fonts` 目錄：

- 推薦: `fonts/NotoSansTC.ttf`

**下載連結：**
- [Noto Sans TC](https://fonts.google.com/noto/specimen/Noto+Sans+TC)

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
  ├── README.md           # 專案文件
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

## 模組說明

### main.py
主視窗程式，包含三個主要介面：
- **單檔轉換介面**: 選擇影像檔案並進行轉換
- **熱資料夾監控介面**: 設定監控資料夾，自動處理新檔案
- **設定介面**: 配置模型路徑、字型路徑、DPI 等參數

### folder_watcher.py
使用 watchdog 實現的資料夾監控模組：
- 自動偵測新檔案
- 檔案寫入完成檢測
- 支援遞歸監控子資料夾

### ocr_engine.py
OCR 引擎模組：
- PyTurboJPEG 加速 JPEG 解碼
- Pillow 作為備用解碼器
- llama-cpp-python (GGUF) 模型推理
- GPU 加速支援

### pdf_builder.py
PDF 建構模組：
- 雙層 PDF 生成（影像層 + 透明文字層）
- PyMuPDF (fitz) 引擎
- 支援中文字型
- 版面資訊精確定位

## 注意事項

1. **模型檔案**: 請確保下載正確的 GGUF 模型檔案
2. **DLL 檔案**: turbojpeg.dll 必須與 PyTurboJPEG 版本匹配
3. **字型檔案**: 確保字型檔案支援中文
4. **GPU 加速**: 如需 GPU 加速，請安裝 CUDA 版本的 llama-cpp-python

## 常見問題

### Q: OCR 識別效果不佳？
A: 嘗試使用更高解析度的影像，或更換更強大的 GGUF 模型。

### Q: 轉換速度很慢？
A: 確保已安裝 GPU 版本的 llama-cpp-python，並啟用 GPU 加速。

### Q: 無法載入 turbojpeg.dll？
A: 確保 DLL 檔案位於 `bin` 目錄中，且版本與 PyTurboJPEG 匹配。

### Q: PDF 中的文字無法搜尋？
A: 確保 OCR 識別成功，且文字層正確插入。檢查字型檔案是否正確載入。

## 授權

本專案僅供學習與研究使用。

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 聯絡方式

如有問題，請在 GitHub 上提交 Issue。
