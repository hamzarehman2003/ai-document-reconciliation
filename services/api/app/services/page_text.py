"""Every word on every page, with its position on the page.

Digital PDFs already contain their words and positions, so we read them
directly (instant and exact). Scanned pages and photos have no text inside,
so they are read with OCR.
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

from app.services.ocr import read_words

PDF_TEXT = "pdf_text"
OCR = "ocr"
MIN_TEXT_CHARS = 10  # fewer characters than this → treat the page as a scan
OCR_DPI = 200


@dataclass(frozen=True)
class Word:
    """A word and its box, as fractions (0-1) of the page width and height."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float | None = None  # OCR only


@dataclass(frozen=True)
class TextLine:
    page: int  # 1, 2, 3...
    words: list[Word]
    source: str  # PDF_TEXT or OCR


def read_page_lines(path: Path, content_type: str, max_pages: int) -> list[TextLine]:
    """All text lines of a document, top to bottom, page by page."""
    if content_type != "application/pdf":
        with Image.open(path) as image:
            return ocr_lines(np.array(image.convert("RGB")), page=1)

    lines: list[TextLine] = []
    with pymupdf.open(path) as pdf:
        for index in range(min(pdf.page_count, max_pages)):
            page = pdf[index]
            words = page.get_text("words")
            if sum(len(word[4]) for word in words) >= MIN_TEXT_CHARS:
                lines += _pdf_text_lines(page, words, index + 1)
            else:
                pixmap = page.get_pixmap(dpi=OCR_DPI)
                image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                    pixmap.height, pixmap.width, pixmap.n
                )
                lines += ocr_lines(image, page=index + 1)
    return lines


def ocr_lines(image: np.ndarray, page: int) -> list[TextLine]:
    """Read an image with OCR; boxes become fractions of the image size."""
    height, width = image.shape[:2]
    return [
        TextLine(
            page=page,
            source=OCR,
            words=[
                Word(text, x0 / width, y0 / height, x1 / width, y1 / height, score)
                for text, (x0, y0, x1, y1), score in line
            ],
        )
        for line in read_words(image)
    ]


def _pdf_text_lines(
    page: pymupdf.Page, words: list[tuple], page_number: int
) -> list[TextLine]:
    """Group PyMuPDF's words into lines, keeping the reading order."""
    width, height = page.rect.width, page.rect.height
    grouped: dict[tuple[int, int], list[Word]] = defaultdict(list)
    for x0, y0, x1, y1, text, block, line, _ in words:
        grouped[(block, line)].append(
            Word(text, x0 / width, y0 / height, x1 / width, y1 / height)
        )
    return [
        TextLine(page=page_number, words=line_words, source=PDF_TEXT)
        for line_words in grouped.values()
    ]
