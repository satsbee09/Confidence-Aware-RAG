"""
Document Degradation Module for Confidence-Aware RAG Evaluation.

Generates realistic OCR degradation artifacts on Indian Legal & Government documents:
- Gaussian defocus / blur
- Salt-and-pepper noise / scanner speckles
- Photocopier contrast degradation / ink fading
- JPEG compression artifacts
- Skew / rotational misalignment
"""

import os
import io
import random
from pathlib import Path
from typing import Literal, Tuple, Dict, Any, List
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import fitz  # PyMuPDF
import numpy as np
from loguru import logger

DegradationLevel = Literal["clean", "low", "medium", "high"]


class DocumentDegrader:
    """
    Applies controlled physical and optical degradation to PDF pages and images
    to simulate real-world scanned Indian government orders, RTI replies, and court circulars.
    """

    @staticmethod
    def add_gaussian_blur(image: Image.Image, radius: float = 1.0) -> Image.Image:
        """Simulates camera defocus and lens softness."""
        if radius <= 0:
            return image
        return image.filter(ImageFilter.GaussianBlur(radius=radius))

    @staticmethod
    def add_salt_and_pepper_noise(image: Image.Image, amount: float = 0.02) -> Image.Image:
        """Simulates scanner dust, toner speckles, and paper grain."""
        if amount <= 0:
            return image

        img_arr = np.array(image)
        if len(img_arr.shape) == 2:  # Grayscale
            h, w = img_arr.shape
            c = 1
        else:
            h, w, c = img_arr.shape

        num_noise = int(amount * h * w)

        # Salt (white dots)
        for _ in range(num_noise // 2):
            y = random.randint(0, h - 1)
            x = random.randint(0, w - 1)
            if c == 1:
                img_arr[y, x] = 255
            else:
                img_arr[y, x] = [255, 255, 255]

        # Pepper (black dots)
        for _ in range(num_noise // 2):
            y = random.randint(0, h - 1)
            x = random.randint(0, w - 1)
            if c == 1:
                img_arr[y, x] = random.randint(0, 50)
            else:
                img_arr[y, x] = [random.randint(0, 50)] * 3

        return Image.fromarray(img_arr)

    @staticmethod
    def add_contrast_and_fading(image: Image.Image, contrast: float = 0.8, brightness: float = 1.1) -> Image.Image:
        """Simulates faded thermal receipts or multi-generation photocopier washout."""
        enhancer = ImageEnhance.Contrast(image)
        img_contrast = enhancer.enhance(contrast)
        enhancer_b = ImageEnhance.Brightness(img_contrast)
        return enhancer_b.enhance(brightness)

    @staticmethod
    def add_jpeg_compression(image: Image.Image, quality: int = 30) -> Image.Image:
        """Simulates lossy government web portal compression."""
        buf = io.BytesIO()
        rgb_img = image.convert("RGB")
        rgb_img.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf)

    @staticmethod
    def add_skew(image: Image.Image, angle: float = 1.5) -> Image.Image:
        """Simulates misaligned scanner feed."""
        if abs(angle) < 0.01:
            return image
        return image.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor="white")

    @classmethod
    def degrade_image(
        cls,
        image: Image.Image,
        level: DegradationLevel = "medium",
        seed: int = 42,
    ) -> Image.Image:
        """
        Applies a calibrated combination of distortions matching the target degradation level.
        """
        random.seed(seed)
        np.random.seed(seed)

        if level == "clean":
            return image

        img = image.convert("RGB")

        if level == "low":
            # Target OCR Confidence: ~85% - 92%
            img = cls.add_skew(img, angle=random.uniform(-0.8, 0.8))
            img = cls.add_gaussian_blur(img, radius=0.6)
            img = cls.add_salt_and_pepper_noise(img, amount=0.008)
            img = cls.add_jpeg_compression(img, quality=55)

        elif level == "medium":
            # Target OCR Confidence: ~70% - 80%
            img = cls.add_skew(img, angle=random.uniform(-1.5, 1.5))
            img = cls.add_contrast_and_fading(img, contrast=0.75, brightness=1.12)
            img = cls.add_gaussian_blur(img, radius=1.2)
            img = cls.add_salt_and_pepper_noise(img, amount=0.025)
            img = cls.add_jpeg_compression(img, quality=30)

        elif level == "high":
            # Target OCR Confidence: ~45% - 60% (Severely noisy)
            img = cls.add_skew(img, angle=random.uniform(-2.5, 2.5))
            img = cls.add_contrast_and_fading(img, contrast=0.6, brightness=1.25)
            img = cls.add_gaussian_blur(img, radius=1.8)
            img = cls.add_salt_and_pepper_noise(img, amount=0.05)
            img = cls.add_jpeg_compression(img, quality=18)

        return img

    @classmethod
    def corrupt_text_for_ocr(cls, text: str, level: DegradationLevel = "medium", seed: int = 42) -> str:
        """
        Simulates realistic character recognition errors produced by OCR engines on degraded scans.
        E.g. S <-> 5, O <-> 0, I <-> 1, B <-> 8, l <-> 1, rn <-> m, cl <-> d.
        """
        if level == "clean":
            return text

        random.seed(seed)
        chars = list(text)
        corruption_prob = 0.06 if level == "low" else (0.18 if level == "medium" else 0.35)

        substitutions = {
            "S": "5", "s": "5",
            "O": "0", "o": "0",
            "I": "1", "l": "1",
            "B": "8",
            "Z": "2", "z": "2",
            "E": "3",
            "A": "4",
            "m": "rn",
            "d": "cl",
        }

        for i in range(len(chars)):
            c = chars[i]
            if c in substitutions and random.random() < corruption_prob:
                chars[i] = substitutions[c]
            elif level in ["medium", "high"] and random.random() < (corruption_prob * 0.2):
                if c.isalnum():
                    chars[i] = random.choice(["~", "|", "^", "'"])

        return "".join(chars)

    @classmethod
    def degrade_pdf_to_pdf(
        cls,
        input_pdf_path: Path,
        output_pdf_path: Path,
        level: DegradationLevel = "medium",
        dpi: int = 150,
    ) -> Path:
        """
        Renders each page of a source PDF to high-res raster image, applies degradation,
        embeds realistic OCR noise text layer, and saves as a new scanned PDF.
        """
        src_doc = fitz.open(str(input_pdf_path))
        dst_doc = fitz.open()

        for page_idx in range(len(src_doc)):
            page = src_doc[page_idx]
            original_text = page.get_text("text")

            # 1. Rasterize visual image
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            degraded_img = cls.degrade_image(img, level=level, seed=42 + page_idx)

            img_byte_arr = io.BytesIO()
            degraded_img.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)
            img_bytes = img_byte_arr.getvalue()

            # 2. Insert image page
            new_page = dst_doc.new_page(width=page.rect.width, height=page.rect.height)
            rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
            new_page.insert_image(rect, stream=img_bytes)

            # 3. Embed degraded text layer matching OCR quality
            degraded_text = cls.corrupt_text_for_ocr(original_text, level=level, seed=42 + page_idx)
            new_page.insert_text((50, 70), degraded_text, fontsize=11, fontname="helv", render_mode=3)

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        dst_doc.save(str(output_pdf_path))
        dst_doc.close()
        src_doc.close()

        logger.info(f"Generated degraded PDF [{level.upper()}] at '{output_pdf_path}'")
        return output_pdf_path



