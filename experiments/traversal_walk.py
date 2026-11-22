"""Variante experimental con os.walk; no sustituye el recorrido de producción."""

import logging
import os
from collections.abc import Collection, Iterator
from pathlib import Path

from utils.text_utils import clean_directory_name, clean_file_name


def _on_walk_error(error: OSError) -> None:
    if not isinstance(error, PermissionError):
        raise error
    logging.error(
        "Permission denied — cannot read directory contents: %s", error.filename
    )


def _walk_visible_entries(
    source_path: Path, ignore_list: Collection[str]
) -> Iterator[tuple[Path, list[str], list[str]]]:
    for root, directories, files in os.walk(
        source_path, topdown=True, followlinks=False, onerror=_on_walk_error
    ):
        parent = Path(root)
        # La modificación in situ impide descender a estos subárboles.
        directories[:] = [
            name for name in directories
            if not name.startswith(".")
            and name not in ignore_list
            and not (parent / name).is_symlink()
        ]
        yield parent, directories, files


def get_name_files_walk(
    source_path: Path, ignore_list: Collection[str] = ()
) -> Iterator[Path]:
    for parent, _, files in _walk_visible_entries(source_path, ignore_list):
        for name in files:
            item = parent / name
            if name.startswith(".") or item.is_symlink():
                continue
            if item.is_file() and clean_file_name(item) != name:
                yield item


def get_name_directories_walk(
    source_path: Path, ignore_list: Collection[str] = ()
) -> Iterator[Path]:
    for parent, directories, _ in _walk_visible_entries(source_path, ignore_list):
        for name in directories:
            item = parent / name
            if clean_directory_name(item) != name:
                yield item
