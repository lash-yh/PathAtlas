"""Carga y validación de una configuración JSON por ejecución."""

import json
import logging
from pathlib import Path
from typing import TypedDict


class Config(TypedDict):
    mount_point_label: str | None
    ignore: list[str]


def load_config(config_path: Path) -> Config:
    """Lee el JSON una vez; las consultas posteriores usan el resultado en memoria.

    Propaga errores de lectura y genera ValueError si el esquema es inválido.
    Las claves opcionales usan valores predeterminados; se omiten los comentarios
    y otras claves adicionales del JSON.
    """
    with config_path.open('r', encoding='utf-8') as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Config must be a JSON object")
    ignore = data.get("ignore", [])
    if not isinstance(ignore, list) or not all(isinstance(name, str) for name in ignore):
        raise ValueError("Config 'ignore' must be a list of strings")
    label = data.get("mount_point_label")
    if label is not None and (not isinstance(label, str) or not label.strip()):
        raise ValueError("Config 'mount_point_label' must be a non-empty string or null")

    logging.info("Config loaded successfully from: %s", config_path)
    return {"mount_point_label": label, "ignore": ignore}
