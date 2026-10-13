"""Formato de tamaños y fechas para los reportes."""

import datetime


def get_change_time(last_change: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(last_change)

def format_size(size_bytes: int) -> str:
    unit: str
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"