def create_sample_legal_documents(output_dir: Path) -> List[Dict[str, Any]]:
    """
    Creates a set of standard Indian legal / RTI sample documents with ground truth factual data.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_info = []

    # Document 1: Delhi High Court Writ Petition Order
    doc1 = fitz.open()
    p1 = doc1.new_page(width=595, height=842)
    text1 = (
        "IN THE HIGH COURT OF DELHI AT NEW DELHI\n"
        "W.P.(C) NO. 4812/2024 & CM APPL. 19842/2024\n\n"
        "IN THE MATTER OF:\n"
        "Surender Sharma & Ors.                                ...Petitioners\n"
        "                    Versus\n"
        "Union of India & Anr.                                ...Respondents\n\n"
        "CORAM:\n"
        "HON'BLE MR. JUSTICE RAJESH CHATURVEDI\n\n"
        "ORDER DATED: 14.08.2024\n\n"
        "1. The present writ petition has been filed under Article 226 challenging the demolition notice.\n"
        "2. The petitioner claims title through registered Sale Deed dated 12.03.1998 for property bearing\n"
        "   Plot No. 44, Khasra No. 312, Village Rangpuri, New Delhi.\n"
        "3. Having heard learned counsel for both sides, this Court finds no merit in the petition.\n"
        "4. The writ petition is accordingly DISMISSED with costs of Rs. 25,000/- to be deposited by the\n"
        "   petitioner with the Delhi State Legal Services Authority within 30 days.\n"
        "5. The statutory appeal period is limited to 45 days under Section 420 of the Municipal Act.\n"
    )
    p1.insert_text((50, 70), text1, fontsize=11, fontname="helv")
    pdf1_path = output_dir / "delhi_high_court_order_2024.pdf"
    doc1.save(str(pdf1_path))
    doc1.close()

    docs_info.append({
        "doc_id": "doc_delhi_hc_2024",
        "title": "Delhi High Court Writ Petition Order",
        "clean_pdf": pdf1_path,
        "facts": {
            "case_number": "W.P.(C) NO. 4812/2024",
            "order_date": "14.08.2024",
            "petitioner": "Surender Sharma & Ors.",
            "decision": "DISMISSED",
            "cost_amount": "Rs. 25,000/-",
            "statutory_section": "Section 420",
            "appeal_period": "45 days",
        }
    })

    # Document 2: RTI Central Information Commission Reply
    doc2 = fitz.open()
    p2 = doc2.new_page(width=595, height=842)
    text2 = (
        "CENTRAL INFORMATION COMMISSION\n"
        "Baba Gangnath Marg, Munirka, New Delhi - 110067\n"
        "DECISION FILE NO: CIC/MORTH/A/2025/001429\n\n"
        "Appellant: Shri Arvind Mehta\n"
        "Public Authority: Ministry of Road Transport & Highways\n"
        "Date of Hearing: 22.01.2025\n"
        "Date of Decision: 28.01.2025\n\n"
        "FACTS OF THE CASE:\n"
        "1. The Appellant sought details of toll collection concessionaire agreement for NH-48.\n"
        "2. The CPIO wrongfully denied information under Section 8(1)(d) without substantiating commercial confidence.\n"
        "3. Commission directs CPIO to provide complete agreement within 15 working days.\n"
        "4. A show-cause notice is issued to CPIO under Section 20(1) imposing penalty of Rs. 15,000/- for\n"
        "   malafide delay exceeding 60 days.\n"
    )
    p2.insert_text((50, 70), text2, fontsize=11, fontname="helv")
    pdf2_path = output_dir / "rti_cic_decision_2025.pdf"
    doc2.save(str(pdf2_path))
    doc2.close()

    docs_info.append({
        "doc_id": "doc_rti_cic_2025",
        "title": "Central Information Commission RTI Decision",
        "clean_pdf": pdf2_path,
        "facts": {
            "file_number": "CIC/MORTH/A/2025/001429",
            "decision_date": "28.01.2025",
            "appellant": "Shri Arvind Mehta",
            "penalty_amount": "Rs. 15,000/-",
            "penalty_section": "Section 20(1)",
            "compliance_timeline": "15 working days",
        }
    })

    logger.info(f"Created {len(docs_info)} synthetic sample legal documents in '{output_dir}'.")
    return docs_info


if __name__ == "__main__":
    clean_dir = Path("./data/clean")
    degraded_dir = Path("./data/degraded")
    
    docs = create_sample_legal_documents(clean_dir)
    degrader = DocumentDegrader()

    for doc in docs:
        src = doc["clean_pdf"]
        for level in ["low", "medium", "high"]:
            out_path = degraded_dir / f"{src.stem}_{level}.pdf"
            degrader.degrade_pdf_to_pdf(src, out_path, level=level)
