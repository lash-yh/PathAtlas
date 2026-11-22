from pathlib import Path

import pytest

from core.actions import rename_files_and_directories, resolve_name_path
from core.traversal import build_directory_tree, get_name_directories, get_name_files


@pytest.mark.parametrize("dry_run", [True, False])
def test_external_directory_link_is_not_traversed(tmp_path: Path, dry_run: bool) -> None:
    selected = tmp_path / "selected"
    selected.mkdir()
    outside = tmp_path / "outside"
    folder = outside / "Mi Carpeta"
    folder.mkdir(parents=True)
    original = folder / "Mi Archivo.TXT"
    original.write_text("outside")
    link = selected / "Enlace Externo"
    link.symlink_to(outside, target_is_directory=True)
    assert list(get_name_files(selected, [])) == []
    assert list(get_name_directories(selected, [])) == []
    assert build_directory_tree(selected, []) == {}
    rename_files_and_directories([link], dry_run)
    assert link.is_symlink()
    assert original.read_text() == "outside"


@pytest.mark.parametrize("kind", ["file", "directory", "broken"])
def test_source_symlinks_are_skipped(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "target"
    if kind == "file":
        target.write_text("content")
    elif kind == "directory":
        target.mkdir()
    link = tmp_path / "Mi Enlace.TXT"
    link.symlink_to(target, target_is_directory=kind == "directory")
    assert resolve_name_path(link) is None
    rename_files_and_directories([link], False)
    assert link.is_symlink()
    assert link.readlink() == target
    assert link not in list(get_name_files(tmp_path, []))
    assert link not in list(get_name_directories(tmp_path, []))
    assert link.name not in build_directory_tree(tmp_path, [])


def test_directory_link_cycle_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "Loop").symlink_to(tmp_path, target_is_directory=True)
    assert list(get_name_files(tmp_path, [])) == []
    assert list(get_name_directories(tmp_path, [])) == []
    assert build_directory_tree(tmp_path, []) == {}


@pytest.mark.parametrize("dry_run", [True, False])
def test_broken_collision_links_are_preserved(tmp_path: Path, dry_run: bool) -> None:
    original = tmp_path / "Hola.TXT"
    original.write_text("content")
    links = [tmp_path / "hola.txt", tmp_path / "hola(1).txt"]
    target = tmp_path / "missing"
    for link in links:
        link.symlink_to(target)
    expected = tmp_path / "hola(2).txt"
    assert resolve_name_path(original) == expected
    rename_files_and_directories([original], dry_run)
    for link in links:
        assert link.is_symlink()
        assert link.readlink() == target
    if dry_run:
        assert original.read_text() == "content"
        assert not expected.exists()
    else:
        assert expected.read_text() == "content"
        assert not original.exists()


def test_target_symlink_to_source_is_preserved(tmp_path: Path) -> None:
    original = tmp_path / "Hola.TXT"
    original.write_text("content")
    link = tmp_path / "hola.txt"
    link.symlink_to(original)
    assert resolve_name_path(original) == tmp_path / "hola(1).txt"
    rename_files_and_directories([original], False)
    assert link.is_symlink()
    assert link.readlink() == original
    assert (tmp_path / "hola(1).txt").read_text() == "content"


def test_broken_link_blocks_directory_destination(tmp_path: Path) -> None:
    original = tmp_path / "Mi Carpeta"
    original.mkdir()
    (original / "content.txt").write_text("content")
    link = tmp_path / "mi-carpeta"
    link.symlink_to(tmp_path / "missing", target_is_directory=True)
    rename_files_and_directories([original], False)
    assert link.is_symlink()
    assert (tmp_path / "mi-carpeta(1)" / "content.txt").read_text() == "content"
