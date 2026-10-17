"""Leitura somente da primeira página, sem salvar ou alterar PDFs."""
from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class TextLine:
    text: str
    bbox: tuple[float, float, float, float]
    confidence: float = 100.0


def open_pdf(path: Path):
    document = pymupdf.open(path)
    if document.needs_pass:
        document.close()
        raise ValueError("PDF protegido por senha")
    if not document.is_pdf or document.page_count == 0:
        document.close()
        raise ValueError("Documento inválido ou sem páginas")
    return document


def read_lines(page) -> list[TextLine]:
    """Retorna linhas com coordenadas relativas à página não rotacionada."""
    width, height = page.cropbox.width, page.cropbox.height
    result = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                x0, y0, x1, y1 = line["bbox"]
                result.append(TextLine(text, (x0 / width, y0 / height, x1 / width, y1 / height)))
    return sorted(result, key=lambda line: (line.bbox[1], line.bbox[0]))
