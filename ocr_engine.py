"""
OCR 引擎模組 - 影像解碼與 llama-cpp-python 推理
OCR Engine Module - Image Decoding and llama-cpp-python Inference
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
    """OCR 引擎 - 使用 llama-cpp-python 進行視覺模型推理"""

    def __init__(self, model_path: Path, mmproj_path: Optional[Path] = None):
        """
        初始化 OCR 引擎
        
        Args:
            model_path: GGUF 模型檔案路徑
            mmproj_path: 視覺投影檔案路徑（多模態模型需要）
        """
        self.model_path = Path(model_path)
        self.mmproj_path = Path(mmproj_path) if mmproj_path else None
        self.model = None
        self.image_decoder = ImageDecoder()
        self._init_model()

    def _init_model(self):
        """初始化 llama-cpp-python 模型"""
        try:
            from llama_cpp import Llama
            
            # 檢查模型檔案是否存在
            if not self.model_path.exists():
                raise FileNotFoundError(f"模型檔案不存在: {self.model_path}")

            # 初始化模型參數
            model_params = {
                'model_path': str(self.model_path),
                'n_ctx': 2048,  # 上下文長度
                'n_gpu_layers': -1,  # 使用 GPU 加速（如果可用）
                'verbose': False,
            }

            # 如果有多模態投影檔，添加參數
            if self.mmproj_path and self.mmproj_path.exists():
                model_params['mmproj'] = str(self.mmproj_path)

            self.model = Llama(**model_params)
            print("OCR 模型初始化成功")

        except Exception as e:
            print(f"OCR 模型初始化失敗: {e}")
            self.model = None

    def process_image(self, image_path: Path) -> Optional[str]:
        """
        處理影像並返回 OCR 結果
        
        Args:
            image_path: 影像檔案路徑
            
        Returns:
            OCR 識別的文字內容，失敗返回 None
        """
        if self.model is None:
            print("OCR 模型未初始化")
            return None

        # 解碼影像
        img_array = self.image_decoder.decode(image_path)
        if img_array is None:
            print(f"影像解碼失敗: {image_path}")
            return None

        try:
            # 執行 OCR 推理
            # 注意：具體的 API 調用方式取決於使用的視覺模型
            # 這裡提供一個通用的框架
            
            # 將影像轉換為模型所需的格式
            # 這部分需要根據具體模型調整
            
            # 執行推理
            result = self.model(
                prompt="請識別圖片中的文字內容：",
                images=[img_array],
                max_tokens=2048,
                temperature=0.1,
            )
            
            # 提取文字結果
            text = result['choices'][0]['text'].strip()
            return text

        except Exception as e:
            print(f"OCR 推理失敗: {e}")
            return None

    def is_ready(self) -> bool:
        """檢查 OCR 引擎是否準備就緒"""
        return self.model is not None
