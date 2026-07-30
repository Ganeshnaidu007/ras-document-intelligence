"""utils/pdf_highlight.py — Render one PDF page as an image with the chunk
text that was actually used to answer a question highlighted on it.

Backs the "View in PDF" button next to each source citation in chat mode.
Requires PyMuPDF (fitz), which the project already depends on for parsing.
"""
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def render_highlighted_page(pdf_path: str, page_number: int, search_text: str,
                            zoom: float = 1.6) -> Optional[bytes]:
    """Returns a PNG image (as bytes) of the given page with search_text
    highlighted, or None if the page/text can't be found. page_number is
    1-indexed (matches what's stored in chunk metadata elsewhere)."""
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF not installed — can't render highlighted pages.")
        return None

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.warning(f"Couldn't open {pdf_path}: {e}")
        return None

    try:
        idx = max(0, min((page_number or 1) - 1, len(doc) - 1))
        page = doc[idx]

        # PDF text search wants a contiguous, whitespace-normalized string —
        # chunk text often has line breaks that don't match the PDF's own
        # layout, so search a shortened, cleaned prefix rather than the
        # whole chunk (which would rarely find an exact match).
        snippet = " ".join((search_text or "").split())[:180]
        rects = page.search_for(snippet) if snippet else []
        if not rects and len(snippet) > 60:
            rects = page.search_for(snippet[:60])
        if not rects and len(snippet) > 25:
            rects = page.search_for(snippet[:25])

        for r in rects:
            page.add_highlight_annot(r)

        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")
    except Exception as e:
        logger.warning(f"Highlight render failed for {pdf_path} p{page_number}: {e}")
        return None
    finally:
        doc.close()
