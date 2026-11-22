import logging
import os
from collections.abc import Callable, Collection, Iterator
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from core.traversal import get_name_directories, get_name_files
from experiments.traversal_walk import (
    get_name_directories_walk,
    get_name_files_walk,
)


type Selector = Callable[[Path, Collection[str]], Iterator[Path]]


@pytest.fixture(params=["actual", "os.walk"])
def selectors(request: pytest.FixtureRequest) -> tuple[Selector, Selector]:
    if request.param == "actual":
        return get_name_files, get_name_directories
    return get_name_files_walk, get_name_directories_walk


def test_unfiltered_os_walk_includes_hidden_entries(tmp_path: Path) -> None:
    hidden_file = tmp_path / ".Archivo Oculto.TXT"
    hidden_file.touch()
    hidden_directory = tmp_path / ".Carpeta Oculta"
    hidden_directory.mkdir()
    nested_file = hidden_directory / "Archivo Interior.TXT"
    nested_file.touch()

    entries = list(os.walk(tmp_path))
    files = {Path(root) / name for root, _, names in entries for name in names}
    directories = {
        Path(root) / name for root, names, _ in entries for name in names
    }

    assert files == {hidden_file, nested_file}
    assert directories == {hidden_directory}


@pytest.mark.parametrize("relative_parent", [".", "contenedor"])
def test_selectors_exclude_hidden_entries_and_subtrees(
    tmp_path: Path, selectors: tuple[Selector, Selector], relative_parent: str
) -> None:
    parent = tmp_path / relative_parent
    parent.mkdir(exist_ok=True)
    (parent / ".Archivo Oculto.TXT").touch()
    (parent / ".env").touch()
    hidden = parent / ".Carpeta Oculta"
    hidden.mkdir()
    (hidden / "Archivo Interior.TXT").touch()
    (hidden / "Subcarpeta Interior").mkdir()
    visible_directory = parent / "Carpeta Visible"
    visible_directory.mkdir()
    (visible_directory / ".Otro Archivo.TXT").touch()
    nested_hidden = visible_directory / ".Otra Carpeta"
    nested_hidden.mkdir()
    (nested_hidden / "Otro Archivo Interior.TXT").touch()
    (nested_hidden / "Otra Subcarpeta Interior").mkdir()
    visible_file = visible_directory / "Archivo Visible.TXT"
    visible_file.touch()
    nested_directory = visible_directory / "Subcarpeta Visible"
    nested_directory.mkdir()
    files, directories = selectors

    assert set(files(tmp_path, ())) == {visible_file}
    assert set(directories(tmp_path, ())) == {visible_directory, nested_directory}


def test_selectors_preserve_exclusions_and_clean_names(
    tmp_path: Path, selectors: tuple[Selector, Selector]
) -> None:
    ignored = tmp_path / "Ignorada"
    ignored.mkdir()
    (ignored / "Archivo Ignorado.TXT").touch()
    (ignored / "Subcarpeta Ignorada").mkdir()
    (tmp_path / "limpio.txt").touch()
    clean_directory = tmp_path / "carpeta-limpia"
    clean_directory.mkdir()
    dirty_file = clean_directory / "Mi Archivo.TXT"
    dirty_file.touch()
    dirty_directory = clean_directory / "01. Mi Carpeta"
    dirty_directory.mkdir()
    # La lista de exclusiones actual se aplica únicamente a directorios.
    file_matching_exclusion = tmp_path / "Archivo Excluido.TXT"
    file_matching_exclusion.touch()
    files, directories = selectors
    exclusions = {"Ignorada", file_matching_exclusion.name}

    assert set(files(tmp_path, exclusions)) == {dirty_file, file_matching_exclusion}
    assert set(directories(tmp_path, exclusions)) == {dirty_directory}


def test_selectors_handle_empty_directory(
    tmp_path: Path, selectors: tuple[Selector, Selector]
) -> None:
    files, directories = selectors

    assert list(files(tmp_path, ())) == []
    assert list(directories(tmp_path, ())) == []


@pytest.mark.parametrize("kind", ["file", "directory", "broken", "cycle"])
def test_selectors_skip_symlinks(
    tmp_path: Path, selectors: tuple[Selector, Selector], kind: str
) -> None:
    selected = tmp_path / "selected"
    selected.mkdir()
    target = tmp_path / "target"
    if kind == "file":
        target.touch()
    elif kind == "directory":
        target.mkdir()
        (target / "Archivo Externo.TXT").touch()
        (target / "Carpeta Externa").mkdir()
    elif kind == "cycle":
        target = selected
    try:
        (selected / "Mi Enlace").symlink_to(
            target, target_is_directory=kind in {"directory", "cycle"}
        )
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"El entorno no permite crear enlaces simbólicos: {error}")
    files, directories = selectors

    assert list(files(selected, ())) == []
    assert list(directories(selected, ())) == []


def test_selectors_continue_after_permission_error(
    tmp_path: Path,
    selectors: tuple[Selector, Selector],
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    restricted = tmp_path / "restricted"
    restricted.mkdir()
    (restricted / "Archivo Inaccesible.TXT").touch()
    visible_file = tmp_path / "Archivo Visible.TXT"
    visible_file.touch()
    original_scandir = os.scandir

    def scandir(path: str | Path) -> AbstractContextManager[Iterator[os.DirEntry[str]]]:
        if Path(path) == restricted:
            raise PermissionError(13, "Access denied", str(path))
        return original_scandir(path)

    mocker.patch("os.scandir", side_effect=scandir)
    files, directories = selectors

    with caplog.at_level(logging.ERROR):
        assert set(files(tmp_path, ())) == {visible_file}
        assert list(directories(tmp_path, ())) == []
    assert "Permission denied" in caplog.text
    assert str(restricted) in caplog.text
