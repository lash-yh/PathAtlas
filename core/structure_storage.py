"""Lectura y escritura de instantáneas de directorios en JSON."""

import json
from pathlib import Path

from core.traversal import DirectoryTree


def save_structure_directories(structure_path: Path | None, new_structure: DirectoryTree) -> None:
    structure_data: DirectoryTree = {}

    if structure_path and structure_path.exists():
        with open(structure_path, 'r', encoding='utf-8') as f:
            try:
                structure_data = json.load(f)
            except json.JSONDecodeError:
                return

    structure_data.update(new_structure)

    if structure_path:
        with open(structure_path, 'w', encoding='utf-8') as f:
            json.dump(structure_data, f, indent=4, ensure_ascii=False)
