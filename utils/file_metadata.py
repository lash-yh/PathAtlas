"""Consulta de estadísticas de archivos y directorios."""

import datetime
import os
from pathlib import Path

from utils.formatting import format_size, get_change_time


def get_directory_stats(path_directory: Path) -> dict[str, str | int | datetime.datetime]:
    total_size: int = 0
    file_count: int = 0
    last_mod: float = 0.0

    # Iteramos solo sobre archivos para el reporte de peso
    for item in path_directory.rglob('*'):
        if item.is_file():
            stats: os.stat_result = item.stat()
            total_size += stats.st_size
            file_count += 1
            if stats.st_mtime > last_mod:
                last_mod = stats.st_mtime

    return {
        "total_size": format_size(total_size),
        "file_count": file_count,
        "last_modified": get_change_time(last_mod) if last_mod > 0 else "N/A"
    }
