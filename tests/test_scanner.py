import pytest
from pathlib import Path
from unittest.mock import MagicMock
from pytest_mock import MockerFixture

from core.scanner import scanner_structure_directories

def test_scanner_structure_directories_not_exists(mocker: MockerFixture) -> None:
    base_path = MagicMock(spec=Path)
    base_path.exists.return_value = False

    with pytest.raises(FileNotFoundError, match="La ruta no existe o no es un directorio"):
        scanner_structure_directories(base_path)

def test_scanner_structure_directories_not_dir(mocker: MockerFixture) -> None:
    base_path = MagicMock(spec=Path)
    base_path.exists.return_value = True
    base_path.is_dir.return_value = False

    with pytest.raises(FileNotFoundError, match="La ruta no existe o no es un directorio"):
        scanner_structure_directories(base_path)

def test_scanner_structure_directories_success(mocker: MockerFixture) -> None:
    base_path = MagicMock(spec=Path)
    base_path.exists.return_value = True
    base_path.is_dir.return_value = True
    base_path.name = "01. Mi Proyecto"

    structure_path = Path("/mock/structure.json")

    mock_build = mocker.patch("core.scanner.build_directory_tree", return_value={"src": {}})
    mock_save = mocker.patch("core.scanner.save_structure_directories")

    scanner_structure_directories(base_path, [".git"], structure_path)

    # Se debió llamar a build_directory_tree con base_path y la lista ignore_dir
    mock_build.assert_called_once_with(base_path, [".git"])

    # Se debió llamar a save_structure_directories
    expected_structure = {
        "mi-proyecto": {"src": {}}
    }
    mock_save.assert_called_once_with(structure_path, expected_structure)

def test_scanner_structure_directories_no_config(mocker: MockerFixture) -> None:
    base_path = MagicMock(spec=Path)
    base_path.exists.return_value = True
    base_path.is_dir.return_value = True
    base_path.name = "Proyecto"

    mock_build = mocker.patch("core.scanner.build_directory_tree", return_value={"src": {}})
    mock_save = mocker.patch("core.scanner.save_structure_directories")

    # Llama sin exclusiones ni destino de guardado
    scanner_structure_directories(base_path)

    # Se debió llamar a build_directory_tree sin exclusiones
    mock_build.assert_called_once_with(base_path, ())

    # No se debió llamar a guardar
    mock_save.assert_not_called()


def test_scanner_saves_using_loaded_config_after_config_file_is_deleted(tmp_path: Path) -> None:
    import json
    from core.config_loader import load_config
    config_path = tmp_path / "config.json"
    config_path.write_text('{"ignore": ["Ignorada"]}')
    selected = tmp_path / "Mi Proyecto"
    selected.mkdir()
    (selected / "file.txt").touch()
    (selected / "Ignorada").mkdir()
    config = load_config(config_path)
    config_path.unlink()
    snapshot = tmp_path / "snapshot.json"
    scanner_structure_directories(selected, config["ignore"], snapshot)
    assert json.loads(snapshot.read_text()) == {"mi-proyecto": {"file.txt": None}}
