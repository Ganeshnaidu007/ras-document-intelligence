"""ocr/preprocessing.py — Image preprocessing for OCR quality (deskew, denoise, threshold)."""
from utils.logger import get_logger
logger = get_logger(__name__)


def preprocess_image_bytes(img_bytes: bytes) -> bytes:
    try:
        import cv2, numpy as np
        nparr = np.frombuffer(img_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return img_bytes
        gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        thresh   = cv2.adaptiveThreshold(denoised, 255,
                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        deskewed = _deskew(thresh)
        _, buf   = cv2.imencode(".png", deskewed)
        return buf.tobytes()
    except ImportError:
        return img_bytes
    except Exception as e:
        logger.warning(f"Preprocessing failed: {e}")
        return img_bytes


def _deskew(image):
    try:
        import cv2, numpy as np
        coords = np.column_stack(np.where(image > 0))
        angle  = cv2.minAreaRect(coords)[-1]
        angle  = -(90 + angle) if angle < -45 else -angle
        if abs(angle) < 0.5:
            return image
        h, w   = image.shape
        M      = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return image
