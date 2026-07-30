"""ocr/hindi_ocr.py — Hindi (Devanagari) OCR helpers."""
import re, unicodedata
from utils.logger import get_logger
from utils.device import gpu_available
from utils.timing import timed
logger = get_logger(__name__)


def ocr_hindi_image(img_bytes: bytes) -> str:
    try:
        import easyocr, cv2, numpy as np
        with timed("ocr.hindi.easyocr_init"):
            reader = easyocr.Reader(["hi","en"], gpu=gpu_available(), verbose=False)
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        with timed("ocr.hindi.easyocr_read"):
            results = reader.readtext(img, detail=0)
        return post_process_hindi(" ".join(results))
    except ImportError:
        logger.warning("EasyOCR not installed — Hindi OCR unavailable.")
        return ""
    except Exception as e:
        logger.error(f"Hindi OCR: {e}"); return ""


def post_process_hindi(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\u0900-\u097F\u0020-\u007E\n]", "", text)
    return re.sub(r" {2,}", " ", text).strip()
