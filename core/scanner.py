"""Coordinación del escaneo y guardado de instantáneas."""

from collections.abc import Collection
from pathlib import Path
from core.structure_storage import save_structure_directories
from core.traversal import DirectoryTree, build_directory_tree
from utils.text_utils import clean_directory_name


def scanner_structure_directories(
    base_path: Path, ignore_list: Collection[str] = (),
    structure_path: Path | None = None,
) -> None:
    if not base_path.exists() or not base_path.is_dir():
        raise FileNotFoundError(f"La ruta no existe o no es un directorio: {base_path}")

    final_structure: DirectoryTree = {
            clean_directory_name(base_path): build_directory_tree(base_path, ignore_list)
    }

    if structure_path:
        save_structure_directories(structure_path, final_structure)
