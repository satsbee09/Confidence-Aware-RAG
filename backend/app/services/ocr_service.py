import io
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image
from loguru import logger

from app.core.config import settings
from app.schemas.ocr import OCRDocument, OCRPage, OCRLine, OCRWord


class BaseOCREngine(ABC):
    """
    Abstract Base Class for OCR Engines.
    Enforces word-level and line-level confidence and bounding-box extraction.
    """

    @abstractmethod
    def extract_from_image(self, image: Image.Image, page_number: int) -> OCRPage:
        """
        Extract text, bounding boxes, and confidence scores from a PIL Image.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the required engine binaries or libraries are available.
        """
        pass


class PaddleOCREngine(BaseOCREngine):
    """
    PaddleOCR Engine implementation.
    Extracts text lines, polygon/box coordinates, and recognition confidence scores.
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._ocr = None

    def is_available(self) -> bool:
        try:
            import importlib
            importlib.import_module("paddleocr")
            return True
        except (ImportError, Exception):
            return False

    def _get_ocr_instance(self):
        if self._ocr is None:
            try:
                import importlib
                paddle_mod = importlib.import_module("paddleocr")
                paddle_cls = getattr(paddle_mod, "PaddleOCR")
                # Initialize with angle classification and specified language
                self._ocr = paddle_cls(use_angle_cls=True, lang=self.lang, show_log=False)
            except (ImportError, Exception) as e:
                raise RuntimeError(
                    f"PaddleOCR is not available in the current environment: {e}. "
                    "Use TesseractOCREngine or DigitalPDFEngine instead."
                )
        return self._ocr

    def extract_from_image(self, image: Image.Image, page_number: int) -> OCRPage:
        import numpy as np

        img_np = np.array(image.convert("RGB"))
        ocr = self._get_ocr_instance()
        result = ocr.ocr(img_np, cls=True)

        lines: List[OCRLine] = []
        all_words: List[OCRWord] = []
        line_idx = 1

        if result and len(result) > 0 and result[0] is not None:
            for line_data in result[0]:
                box, (text, conf) = line_data
                # box is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                bbox = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
                conf = float(conf)

                # Approximate word-level splitting from line
                tokens = text.strip().split()
                line_words: List[OCRWord] = []
                if tokens:
                    num_tokens = len(tokens)
                    token_width = (bbox[2] - bbox[0]) / max(num_tokens, 1)
                    for i, tok in enumerate(tokens):
                        w_bbox = [
                            bbox[0] + i * token_width,
                            bbox[1],
                            bbox[0] + (i + 1) * token_width,
                            bbox[3],
                        ]
                        word_obj = OCRWord(
                            text=tok,
                            confidence=conf,
                            page=page_number,
                            bbox=w_bbox,
                            line_number=line_idx,
                        )
                        line_words.append(word_obj)
                        all_words.append(word_obj)

                line_obj = OCRLine(
                    text=text,
                    confidence=conf,
                    page=page_number,
                    bbox=bbox,
                    line_number=line_idx,
                    words=line_words,
                )
                lines.append(line_obj)
                line_idx += 1

        # Calculate statistics
        page_text = "\n".join([line.text for line in lines])
        if all_words:
            avg_conf = sum(w.confidence for w in all_words) / len(all_words)
            min_conf = min(w.confidence for w in all_words)
        else:
            avg_conf = 1.0
            min_conf = 1.0

        return OCRPage(
            page=page_number,
            width=image.width,
            height=image.height,
            lines=lines,
            words=all_words,
            text=page_text,
            average_confidence=round(avg_conf, 4),
            min_confidence=round(min_conf, 4),
        )


class TesseractOCREngine(BaseOCREngine):
    """
    Tesseract OCR Engine implementation using pytesseract.
    Parses word-level and line-level data with bounding boxes and normalized confidence.
    """

    def __init__(self, lang: str = "eng", tesseract_cmd: str = ""):
        self.lang = lang
        self.tesseract_cmd = tesseract_cmd

    def is_available(self) -> bool:
        try:
            import pytesseract
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_from_image(self, image: Image.Image, page_number: int) -> OCRPage:
        import pytesseract
        from pytesseract import Output

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        # Extract detailed word-level data dictionary
        data = pytesseract.image_to_data(
            image.convert("RGB"),
            lang=self.lang,
            output_type=Output.DICT,
        )

        n_boxes = len(data["text"])
        lines_dict: Dict[Tuple[int, int], List[OCRWord]] = {}
        all_words: List[OCRWord] = []

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf_val = float(data["conf"][i])

            # Filter out empty tokens or invalid noise (-1 confidence)
            if not text or conf_val < 0:
                continue

            # Normalize confidence from 0-100 to 0.0-1.0
            conf = conf_val / 100.0
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            bbox = [float(x), float(y), float(x + w), float(y + h)]

            block_num = data["block_num"][i]
            line_num = data["line_num"][i]
            key = (block_num, line_num)

            word_obj = OCRWord(
                text=text,
                confidence=conf,
                page=page_number,
                bbox=bbox,
                line_number=line_num,
            )
            all_words.append(word_obj)

            if key not in lines_dict:
                lines_dict[key] = []
            lines_dict[key].append(word_obj)

        # Build lines
        lines: List[OCRLine] = []
        for line_idx, ((_, _), words) in enumerate(lines_dict.items(), start=1):
            line_text = " ".join(w.text for w in words)
            line_conf = sum(w.confidence for w in words) / len(words)
            min_x = min(w.bbox[0] for w in words)
            min_y = min(w.bbox[1] for w in words)
            max_x = max(w.bbox[2] for w in words)
            max_y = max(w.bbox[3] for w in words)

            for w in words:
                w.line_number = line_idx

            lines.append(
                OCRLine(
                    text=line_text,
                    confidence=round(line_conf, 4),
                    page=page_number,
                    bbox=[min_x, min_y, max_x, max_y],
                    line_number=line_idx,
                    words=words,
                )
            )

        page_text = "\n".join(l.text for l in lines)
        if all_words:
            avg_conf = sum(w.confidence for w in all_words) / len(all_words)
            min_conf = min(w.confidence for w in all_words)
        else:
            avg_conf = 1.0
            min_conf = 1.0

        return OCRPage(
            page=page_number,
            width=image.width,
            height=image.height,
            lines=lines,
            words=all_words,
            text=page_text,
            average_confidence=round(avg_conf, 4),
            min_confidence=round(min_conf, 4),
        )


class DigitalPDFEngine(BaseOCREngine):
    """
    Direct Digital PDF Text Extraction Engine using PyMuPDF (fitz).
    Used for native digital PDFs or as a fast testing fallback engine.
    Extracts word positions and assigns default high confidence (0.98+).
    """

    def is_available(self) -> bool:
        try:
            import fitz  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_from_image(self, image: Image.Image, page_number: int) -> OCRPage:
        # Fallback empty page if only image is provided to digital engine
        return OCRPage(
            page=page_number,
            width=image.width,
            height=image.height,
            lines=[],
            words=[],
            text="",
            average_confidence=1.0,
            min_confidence=1.0,
        )

    def extract_from_pdf_page(self, page_obj, page_number: int) -> OCRPage:
        """Extract text blocks and words directly from PyMuPDF page object."""
        # page.get_text("words") returns (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        word_tuples = page_obj.get_text("words")
        rect = page_obj.rect
        width = int(rect.width)
        height = int(rect.height)

        all_words: List[OCRWord] = []
        lines_dict: Dict[Tuple[int, int], List[OCRWord]] = {}

        for w_tuple in word_tuples:
            x0, y0, x1, y1, text, block_no, line_no, _ = w_tuple
            text = text.strip()
            if not text:
                continue

            # Calculate calibrated confidence:
            # Clean digital text has high optical fidelity (0.99).
            # Detect genuine OCR corruption artifacts, replacement characters, or unmapped font glyphs.
            conf = 0.99
            
            # 1. Unprintable control characters or Unicode replacement (\ufffd)
            has_unicode_err = "\ufffd" in text or any(ord(c) < 32 and c not in "\t\n\r" for c in text)
            
            # 2. Obvious OCR noise tokens (e.g. repeated tildes, backticks, pipes like '~~~', '|||')
            has_raw_noise = bool(re.search(r"[~`^|\\]{2,}", text))
            
            # 3. Non-standard corrupt mojibake characters (excluding standard typography, bullets, quotes, dashes, and currencies)
            standard_punct = set(".,:;!?()[]{}-_/@&%$₹€£¥#+=*\"'<>~`^|•▪●○★–—«»“”‘’′″→←↑↓©®™°±×÷§¶…")
            corrupt_symbols = [c for c in text if not c.isalnum() and c not in standard_punct and not c.isspace()]
            has_excessive_mojibake = len(corrupt_symbols) > 0 and (len(corrupt_symbols) / max(1, len(text)) > 0.40)

            if has_unicode_err or has_raw_noise or has_excessive_mojibake:
                conf = 0.52  # Flagged below low-confidence threshold
            else:
                conf = 0.99

            word_obj = OCRWord(
                text=text,
                confidence=conf,
                page=page_number,
                bbox=[float(x0), float(y0), float(x1), float(y1)],
                line_number=line_no,
            )
            all_words.append(word_obj)
            key = (block_no, line_no)
            if key not in lines_dict:
                lines_dict[key] = []
            lines_dict[key].append(word_obj)

        lines: List[OCRLine] = []
        for line_idx, ((_, _), words) in enumerate(lines_dict.items(), start=1):
            line_text = " ".join(w.text for w in words)
            min_x = min(w.bbox[0] for w in words)
            min_y = min(w.bbox[1] for w in words)
            max_x = max(w.bbox[2] for w in words)
            max_y = max(w.bbox[3] for w in words)
            line_conf = round(sum(w.confidence for w in words) / len(words), 4) if words else 0.99

            for w in words:
                w.line_number = line_idx

            lines.append(
                OCRLine(
                    text=line_text,
                    confidence=line_conf,
                    page=page_number,
                    bbox=[min_x, min_y, max_x, max_y],
                    line_number=line_idx,
                    words=words,
                )
            )


        page_text = "\n".join(l.text for l in lines)
        return OCRPage(
            page=page_number,
            width=width,
            height=height,
            lines=lines,
            words=all_words,
            text=page_text,
            average_confidence=0.99 if all_words else 1.0,
            min_confidence=0.99 if all_words else 1.0,
        )


class OCRService:
    """
    Main OCR Orchestrator Service.
    Handles PDF rasterization, engine selection, page-by-page error isolation,
    and hierarchical confidence aggregation.
    """

    def __init__(self, engine_override: Optional[str] = None):
        self.engine_type = engine_override or settings.OCR_ENGINE
        self.engine = self._select_engine()
        logger.info(f"OCRService initialized with engine: {type(self.engine).__name__}")

    def _select_engine(self) -> BaseOCREngine:
        if self.engine_type == "paddleocr":
            paddle_eng = PaddleOCREngine(lang=settings.OCR_LANG)
            if paddle_eng.is_available():
                return paddle_eng
            logger.warning("PaddleOCR requested but unavailable. Falling back to Tesseract / Digital.")

        if self.engine_type == "tesseract":
            tess_eng = TesseractOCREngine(lang="eng", tesseract_cmd=settings.TESSERACT_CMD)
            if tess_eng.is_available():
                return tess_eng
            logger.warning("Tesseract requested but unavailable. Falling back to Digital engine.")

        # Auto selection: PaddleOCR -> Tesseract -> Digital
        paddle = PaddleOCREngine(lang=settings.OCR_LANG)
        if paddle.is_available():
            return paddle

        tess = TesseractOCREngine(lang="eng", tesseract_cmd=settings.TESSERACT_CMD)
        if tess.is_available():
            return tess

        return DigitalPDFEngine()

    def process_pdf(self, file_path: Path, doc_id: Optional[str] = None) -> OCRDocument:
        """
        Process a multi-page PDF document into an OCRDocument with word-level confidence.
        Isolates page-level failures so one bad page doesn't abort the entire document.
        """
        import fitz  # PyMuPDF

        document_id = doc_id or str(uuid.uuid4())
        filename = file_path.name
        logger.info(f"Starting OCR extraction for document '{filename}' (ID: {document_id})")

        pages: List[OCRPage] = []
        all_words: List[OCRWord] = []

        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            logger.info(f"Document '{filename}' contains {total_pages} page(s).")

            for page_idx in range(total_pages):
                page_num = page_idx + 1
                try:
                    page = doc[page_idx]
                    
                    # If using Digital engine or if PDF has native text and no OCR engine installed
                    if isinstance(self.engine, DigitalPDFEngine):
                        ocr_page = self.engine.extract_from_pdf_page(page, page_number=page_num)
                    else:
                        # Rasterize page to high-res image (200-300 DPI) for OCR
                        pix = page.get_pixmap(dpi=200)
                        img_bytes = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_bytes))
                        ocr_page = self.engine.extract_from_image(image, page_number=page_num)

                    pages.append(ocr_page)
                    all_words.extend(ocr_page.words)
                    logger.debug(
                        f"Page {page_num}/{total_pages} processed. "
                        f"Words: {len(ocr_page.words)}, Avg Conf: {ocr_page.average_confidence:.2f}"
                    )
                except Exception as page_err:
                    logger.error(f"Error processing page {page_num} of '{filename}': {page_err}")
                    # Create degraded placeholder page with error message
                    err_page = OCRPage(
                        page=page_num,
                        lines=[],
                        words=[],
                        text="",
                        average_confidence=0.0,
                        min_confidence=0.0,
                        error=str(page_err),
                    )
                    pages.append(err_page)

            doc.close()

        except Exception as doc_err:
            logger.error(f"Fatal error opening PDF '{filename}': {doc_err}")
            raise doc_err

        # Compute document-level statistics
        full_text = "\n\n".join(p.text for p in pages if p.text)
        if all_words:
            doc_avg_conf = sum(w.confidence for w in all_words) / len(all_words)
            doc_min_conf = min(w.confidence for w in all_words)
        else:
            doc_avg_conf = 0.0
            doc_min_conf = 0.0

        ocr_document = OCRDocument(
            doc_id=document_id,
            filename=filename,
            total_pages=len(pages),
            pages=pages,
            all_words=all_words,
            full_text=full_text,
            average_confidence=round(doc_avg_conf, 4),
            min_confidence=round(doc_min_conf, 4),
            metadata={
                "engine": type(self.engine).__name__,
                "source_file": str(file_path),
            },
        )

        logger.info(
            f"OCR completed for '{filename}'. Total Pages: {total_pages}, "
            f"Total Words: {len(all_words)}, Avg Conf: {doc_avg_conf:.4f}, Min Conf: {doc_min_conf:.4f}"
        )
        return ocr_document

    def process_image(self, file_path: Path, doc_id: Optional[str] = None) -> OCRDocument:
        """
        Process a single image file (PNG, JPG, TIFF) into an OCRDocument.
        """
        document_id = doc_id or str(uuid.uuid4())
        filename = file_path.name
        image = Image.open(file_path)

        ocr_page = self.engine.extract_from_image(image, page_number=1)
        return OCRDocument(
            doc_id=document_id,
            filename=filename,
            total_pages=1,
            pages=[ocr_page],
            all_words=ocr_page.words,
            full_text=ocr_page.text,
            average_confidence=ocr_page.average_confidence,
            min_confidence=ocr_page.min_confidence,
            metadata={
                "engine": type(self.engine).__name__,
                "source_file": str(file_path),
            },
        )
