"""
OCR 引擎模組 - 影像解碼與 Ollama GLM-OCR 推理
OCR Engine Module - Image Decoding and Ollama GLM-OCR Inference
"""

import logging
import time
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


class ImageDecoder:
    """影像解碼器 - 使用 PyTurboJPEG 加速 JPEG 解碼（可選組件）

    注意：目前 Ollama chat API 直接接受檔案路徑，不需要預先解碼。
    此類別保留作為未來需要影像預處理時的工具。
    """

    def __init__(self):
        """初始化影像解碼器"""
        self.turbojpeg = None
        self._init_turbojpeg()

    def _init_turbojpeg(self):
        """初始化 PyTurboJPEG"""
        try:
            from turbojpeg import TurboJPEG

            # 嘗試從 bin 目錄載入 DLL
            bin_path = Path(__file__).parent / 'bin'
            if bin_path.exists():
                import os
                os.add_dll_directory(str(bin_path))
                # 使用正確的 DLL 檔名 libturbojpeg.dll
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
        """
        解碼影像檔案

        Args:
            image_path: 影像檔案路徑

        Returns:
            PIL Image 物件 (RGB 格式)，失敗返回 None
        """
        image_path = Path(image_path)

        # 優先使用 PyTurboJPEG 處理 JPEG
        if self.turbojpeg and image_path.suffix.lower() in ['.jpg', '.jpeg']:
            try:
                with open(image_path, 'rb') as f:
                    img_array = self.turbojpeg.decode(f.read())
                    # TurboJPEG 回傳 BGR，轉換為 RGB PIL Image
                    img = Image.fromarray(img_array[:, :, ::-1] if img_array.shape[-1] == 3 else img_array[:, :, :3][:, :, ::-1])
                    return img
            except Exception as e:
                logger.warning(f"PyTurboJPEG 解碼失敗，嘗試使用 Pillow: {e}")

        # 使用 Pillow 作為備用方案
        return self._decode_with_pillow(image_path)

    def _decode_with_pillow(self, image_path: Path) -> Optional[Image.Image]:
        """
        使用 Pillow 解碼影像

        Args:
            image_path: 影像檔案路徑

        Returns:
            PIL Image 物件 (RGB 格式)，失敗返回 None
        """
        try:
            img = Image.open(image_path)
            # 轉換為 RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
        except Exception as e:
            logger.error(f"Pillow 解碼失敗: {e}")
            return None


class OCREngine:
    """OCR 引擎 - 使用 Ollama GLM-OCR 模型進行視覺推理"""

    def __init__(self, model_name: str = "glm-ocr:q8_0", max_retries: int = 2, timeout: int = 120):
        """
        初始化 OCR 引擎

        Args:
            model_name: Ollama 模型名稱，預設為 "glm-ocr:q8_0"
            max_retries: 最大重試次數
            timeout: 請求超時時間（秒）
        """
        self.model_name = model_name
        self.max_retries = max_retries
        self.timeout = timeout
        self.client = None
        self._ready = False
        self._init_model()

    def _init_model(self):
        """初始化 Ollama 客戶端"""
        try:
            from ollama import Client

            # 初始化 Ollama 客戶端（預設連接到本地 Ollama 服務）
            self.client = Client(host='http://localhost:11434')

            # 檢查模型是否存在
            self._check_model_availability()

        except ImportError:
            logger.error("Ollama 套件未安裝，請執行: pip install ollama")
            self.client = None
            self._ready = False
        except Exception as e:
            logger.error(f"Ollama 客戶端初始化失敗: {e}")
            self.client = None
            self._ready = False

    def _check_model_availability(self):
        """檢查模型是否可用"""
        try:
            models = self.client.list()
            model_list = models.get('models', [])
            model_names = [m.get('name', '') for m in model_list]

            # 支援部分名稱匹配（例如 "glm-ocr:q8_0" 匹配 "glm-ocr:q8_0"）
            found = False
            for name in model_names:
                if self.model_name in name or name in self.model_name:
                    found = True
                    break

            if not found:
                logger.warning(
                    f"模型 {self.model_name} 未找到。"
                    f"可用模型: {model_names}。"
                    f"請先執行: ollama pull {self.model_name}"
                )
                self._ready = False
            else:
                logger.info(f"OCR 模型初始化成功: {self.model_name}")
                self._ready = True

        except Exception as e:
            logger.error(f"無法檢查模型列表: {e}")
            self._ready = False

    def check_service_status(self) -> dict:
        """
        檢查 Ollama 服務與模型狀態

        Returns:
            dict 包含 'service_available', 'model_available', 'message' 等資訊
        """
        result = {
            'service_available': False,
            'model_available': False,
            'message': ''
        }

        try:
            from ollama import Client
            client = Client(host='http://localhost:11434')
            models = client.list()
            result['service_available'] = True

            model_list = models.get('models', [])
            model_names = [m.get('name', '') for m in model_list]

            for name in model_names:
                if self.model_name in name or name in self.model_name:
                    result['model_available'] = True
                    break

            if result['model_available']:
                result['message'] = f"✓ Ollama 服務正常，模型 {self.model_name} 已就緒"
            else:
                result['message'] = f"⚠ Ollama 服務正常，但模型 {self.model_name} 未安裝"

        except ImportError:
            result['message'] = "✗ Ollama 套件未安裝"
        except Exception as e:
            result['message'] = f"✗ 無法連接 Ollama 服務: {e}"

        return result

    def process_image(self, image_path: Path) -> Optional[str]:
        """
        處理影像並返回 OCR 結果（帶重試機制）

        Args:
            image_path: 影像檔案路徑

        Returns:
            OCR 識別的文字內容，失敗返回 None
        """
        if self.client is None or not self._ready:
            logger.error("OCR 模型未初始化")
            return None

        image_path = Path(image_path)
        if not image_path.exists():
            logger.error(f"影像檔案不存在: {image_path}")
            return None

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"OCR 重試中... (第 {attempt} 次)")
                    time.sleep(1)  # 重試前等待

                # 使用 Ollama 的 chat API 處理影像
                response = self.client.chat(
                    model=self.model_name,
                    messages=[
                        {
                            'role': 'user',
                            'content': '請識別圖片中的文字內容，並以純文字格式返回結果。',
                            'images': [str(image_path)]
                        }
                    ],
                    options={
                        'temperature': 0.1,
                        'num_predict': 2048,
                    }
                )

                # 提取文字結果
                text = response['message']['content'].strip()
                logger.info(f"OCR 識別成功，文字長度: {len(text)}")
                return text

            except Exception as e:
                last_error = e
                logger.warning(f"OCR 推理失敗 (嘗試 {attempt + 1}/{self.max_retries + 1}): {e}")

                # 檢查是否需要重新初始化客戶端
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    logger.info("嘗試重新連接 Ollama 服務...")
                    self._init_model()

        # 所有重試都失敗
        logger.error(f"OCR 識別完全失敗，最後錯誤: {last_error}")
        return None

    def is_ready(self) -> bool:
        """檢查 OCR 引擎是否準備就緒"""
        return self.client is not None and self._ready
