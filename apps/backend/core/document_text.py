"""Shared bounded-document extraction, shipped with the backend worker image."""
import io
import re
import unicodedata


class IngestionError(ValueError):
    """Safe-to-display extraction/ingestion failure, without source URLs."""


def extract_text(data: bytes, kind: str) -> str:
    if kind not in {"txt", "md", "html", "pdf"}:
        raise IngestionError("Chỉ hỗ trợ txt, md, html, pdf.")
    try:
        if kind == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = data.decode("utf-8-sig")
            if kind == "html":
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
                    tag.decompose()
                text = (soup.find("main") or soup.find("article") or soup).get_text("\n")
    except Exception:
        raise IngestionError("Không trích được text; kiểm tra định dạng/UTF-8/PDF mã hóa.") from None
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text or "\x00" in text:
        raise IngestionError("Không có text hợp lệ; PDF scan/ảnh cần OCR trước ingestion.")
    return text
