# AI 離線雙層 PDF 轉換服務

一個完全離線、本地執行的 Windows 桌面應用程式，將圖片轉換為「雙層可搜尋 PDF」。

## 功能特色

- **單檔 / 批次轉換**: 支援拖曳或選擇多個影像檔案進行轉換
- **熱資料夾監控**: 自動監控指定資料夾，新加入的影像檔案自動轉換
- **雙層 PDF**: 產生包含原始影像層和透明文字層的 PDF，可搜尋文字
- **極速處理**: 使用 PyTurboJPEG 加速 JPEG 解碼
- **完全離線**: 直接載入 GLM-OCR GGUF 模型，無需外部服務或網路連線
- **GPU 加速**: 自動使用 GPU 加速推理（如果可用）
- **現代化 UI**: 使用 PyQt-Fluent-Widgets 打造 Windows 11 Fluent Design 質感

## 系統需求

- Windows 10/11
- Python 3.10+
- 8GB+ RAM（模型需約 1.5GB 記憶體）
- **Visual Studio Build Tools**（安裝 `llama-cpp-python` 需要 C compiler）
- 支援 CUDA GPU 加速（選用）

## 安裝步驟

### 1. 安裝 Visual Studio Build Tools

`llama-cpp-python` 需要 C compiler 來編譯。請安裝 Visual Studio Build Tools：

```bash
# 下載安裝 Visual Studio Build Tools
# 訪問: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 選擇「使用 C++ 的桌面開發」工作負載
```

> **注意**: 如果你已安裝 Visual Studio，可以跳過此步驟。

### 2. 下載 GLM-OCR GGUF 模型

從 Hugging Face 下載 GLM-OCR GGUF 模型檔案，放入 `models/` 目錄：

**模型來源：** [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF)

| 檔案名稱 | 大小 | 說明 | 必要性 |
|----------|------|------|--------|
| `GLM-OCR-Q8_0.gguf` | 950 MB | Q8_0 量化主模型（推薦） | **必要** |
| `mmproj-GLM-OCR-Q8_0.gguf` | 484 MB | 視覺投影模型（多模態必需） | **必要** |
| `GLM-OCR-f16.gguf` | 1.79 GB | FP16 全精度版，最高品質 | 選用 |

**下載方式一：使用瀏覽器**

直接前往 [HuggingFace Files 頁面](https://huggingface.co/ggml-org/GLM-OCR-GGUF/tree/main)，點擊各檔案的下載按鈕，下載後放入 `models/` 目錄。

**下載方式二：使用 huggingface-cli**

```bash
# 安裝 huggingface-cli
pip install huggingface_hub

# 下載 Q8_0 量化版（推薦）
huggingface-cli download ggml-org/GLM-OCR-GGUF GLM-OCR-Q8_0.gguf --local-dir ./models
huggingface-cli download ggml-org/GLM-OCR-GGUF mmproj-GLM-OCR-Q8_0.gguf --local-dir ./models
```

### 3. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

> **GPU 加速**: 如需 CUDA 加速，請安裝支援 GPU 的版本：
> ```bash
> pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124
> ```

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
# 直接執行（不需要任何外部服務）
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
  ├── ocr_engine.py       # OCR 引擎（llama-cpp-python + GLM-OCR GGUF）
  ├── pdf_builder.py      # PDF 建構器（雙層 PDF）
  ├── requirements.txt    # 依賴套件
  ├── build.py            # 打包腳本
  ├── README.md           # 專案文件
  ├── /models             # GGUF 模型檔案（需手動下載）
  │   ├── GLM-OCR-Q8_0.gguf         # 主模型
  │   └── mmproj-GLM-OCR-Q8_0.gguf  # 視覺投影模型
  ├── /fonts              # 字型檔案
  └── /bin                # turbojpeg.dll（選用）
```

## 技術棧

- **GUI**: PyQt6 + PyQt-Fluent-Widgets
- **AI 推理**: llama-cpp-python（直接載入 GGUF，無需 Ollama）
- **OCR 模型**: [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF)
- **影像處理**: PyTurboJPEG + Pillow
- **資料夾監控**: watchdog
- **PDF 引擎**: PyMuPDF

## 模組說明

### main.py
主視窗程式，包含三個主要介面：
- **影像轉換介面**: 拖放或選擇影像檔案，支援批次轉換
- **熱資料夾監控介面**: 設定監控資料夾，自動處理新檔案
- **設定介面**: 配置 GGUF 模型路徑、視覺投影路徑、字型、DPI、GPU 開關

### ocr_engine.py
OCR 引擎模組：
- 使用 `llama-cpp-python` 的 `Llava15ChatHandler` 進行多模態推理
- 直接載入 GGUF 模型和視覺投影模型，無需外部服務
- 支援 GPU 加速（`n_gpu_layers=-1` 使用全部 GPU 層）
- 影像以 base64 data URI 傳入推理
- 帶重試機制的錯誤處理

### folder_watcher.py
使用 watchdog 實現的資料夾監控模組：
- 自動偵測新檔案
- 檔案寫入完成檢測
- 支援遞歸監控子資料夾
- 線程安全，LRU 哈希去重

### pdf_builder.py
PDF 建構模組：
- 雙層 PDF 生成（影像層 + 不可見文字層）
- PyMuPDF TextWriter 引擎
- 支援中文字型（CJK 寬度自適應）
- render_mode=3 不可見渲染，文字可搜尋

## 注意事項

1. **C Compiler**: 安裝 `llama-cpp-python` 需要 Visual Studio Build Tools
2. **GGUF 模型**: 從 [ggml-org/GLM-OCR-GGUF](https://huggingface.co/ggml-org/GLM-OCR-GGUF) 下載兩個必要檔案
3. **無需 Ollama**: 本專案直接載入 GGUF 模型，不依賴任何外部服務
4. **DLL 檔案**: turbojpeg.dll 為選用，可加速 JPEG 解碼
5. **字型檔案**: 確保字型檔案支援中文
6. **GPU 加速**: 預設啟用，可在設定頁面關閉

## 常見問題

### Q: 安裝 llama-cpp-python 失敗？
A: 確保已安裝 Visual Studio Build Tools（選擇「使用 C++ 的桌面開發」工作負載）。或嘗試安裝預編譯版本：`pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124`

### Q: 模型載入失敗？
A: 確保 `models/` 目錄中包含 `GLM-OCR-Q8_0.gguf` 和 `mmproj-GLM-OCR-Q8_0.gguf` 兩個檔案。可在設定頁面點擊「檢查模型狀態」進行診斷。

### Q: OCR 識別效果不佳？
A: 嘗試使用更高解析度的影像，或使用 FP16 全精度版本（`GLM-OCR-f16.gguf`）。

### Q: 轉換速度很慢？
A: 確保已安裝 CUDA 版本的 `llama-cpp-python`，並在設定中開啟 GPU 加速。

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
