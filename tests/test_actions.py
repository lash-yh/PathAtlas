import pytest
from pathlib import Path
from pytest_mock import MockerFixture

from core.actions import (
    _unique_path,
    resolve_name_path,
    organize_for_depth_and_alphabetical,
    rename_files_and_directories,
)


def test_unique_path_no_collision(mocker: MockerFixture) -> None:
    # Si la ruta no existe, debe retornar la original
    path = Path("/tmp/documento.txt")
    mocker.patch.object(Path, "exists", return_value=False)

    assert _unique_path(path) == path

def test_unique_path_with_collision(mocker: MockerFixture) -> None:
    # Simular colisiones: documento.txt existe, pero documento(1).txt no
    path = Path("/tmp/documento.txt")

    def mock_exists(self: Path) -> bool:
        if self.name == "documento.txt":
            return True
        return False

    mocker.patch.object(Path, "exists", autospec=True, side_effect=mock_exists)

    result = _unique_path(path)
    assert result == Path("/tmp/documento(1).txt")

def test_resolve_name_path_file_no_collision(mocker: MockerFixture) -> None:
    path = Path("/tmp/Documento Importante!.txt")

    mocker.patch.object(Path, "is_file", return_value=True)
    mocker.patch.object(Path, "is_dir", return_value=False)
    mocker.patch.object(Path, "exists", return_value=False)

    result = resolve_name_path(path)
    assert result == Path("/tmp/documento-importante.txt")

def test_resolve_name_path_directory(mocker: MockerFixture) -> None:
    path = Path("/tmp/01. Mi Carpeta")

    mocker.patch.object(Path, "is_file", return_value=False)
    mocker.patch.object(Path, "is_dir", return_value=True)
    mocker.patch.object(Path, "exists", return_value=False)

    result = resolve_name_path(path)
    assert result == Path("/tmp/mi-carpeta")

def test_resolve_name_path_empty_error(mocker: MockerFixture) -> None:
    path = Path("/tmp/---")
    mocker.patch.object(Path, "is_file", return_value=True)
    mocker.patch.object(Path, "is_dir", return_value=False)

    with pytest.raises(ValueError, match="new name is empty"):
        resolve_name_path(path)

def test_organize_for_depth_and_alphabetical() -> None:
    paths = [
        Path("/a/b/c/d.txt"),
        Path("/a/b.txt"),
        Path("/a/b/c.txt"),
        Path("/z/y.txt"),
        Path("/a/c.txt")
    ]

    # Validar que los elementos se ordenen primero por profundidad y luego alfabéticamente
    result = organize_for_depth_and_alphabetical(paths)

    expected = [
        Path("/a/b/c/d.txt"),  # len parts = 5
        Path("/a/b/c.txt"),    # len parts = 4
        Path("/a/b.txt"),      # len parts = 3, 'b' < 'c' < 'z'
        Path("/a/c.txt"),      # len parts = 3, 'b' < 'c' < 'z'
        Path("/z/y.txt")       # len parts = 3, 'b' < 'c' < 'z'
    ]

    assert result == expected



def test_rename_dry_run_keeps_original_file(tmp_path: Path) -> None:
    original = tmp_path / "Mi Archivo.TXT"
    original.write_text("contenido")

    rename_files_and_directories([original], is_dry_run=True)

    assert original.read_text() == "contenido"
    assert not (tmp_path / "mi-archivo.txt").exists()


def test_rename_collision_preserves_existing_file(tmp_path: Path) -> None:
    original = tmp_path / "Mi Archivo.TXT"
    original.write_text("nuevo")
    existing = tmp_path / "mi-archivo.txt"
    existing.write_text("anterior")

    rename_files_and_directories([original], is_dry_run=False)

    assert existing.read_text() == "anterior"
    assert (tmp_path / "mi-archivo(1).txt").read_text() == "nuevo"
    assert not original.exists()


def test_resolve_name_path_same_file_skips_collision(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    original = tmp_path / "Mi Archivo.TXT"
    original.write_text("contenido")
    target = tmp_path / "mi-archivo.txt"
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch.object(Path, "samefile", return_value=True)

    assert resolve_name_path(original) == target


def test_rename_files_then_deepest_directories(tmp_path: Path) -> None:
    from core.traversal import get_name_directories, get_name_files

    child = tmp_path / "01. Mi Carpeta" / "02. Sub Carpeta"
    child.mkdir(parents=True)
    (child / "Mi Archivo.TXT").write_text("contenido")
    files = organize_for_depth_and_alphabetical(
        get_name_files(tmp_path, None, "ignore", [])
    )
    directories = organize_for_depth_and_alphabetical(
        get_name_directories(tmp_path, None, "ignore", [])
    )

    rename_files_and_directories(files, is_dry_run=False)
    rename_files_and_directories(directories, is_dry_run=False)

    result = tmp_path / "mi-carpeta" / "sub-carpeta" / "mi-archivo.txt"
    assert result.read_text() == "contenido"
