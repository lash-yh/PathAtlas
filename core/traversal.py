"""Recorridos del sistema de archivos y selección de nombres por limpiar."""

import logging
from collections.abc import Collection, Iterator
from pathlib import Path

from utils.text_utils import clean_directory_name, clean_file_name


type DirectoryTree = dict[str, DirectoryTree | None]


def get_name_files(source_path: Path, ignore_list: Collection[str] = ()) -> Iterator[Path]:
    """Selecciona archivos usando exclusiones ya cargadas por el llamador."""
    try:
        for item in source_path.iterdir():
            if item.is_symlink():
                continue

            if item.is_dir():
                if item.name in ignore_list:
                    continue

                yield from get_name_files(item, ignore_list)

            elif item.is_file():
                if clean_file_name(item) != item.name:
                    yield item
    except PermissionError:
        logging.error("Permission denied — cannot read directory contents: %s", source_path)


def get_name_directories(source_path: Path, ignore_list: Collection[str] = ()) -> Iterator[Path]:
    """Selecciona directorios sin consultar la configuración en disco."""
    try:
        for item in source_path.iterdir():
            if item.is_symlink():
                continue

            if item.is_dir():
                if item.name in ignore_list:
                    continue

                if clean_directory_name(item) != item.name:
                    yield item

                yield from get_name_directories(item, ignore_list)
    except PermissionError:
        logging.error("Permission denied — cannot read directory contents: %s", source_path)



def build_directory_tree(base_path: Path, ignore_list: Collection[str]) -> DirectoryTree:
    tree: DirectoryTree = {}
    try:
        for item in base_path.iterdir():
            if item.is_symlink():
                continue
            if item.name in ignore_list:
                continue

            if item.is_dir():
                tree[item.name] = build_directory_tree(item, ignore_list)

            elif item.is_file():
                tree[item.name] = None

    except PermissionError:
        logging.error("Permission denied — skipping directory tree at: %s", base_path)

    return tree
