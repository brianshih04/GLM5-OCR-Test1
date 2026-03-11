"""
PDF 建構模組 - 產生雙層可搜尋 PDF
PDF Builder Module - Generate Dual-Layer Searchable PDF
"""

from pathlib import Path
from typing import Optional, List, Tuple
import fitz  # PyMuPDF
from PIL import Image


class PDFBuilder:
    """PDF 建構器 - 產生雙層可搜尋 PDF"""

    def __init__(self, font_path: Optional[Path] = None):
        """
        初始化 PDF 建構器
        
        Args:
            font_path: 中文字型檔案路徑（用於渲染文字層）
        """
        self.font_path = Path(font_path) if font_path else None
        self._validate_font()

    def _validate_font(self):
        """驗證字型檔案"""
        if self.font_path and not self.font_path.exists():
            print(f"警告：字型檔案不存在: {self.font_path}")
            self.font_path = None

    def create_dual_layer_pdf(
        self,
        image_path: Path,
        ocr_text: str,
        output_path: Path,
        dpi: int = 150
    ) -> bool:
        """
        建立雙層 PDF（影像層 + 文字層）
        
        Args:
            image_path: 來源影像路徑
            ocr_text: OCR 識別的文字內容
            output_path: 輸出 PDF 路徑
            dpi: 影像 DPI（影響文字層位置計算）
            
        Returns:
            成功返回 True，失敗返回 False
        """
        try:
            # 建立新 PDF 文件
            doc = fitz.open()
            
            # 計算頁面尺寸（基於影像）
            page_width, page_height = self._get_image_dimensions(image_path)
            
            # 建立頁面
            page = doc.new_page(width=page_width, height=page_height)
            
            # 插入影像層
            self._insert_image_layer(page, image_path)
            
            # 插入文字層（透明文字）
            self._insert_text_layer(page, ocr_text, dpi)
            
            # 儲存 PDF
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), deflate=True)
            doc.close()
            
            return True

        except Exception as e:
            print(f"PDF 建構失敗: {e}")
            return False

    def _get_image_dimensions(self, image_path: Path, assumed_dpi: int = 150) -> Tuple[float, float]:
        """
        取得影像尺寸
        
        Args:
            image_path: 影像路徑
            assumed_dpi: 假設的原始影像 DPI
            
        Returns:
            (width, height) 單位為點（72 DPI）
        """
        try:
            with Image.open(image_path) as img:
                # 嘗試從 EXIF 讀取 DPI，如果失敗則使用預設值
                try:
                    dpi = img.info.get('dpi', (assumed_dpi, assumed_dpi))
                    x_dpi = dpi[0] if dpi[0] > 0 else assumed_dpi
                    y_dpi = dpi[1] if dpi[1] > 0 else assumed_dpi
                except (KeyError, TypeError, IndexError):
                    x_dpi = y_dpi = assumed_dpi
                
                # 將像素轉換為點（PDF 使用 72 DPI）
                width_pt = img.width * 72 / x_dpi
                height_pt = img.height * 72 / y_dpi
                return width_pt, height_pt
        except Exception as e:
            print(f"無法取得影像尺寸: {e}")
            return 595.0, 842.0  # A4 尺寸

    def _insert_image_layer(self, page: fitz.Page, image_path: Path):
        """
        插入影像層
        
        Args:
            page: PyMuPDF 頁面物件
            image_path: 影像路徑
        """
        try:
            # 插入影像並填滿整個頁面
            rect = page.rect
            page.insert_image(rect, filename=str(image_path))
        except Exception as e:
            print(f"插入影像層失敗: {e}")

    def _insert_text_layer(self, page: fitz.Page, ocr_text: str, dpi: int = 150, 
                           font_size: float = 10, line_spacing: float = 1.5):
        """
        插入文字層（透明文字）
        
        Args:
            page: PyMuPDF 頁面物件
            ocr_text: OCR 識別的文字
            dpi: 影像 DPI
            font_size: 字體大小
            line_spacing: 行距倍數
        """
        try:
            # 計算行高
            line_height = font_size * line_spacing
            
            # 選擇字型
            if self.font_path:
                fontname = page.insert_font(str(self.font_path))
            else:
                fontname = "helv"  # 使用內建字型
            
            # 設定文字顏色為近乎透明（便於搜尋但幾乎不可見）
            text_color = (0, 0, 0, 0.01)  # 非常淡的黑色
            
            # 將文字分為多行
            lines = ocr_text.split('\n')
            
            # 頁面邊距
            margin = 50
            
            # 計算可用寬度
            available_width = page.rect.width - 2 * margin
            
            # 估算每行最大字數（粗略估算，中文約為字體大小的 1.5 倍）
            max_chars_per_line = int(available_width / (font_size * 0.6))
            
            # 包裝長行文字
            wrapped_lines = []
            for line in lines:
                if len(line) > max_chars_per_line:
                    # 簡單的按字數換行
                    for i in range(0, len(line), max_chars_per_line):
                        wrapped_lines.append(line[i:i + max_chars_per_line])
                else:
                    wrapped_lines.append(line)
            
            # 計算起始位置（從頁面頂部開始，PDF 座標系原點在左下角）
            y_pos = page.rect.height - margin  # 從上方開始
            x_pos = margin  # 左邊距
            
            # 插入每一行文字
            for line in wrapped_lines:
                if not line.strip():
                    y_pos -= line_height
                    continue
                
                # 檢查是否超出頁面底部
                if y_pos < margin:
                    break
                
                # 插入文字
                point = fitz.Point(x_pos, y_pos)
                page.insert_text(
                    point,
                    line,
                    fontname=fontname,
                    fontsize=font_size,
                    color=text_color
                )
                
                y_pos -= line_height

        except Exception as e:
            print(f"插入文字層失敗: {e}")

    def create_dual_layer_pdf_with_layout(
        self,
        image_path: Path,
        ocr_result: List[dict],
        output_path: Path
    ) -> bool:
        """
        建立帶有版面資訊的雙層 PDF
        
        Args:
            image_path: 來源影像路徑
            ocr_result: OCR 結果列表，每個元素包含文字和位置資訊
                [{'text': '文字', 'bbox': [x0, y0, x1, y1]}, ...]
            output_path: 輸出 PDF 路徑
            
        Returns:
            成功返回 True，失敗返回 False
        """
        try:
            doc = fitz.open()
            
            # 建立頁面
            page_width, page_height = self._get_image_dimensions(image_path)
            page = doc.new_page(width=page_width, height=page_height)
            
            # 插入影像層
            self._insert_image_layer(page, image_path)
            
            # 插入文字層（使用精確位置）
            self._insert_text_layer_with_layout(page, ocr_result)
            
            # 儲存 PDF
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), deflate=True)
            doc.close()
            
            return True

        except Exception as e:
            print(f"PDF 建構失敗: {e}")
            return False

    def _insert_text_layer_with_layout(self, page: fitz.Page, ocr_result: List[dict]):
        """
        使用版面資訊插入文字層
        
        Args:
            page: PyMuPDF 頁面物件
            ocr_result: OCR 結果列表
        """
        try:
            # 選擇字型
            if self.font_path:
                fontname = page.insert_font(str(self.font_path))
            else:
                fontname = "helv"
            
            # 設定文字顏色為透明
            text_color = (0, 0, 0, 0)
            
            # 插入每個文字區塊
            for item in ocr_result:
                text = item.get('text', '')
                bbox = item.get('bbox', [0, 0, 0, 0])
                
                if not text:
                    continue
                
                # 計算字體大小（根據 bbox 高度）
                height = bbox[3] - bbox[1]
                font_size = max(8, height * 0.8)
                
                # 插入文字
                point = fitz.Point(bbox[0], bbox[3])
                page.insert_text(
                    point,
                    text,
                    fontname=fontname,
                    fontsize=font_size,
                    color=text_color
                )

        except Exception as e:
            print(f"插入文字層失敗: {e}")
