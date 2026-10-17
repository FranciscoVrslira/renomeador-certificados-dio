"""OCR local com coordenadas, confiança por palavra e timeout."""
from collections import defaultdict
import logging
import subprocess

from PIL import Image, ImageOps
import pymupdf
import pytesseract

from config import Config
from modules.pdf_reader import TextLine
from modules.title_extractor import TitleResult, extract_title


class OCRService:
    def __init__(self, config: Config):
        self.config = config
        self.checked = False
        self.error: str | None = None
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_path or "tesseract"

    def check(self) -> None:
        """Verifica executável e idiomas uma vez, sem instalar software."""
        if not self.checked:
            self.checked = True
            try:
                result = subprocess.run(
                    [pytesseract.pytesseract.tesseract_cmd, "--list-langs"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=self.config.timeout, check=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                available = set((result.stdout + "\n" + result.stderr).splitlines())
                missing = set(self.config.ocr_language.split("+")) - available
                if missing:
                    raise RuntimeError(f"Idiomas OCR indisponíveis: {', '.join(sorted(missing))}")
            except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                self.error = f"Tesseract ausente/mal configurado: {exc}"
        if self.error:
            raise RuntimeError(self.error)

    def lines(self, image: Image.Image, region: tuple, psm: int) -> list[TextLine]:
        data = pytesseract.image_to_data(
            image, lang=self.config.ocr_language, config=f"--psm {psm}",
            output_type=pytesseract.Output.DICT, timeout=self.config.timeout,
        )
        grouped = defaultdict(list)
        for i, text in enumerate(data["text"]):
            if text.strip():
                key = tuple(data[k][i] for k in ("block_num", "par_num", "line_num"))
                grouped[key].append(i)
        x0, y0, x1, y1 = region
        result = []
        for indices in grouped.values():
            left = min(data["left"][i] for i in indices)
            top = min(data["top"][i] for i in indices)
            right = max(data["left"][i] + data["width"][i] for i in indices)
            bottom = max(data["top"][i] + data["height"][i] for i in indices)
            result.append(TextLine(
                " ".join(data["text"][i] for i in indices),
                (x0 + left / image.width * (x1 - x0), y0 + top / image.height * (y1 - y0),
                 x0 + right / image.width * (x1 - x0), y0 + bottom / image.height * (y1 - y0)),
                min(float(data["conf"][i]) for i in indices),
            ))
        return sorted(result, key=lambda line: (line.bbox[1], line.bbox[0]))

    def extract(self, page, logger: logging.Logger) -> TitleResult:
        self.check()
        # Match native coordinates: render the unrotated cropbox.
        page.set_rotation(0)
        rect = page.rect
        pixels = rect.width * rect.height * (self.config.dpi / 72) ** 2
        if pixels > 40_000_000:
            raise ValueError("Página excede limite de 40 milhões de pixels; reduza OCR_DPI")
        regions = []
        if self.config.title_region:
            # Include surrounding context; an isolated heading is never sufficient.
            a, b, c, d = self.config.title_region
            regions.append((max(0, a - .1), max(0, b - .15), min(1, c + .1), min(1, d + .15)))
        regions.append((0, 0, 1, 1))
        last = TitleResult(None, 0, "OCR sem título confiável")
        for region in regions:
            a, b, c, d = region
            clip = pymupdf.Rect(a * rect.width, b * rect.height, c * rect.width, d * rect.height)
            pix = page.get_pixmap(dpi=self.config.dpi, clip=clip, colorspace=pymupdf.csRGB, alpha=False)
            with Image.frombytes("RGB", (pix.width, pix.height), pix.samples) as image:
                for preprocess in (False, True):
                    candidate = ImageOps.autocontrast(ImageOps.grayscale(image)) if preprocess else image
                    try:
                        lines = self.lines(candidate, region, 6 if region != (0, 0, 1, 1) else 3)
                    finally:
                        if candidate is not image:
                            candidate.close()
                    last = extract_title(lines, self.config, ocr=True)
                    logger.debug("OCR região=%s preprocessamento=%s resultado=%s", region, preprocess, last)
                    if last.title or last.reason == "Títulos ambíguos":
                        return last
        return last
