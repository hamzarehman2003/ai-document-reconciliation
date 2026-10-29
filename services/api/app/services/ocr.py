"""Optical character recognition with RapidOCR (runs on the CPU, fully offline).

The OCR models ship inside the rapidocr package, so nothing is downloaded.
"""

from functools import lru_cache

import numpy as np
from rapidocr import RapidOCR

# One word: (text, (x0, y0, x1, y1) in pixels, confidence 0-1)
OcrWord = tuple[str, tuple[float, float, float, float], float]


@lru_cache(maxsize=1)
def _engine() -> RapidOCR:
    """Load the OCR models once and reuse them."""
    return RapidOCR(params={"Global.log_level": "warning"})


def read_words(image: np.ndarray) -> list[list[OcrWord]]:
    """Read an image: a list of text lines, each a list of words with boxes."""
    result = _engine()(image, return_word_box=True)
    if not result.txts:
        return []

    lines: list[list[OcrWord]] = []
    for line_text, line_box, line_score, words in zip(
        result.txts, result.boxes, result.scores, result.word_results, strict=False
    ):
        line_words = [
            (text, _bounds(points), float(score))
            for text, score, points in words
            if text.strip() and points is not None
        ]
        # If no word boxes came back, fall back to one box for the whole line.
        lines.append(line_words or [(line_text, _bounds(line_box), float(line_score))])
    return lines


def _bounds(
    points: list[list[float]] | np.ndarray,
) -> tuple[float, float, float, float]:
    """Four corner points → (x0, y0, x1, y1)."""
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)
