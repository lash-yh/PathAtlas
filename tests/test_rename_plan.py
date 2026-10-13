import logging
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from core.actions import (
    build_rename_plan, organize_for_depth_and_alphabetical,
    rename_files_and_directories,
)
from core.traversal import get_name_directories, get_name_files
from utils.text_utils import clean_directory_name, clean_file_name, clean_name


@pytest.mark.parametrize("name, expected", [
    ("Programación en C++ y C#", "programacion-en-c++-y-c#"),
    ("C++ & C# (Nivel 2) [50%] @Casa!", "c++-&-c#-(nivel-2)-[50%]-@casa!"),
    ("A!.TXT", "a!.txt"),
    ("A?.TXT", "a?.txt" if sys.platform.startswith("linux") else "a.txt"),
    ("A*.TXT", "a*.txt" if sys.platform.startswith("linux") else "a.txt"),
    ("a(1).txt", "a(1).txt"),
    (".env", ".env"),
    ("archivo.tar.gz", "archivo.tar.gz"),
    ("COPY_OF Reporte", "reporte"),
    ("nombre<con>caracteres:invalidos", "nombre-con-caracteres-invalidos"),
])
def test_normalization_preserves_details_and_is_stable(name: str, expected: str) -> None:
    cleaned = clean_file_name(Path(name))
    assert cleaned == expected
    assert clean_file_name(Path(cleaned)) == cleaned


def test_control_characters_are_removed() -> None:
    assert clean_name("Hola\x00Mundo\nFinal") == "hola-mundo-final"


def test_directory_numeric_prefixes_are_removed_in_one_pass() -> None:
    cleaned = clean_directory_name(Path("01. 02. C++ y C#"))
    assert cleaned == "c++-y-c#"
    assert clean_directory_name(Path(cleaned)) == cleaned


def test_preview_and_execution_have_identical_collision_destinations(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    sources = [tmp_path / name for name in ("Á.TXT", "A.TXT", "A!.TXT", "A?.TXT", "á.TXT")]
    for index, source in enumerate(sources):
        source.write_text(str(index))
    plan = build_rename_plan(sources)
    assert len({target for _, target in plan}) == len(plan)
    expected_names = (["a.txt", "a(1).txt", "a!.txt", "a?.txt", "a(2).txt"]
                      if sys.platform.startswith("linux")
                      else ["a.txt", "a(1).txt", "a!.txt", "a(2).txt", "a(3).txt"])
    assert [target.name for _, target in plan] == expected_names
    with caplog.at_level(logging.INFO):
        rename_files_and_directories(sources, True)
    preview = [record.getMessage().split(" -> ")[1] for record in caplog.records]
    assert preview == [str(target) for _, target in plan]
    assert all(source.exists() for source in sources)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        rename_files_and_directories(sources, False)
    actual = [record.getMessage().split(" -> ")[1] for record in caplog.records]
    assert actual == preview
    for index, (_, target) in enumerate(plan):
        assert target.read_text() == str(index)
    assert list(get_name_files(tmp_path, [])) == []


@pytest.mark.parametrize("dry_run", [True, False])
def test_invalid_names_are_logged_before_any_rename_and_batch_continues(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, mocker: MockerFixture,
    dry_run: bool,
) -> None:
    good = tmp_path / "Mi Archivo.TXT"
    empty_file = tmp_path / "---"
    empty_stem = tmp_path / "<<<.TXT"
    empty_directory = tmp_path / "01."
    for source in (good, empty_file, empty_stem):
        source.write_text("content")
    empty_directory.mkdir()
    original_rename = Path.rename
    def checked_rename(source: Path, target: Path) -> Path:
        assert len([record for record in caplog.records if record.levelno == logging.ERROR]) == 3
        return original_rename(source, target)
    mocker.patch.object(Path, "rename", autospec=True, side_effect=checked_rename)
    with caplog.at_level(logging.INFO):
        rename_files_and_directories([good, empty_file, empty_stem, empty_directory], dry_run)
    assert len([record for record in caplog.records if record.levelno == logging.ERROR]) == 3
    assert empty_file.exists() and empty_stem.exists() and empty_directory.exists()
    if dry_run:
        assert good.read_text() == "content"
    else:
        assert (tmp_path / "mi-archivo.txt").read_text() == "content"


def test_nested_directory_collisions_are_stable_after_second_run(tmp_path: Path) -> None:
    for parent_name in ("Á", "A"):
        parent = tmp_path / parent_name
        parent.mkdir()
        for child_name in ("Mi Carpeta.v1", "Mí Carpeta.v1"):
            child = parent / child_name
            child.mkdir()
            (child / "Programación en C++.TXT").write_text(parent_name + child_name)
    files = organize_for_depth_and_alphabetical(get_name_files(tmp_path, []))
    directories = organize_for_depth_and_alphabetical(get_name_directories(tmp_path, []))
    rename_files_and_directories([*files, *directories], False)
    before = {str(path.relative_to(tmp_path)): path.read_text() for path in tmp_path.rglob("*") if path.is_file()}
    assert len(before) == 4
    assert {path.name for path in tmp_path.iterdir()} == {"a", "a(1)"}
    assert {path.name for path in (tmp_path / "a").iterdir()} == {"mi-carpeta.v1", "mi-carpeta.v1(1)"}
    files = list(get_name_files(tmp_path, []))
    directories = list(get_name_directories(tmp_path, []))
    assert files == [] and directories == []
    rename_files_and_directories([*files, *directories], False)
    after = {str(path.relative_to(tmp_path)): path.read_text() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_files_and_directories_share_destination_reservations(tmp_path: Path) -> None:
    file = tmp_path / "Carpeta"
    file.write_text("content")
    directory = tmp_path / "01. Carpeta"
    directory.mkdir()
    plan = build_rename_plan([file, directory])
    assert plan == [(file, tmp_path / "carpeta"), (directory, tmp_path / "carpeta(1)")]
    rename_files_and_directories([file, directory], False)
    assert (tmp_path / "carpeta").read_text() == "content"
    assert (tmp_path / "carpeta(1)").is_dir()


def test_newly_occupied_destination_is_skipped_without_overwrite(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture,
) -> None:
    source = tmp_path / "Mi Archivo.TXT"
    source.write_text("original")
    target = tmp_path / "mi-archivo.txt"
    planner = build_rename_plan
    def concurrent_plan(items: list[Path]) -> list[tuple[Path, Path]]:
        plan = planner(items)
        target.write_text("new occupant")
        return plan
    mocker.patch("core.actions.build_rename_plan", side_effect=concurrent_plan)
    rename_files_and_directories([source], False)
    assert source.read_text() == "original"
    assert target.read_text() == "new occupant"
    assert "Destination is occupied" in caplog.text


def test_question_mark_and_asterisk_are_filtered_outside_linux(mocker: MockerFixture) -> None:
    mocker.patch("utils.text_utils._INVALID_CHARACTERS", frozenset('<>:"/\\|?*'))
    assert clean_file_name(Path("C++? C#*.TXT")) == "c++-c#.txt"
