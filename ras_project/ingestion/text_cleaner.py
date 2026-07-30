"""ingestion/text_cleaner.py — Clean and normalise extracted page text."""
import re, unicodedata
from typing import Dict, Any


class TextCleaner:
    def clean(self, page: Dict[str, Any]) -> Dict[str, Any]:
        t = page.get("text","")
        t = unicodedata.normalize("NFC", t)
        t = t.replace("\ufffd"," ").replace("\x00","")
        t = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]","",t)
        t = t.replace("\r\n","\n").replace("\r","\n")
        t = re.sub(r"[ \t]+"," ",t)
        t = re.sub(r"\n{3,}","\n\n",t)
        page["text"] = t.strip()
        return page
