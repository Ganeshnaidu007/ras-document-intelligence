"""ingestion/pdf_parser.py — Table-aware PDF parser with deduplication support."""
import os, hashlib
from typing import List, Dict, Any
from utils.logger import get_logger
logger = get_logger(__name__)


def file_hash(file_path: str) -> str:
    """SHA-256 of file — used for deduplication."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()[:16]


def _table_to_markdown(table: List[List]) -> str:
    """Convert a pdfplumber table (list of rows) to markdown table string."""
    if not table or not table[0]:
        return ""
    rows = [[str(cell or "").strip() for cell in row] for row in table]
    # Header row
    header = "| " + " | ".join(rows[0]) + " |"
    sep    = "| " + " | ".join(["---"] * len(rows[0])) + " |"
    body   = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(filter(None, [header, sep, body]))


class PDFParser:
    def __init__(self, ocr_enabled: bool = True, ocr_engine: str = "EasyOCR"):
        self.ocr_enabled = ocr_enabled
        self.ocr_engine  = ocr_engine
        self._ocr = None

    def parse(self, file_path: str) -> Dict[str, Any]:
        logger.info(f"Parsing PDF: {file_path}")
        pages, metadata = [], {}
        doc_hash = file_hash(file_path)
        try:
            import fitz
            doc = fitz.open(file_path)
            metadata = {k: doc.metadata.get(k, "") for k in ("title","author","subject")}
            metadata["page_count"] = len(doc)
            metadata["file_hash"]  = doc_hash

            # Use pdfplumber for table extraction on all pages at once (faster)
            table_map = self._extract_all_tables(file_path)

            for pnum, page in enumerate(doc, 1):
                text       = page.get_text("text").strip()
                is_scanned = len(text) < 50
                if is_scanned and self.ocr_enabled:
                    text = self._ocr_page(page, file_path, pnum)

                # ── Table-aware: inject markdown tables into text ──────────────
                raw_tables  = table_map.get(pnum, [])
                md_tables   = [_table_to_markdown(t) for t in raw_tables if t]
                md_tables   = [t for t in md_tables if t.strip()]
                if md_tables:
                    table_block = "\n\n".join(f"[TABLE]\n{t}\n[/TABLE]" for t in md_tables)
                    text = text + "\n\n" + table_block if text else table_block

                pages.append({
                    "page_number": pnum,
                    "text":        text,
                    "tables":      md_tables,   # already markdown
                    "source":      os.path.basename(file_path),
                    "is_scanned":  is_scanned,
                })
            doc.close()
        except ImportError:
            logger.warning("PyMuPDF not installed, using pdfplumber.")
            pages = self._pdfplumber_parse(file_path, doc_hash)
        except Exception as e:
            logger.error(f"PDF parse error: {e}")
            pages = [{"page_number":1,"text":"","tables":[],
                      "source":os.path.basename(file_path),"is_scanned":False}]

        return {"source": file_path, "metadata": metadata,
                "pages": pages, "file_hash": doc_hash}

    def _extract_all_tables(self, file_path: str) -> Dict[int, List]:
        """Extract all tables from all pages at once using pdfplumber."""
        table_map = {}
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    if tables:
                        table_map[i] = tables
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        return table_map

    def _ocr_page(self, page, file_path, page_num):
        from ocr.ocr_engine import OCREngine
        if self._ocr is None:
            self._ocr = OCREngine(engine=self.ocr_engine)
        try:
            import fitz
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            return self._ocr.ocr_image_bytes(pix.tobytes("png"))
        except Exception as e:
            logger.error(f"OCR page {page_num}: {e}")
            return ""

    def _pdfplumber_parse(self, file_path: str, doc_hash: str = "") -> List[Dict]:
        pages = []
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    text   = (page.extract_text() or "").strip()
                    tables = page.extract_tables() or []
                    md_tables = [_table_to_markdown(t) for t in tables if t]
                    md_tables = [t for t in md_tables if t.strip()]
                    if md_tables:
                        text += "\n\n" + "\n\n".join(
                            f"[TABLE]\n{t}\n[/TABLE]" for t in md_tables)
                    pages.append({"page_number":i,"text":text,"tables":md_tables,
                                  "source":os.path.basename(file_path),
                                  "is_scanned":len(text)<50})
        except Exception as e:
            logger.error(f"pdfplumber error: {e}")
        return pages