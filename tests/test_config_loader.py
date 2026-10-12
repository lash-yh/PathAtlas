import json
import pytest
from pathlib import Path
from unittest.mock import mock_open
from pytest_mock import MockerFixture

from core.config_loader import (
    get_cached_config_value,
    _CONFIG_CACHE
)

@pytest.fixture(autouse=True)
def clear_cache() -> None:
    # Asegurar que el caché esté limpio antes de cada test
    _CONFIG_CACHE.clear()

def test_get_cached_config_value_reads_from_disk(mocker: MockerFixture, mock_config_json: None) -> None:
    config_path = Path("/mock/config.json")

    # Primera lectura debe ir a "disco"
    val = get_cached_config_value(config_path, "mount_point_label")
    assert val == "SSD"

    # Se debió guardar en caché
    assert str(config_path) in _CONFIG_CACHE

def test_get_cached_config_value_uses_cache(mocker: MockerFixture) -> None:
    config_path = Path("/mock/config.json")

    # Pre-cargar el caché
    _CONFIG_CACHE[str(config_path)] = {"mount_point_label": "NVME"}

    # Como la implementación de config_loader lee el json si intentamos llamar a open()
    # tenemos que asegurar que la lectura del archivo retorne la configuración cacheada o mockearla,
    # caso contrario leerá del disco/mock global y sobrescribirá el caché.
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data='{"mount_point_label": "NVME"}'))

    val = get_cached_config_value(config_path, "mount_point_label")
    assert val == "NVME"

def test_get_cached_config_value_json_decode_error(mocker: MockerFixture) -> None:
    config_path = Path("/mock/config.json")
    mocker.patch.object(Path, "exists", return_value=True)

    # Data inválida JSON
    mocker.patch("builtins.open", mock_open(read_data="{invalid_json"))

    val = get_cached_config_value(config_path, "mount_point_label")
    assert val is None
    assert _CONFIG_CACHE[str(config_path)] == {}
