"""
PDF 建構模組 - 產生雙層可搜尋 PDF
PDF Builder Module - Generate Dual-Layer Searchable PDF
"""

import logging
import unicodedata
from pathlib import Path
from typing import Optional, List, Tuple

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


def _is_wide_char(c: str) -> bool:
    """判斷字元是否為全形/CJK 字元"""
    eaw = unicodedata.east_asian_width(c)
    return eaw in ('W', 'F')


def _estimate_text_width(text: str, font_size: float) -> float:
    """
    估算文字渲染寬度

    中文字元寬度約等於 font_size，英文字元約為 font_size * 0.5
    """
    width = 0.0
    for c in text:
        if _is_wide_char(c):
            width += font_size  # 全形字元
        else:
            width += font_size * 0.5  # 半形字元
    return width


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
            logger.warning(f"字型檔案不存在: {self.font_path}")
            # 嘗試在同目錄下找其他 .ttf
            parent = self.font_path.parent
            if parent.exists():
                for ttf in parent.glob('*.ttf'):
                    logger.info(f"自動找到備用字型: {ttf}")
                    self.font_path = ttf
                    return
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

            logger.info(f"PDF 建立成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"PDF 建構失敗: {e}")
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
            logger.error(f"無法取得影像尺寸: {e}")
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
            logger.error(f"插入影像層失敗: {e}")

    def _insert_text_layer(self, page: fitz.Page, ocr_text: str, dpi: int = 150,
                           font_size: float = 10, line_spacing: float = 1.5):
        """
        插入文字層（不可見文字，用於搜尋）

        使用 render_mode=3 (invisible) 讓文字不可見但可搜尋。
        PyMuPDF 座標原點在左上角，Y 軸向下遞增。

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

            # 使用 TextWriter 進行排版
            tw = fitz.TextWriter(page.rect)

            # 載入字型
            if self.font_path and self.font_path.exists():
                font = fitz.Font(fontfile=str(self.font_path))
            else:
                font = fitz.Font("helv")
                logger.warning("使用內建字型 Helvetica，中文字元可能無法正確顯示")

            # 頁面邊距
            margin = 50

            # 計算可用寬度
            available_width = page.rect.width - 2 * margin

            # 將文字分為多行
            lines = ocr_text.split('\n')

            # 包裝長行文字（考慮中英文寬度差異）
            wrapped_lines = []
            for line in lines:
                if not line:
                    wrapped_lines.append('')
                    continue

                estimated_width = _estimate_text_width(line, font_size)
                if estimated_width <= available_width:
                    wrapped_lines.append(line)
                else:
                    # 按寬度換行
                    current_line = ''
                    current_width = 0.0
                    for ch in line:
                        ch_width = font_size if _is_wide_char(ch) else font_size * 0.5
                        if current_width + ch_width > available_width and current_line:
                            wrapped_lines.append(current_line)
                            current_line = ch
                            current_width = ch_width
                        else:
                            current_line += ch
                            current_width += ch_width
                    if current_line:
                        wrapped_lines.append(current_line)

            # PyMuPDF 座標: 原點在左上角，Y 軸向下
            y_pos = margin + font_size  # 從頂部邊距開始（加上 font_size 因為 baseline 在文字底部）
            x_pos = margin

            # 使用 TextWriter 逐行插入文字
            for line in wrapped_lines:
                if not line.strip():
                    y_pos += line_height
                    continue

                # 檢查是否超出頁面底部
                if y_pos > page.rect.height - margin:
                    break

                try:
                    tw.append(
                        pos=(x_pos, y_pos),
                        text=line,
                        font=font,
                        fontsize=font_size,
                    )
                except Exception as e:
                    logger.debug(f"文字行寫入失敗 (可能含不支援字元): {e}")

                y_pos += line_height

            # 將 TextWriter 內容寫入頁面
            # render_mode=3 = invisible text (可搜尋但不可見)
            # color=(0, 0, 0) = 黑色 (RGB 三元組)
            tw.write_text(page, color=(0, 0, 0), render_mode=3)

        except Exception as e:
            logger.error(f"插入文字層失敗: {e}")

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

            logger.info(f"PDF (含版面) 建立成功: {output_path}")
            return True

        except Exception as e:
            logger.error(f"PDF 建構失敗: {e}")
            return False

    def _insert_text_layer_with_layout(self, page: fitz.Page, ocr_result: List[dict]):
        """
        使用版面資訊插入文字層

        Args:
            page: PyMuPDF 頁面物件
            ocr_result: OCR 結果列表
        """
        try:
            tw = fitz.TextWriter(page.rect)

            # 載入字型
            if self.font_path and self.font_path.exists():
                font = fitz.Font(fontfile=str(self.font_path))
            else:
                font = fitz.Font("helv")

            # 插入每個文字區塊
            for item in ocr_result:
                text = item.get('text', '')
                bbox = item.get('bbox', [0, 0, 0, 0])

                if not text:
                    continue

                # 計算字體大小（根據 bbox 高度）
                height = bbox[3] - bbox[1]
                font_size = max(8, height * 0.8)

                # PyMuPDF 座標原點在左上角
                try:
                    tw.append(
                        pos=(bbox[0], bbox[3]),
                        text=text,
                        font=font,
                        fontsize=font_size,
                    )
                except Exception as e:
                    logger.debug(f"版面文字寫入失敗: {e}")

            # render_mode=3 = invisible rendering
            tw.write_text(page, color=(0, 0, 0), render_mode=3)

        except Exception as e:
            logger.error(f"插入文字層失敗: {e}")
