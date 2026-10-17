"""Nomes Windows, colisões e renomeação sem sobrescrita."""
import os
from pathlib import Path
import re

RESERVED = re.compile(r"^(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.I)


def units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def truncate(value: str, limit: int) -> str:
    return value.encode("utf-16-le")[:limit * 2].decode("utf-16-le", errors="ignore").rstrip(" .")


def normalize_title(title: str) -> str:
    """Preserva Unicode e pontuação legal; substitui caracteres proibidos por _."""
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).rstrip(" .")
    if not value or value in {".", ".."}:
        raise ValueError("Título não produz nome de arquivo válido")
    if RESERVED.match(value):
        value = "_" + value
    return value


def filename(title: str, folder: Path, max_units: int, index: int = 1) -> str:
    # Keep compatibility with Windows applications without long-path support.
    budget = min(max_units, 259 - units(str(folder.resolve())) - 1)
    suffix = "" if index == 1 else f" ({index})"
    available = budget - units(suffix + ".pdf")
    if available < 1:
        raise ValueError("Caminho muito longo: mova a pasta para um caminho menor")
    base = truncate(normalize_title(title), available)
    if not base:
        raise ValueError("Sem espaço para um nome válido")
    if RESERVED.match(base):
        base = truncate("_" + base, available)
    return base + suffix + ".pdf"


def already_processed(path: Path, title: str, max_units: int) -> bool:
    if path.name.casefold() == filename(title, path.parent, max_units).casefold():
        return True
    match = re.search(r" \(([2-9]|[1-9]\d+)\)\.pdf$", path.name, re.I)
    return bool(match and path.name.casefold() == filename(
        title, path.parent, max_units, int(match[1])).casefold())


class Renamer:
    def __init__(self, folder: Path, max_units: int = 240, dry_run: bool = False):
        self.folder, self.max_units, self.dry_run = folder, max_units, dry_run
        self.reserved: set[str] = set()

    def rename(self, source: Path, title: str) -> tuple[str, Path]:
        """No Windows, os.rename falha atomicamente se o destino existir."""
        if source.is_symlink() or not source.is_file():
            raise ValueError("Origem inválida ou link simbólico")
        if already_processed(source, title, self.max_units):
            return "JA_PROCESSADO", source
        if os.name != "nt" and not self.dry_run:
            raise OSError("Renomeação real suportada apenas no Windows (sem sobrescrita)")
        index = 1
        while True:
            occupied = {p.name.casefold() for p in self.folder.iterdir()} | self.reserved
            target = self.folder / filename(title, self.folder, self.max_units, index)
            if target.name.casefold() in occupied:
                index += 1
                continue
            if self.dry_run:
                self.reserved.add(target.name.casefold())
                return "SIMULADO", target
            try:
                os.rename(source, target)
                return "RENOMEADO", target
            except FileExistsError:
                index += 1
