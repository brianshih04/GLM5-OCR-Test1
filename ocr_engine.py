"""
OCR 引擎模組 - 影像解碼與 Ollama GLM-OCR 推理
OCR Engine Module - Image Decoding and Ollama GLM-OCR Inference
"""

from pathlib import Path
from typing import Optional, Tuple
import numpy as np


class ImageDecoder:
    """影像解碼器 - 使用 PyTurboJPEG 加速 JPEG 解碼"""

    def __init__(self):
        """初始化影像解碼器"""
        self.turbojpeg = None
        self._init_turbojpeg()

    def _init_turbojpeg(self):
        """初始化 PyTurboJPEG"""
        try:
            from PyTurboJPEG import TurboJPEG
            # 嘗試從 bin 目錄載入 DLL
            bin_path = Path(__file__).parent / 'bin'
            if bin_path.exists():
                import os
                os.add_dll_directory(str(bin_path))
            self.turbojpeg = TurboJPEG()
        except Exception as e:
            print(f"PyTurboJPEG 初始化失敗，將使用 Pillow 作為備用: {e}")
            self.turbojpeg = None

    def decode(self, image_path: Path) -> Optional[np.ndarray]:
        """
        解碼影像檔案
        
        Args:
            image_path: 影像檔案路徑
            
        Returns:
            解碼後的影像陣列 (RGB 格式)，失敗返回 None
        """
        image_path = Path(image_path)
        
        # 優先使用 PyTurboJPEG 處理 JPEG
        if self.turbojpeg and image_path.suffix.lower() in ['.jpg', '.jpeg']:
            try:
                with open(image_path, 'rb') as f:
                    img_array = self.turbojpeg.decode(f.read())
                    # 轉換為 RGB 格式
                    if img_array.shape[-1] == 3:
                        return img_array
                    elif img_array.shape[-1] == 4:
                        return img_array[:, :, :3]
            except Exception as e:
                print(f"PyTurboJPEG 解碼失敗，嘗試使用 Pillow: {e}")

        # 使用 Pillow 作為備用方案
        return self._decode_with_pillow(image_path)

    def _decode_with_pillow(self, image_path: Path) -> Optional[np.ndarray]:
        """
        使用 Pillow 解碼影像
        
        Args:
            image_path: 影像檔案路徑
            
        Returns:
            解碼後的影像陣列 (RGB 格式)，失敗返回 None
        """
        try:
            from PIL import Image
            img = Image.open(image_path)
            # 轉換為 RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return np.array(img)
        except Exception as e:
            print(f"Pillow 解碼失敗: {e}")
            return None


class OCREngine:
    """OCR 引擎 - 使用 Ollama GLM-OCR 模型進行視覺推理"""

    def __init__(self, model_name: str = "glm-ocr:q8_0"):
        """
        初始化 OCR 引擎
        
        Args:
            model_name: Ollama 模型名稱，預設為 "glm-ocr:q8_0"
        """
        self.model_name = model_name
        self.client = None
        self.image_decoder = ImageDecoder()
        self._init_model()

    def _init_model(self):
        """初始化 Ollama 客戶端"""
        try:
            from ollama import Client
            
            # 初始化 Ollama 客戶端（預設連接到本地 Ollama 服務）
            self.client = Client(host='http://localhost:11434')
            
            # 檢查模型是否存在
            try:
                models = self.client.list()
                model_names = [m['name'] for m in models.get('models', [])]
                
                if self.model_name not in model_names:
                    print(f"警告：模型 {self.model_name} 未找到，請先執行: ollama pull {self.model_name}")
                    self.client = None
                else:
                    print(f"OCR 模型初始化成功: {self.model_name}")
                    
            except Exception as e:
                print(f"無法檢查模型列表: {e}")
                self.client = None

        except ImportError:
            print("Ollama 套件未安裝，請執行: pip install ollama")
            self.client = None
        except Exception as e:
            print(f"Ollama 客戶端初始化失敗: {e}")
            self.client = None

    def process_image(self, image_path: Path) -> Optional[str]:
        """
        處理影像並返回 OCR 結果
        
        Args:
            image_path: 影像檔案路徑
            
        Returns:
            OCR 識別的文字內容，失敗返回 None
        """
        if self.client is None:
            print("OCR 模型未初始化")
            return None

        try:
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
            return text

        except Exception as e:
            print(f"OCR 推理失敗: {e}")
            return None

    def is_ready(self) -> bool:
        """檢查 OCR 引擎是否準備就緒"""
        return self.client is not None
