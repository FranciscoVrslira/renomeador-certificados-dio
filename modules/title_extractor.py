"""Regras conservadoras: somente títulos delimitados por contexto explícito."""
from dataclasses import dataclass
import re

from config import Config
from modules.pdf_reader import TextLine

FLAGS = re.IGNORECASE
START = re.compile(
    r"\b(?:concluiu|conclu[ií]do|finalizou)\s+(?:com\s+(?:sucesso|êxito)\s+)?"
    r"(?:(?:o|a)\s+)?(?:(?:curso|bootcamp|treinamento|m[oó]dulo)\s*(?::\s*|de\s+)?)?",
    FLAGS,
)
LABEL = re.compile(r"\b(?:nome\s+do\s+curso|curso|bootcamp|treinamento)\s*:\s*", FLAGS)
END = re.compile(
    r"(?:[,;]\s*)?(?:\b(?:com\s+)?carga\s+hor[aá]ria\b|"
    r"\bcom\s+dura[çc][ãa]o\b|\bcom\s+\d+(?:[.,]\d+)?\s*horas?\b|"
    r"\b(?:realizado|realizada)\s+(?:em|no\s+per[ií]odo)\b)", FLAGS,
)
FORBIDDEN = re.compile(
    r"\b(?:certificamos|certificado|certifica|concluiu|carga\s+hor[aá]ria|"
    r"autenticidade|autentica[çc][ãa]o|assinatura|inscrito|portador|cpf)\b|"
    r"https?://|www\.|\b\d{2}/\d{2}/\d{4}\b", FLAGS,
)


@dataclass(frozen=True)
class TitleResult:
    title: str | None
    confidence: float
    reason: str


def extract_title(lines: list[TextLine], config: Config, *, ocr: bool = False) -> TitleResult:
    """Rejeita ambiguidade; nunca usa tamanho da fonte ou região isolados."""
    pieces, spans = [], []
    offset = 0
    for line in lines:
        text = re.sub(r"\s+", " ", line.text).strip()
        pieces.append(text)
        spans.append((offset, offset + len(text), line))
        offset += len(text) + 1
    text = " ".join(pieces)
    candidates: dict[str, float] = {}
    for pattern, score in ((START, 0.98), (LABEL, 0.94)):
        for start in pattern.finditer(text):
            end = END.search(text, start.end())
            if not end:
                continue
            raw = text[start.end():end.start()].strip()
            # Strip only paired quotation delimiters, preserving title punctuation.
            if len(raw) > 1 and (raw[0], raw[-1]) in {( '"', '"'), ('“', '”'), ("'", "'")}:
                raw = raw[1:-1].strip()
            if (not 3 <= len(raw) <= config.max_title_chars
                    or not any(c.isalpha() for c in raw) or FORBIDDEN.search(raw)):
                continue
            selected = [line for a, b, line in spans if b > start.end() and a < end.start()]
            if not selected or len(selected) > 6:
                continue
            context = [line for a, b, line in spans if b > start.start() and a < end.end()]
            if max(l.bbox[3] for l in context) - min(l.bbox[1] for l in context) > 0.45:
                continue
            # A distant footer cannot serve as a delimiter across the entire page.
            if max(l.bbox[3] for l in selected) - min(l.bbox[1] for l in selected) > 0.35:
                continue
            if config.title_region:
                x0, y0, x1, y1 = config.title_region
                if not all(x0 <= (l.bbox[0] + l.bbox[2]) / 2 <= x1
                           and y0 <= (l.bbox[1] + l.bbox[3]) / 2 <= y1 for l in selected):
                    continue
            if ocr and min(l.confidence for l in selected) < config.ocr_min_confidence:
                continue
            candidates[raw] = max(score, candidates.get(raw, 0))
    if len(candidates) != 1:
        return TitleResult(None, 0, "Títulos ambíguos" if candidates else "Sem título delimitado confiável")
    title, confidence = next(iter(candidates.items()))
    if confidence < config.min_confidence:
        return TitleResult(None, confidence, "Abaixo de TITLE_MIN_CONFIDENCE")
    return TitleResult(title, confidence, "Contexto de conclusão/curso e carga horária/duração")
