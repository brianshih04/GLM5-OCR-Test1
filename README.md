# AI 離線雙層 PDF 轉換服務

一個完全離線、本地執行的 Windows 桌面應用程式，將圖片轉換為「雙層可搜尋 PDF」。

## 功能特色

- **單檔 / 批次轉換**: 支援拖曳或選擇多個影像檔案進行轉換
- **熱資料夾監控**: 自動監控指定資料夾，新加入的影像檔案自動轉換
- **雙層 PDF**: 產生包含原始影像層和透明文字層的 PDF，可搜尋文字
- **極速處理**: 使用 PyTurboJPEG 加速 JPEG 解碼
- **完全離線**: 使用 GLM-OCR GGUF 模型，透過 Ollama 本地推理，無需網路連線
- **現代化 UI**: 使用 PyQt-Fluent-Widgets 打造 Windows 11 Fluent Design 質感

## 系統需求

- Windows 10/11
- Python 3.10+
- 4GB+ RAM（建議 8GB+）
- 支援 GPU 加速（選用，Ollama 自動偵測）

## 安裝步驟

### 1. 下載 GLM-OCR GGUF 模型

從 Hugging Face 下載 GLM-OCR GGUF 模型檔案：

**模型來源：** [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF)

**可用模型版本：**

| 檔案名稱 | 大小 | 說明 |
|----------|------|------|
| `GLM-OCR-Q8_0.gguf` | 950 MB | Q8_0 量化版，推薦（精度與速度平衡） |
| `GLM-OCR-f16.gguf` | 1.79 GB | FP16 全精度版，最高品質 |
| `mmproj-GLM-OCR-Q8_0.gguf` | 484 MB | 視覺投影模型（多模態必需） |

**下載方式一：使用瀏覽器**

