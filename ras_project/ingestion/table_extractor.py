"""ingestion/table_extractor.py — Extract tables from PDFs as structured JSON."""
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
logger = get_logger(__name__)


class TableExtractor:
    def extract_from_pdf(self, file_path: str, page_number: Optional[int]=None) -> List[Dict[str,Any]]:
        results = self._pdfplumber(file_path, page_number)
        if not results:
            results = self._camelot(file_path, page_number)
        return results

    def table_to_json(self, raw: List[List[str]]) -> List[Dict[str,str]]:
        if not raw or len(raw) < 2:
            return []
        headers = [str(h).strip() for h in raw[0]]
        return [{headers[i] if i<len(headers) else f"col_{i}": str(cell).strip()
                 for i, cell in enumerate(row)} for row in raw[1:]]

    def _pdfplumber(self, file_path, page_number):
        results = []
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages = ([pdf.pages[page_number-1]] if page_number and page_number<=len(pdf.pages)
                         else pdf.pages)
                for i, page in enumerate(pages):
                    pnum = page_number if page_number else i+1
                    for tbl in (page.extract_tables() or []):
                        results.append({"page":pnum,"data":tbl,"json":self.table_to_json(tbl)})
        except ImportError:
            logger.warning("pdfplumber not installed.")
        except Exception as e:
            logger.error(f"Table extract error: {e}")
        return results

    def _camelot(self, file_path, page_number):
        results = []
        try:
            import camelot
            tables = camelot.read_pdf(file_path, pages=str(page_number) if page_number else "all", flavor="stream")
            for t in tables:
                df  = t.df
                raw = [df.columns.tolist()] + df.values.tolist()
                results.append({"page": page_number or 0,"data":raw,"json":self.table_to_json(raw)})
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"Camelot error: {e}")
        return results
