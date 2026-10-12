"""Resolución de colisiones, orden y ejecución segura de renombrados."""

import logging
from collections.abc import Iterable
from itertools import count
from pathlib import Path

from utils.text_utils import clean_directory_name, clean_file_name


def _unique_path(base_path: Path)-> Path | None:
    """Genera una ruta única añadiendo un sufijo numérico para evitar colisiones.

    Args:
        base_path (Path): La ruta deseada original.

    Returns:
        Path | None: La ruta única si se encuentra, o None si no hay colisión (es decir, el path base ya era válido).
    """
    if not base_path.exists():
        return base_path
    stem, suffix = base_path.stem, base_path.suffix
    for n in count(1):
        candidate: Path = base_path.parent / f"{stem}({n}){suffix}"
        if not candidate.exists():
            return candidate
    return None


def resolve_name_path(base_path: Path) -> Path | None:
    """Resuelve y limpia el nombre para un archivo o directorio.

    Detecta si la ruta proporcionada (`base_path`) corresponde a un directorio o a un
    archivo. Dependiendo del tipo, aplica la limpieza correspondiente (`clean_directory_name`
    o `clean_file_name`). Posteriormente, maneja la resolución de colisiones: si el nuevo
    nombre limpio ya existe en el directorio destino, delega en la función `_unique_path`
    para adjuntar un sufijo numérico incremental (por ejemplo, `archivo(1).txt`) garantizando
    que la ruta final sea única.

    Args:
        base_path (Path): La ruta original a resolver y renombrar.

    Returns:
        Path | None: La ruta resuelta con el nombre limpio y único, o None si hay error.

    Raises:
        ValueError: Si el nombre resultante después de la limpieza está vacío.
    """
    new_name = ""

    if base_path.is_dir():
        new_name: str = clean_directory_name(base_path)
    elif base_path.is_file():
        new_name: str = clean_file_name(base_path)

    if not new_name:
        raise ValueError(f"new name is empty: {base_path}")

    final_name: Path = base_path.parent / new_name

    if  final_name.name == base_path.name:
        return final_name

    if final_name.exists() and final_name.samefile(base_path):
        return final_name

    return _unique_path(final_name)


def organize_for_depth_and_alphabetical(list_items: Iterable[Path]) -> list[Path]:
    return sorted(list(list_items), key=lambda part: (-len(part.parts), part))


def rename_files_and_directories(list_items: Iterable[Path], is_dry_run: bool) -> None:
    for item in list_items:
        try:
            new_path_file: Path | None = resolve_name_path(item)
            if new_path_file and new_path_file != item:
                if is_dry_run:
                    logging.info("[DRY RUN] Would rename: %s -> %s", item.name, new_path_file.name)
                else:
                    try:
                        logging.info("[RENAME] %s -> %s", item.name, new_path_file.name)
                        item.rename(new_path_file)
                    except PermissionError:
                        logging.error("Permission denied — could not rename: %s -> %s", item.name, new_path_file.name)

        except PermissionError:
            logging.error("Permission denied — cannot access item: %s", item)
        except OSError as e:
            logging.error("OS error while processing %s: %s", item, e)
