"""Carga de la configuración JSON de la aplicación."""

import json
import logging
from pathlib import Path

_CONFIG_CACHE: dict[str, dict] = {}

def get_cached_config_value(config_path: Path, key: str)-> str | list[str] | None:
    path_str: str = str(config_path)

    if path_str not in _CONFIG_CACHE:
        if not config_path.exists():
            _CONFIG_CACHE[path_str] = {}
            return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _CONFIG_CACHE[path_str] = json.load(f)
            logging.info("Config loaded successfully from: %s", config_path)

    except json.JSONDecodeError:
        logging.error("Invalid JSON — could not parse config file: %s", config_path)
        _CONFIG_CACHE[path_str] = {}
    except PermissionError:
        logging.error("Permission denied — cannot read config file: %s", config_path)
        _CONFIG_CACHE[path_str] = {}

    return _CONFIG_CACHE[path_str].get(key)
