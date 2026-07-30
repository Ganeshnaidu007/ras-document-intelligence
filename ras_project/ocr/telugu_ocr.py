"""ocr/telugu_ocr.py — Telugu script OCR helpers."""
import re, unicodedata
from utils.logger import get_logger
from utils.device import gpu_available
from utils.timing import timed
logger = get_logger(__name__)
TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")


def ocr_telugu_image(img_bytes: bytes) -> str:
    try:
        import easyocr, cv2, numpy as np
        with timed("ocr.telugu.easyocr_init"):
            reader = easyocr.Reader(["te","en"], gpu=gpu_available(), verbose=False)
        img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        with timed("ocr.telugu.easyocr_read"):
            results = reader.readtext(img, detail=0)
        return post_process_telugu(" ".join(results))
    except ImportError:
        return _paddle_telugu(img_bytes)
    except Exception as e:
        logger.error(f"Telugu OCR: {e}"); return ""


def _paddle_telugu(img_bytes):
    try:
        from paddleocr import PaddleOCR
        import cv2, numpy as np
        ocr     = PaddleOCR(use_angle_cls=True, lang="te", show_log=False)
        img     = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        results = ocr.ocr(img, cls=True)
        lines   = []
        if results:
            for grp in results:
                if grp:
                    for box in grp:
                        if box and len(box) >= 2:
                            lines.append(box[1][0])
        return post_process_telugu(" ".join(lines))
    except Exception as e:
        logger.error(f"PaddleOCR Telugu: {e}"); return ""


def post_process_telugu(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\u0C00-\u0C7F\u0020-\u007E\n]","",text)
    return re.sub(r" {2,}"," ",text).strip()


def contains_telugu(text: str) -> bool:
    return bool(TELUGU_RE.search(text))
