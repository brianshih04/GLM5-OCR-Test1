"""
OCR 引擎模組 - 支援本地 GGUF 推理 + ZhipuAI 雲端 API
OCR Engine Module - Local GGUF Inference + ZhipuAI Cloud API

支援兩種模式：
1. 本地模式：使用 llama-cpp-python 直接載入 GGUF 模型
2. 雲端模式：使用 ZhipuAI (z.ai) OpenAI 相容 API
"""

import base64
import ctypes
import json
import logging
import mimetypes
import shutil
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

# 預設模型路徑
DEFAULT_MODEL_DIR = Path(__file__).parent / 'models'
DEFAULT_MODEL_FILE = 'GLM-OCR-Q8_0.gguf'
DEFAULT_MMPROJ_FILE = 'mmproj-GLM-OCR-Q8_0.gguf'

# ZhipuAI API 設定
ZHIPUAI_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
ZHIPUAI_MODEL_NAME = "glm-ocr"

# OCR 模式
MODE_LOCAL = "local"
MODE_CLOUD = "cloud"


def detect_gpu() -> dict:
    """
    自動偵測是否有 NVIDIA GPU 可用

    Returns:
        dict 包含:
            'available': bool - 是否偵測到 NVIDIA GPU
            'name': str - GPU 名稱（如有）
            'message': str - 偵測結果訊息
    """
    result = {'available': False, 'name': '', 'message': ''}

    # 方法 1: 嘗試 nvidia-smi
    nvidia_smi = shutil.which('nvidia-smi')
    if nvidia_smi:
        try:
            output = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if output.returncode == 0 and output.stdout.strip():
                gpu_name = output.stdout.strip().split('\n')[0]
                result['available'] = True
                result['name'] = gpu_name
                result['message'] = f'✓ 偵測到 NVIDIA GPU: {gpu_name}'
                logger.info(f"偵測到 NVIDIA GPU: {gpu_name}")
                return result
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"nvidia-smi 執行失敗: {e}")

    # 方法 2: 嘗試載入 CUDA DLL
    try:
        if hasattr(ctypes, 'windll'):
            ctypes.windll.LoadLibrary('nvcuda.dll')
            result['available'] = True
            result['name'] = 'NVIDIA GPU (via CUDA DLL)'
            result['message'] = '✓ 偵測到 NVIDIA CUDA 支援'
            logger.info("透過 CUDA DLL 偵測到 NVIDIA GPU")
            return result
    except (OSError, Exception):
        pass

    result['message'] = '✗ 未偵測到 NVIDIA GPU，將使用 CPU 推理'
    logger.info("未偵測到 NVIDIA GPU，將使用 CPU")
    return result


class ImageDecoder:
    """影像解碼器 - 使用 PyTurboJPEG 加速 JPEG 解碼（可選組件）"""

    def __init__(self):
        """初始化影像解碼器"""
        self.turbojpeg = None
        self._init_turbojpeg()

    def _init_turbojpeg(self):
        """初始化 PyTurboJPEG"""
        try:
            from turbojpeg import TurboJPEG

            bin_path = Path(__file__).parent / 'bin'
            if bin_path.exists():
                import os
                os.add_dll_directory(str(bin_path))
                lib_path = bin_path / 'libturbojpeg.dll'
                if lib_path.exists():
                    self.turbojpeg = TurboJPEG(lib_path=str(lib_path))
                else:
                    self.turbojpeg = TurboJPEG()
            else:
                self.turbojpeg = TurboJPEG()
            logger.info("PyTurboJPEG 初始化成功")
        except Exception as e:
            logger.warning(f"PyTurboJPEG 初始化失敗，將使用 Pillow 作為備用: {e}")
            self.turbojpeg = None

    def decode(self, image_path: Path) -> Optional[Image.Image]:
        """解碼影像檔案，返回 PIL Image (RGB)"""
        image_path = Path(image_path)

        if self.turbojpeg and image_path.suffix.lower() in ['.jpg', '.jpeg']:
            try:
                with open(image_path, 'rb') as f:
                    img_array = self.turbojpeg.decode(f.read())
                    img = Image.fromarray(
                        img_array[:, :, ::-1] if img_array.shape[-1] == 3
                        else img_array[:, :, :3][:, :, ::-1]
                    )
                    return img
            except Exception as e:
                logger.warning(f"PyTurboJPEG 解碼失敗，嘗試使用 Pillow: {e}")

        return self._decode_with_pillow(image_path)

    def _decode_with_pillow(self, image_path: Path) -> Optional[Image.Image]:
        """使用 Pillow 解碼影像"""
        try:
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
        except Exception as e:
            logger.error(f"Pillow 解碼失敗: {e}")
            return None


def _image_to_base64_data_uri(image_path: Path) -> str:
    """將影像檔案轉換為 base64 data URI"""
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = 'image/jpeg'

    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    return f"data:{mime_type};base64,{image_data}"


