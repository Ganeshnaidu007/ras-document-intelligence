"""ingestion/image_extractor.py — Extract images from PDF pages."""
import os
from typing import List, Dict, Any
from utils.logger import get_logger
logger = get_logger(__name__)


class ImageExtractor:
    def __init__(self, output_dir: str = "temp/images"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def extract_from_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        images = []
        try:
            import fitz
            doc       = fitz.open(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            for pnum, page in enumerate(doc, 1):
                for idx, img_info in enumerate(page.get_images(full=True)):
                    base_img = doc.extract_image(img_info[0])
                    ext      = base_img["ext"]
                    fname    = f"{base_name}_p{pnum}_img{idx}.{ext}"
                    fpath    = os.path.join(self.output_dir, fname)
                    with open(fpath, "wb") as f:
                        f.write(base_img["image"])
                    images.append({"page":pnum,"index":idx,"path":fpath,
                                   "width":base_img.get("width",0),
                                   "height":base_img.get("height",0),"ext":ext})
            doc.close()
        except ImportError:
            logger.warning("PyMuPDF not installed.")
        except Exception as e:
            logger.error(f"Image extract error: {e}")
        return images