直接前往 [HuggingFace Files 頁面](https://huggingface.co/ggml-org/GLM-OCR-GGUF/tree/main)，點擊各檔案的下載按鈕。

**下載方式二：使用 huggingface-cli**

```bash
# 安裝 huggingface-cli
pip install huggingface_hub

# 下載 Q8_0 量化版（推薦）
huggingface-cli download ggml-org/GLM-OCR-GGUF GLM-OCR-Q8_0.gguf --local-dir ./models
huggingface-cli download ggml-org/GLM-OCR-GGUF mmproj-GLM-OCR-Q8_0.gguf --local-dir ./models

# 或下載 FP16 全精度版
# huggingface-cli download ggml-org/GLM-OCR-GGUF GLM-OCR-f16.gguf --local-dir ./models
```

**下載方式三：使用 llama-server 自動下載**

```bash
# llama-server 會自動從 HuggingFace 下載模型
llama-server -hf ggml-org/GLM-OCR-GGUF
```

### 2. 安裝 Ollama 並匯入模型

下載完成後，使用 Ollama 來管理和運行 GGUF 模型：

**安裝 Ollama：**

```bash
# 下載安裝 Ollama
# 訪問: https://ollama.com/download
```

**從 GGUF 建立 Ollama 模型：**

建立一個 `Modelfile` 檔案：

```
FROM ./models/GLM-OCR-Q8_0.gguf
```

然後執行：

```bash
# 從 GGUF 檔案建立 Ollama 模型
ollama create glm-ocr:q8_0 -f Modelfile

# 驗證模型已匯入
ollama list
```

**或直接使用 Ollama 拉取（如果 Ollama 庫中已有）：**

```bash
ollama pull glm-ocr:q8_0
```

### 3. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

### 4. 下載字型檔案

將中文字型檔案放置於 `fonts` 目錄：

- 推薦: `fonts/NotoSansTC-VariableFont_wght.ttf`

**下載連結：**
- [Noto Sans TC](https://fonts.google.com/noto/specimen/Noto+Sans+TC)

### 5. 下載 DLL 檔案（選用）

將 `libturbojpeg.dll` 放置於 `bin` 目錄以加速 JPEG 解碼：

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
  ├── main.py             # GUI 主視窗（拖放 / 批次轉換 / 設定）
  ├── folder_watcher.py   # 資料夾監控
  ├── ocr_engine.py       # OCR 引擎（Ollama GLM-OCR）
  ├── pdf_builder.py      # PDF 建構器（雙層 PDF）
  ├── requirements.txt    # 依賴套件
  ├── build.py            # 打包腳本
  ├── README.md           # 專案文件
  ├── /models             # GGUF 模型檔案
  ├── /fonts              # 字型檔案
  └── /bin                # turbojpeg.dll（選用）
```

## 技術棧

- **GUI**: PyQt6 + PyQt-Fluent-Widgets
- **AI 推理**: Ollama + GLM-OCR GGUF（來源：[ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF)）
- **影像處理**: PyTurboJPEG + Pillow
- **資料夾監控**: watchdog
- **PDF 引擎**: PyMuPDF

## 模組說明

### main.py
主視窗程式，包含三個主要介面：
- **影像轉換介面**: 拖放或選擇影像檔案，支援批次轉換
- **熱資料夾監控介面**: 設定監控資料夾，自動處理新檔案
- **設定介面**: 配置模型名稱、字型路徑、DPI 等參數，可檢查 Ollama 連線狀態

### folder_watcher.py
使用 watchdog 實現的資料夾監控模組：
- 自動偵測新檔案
- 檔案寫入完成檢測
- 支援遞歸監控子資料夾
- 線程安全，LRU 哈希去重

### ocr_engine.py
OCR 引擎模組：
- 使用 Ollama 運行 GLM-OCR GGUF 模型進行 OCR 識別
- PyTurboJPEG 加速 JPEG 解碼（可選）
- Pillow 作為備用解碼器
- 支援中英文文字識別

### pdf_builder.py
PDF 建構模組：
- 雙層 PDF 生成（影像層 + 不可見文字層）
- PyMuPDF TextWriter 引擎
- 支援中文字型（CJK 寬度自適應）
- render_mode=3 不可見渲染，文字可搜尋

## GLM-OCR GGUF 模型管理

### 模型來源

所有模型檔案來自 Hugging Face：
- **儲存庫**: [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF)
- **原始模型**: [zai-org/GLM-OCR](https://huggingface.co/zai-org/GLM-OCR)

### 查看已安裝的 Ollama 模型

```bash
ollama list
```

### 從 GGUF 匯入模型到 Ollama

```bash
# 建立 Modelfile
echo "FROM ./models/GLM-OCR-Q8_0.gguf" > Modelfile

# 建立 Ollama 模型
ollama create glm-ocr:q8_0 -f Modelfile
```

### 切換模型版本

在應用程式的「設定」頁面中可直接選擇或輸入模型名稱，例如：
- `glm-ocr:q8_0` — Q8_0 量化（推薦）
- `glm-ocr:f16` — FP16 全精度

### 刪除模型

```bash
ollama rm glm-ocr:q8_0
```

## 注意事項

1. **GGUF 模型**: 從 [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF) 下載模型後匯入 Ollama
2. **Ollama 服務**: 確保 Ollama 服務正在運行（`ollama serve`）
3. **DLL 檔案**: turbojpeg.dll 為選用，可加速 JPEG 解碼
4. **字型檔案**: 確保字型檔案支援中文
5. **GPU 加速**: Ollama 自動支援 GPU 加速（如果可用）

## 常見問題

### Q: 如何下載 GGUF 模型？
A: 前往 [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF/tree/main)，下載 `GLM-OCR-Q8_0.gguf` 和 `mmproj-GLM-OCR-Q8_0.gguf`，放入 `models` 目錄，然後使用 `ollama create` 匯入。

### Q: OCR 識別效果不佳？
A: 嘗試使用更高解析度的影像，或使用 FP16 全精度版本（`GLM-OCR-f16.gguf`）。

### Q: 轉換速度很慢？
A: 確保 Ollama 已偵測到 GPU。也可以嘗試使用 Q8_0 量化版本以獲得較快速度。

### Q: 無法連接到 Ollama？
A: 確保 Ollama 服務正在運行（`ollama serve`），並在應用程式設定頁面點擊「檢查 Ollama 狀態」進行診斷。

### Q: 無法載入 libturbojpeg.dll？
A: DLL 為選用。如果無法載入，系統會自動使用 Pillow 作為備用解碼器。

### Q: PDF 中的文字無法搜尋？
A: 確保 OCR 識別成功，且字型檔案已正確載入。檢查輸出日誌中是否有字型相關警告。

## 授權

本專案僅供學習與研究使用。

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 聯絡方式

如有問題，請在 GitHub 上提交 Issue。
