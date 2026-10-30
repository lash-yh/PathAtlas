import logging
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from core.actions import rename_files_and_directories


@pytest.mark.parametrize("answer", ["s", " SÍ ", "yes"])
@pytest.mark.parametrize("directory", [False, True])
def test_large_name_loss_requires_confirmation(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture,
    answer: str, directory: bool,
) -> None:
    source = tmp_path / ("0001. Informe" if directory else "Copy of Informe.TXT")
    if directory:
        source.mkdir()
    else:
        source.write_text("contenido")
    target = tmp_path / ("informe" if directory else "informe.txt")
    confirm = mocker.patch("builtins.input", return_value=answer)

    rename_files_and_directories([source], False)

    confirm.assert_called_once()
    assert target.exists()
    assert not source.exists()
    assert repr(source.name) in caplog.text
    assert repr(target.name) in caplog.text
    assert ("6 caracteres (46.2%)" if directory else "8 caracteres (42.1%)") in caplog.text


@pytest.mark.parametrize("answer", ["", "n", "otra respuesta"])
def test_rejected_rename_keeps_source_and_continues_batch(
    tmp_path: Path, mocker: MockerFixture, answer: str,
) -> None:
    source = tmp_path / "Copy of Informe.TXT"
    source.write_text("original")
    safe = tmp_path / "Otro.TXT"
    safe.write_text("otro")
    mocker.patch("builtins.input", return_value=answer)

    rename_files_and_directories([source, safe], False)

    assert source.read_text() == "original"
    assert not (tmp_path / "informe.txt").exists()
    assert (tmp_path / "otro.txt").read_text() == "otro"


@pytest.mark.parametrize("error", [EOFError, OSError])
def test_unavailable_input_skips_lossy_rename(
    tmp_path: Path, mocker: MockerFixture, error: type[Exception],
) -> None:
    source = tmp_path / "Copy of Informe.TXT"
    source.touch()
    mocker.patch("builtins.input", side_effect=error)

    rename_files_and_directories([source], False)

    assert source.exists()
    assert not (tmp_path / "informe.txt").exists()


@pytest.mark.parametrize("name", ["01. Informe", "Mi Carpeta", "Programación"])
def test_at_most_four_characters_lost_needs_no_confirmation(
    tmp_path: Path, mocker: MockerFixture, name: str,
) -> None:
    source = tmp_path / name
    source.mkdir()
    confirm = mocker.patch("builtins.input")

    rename_files_and_directories([source], False)

    confirm.assert_not_called()
    assert not source.exists()


def test_preview_reports_loss_without_prompting_or_changing_files(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture,
) -> None:
    source = tmp_path / "Copy of Informe.TXT"
    source.write_text("contenido")
    confirm = mocker.patch("builtins.input")

    with caplog.at_level(logging.INFO):
        rename_files_and_directories([source], True)

    confirm.assert_not_called()
    assert "Pérdida: 8 caracteres (42.1%)" in caplog.text
    assert "[DRY RUN]" in caplog.text
    assert source.read_text() == "contenido"
    assert not (tmp_path / "informe.txt").exists()


def test_collision_suffix_does_not_hide_five_character_loss(
    tmp_path: Path, mocker: MockerFixture,
) -> None:
    source = tmp_path / "001. Informe"
    source.mkdir()
    existing = tmp_path / "informe"
    existing.mkdir()
    confirm = mocker.patch("builtins.input", return_value="s")

    rename_files_and_directories([source], False)

    confirm.assert_called_once()
    assert (tmp_path / "informe(1)").is_dir()
    assert existing.is_dir()