# ============================================================
# 本地 GGUF 推理引擎
# ============================================================

class OCREngine:
    """OCR 引擎 - 支援本地 GGUF 推理和 ZhipuAI 雲端 API"""

    def __init__(
        self,
        mode: str = MODE_LOCAL,
        # 本地模式參數
        model_path: Optional[Path] = None,
        mmproj_path: Optional[Path] = None,
        n_ctx: int = 4096,
        n_gpu_layers: Optional[int] = None,
        flash_attn: bool = False,
        # 雲端模式參數
        api_key: Optional[str] = None,
        api_base: str = ZHIPUAI_API_BASE,
        api_model: str = ZHIPUAI_MODEL_NAME,
        # 通用參數
        max_retries: int = 2,
    ):
        """
        初始化 OCR 引擎

        Args:
            mode: 推理模式 ('local' = 本地 GGUF, 'cloud' = ZhipuAI API)
            model_path: [本地] 主模型 GGUF 路徑
            mmproj_path: [本地] 視覺投影模型 GGUF 路徑
            n_ctx: [本地] 上下文長度
            n_gpu_layers: [本地] GPU 層數 (None=自動, -1=全GPU, 0=CPU)
            flash_attn: [本地] 是否啟用 flash attention
            api_key: [雲端] ZhipuAI API Key
            api_base: [雲端] API 基礎 URL
            api_model: [雲端] 模型名稱
            max_retries: 最大重試次數
        """
        self.mode = mode
        self.max_retries = max_retries
        self.llm = None
        self._ready = False
        self.gpu_info = {'available': False, 'name': '', 'message': ''}

        if mode == MODE_CLOUD:
            # 雲端模式
            self.api_key = api_key
            self.api_base = api_base.rstrip('/')
            self.api_model = api_model
            self._init_cloud()
        else:
            # 本地模式
            if model_path is None:
                model_path = DEFAULT_MODEL_DIR / DEFAULT_MODEL_FILE
            if mmproj_path is None:
                mmproj_path = DEFAULT_MODEL_DIR / DEFAULT_MMPROJ_FILE

            self.model_path = Path(model_path)
            self.mmproj_path = Path(mmproj_path)
            self.n_ctx = n_ctx
            self.flash_attn = flash_attn

            # 自動偵測 GPU
            if n_gpu_layers is None:
                self.gpu_info = detect_gpu()
                self.n_gpu_layers = -1 if self.gpu_info['available'] else 0
            else:
                self.n_gpu_layers = n_gpu_layers
                if n_gpu_layers != 0:
                    self.gpu_info = detect_gpu()

            self._init_local()

    # --- 雲端模式 ---

    def _init_cloud(self):
        """初始化雲端 API 模式"""
        if not self.api_key:
            logger.error("ZhipuAI API Key 未設定")
            self._ready = False
            return

        self._ready = True
        logger.info(
            f"ZhipuAI 雲端 API 模式已啟用\n"
            f"  API Base: {self.api_base}\n"
            f"  模型: {self.api_model}"
        )

    def _process_image_cloud(self, image_path: Path) -> Optional[str]:
        """使用 ZhipuAI API 進行 OCR"""
        # 編碼影像
        try:
            data_uri = _image_to_base64_data_uri(image_path)
        except Exception as e:
            logger.error(f"影像編碼失敗: {e}")
            return None

        # 建立請求
        payload = {
            "model": self.api_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                        {
                            "type": "text",
                            "text": "請識別圖片中的文字內容，並以純文字格式返回結果。",
                        },
                    ],
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        url = f"{self.api_base}/chat/completions"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"API 重試中... (第 {attempt} 次)")
                    time.sleep(2 ** attempt)  # 指數退避

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST',
                )

                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))

                text = result['choices'][0]['message']['content'].strip()
                logger.info(f"雲端 OCR 識別成功，文字長度: {len(text)}")
                return text

            except urllib.error.HTTPError as e:
                last_error = e
                error_body = e.read().decode('utf-8', errors='replace')
                logger.warning(
                    f"API HTTP 錯誤 {e.code} (嘗試 {attempt + 1}/{self.max_retries + 1}): {error_body}"
                )
                if e.code in (401, 403):
                    logger.error("API Key 無效或已過期")
                    break  # 認證錯誤不重試
            except Exception as e:
                last_error = e
                logger.warning(
                    f"API 呼叫失敗 (嘗試 {attempt + 1}/{self.max_retries + 1}): {e}"
                )

        logger.error(f"雲端 OCR 完全失敗，最後錯誤: {last_error}")
        return None

    # --- 本地模式 ---

    def _init_local(self):
        """初始化本地 GGUF 模型"""
        if not self.model_path.exists():
            logger.error(
                f"主模型檔案不存在: {self.model_path}\n"
                f"請從 https://huggingface.co/ggml-org/GLM-OCR-GGUF 下載"
            )
            self._ready = False
            return

        if not self.mmproj_path.exists():
            logger.error(
                f"視覺投影模型不存在: {self.mmproj_path}\n"
                f"請從 https://huggingface.co/ggml-org/GLM-OCR-GGUF 下載 mmproj-GLM-OCR-Q8_0.gguf"
            )
            self._ready = False
            return

        try:
            from llama_cpp import Llama
            from llama_cpp.llama_chat_format import Llava15ChatHandler

            chat_handler = Llava15ChatHandler(
                clip_model_path=str(self.mmproj_path),
                verbose=False,
            )

            self.llm = Llama(
                model_path=str(self.model_path),
                chat_handler=chat_handler,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                flash_attn=self.flash_attn,
                verbose=False,
            )

            self._ready = True
            logger.info(
                f"GLM-OCR 本地模型載入成功\n"
                f"  主模型: {self.model_path.name}\n"
                f"  視覺投影: {self.mmproj_path.name}\n"
                f"  GPU 層數: {self.n_gpu_layers}\n"
                f"  上下文長度: {self.n_ctx}"
            )

        except ImportError:
            logger.error(
                "llama-cpp-python 套件未安裝。請執行:\n"
                "  pip install llama-cpp-python\n"
                "  (Windows 需要已安裝 Visual Studio Build Tools)"
            )
            self._ready = False
        except Exception as e:
            logger.error(f"模型載入失敗: {e}")
            self._ready = False

    def _process_image_local(self, image_path: Path) -> Optional[str]:
        """使用本地 GGUF 模型進行 OCR"""
        try:
            data_uri = _image_to_base64_data_uri(image_path)
        except Exception as e:
            logger.error(f"影像編碼失敗: {e}")
            return None

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"OCR 重試中... (第 {attempt} 次)")
                    time.sleep(1)

                response = self.llm.create_chat_completion(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_uri},
                                },
                                {
                                    "type": "text",
                                    "text": "請識別圖片中的文字內容，並以純文字格式返回結果。",
                                },
                            ],
                        }
                    ],
                    max_tokens=2048,
                    temperature=0.1,
                )

                text = response['choices'][0]['message']['content'].strip()
                logger.info(f"本地 OCR 識別成功，文字長度: {len(text)}")
                return text

            except Exception as e:
                last_error = e
                logger.warning(
                    f"本地 OCR 推理失敗 (嘗試 {attempt + 1}/{self.max_retries + 1}): {e}"
                )

        logger.error(f"本地 OCR 完全失敗，最後錯誤: {last_error}")
        return None

    # --- 通用介面 ---

    def check_model_status(self) -> dict:
        """
        檢查模型/API 狀態

        Returns:
            dict 包含狀態資訊
        """
        if self.mode == MODE_CLOUD:
            return {
                'loaded': self._ready,
                'mode': MODE_CLOUD,
                'message': f"✓ 雲端 API 模式 ({self.api_model})" if self._ready
                           else "✗ API Key 未設定",
            }

        result = {
            'model_exists': self.model_path.exists(),
            'mmproj_exists': self.mmproj_path.exists(),
            'loaded': self._ready,
            'mode': MODE_LOCAL,
            'message': '',
            'model_path': str(self.model_path),
            'mmproj_path': str(self.mmproj_path),
        }

        if not result['model_exists']:
            result['message'] = f"✗ 主模型不存在: {self.model_path}"
        elif not result['mmproj_exists']:
            result['message'] = f"✗ 視覺投影模型不存在: {self.mmproj_path}"
        elif not result['loaded']:
            result['message'] = "✗ 模型檔案存在但載入失敗（請檢查 llama-cpp-python）"
        else:
            model_size_mb = self.model_path.stat().st_size / (1024 * 1024)
            result['message'] = f"✓ 本地模型已載入 ({self.model_path.name}, {model_size_mb:.0f} MB)"

        return result

    def process_image(self, image_path: Path) -> Optional[str]:
        """
        處理影像並返回 OCR 結果

        Args:
            image_path: 影像檔案路徑

        Returns:
            OCR 識別的文字內容，失敗返回 None
        """
        if not self._ready:
            logger.error("OCR 引擎未就緒")
            return None

        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"影像檔案不存在: {image_path}")
            return None

        if self.mode == MODE_CLOUD:
            return self._process_image_cloud(image_path)
        else:
            if self.llm is None:
                logger.error("本地模型未載入")
                return None
            return self._process_image_local(image_path)

    def is_ready(self) -> bool:
        """檢查 OCR 引擎是否準備就緒"""
        if self.mode == MODE_CLOUD:
            return self._ready
        return self._ready and self.llm is not None
