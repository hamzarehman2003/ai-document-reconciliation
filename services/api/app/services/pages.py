"""Turn a stored file into what the AI reads: page images plus any PDF text."""

from pathlib import Path

import pymupdf

from app.llm.base import PageImage, PreparedDocument

RENDER_DPI = 150


def prepare_document(path: Path, content_type: str, max_pages: int) -> PreparedDocument:
    """PDF → one PNG per page (up to max_pages) and its text layer.

    Images (PNG/JPEG) are passed through as they are, with no text.
    Scanned PDFs simply have an empty text layer.
    """
    if content_type != "application/pdf":
        return PreparedDocument(images=[PageImage(path.read_bytes(), content_type)])

    with pymupdf.open(path) as pdf:
        pages = [pdf[index] for index in range(min(pdf.page_count, max_pages))]
        images = [
            PageImage(page.get_pixmap(dpi=RENDER_DPI).tobytes("png"), "image/png")
            for page in pages
        ]
        text = "\n\n".join(page.get_text() for page in pages).strip()
    return PreparedDocument(images=images, text=text)
