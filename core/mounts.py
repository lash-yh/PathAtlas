"""Detección de unidades y puntos de montaje."""

import logging
from pathlib import Path

import psutil


def find_ssd_mount_point(label_ssd: str | None)-> Path | None:
    if not label_ssd:
        raise ValueError("label_ssd is empty")

    for part in psutil.disk_partitions():
        mount_point: str = part.mountpoint.rstrip('/')
        if mount_point.endswith(label_ssd):
            logging.info("SSD found — device: %s | mount point: %s | filesystem: %s",
                        part.device, part.mountpoint, part.fstype)
            return Path(part.mountpoint)
    return None
