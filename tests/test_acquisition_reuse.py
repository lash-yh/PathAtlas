"""Comparación funcional y cambios de disco entre etapas del prototipo."""

import logging
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from core import actions
from experiments.acquisition_reuse import MODES, count_operations, run_tree
from experiments.batch_names import make_tree, snapshot


@pytest.mark.parametrize("mode", MODES[1:])
@pytest.mark.parametrize("dry_run", [True, False])
def test_acquisition_reuse_matches_destinations_and_contents(
    tmp_path: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture,
    mode: str, dry_run: bool,
) -> None:
    reference = tmp_path / "actual"
    candidate = tmp_path / "candidato"
    mocker.patch("builtins.input", return_value="s")
    previews: list[list[str]] = []
    for root, variant in ((reference, "actual"), (candidate, mode)):
        make_tree(root, 402)
        (root / "limpio.txt").write_text("limpio")
        (root / "---").write_text("invalido")
        (root / "01.").mkdir()
        (root / "Carpeta").write_text("archivo")
        (root / "01. Carpeta").mkdir()
        (root / "Copy of Informe.TXT").write_text("confirmacion")
        (root / "Enlace.TXT").symlink_to("no-existe")
        before = snapshot(root)
        caplog.clear()
        with caplog.at_level(logging.INFO):
            run_tree(root, variant, dry_run)
        previews.append([record.getMessage().replace(str(root), "ROOT")
                         for record in caplog.records])
        assert (root / "---").read_text() == "invalido"
        assert (root / "01.").is_dir()
        assert (root / "Enlace.TXT").is_symlink()
        if dry_run:
            assert snapshot(root) == before
        else:
            assert (root / "carpeta").read_text() == "archivo"
            assert (root / "carpeta(1)").is_dir()
            assert (root / "informe.txt").read_text() == "confirmacion"
    assert snapshot(reference) == snapshot(candidate)
    assert previews[0] == previews[1]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("change", ["destination", "source_link", "source_type", "removed"])
def test_disk_changes_after_acquisition_still_require_live_validation(
    tmp_path: Path, mocker: MockerFixture, mode: str, change: str,
) -> None:
    source = tmp_path / "01. Informe"
    source.mkdir()
    target = tmp_path / "informe"
    planner = actions.build_rename_plan

    def change_then_plan(items: list[Path]) -> list[tuple[Path, Path]]:
        if change == "destination":
            target.write_text("ocupante")
        else:
            source.rmdir()
            if change == "source_link":
                source.symlink_to("externo")
            elif change == "source_type":
                source.write_text("ahora archivo")
        return planner(items)

    mocker.patch.object(actions, "build_rename_plan", side_effect=change_then_plan)
    run_tree(tmp_path, mode)
    if change == "destination":
        assert target.read_text() == "ocupante"
        assert (tmp_path / "informe(1)").is_dir()
    elif change == "source_link":
        assert source.is_symlink()
        assert not target.exists()
    elif change == "source_type":
        # Los prefijos numéricos solo se eliminan de directorios.
        assert (tmp_path / "01.-informe").read_text() == "ahora archivo"
        assert not target.exists()
    else:
        assert not source.exists() and not target.exists()


@pytest.mark.parametrize("mode", MODES)
def test_late_destination_is_not_overwritten(
    tmp_path: Path, mocker: MockerFixture, mode: str,
) -> None:
    source = tmp_path / "Informe.TXT"
    source.write_text("original")
    target = tmp_path / "informe.txt"
    planner = actions.build_rename_plan

    def plan_then_occupy(items: list[Path]) -> list[tuple[Path, Path]]:
        plan = planner(items)
        target.write_text("ocupante tardio")
        return plan

    mocker.patch.object(actions, "build_rename_plan", side_effect=plan_then_occupy)
    run_tree(tmp_path, mode)
    assert source.read_text() == "original"
    assert target.read_text() == "ocupante tardio"


def test_acquisition_reuse_reduces_measured_work(tmp_path: Path) -> None:
    make_tree(tmp_path, 10)
    counts = {mode: count_operations(tmp_path, mode, True) for mode in MODES}
    current, reuse, single = (counts[mode] for mode in MODES)
    assert current["iterdir"] == reuse["iterdir"] == 2 * single["iterdir"]
    for operation in ("clean_file_name", "clean_directory_name"):
        assert current[operation] == 3 * reuse[operation] == 3 * single[operation]
    # La caché elimina cálculos puros, conserva consultas de seguridad al disco.
    for operation in ("exists", "samefile", "is_symlink", "is_dir", "is_file"):
        assert reuse.get(operation, 0) == current.get(operation, 0)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("answer", ["s", "n"])
def test_reused_name_preserves_loss_confirmation_with_collision(
    tmp_path: Path, mocker: MockerFixture, mode: str, answer: str,
) -> None:
    source = tmp_path / "Copy of Informe.TXT"
    source.write_text("original")
    target = tmp_path / "informe.txt"
    target.write_text("existente")
    confirmation = mocker.patch("builtins.input", return_value=answer)
    run_tree(tmp_path, mode)
    confirmation.assert_called_once()
    assert target.read_text() == "existente"
    collision = tmp_path / "informe(1).txt"
    assert collision.exists() == (answer == "s")
    assert (collision if answer == "s" else source).read_text() == "original"


@pytest.mark.parametrize("mode", MODES)
def test_source_becoming_symlink_during_confirmation_is_skipped(
    tmp_path: Path, mocker: MockerFixture, mode: str,
) -> None:
    source = tmp_path / "Copy of Informe.TXT"
    source.write_text("original")
    outside = tmp_path / "externo"
    outside.write_text("protegido")

    def confirm(prompt: str) -> str:
        source.unlink()
        source.symlink_to(outside)
        return "s"

    mocker.patch("builtins.input", side_effect=confirm)
    run_tree(tmp_path, mode)
    assert source.is_symlink()
    assert outside.read_text() == "protegido"
    assert not (tmp_path / "informe.txt").exists()
