"""Configuração validada; caminhos relativos são ancorados no projeto."""
from dataclasses import dataclass
import math
import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    folder: Path
    log_level: str = "INFO"
    ocr_enabled: bool = True
    ocr_language: str = "por"
    tesseract_path: str = ""
    dry_run: bool = False
    min_confidence: float = 0.90
    ocr_min_confidence: float = 85
    dpi: int = 300
    timeout: int = 45
    title_region: tuple[float, float, float, float] | None = None
    max_title_chars: int = 240
    max_name_units: int = 240


def load_config(root: Path = ROOT) -> Config:
    values = {**dotenv_values(root / ".env", encoding="utf-8-sig"), **os.environ}

    def get(key: str, default: str) -> str:
        return str(values.get(key) or default).strip()

    def boolean(key: str, default: str) -> bool:
        value = get(key, default).lower()
        if value not in {"true", "false"}:
            raise ValueError(f"{key} deve ser true ou false")
        return value == "true"

    def number(key: str, default: str, low: float, high: float) -> float:
        value = float(get(key, default))
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key} deve estar entre {low} e {high}")
        return value

    def path(value: str) -> Path:
        candidate = Path(value).expanduser()
        return (root / candidate).resolve() if not candidate.is_absolute() else candidate

    region = None
    if get("TITLE_REGION", ""):
        region = tuple(float(v) for v in get("TITLE_REGION", "").split(","))
        if (len(region) != 4 or not all(math.isfinite(v) for v in region)
                or not (0 <= region[0] < region[2] <= 1 and 0 <= region[1] < region[3] <= 1)):
            raise ValueError("TITLE_REGION deve ser x0,y0,x1,y1 entre 0 e 1")
    level = get("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise ValueError("LOG_LEVEL inválido")
    language = get("OCR_LANGUAGE", "por")
    if "por" not in language.split("+"):
        raise ValueError("OCR_LANGUAGE deve incluir por; exemplo: por+eng")
    tesseract = get("TESSERACT_PATH", "")
    return Config(
        folder=path(get("PASTA_CERTIFICADOS", "certificados")),
        log_level=level, ocr_enabled=boolean("OCR_ENABLED", "true"),
        ocr_language=language, tesseract_path=str(path(tesseract)) if tesseract else "",
        dry_run=boolean("DRY_RUN", "false"),
        min_confidence=number("TITLE_MIN_CONFIDENCE", "0.90", 0.9, 1),
        ocr_min_confidence=number("OCR_MIN_CONFIDENCE", "85", 0, 100),
        dpi=int(number("OCR_DPI", "300", 150, 600)),
        timeout=int(number("OCR_TIMEOUT", "45", 1, 300)),
        title_region=region,
        max_title_chars=int(number("MAX_TITLE_CHARS", "240", 3, 1000)),
        max_name_units=int(number("MAX_FILENAME_UNITS", "240", 30, 255)),
    )
