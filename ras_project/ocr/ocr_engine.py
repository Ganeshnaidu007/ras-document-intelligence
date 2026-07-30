"""ocr/ocr_engine.py — OCR dispatcher for EasyOCR, PaddleOCR, and Tesseract."""
from utils.logger import get_logger
from utils.device import gpu_available
from utils.timing import timed
from ocr.preprocessing import preprocess_image_bytes
logger = get_logger(__name__)

LANG_MAP = {
    "English":        {"easy": ["en"],         "paddle": "en",  "tess": "eng"},
    "Hindi":          {"easy": ["hi","en"],     "paddle": "hi",  "tess": "hin+eng"},
    "Telugu":         {"easy": ["te","en"],     "paddle": "te",  "tess": "tel+eng"},
    "Mixed Language": {"easy": ["hi","te","en"],"paddle": "en",  "tess": "hin+tel+eng"},
}


class OCREngine:
    def __init__(self, engine: str = "EasyOCR", language: str = "English"):
        self.engine   = engine
        self.language = language
        self._reader  = None
        self._init()

    def ocr_image_bytes(self, img_bytes: bytes) -> str:
        img_bytes = preprocess_image_bytes(img_bytes)
        return {"EasyOCR": self._easy, "PaddleOCR": self._paddle}.get(self.engine, self._tess)(img_bytes)

    def ocr_image_file(self, path: str) -> str:
        return self.ocr_image_bytes(open(path, "rb").read())

    def _init(self):
        codes = LANG_MAP.get(self.language, LANG_MAP["English"])
        try:
            with timed(f"ocr.init.{self.engine}"):
                if self.engine == "EasyOCR":
                    import easyocr
                    self._reader = easyocr.Reader(codes["easy"], gpu=gpu_available(), verbose=False)
                elif self.engine == "PaddleOCR":
                    from paddleocr import PaddleOCR
                    # PaddleOCR auto-detects GPU via the installed paddlepaddle build
                    # (paddlepaddle-gpu vs paddlepaddle) — nothing to force here.
                    self._reader = PaddleOCR(use_angle_cls=True, lang=codes["paddle"], show_log=False)
        except ImportError as e:
            logger.warning(f"OCR import error ({self.engine}): {e}")
        except Exception as e:
            logger.error(f"OCR init error: {e}")

    def _easy(self, img_bytes):
        if not self._reader:
            return ""
        try:
            import cv2, numpy as np
            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            with timed("ocr.read.EasyOCR"):
                return " ".join(self._reader.readtext(img, detail=0))
        except Exception as e:
            logger.error(f"EasyOCR: {e}"); return ""

    def _paddle(self, img_bytes):
        if not self._reader:
            return ""
        try:
            import cv2, numpy as np
            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            with timed("ocr.read.PaddleOCR"):
                results = self._reader.ocr(img, cls=True)
            lines   = []
            if results:
                for grp in results:
                    if grp:
                        for box in grp:
                            if box and len(box) >= 2:
                                lines.append(box[1][0])
            return " ".join(lines)
        except Exception as e:
            logger.error(f"PaddleOCR: {e}"); return ""

    def _tess(self, img_bytes):
        try:
            import pytesseract
            from PIL import Image
            import io
            codes = LANG_MAP.get(self.language, LANG_MAP["English"])
            return pytesseract.image_to_string(Image.open(io.BytesIO(img_bytes)), lang=codes["tess"])
        except Exception as e:
            logger.error(f"Tesseract: {e}"); return ""
