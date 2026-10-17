"""Diagnóstico não destrutivo usado pelo instalador."""
import sys
from config import load_config
from modules.ocr_service import OCRService


def main() -> int:
    if sys.version_info[:2] != (3, 14):
        print("Necessário Python 3.14.")
        return 2
    try:
        config = load_config()
        OCRService(config).check()
    except Exception as exc:
        print(f"Dependências Python disponíveis; OCR ainda não configurado: {exc}")
        print("Instale Tesseract manualmente conforme README.md, incluindo português (por).")
        print("Defina TESSERACT_PATH no .env. Nenhuma instalação administrativa foi executada.")
        return 1
    print("Python 3.14, dependências, Tesseract e português disponíveis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
