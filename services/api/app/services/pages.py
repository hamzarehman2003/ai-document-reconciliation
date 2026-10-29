"""Turn a stored file into page images: for the AI, and for the page viewer."""

from pathlib import Path

import pymupdf

from app.llm.base import PageImage, PreparedDocument

RENDER_DPI = 150
VIEWER_DPI = 110


def render_page_png(path: Path, page_number: int, dpi: int = VIEWER_DPI) -> bytes:
    """One PDF page (1, 2, 3...) as a PNG. Raises IndexError if there's no such page."""
    with pymupdf.open(path) as pdf:
        if not 1 <= page_number <= pdf.page_count:
            raise IndexError(f"The document has no page {page_number}.")
        return pdf[page_number - 1].get_pixmap(dpi=dpi).tobytes("png")


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
