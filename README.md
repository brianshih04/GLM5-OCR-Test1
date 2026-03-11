# AI 離線雙層 PDF 轉換服務

一個完全離線、本地執行的 Windows 桌面應用程式，將圖片轉換為「雙層可搜尋 PDF」。

## 功能特色

- **單檔轉換**: 支援拖曳或選擇單一影像檔案進行轉換
- **熱資料夾監控**: 自動監控指定資料夾，新加入的影像檔案自動轉換
- **雙層 PDF**: 產生包含原始影像層和透明文字層的 PDF，可搜尋文字
- **極速處理**: 使用 PyTurboJPEG 加速 JPEG 解碼
- **完全離線**: 使用 Ollama GLM-OCR 模型，無需網路連線
- **現代化 UI**: 使用 PyQt-Fluent-Widgets 打造 Windows 11 Fluent Design 質感

## 系統需求

- Windows 10/11
- Python 3.10+
- 4GB+ RAM
- 支援 GPU 加速（選用）

## 安裝步驟

### 1. 安裝 Ollama

首先需要安裝 Ollama 來運行 GLM-OCR 模型：

**Windows:**
```bash
# 下載並安裝 Ollama
# 訪問: https://ollama.com/download
```

**驗證安裝：**
```bash
ollama --version
```

### 2. 下載 GLM-OCR 模型

```bash
# 下載 GLM-OCR 模型（q8_0 量化版本）
ollama pull glm-ocr:q8_0

# 或使用其他版本
# ollama pull glm-ocr:q4_0  # 輕量級版本
# ollama pull glm-ocr:q4_k_m  # 平衡版本
```

**模型資訊：**
- [GLM-OCR](https://ollama.com/library/glm-ocr) - GLM-OCR 視覺語言模型
- 支援中英文 OCR 識別
- q8_0 版本提供最佳精度，q4_0 版本提供更快速度

### 3. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

### 4. 下載字型檔案

將中文字型檔案放置於 `fonts` 目錄：

- 推薦: `fonts/NotoSansTC.ttf`

**下載連結：**
- [Noto Sans TC](https://fonts.google.com/noto/specimen/Noto+Sans+TC)

### 5. 下載 DLL 檔案（選用）

將 `turbojpeg.dll` 放置於 `bin` 目錄以加速 JPEG 解碼：

- 從 [libjpeg-turbo](https://github.com/libjpeg-turbo/libjpeg-turbo/releases) 下載
- 或使用 conda 安裝: `conda install -c conda-forge libjpeg-turbo`

## 使用方法

### 開發模式執行

```bash
# 確保 Ollama 服務正在運行
ollama serve

# 在另一個終端機執行應用程式
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
  ├── ocr_engine.py       # OCR 引擎（Ollama GLM-OCR）
  ├── pdf_builder.py      # PDF 建構器
  ├── requirements.txt    # 依賴套件
  ├── build.py            # 打包腳本
  ├── README.md           # 專案文件
  ├── /fonts              # 字型檔案
  └── /bin                # turbojpeg.dll 檔案（選用）
```

## 技術棧

- **GUI**: PyQt6 + PyQt-Fluent-Widgets
- **AI 推理**: Ollama GLM-OCR
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
- 使用 Ollama GLM-OCR 模型進行 OCR 識別
- PyTurboJPEG 加速 JPEG 解碼
- Pillow 作為備用解碼器
- 支援中英文文字識別

### pdf_builder.py
PDF 建構模組：
- 雙層 PDF 生成（影像層 + 透明文字層）
- PyMuPDF (fitz) 引擎
- 支援中文字型
- 版面資訊精確定位

## Ollama 模型管理

### 查看已安裝的模型

```bash
ollama list
```

### 切換模型版本

修改 [`ocr_engine.py`](ocr_engine.py:86) 中的 `model_name` 參數：

```python
self.ocr_engine = OCREngine(model_name="glm-ocr:q4_0")  # 輕量級
self.ocr_engine = OCREngine(model_name="glm-ocr:q8_0")  # 高精度
```

### 更新模型

```bash
ollama pull glm-ocr:q8_0
```

### 刪除模型

```bash
ollama rm glm-ocr:q8_0
```

## 注意事項

1. **Ollama 服務**: 確保 Ollama 服務正在運行（`ollama serve`）
2. **模型檔案**: 確保已下載 GLM-OCR 模型（`ollama pull glm-ocr:q8_0`）
3. **DLL 檔案**: turbojpeg.dll 必須與 PyTurboJPEG 版本匹配（選用）
4. **字型檔案**: 確保字型檔案支援中文
5. **GPU 加速**: Ollama 自動支援 GPU 加速（如果可用）

## 常見問題

### Q: OCR 識別效果不佳？
A: 嘗試使用更高解析度的影像，或使用 q8_0 版本的 GLM-OCR 模型。

### Q: 轉換速度很慢？
A: 確保已安裝 GPU 版本的 Ollama，並啟用 GPU 加速。也可以嘗試使用 q4_0 版本的模型。

### Q: 無法連接到 Ollama？
A: 確保 Ollama 服務正在運行（`ollama serve`），並檢查防火牆設定。

### Q: 無法載入 turbojpeg.dll？
A: 確保 DLL 檔案位於 `bin` 目錄中，且版本與 PyTurboJPEG 匹配。如果無法載入，系統會自動使用 Pillow 作為備用。

### Q: PDF 中的文字無法搜尋？
A: 確保 OCR 識別成功，且文字層正確插入。檢查字型檔案是否正確載入。

### Q: 如何查看 Ollama 日誌？
A: 運行 `ollama serve` 時會顯示詳細日誌，可以查看模型載入和推理的詳細資訊。

## 授權

本專案僅供學習與研究使用。

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 聯絡方式

如有問題，請在 GitHub 上提交 Issue。
