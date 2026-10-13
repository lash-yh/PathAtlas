import unicodedata as udd
import re
import sys
from pathlib import Path


_INVALID_CHARACTERS = frozenset('<>:"/\\|?*')
if sys.platform.startswith('linux'):
    _INVALID_CHARACTERS -= frozenset('?*')


def clean_name(name: str) -> str:
    """Normaliza tildes, mayúsculas y espacios conservando signos compatibles.

    Conserva símbolos como +, #, !, %, paréntesis y puntos. Los caracteres
    reservados <>:"/\\| y los de control se sustituyen por espacios.
    En Linux también se conservan ? y *; en otros sistemas se filtran.
    """
    normalized = udd.normalize('NFKD', name)
    without_accents = "".join(c for c in normalized if udd.category(c) != 'Mn')
    cleaned = "".join(
        " " if c in _INVALID_CHARACTERS or udd.category(c).startswith('C') else c
        for c in without_accents
    )
    cleaned = re.sub(r'copy[\s_-]+of[\s_-]*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\s_-]+', '-', cleaned.lower()).strip('-')
    return cleaned.rstrip('.')


def clean_file_name(path_file: Path) -> str:
    """Limpia el nombre y la extensión; devuelve vacío si falta un nombre válido."""
    name = clean_name(path_file.stem)
    if not name:
        return ""
    return f"{name}{clean_name(path_file.suffix)}"


def clean_directory_name(path_dir: Path) -> str:
    """Limpia el nombre eliminando los prefijos numéricos iniciales."""
    title = re.sub(r'^(?:\d+[\s.\-]+)+', '', path_dir.name).strip()
    return clean_name(title)
