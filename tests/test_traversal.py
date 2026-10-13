from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from core.traversal import (
    build_directory_tree,
    get_name_directories,
    get_name_files,
)


def test_get_name_files(mocker: MockerFixture) -> None:
    source_path = MagicMock(spec=Path)
    source_path.is_symlink.return_value = False

    # Configurar mock de iterdir para retornar una estructura mixta
    file1 = MagicMock(spec=Path)
    file1.is_symlink.return_value = False
    file1.is_dir.return_value = False
    file1.is_file.return_value = True
    file1.name = "Archivo Uno.TXT"
    file1.stem = "Archivo Uno"
    file1.suffix = ".TXT"

    dir1 = MagicMock(spec=Path)
    dir1.is_symlink.return_value = False
    dir1.is_dir.return_value = True
    dir1.is_file.return_value = False
    dir1.name = ".git"

    dir2 = MagicMock(spec=Path)
    dir2.is_symlink.return_value = False
    dir2.is_dir.return_value = True
    dir2.is_file.return_value = False
    dir2.name = "src"

    file2 = MagicMock(spec=Path)
    file2.is_symlink.return_value = False
    file2.is_dir.return_value = False
    file2.is_file.return_value = True
    file2.name = "Archivo Dos.TXT"
    file2.stem = "Archivo Dos"
    file2.suffix = ".TXT"

    # iterdir for dir2
    dir2.iterdir.return_value = [file2]

    # iterdir for source_path
    source_path.iterdir.return_value = [file1, dir1, dir2]

    # Mocking config para ignorar ".git"

    result = list(get_name_files(source_path, [".git"]))

    assert file1 in result
    assert file2 in result
    assert len(result) == 2

def test_get_name_directories(mocker: MockerFixture) -> None:
    source_path = MagicMock(spec=Path)
    source_path.is_symlink.return_value = False

    dir1 = MagicMock(spec=Path)
    dir1.is_symlink.return_value = False
    dir1.is_dir.return_value = True
    dir1.name = "node_modules"

    dir2 = MagicMock(spec=Path)
    dir2.is_symlink.return_value = False
    dir2.is_dir.return_value = True
    dir2.name = "01. Src"

    dir3 = MagicMock(spec=Path)
    dir3.is_symlink.return_value = False
    dir3.is_dir.return_value = True
    dir3.name = "Mis Componentes"
    dir3.iterdir.return_value = []

    dir2.iterdir.return_value = [dir3]
    source_path.iterdir.return_value = [dir1, dir2]


    result = list(get_name_directories(source_path, ["node_modules"]))

    assert dir2 in result
    assert dir3 in result
    assert dir1 not in result
    assert len(result) == 2

def test_build_directory_tree(mocker: MockerFixture) -> None:
    base_path = MagicMock(spec=Path)
    base_path.is_symlink.return_value = False

    # Ignorar dir1
    dir1 = MagicMock(spec=Path)
    dir1.is_symlink.return_value = False
    dir1.name = "node_modules"

    # Procesar dir2 y un archivo
    dir2 = MagicMock(spec=Path)
    dir2.is_symlink.return_value = False
    dir2.name = "src"
    dir2.is_dir.return_value = True
    dir2.is_file.return_value = False

    file1 = MagicMock(spec=Path)
    file1.is_symlink.return_value = False
    file1.name = "main.py"
    file1.is_dir.return_value = False
    file1.is_file.return_value = True

    dir2.iterdir.return_value = [file1]

    # Archivo en base_path
    file2 = MagicMock(spec=Path)
    file2.is_symlink.return_value = False
    file2.name = "README.md"
    file2.is_dir.return_value = False
    file2.is_file.return_value = True

    base_path.iterdir.return_value = [dir1, dir2, file2]

    ignore_list = ["node_modules"]

    tree = build_directory_tree(base_path, ignore_list)

    expected = {
        "src": {"main.py": None},
        "README.md": None
    }

    assert tree == expected

def test_build_directory_tree_permission_error(mocker: MockerFixture) -> None:
    base_path = MagicMock(spec=Path)
    base_path.is_symlink.return_value = False

    dir1 = MagicMock(spec=Path)
    dir1.is_symlink.return_value = False
    dir1.name = "restricted_folder"
    dir1.is_dir.side_effect = PermissionError("Access denied")

    base_path.iterdir.return_value = [dir1]

    tree = build_directory_tree(base_path, [])

    # El recorrido omite el directorio que no puede consultar.
    assert tree == {}



def test_traversal_skips_clean_names_and_ignored_subtrees(tmp_path: Path) -> None:
    ignored = tmp_path / "Ignorada"
    ignored.mkdir()
    (ignored / "Archivo Ignorado.TXT").touch()
    (tmp_path / "limpio.txt").touch()
    (tmp_path / "Mi Archivo.TXT").touch()
    clean_directory = tmp_path / "carpeta-limpia"
    clean_directory.mkdir()
    dirty_directory = clean_directory / "Mi Carpeta"
    dirty_directory.mkdir()
    nested_file = dirty_directory / "Otro Archivo.TXT"
    nested_file.touch()

    files = set(get_name_files(tmp_path, ["Ignorada"]))
    directories = set(get_name_directories(tmp_path, ["Ignorada"]))

    assert files == {tmp_path / "Mi Archivo.TXT", nested_file}
    assert directories == {dirty_directory}


def test_traversal_uses_loaded_exclusions_without_file_reads(tmp_path: Path, mocker: MockerFixture) -> None:
    from core.config_loader import load_config
    path = tmp_path / "config.json"
    path.write_text('{"ignore": ["Ignorada"]}')
    selected = tmp_path / "selected"
    selected.mkdir()
    (selected / "Mi Archivo.TXT").touch()
    ignored = selected / "Ignorada"
    ignored.mkdir()
    (ignored / "No Cambiar.TXT").touch()
    config = load_config(path)
    path.unlink()
    opened = mocker.patch.object(Path, "open", side_effect=AssertionError("Unexpected file read"))
    assert list(get_name_files(selected, config["ignore"])) == [selected / "Mi Archivo.TXT"]
    assert list(get_name_directories(selected, config["ignore"])) == []
    assert build_directory_tree(selected, config["ignore"]) == {"Mi Archivo.TXT": None}
    opened.assert_not_called()
