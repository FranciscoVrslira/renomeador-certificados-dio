"""Entrada da aplicação. Execute com Python 3.14 no Windows."""
import argparse
from collections import Counter
import logging
from pathlib import Path
import sys

from config import Config, ROOT, load_config
from modules.file_renamer import Renamer
from modules.logger_config import configure_logger
from modules.ocr_service import OCRService
from modules.pdf_reader import open_pdf, read_lines
from modules.title_extractor import extract_title


def process_file(path: Path, config: Config, renamer: Renamer,
                 ocr: OCRService, logger: logging.Logger) -> str:
    method, attempted, title, final = "NATIVA", False, None, path.name
    status, reason = "ERRO_LEITURA", ""
    try:
        if path.is_symlink():
            raise ValueError("Link simbólico não permitido")
        with open_pdf(path) as document:
            page = document[0]
            try:
                result = extract_title(read_lines(page), config)
            except Exception as exc:
                logger.debug("Extração nativa falhou", exc_info=True)
                from modules.title_extractor import TitleResult
                result = TitleResult(None, 0, f"Falha na extração nativa: {exc}")
            if not result.title and config.ocr_enabled:
                attempted, method = True, "OCR"
                try:
                    result = ocr.extract(page, logger)
                except Exception as exc:
                    logger.debug("OCR falhou", exc_info=True)
                    reason = f"{result.reason}; falha OCR: {exc}"
            title = result.title
            reason = reason or result.reason
            logger.debug("Extração: confiança=%s motivo=%s", result.confidence, reason)
        # Close PDF handles before attempting a Windows rename.
        if title is None:
            status = "TITULO_NAO_IDENTIFICADO"
        else:
            status = "ERRO_RENOMEACAO"
            status, destination = renamer.rename(path, title)
            final = destination.name
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        logger.debug("Falha individual em %s", path, exc_info=True)
    level = logging.INFO if status in {"RENOMEADO", "JA_PROCESSADO", "SIMULADO"} else (
        logging.WARNING if status == "TITULO_NAO_IDENTIFICADO" else logging.ERROR)
    logger.log(level, "status=%s | original=%r | titulo=%r | metodo=%s | ocr_tentado=%s | final=%r | motivo=%s",
               status, path.name, title, method, attempted, final, reason)
    return status


def run_batch(config: Config, logger: logging.Logger) -> Counter:
    if not config.folder.is_dir():
        raise NotADirectoryError(f"Pasta inexistente ou inválida: {config.folder}")
    paths = sorted((p for p in config.folder.iterdir() if p.suffix.lower() == ".pdf"
                    and not p.is_dir()), key=lambda p: p.name.casefold())
    renamer, ocr = Renamer(config.folder, config.max_name_units, config.dry_run), OCRService(config)
    counts = Counter()
    for i, path in enumerate(paths, 1):
        logger.info("Processando %d/%d: %s", i, len(paths), path.name)
        counts[process_file(path, config, renamer, ocr, logger)] += 1
    failed = sum(n for status, n in counts.items() if status not in {"RENOMEADO", "JA_PROCESSADO", "SIMULADO"})
    logger.info("\n========== RESUMO ==========\nTotal de PDFs: %d\nRenomeados: %d\nJá processados: %d\nSimulados: %d\nFalhas: %d\n============================",
                len(paths), counts["RENOMEADO"], counts["JA_PROCESSADO"], counts["SIMULADO"], failed)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Simular sem renomear")
    args = parser.parse_args()
    try:
        config = load_config()
        if args.dry_run:
            from dataclasses import replace
            config = replace(config, dry_run=True)
        logger = configure_logger(ROOT / "logs", config.log_level)
    except Exception as exc:
        print(f"Falha na configuração/log: {exc}", file=sys.stderr)
        return 2
    try:
        counts = run_batch(config, logger)
        return int(any(n and s not in {"RENOMEADO", "JA_PROCESSADO", "SIMULADO"} for s, n in counts.items()))
    except Exception:
        logger.exception("Não foi possível iniciar/concluir o lote")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
