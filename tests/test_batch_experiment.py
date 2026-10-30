import threading
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from experiments.batch_names import make_tree, prepare_names, run_tree, snapshot
from utils.text_utils import clean_file_name


@pytest.mark.parametrize("workers", [0, 2, 4, 8])
@pytest.mark.parametrize("count", [0, 49, 50, 51, 123])
def test_batches_keep_every_name_in_order(workers: int, count: int) -> None:
    items = [(Path(f"Programación C++ {index}.TXT"), False) for index in range(count)]
    result = prepare_names(items, workers)
    assert list(result.items()) == [(path, clean_file_name(path)) for path, _ in items]


@pytest.mark.parametrize("workers", [0, 2, 4, 8])
@pytest.mark.parametrize("dry_run", [False, True])
def test_batch_pipeline_matches_current_with_nested_collisions_and_ignores(
    tmp_path: Path, workers: int, dry_run: bool,
) -> None:
    current, candidate = tmp_path / "actual", tmp_path / "prototipo"
    # 402 archivos fuerzan colisiones entre lotes y varios padres.
    for root in (current, candidate):
        make_tree(root, 402)
    before = snapshot(current)

    run_tree(current, None, dry_run)
    run_tree(candidate, workers, dry_run)

    assert snapshot(candidate) == snapshot(current)
    if dry_run:
        assert snapshot(candidate) == before
    else:
        assert (candidate / "carpeta-000" / "sub-carpeta" / "informe-00024(1).txt").read_text() == "49"
        assert (candidate / "Ignorada" / "No Cambiar.TXT").read_text() == "ignorado"


@pytest.mark.parametrize("answer", ["s", "n"])
def test_batch_confirmation_stays_on_main_thread_and_preserves_content(
    tmp_path: Path, mocker: MockerFixture, answer: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / "Copy of Informe.TXT"
    source.write_text("contenido")
    link = root / "Enlace.TXT"
    link.symlink_to(source)

    def confirm(prompt: str) -> str:
        assert threading.current_thread() is threading.main_thread()
        return answer

    confirmation = mocker.patch("builtins.input", side_effect=confirm)
    run_tree(root, 4)

    confirmation.assert_called_once()
    assert link.is_symlink()
    assert link.readlink() == source
    target = root / "informe.txt"
    assert (target if answer == "s" else source).read_text() == "contenido"
    assert target.exists() == (answer == "s")
