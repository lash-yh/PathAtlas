"""Compara trabajo repetido entre obtención, planificación y renombrado.

Ejecutar: .venv/bin/python -m experiments.acquisition_reuse
Solo modifica árboles temporales; no cambia las funciones de producción.
"""

import argparse
import json
import logging
import platform
import random
from collections import Counter
from collections.abc import Callable, Collection, Iterator
from contextlib import ExitStack
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from unittest.mock import patch

from core import actions, traversal
from experiments.batch_names import make_tree, snapshot
from utils.text_utils import clean_directory_name, clean_file_name

MODES = ("actual", "reutilizar_dos_recorridos", "reutilizar_un_recorrido")


def _collect_once(
    root: Path, ignore: Collection[str], names: dict[tuple[Path, bool], str],
) -> Iterator[tuple[Path, bool]]:
    try:
        for item in root.iterdir():
            if item.is_symlink():
                continue
            if item.is_dir():
                if item.name in ignore:
                    continue
                cleaned = clean_directory_name(item)
                if cleaned != item.name:
                    names[item, True] = cleaned
                    yield item, True
                yield from _collect_once(item, ignore, names)
            elif item.is_file():
                cleaned = clean_file_name(item)
                if cleaned != item.name:
                    names[item, False] = cleaned
                    yield item, False
    except PermissionError:
        logging.error("Permission denied — cannot read directory contents: %s", root)


def run_tree(root: Path, mode: str, dry_run: bool = False) -> None:
    """Reutiliza únicamente cálculos puros, nunca comprobaciones del disco."""
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    names: dict[tuple[Path, bool], str] = {}
    if mode == "reutilizar_un_recorrido":
        entries = list(_collect_once(root, {"Ignorada"}, names))
        files = [path for path, directory in entries if not directory]
        directories = [path for path, directory in entries if directory]
    else:
        def remember_file(path: Path) -> str:
            names[path, False] = clean_file_name(path)
            return names[path, False]

        def remember_directory(path: Path) -> str:
            names[path, True] = clean_directory_name(path)
            return names[path, True]

        with ExitStack() as stack:
            if mode != "actual":
                stack.enter_context(patch.object(traversal, "clean_file_name", remember_file))
                stack.enter_context(patch.object(traversal, "clean_directory_name", remember_directory))
            files = list(traversal.get_name_files(root, {"Ignorada"}))
            directories = list(traversal.get_name_directories(root, {"Ignorada"}))
    items = [*actions.organize_for_depth_and_alphabetical(files),
             *actions.organize_for_depth_and_alphabetical(directories)]

    def cached_file(path: Path) -> str:
        key = (path, False)
        return names[key] if key in names else clean_file_name(path)

    def cached_directory(path: Path) -> str:
        key = (path, True)
        return names[key] if key in names else clean_directory_name(path)

    with ExitStack() as stack:
        if mode != "actual":
            stack.enter_context(patch.object(actions, "clean_file_name", cached_file))
            stack.enter_context(patch.object(actions, "clean_directory_name", cached_directory))
        actions.rename_files_and_directories(items, dry_run)


def count_operations(root: Path, mode: str, dry_run: bool) -> dict[str, int]:
    """Instrumentación separada de las mediciones de tiempo."""
    calls: Counter[str] = Counter()

    def counted(label: str, function: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            calls[label] += 1
            return function(*args, **kwargs)
        return wrapper

    with ExitStack() as stack:
        for name in ("iterdir", "is_dir", "is_file", "is_symlink", "exists", "samefile"):
            stack.enter_context(patch.object(Path, name, counted(name, getattr(Path, name))))
        # La misma función pura se importa en los tres puntos del prototipo.
        for module in (actions, traversal, __import__(__name__, fromlist=["*"])):
            for name in ("clean_file_name", "clean_directory_name"):
                stack.enter_context(patch.object(module, name, counted(name, getattr(module, name))))
        run_tree(root, mode, dry_run)
    return dict(calls)


def benchmark(files_count: int, repeats: int) -> dict[str, object]:
    times: dict[str, dict[str, list[float]]] = {
        stage: {mode: [] for mode in MODES} for stage in ("preview", "rename")
    }
    counts: dict[str, dict[str, dict[str, int]]] = {stage: {} for stage in times}
    randomizer = random.Random(17)
    for stage in times:
        dry_run = stage == "preview"
        reference = None
        for repetition in range(repeats + 1):
            modes = list(MODES)
            randomizer.shuffle(modes)
            for mode in modes:
                with TemporaryDirectory(prefix="rename-acquisition-") as temporary:
                    root = Path(temporary)
                    make_tree(root, files_count)
                    # Incluye nombres limpios, inválidos, enlaces y colisiones
                    # entre archivos y directorios, además del árbol compartido.
                    (root / "limpio.txt").write_text("limpio")
                    (root / "---").write_text("invalido")
                    (root / "01.").mkdir()
                    (root / "Carpeta").write_text("archivo")
                    (root / "01. Carpeta").mkdir()
                    (root / "Enlace.TXT").symlink_to("no-existe")
                    before = snapshot(root) if dry_run else None
                    with patch("builtins.input", return_value="s"):
                        if repetition == 0:
                            counts[stage][mode] = count_operations(root, mode, dry_run)
                        else:
                            start = perf_counter()
                            run_tree(root, mode, dry_run)
                            times[stage][mode].append(perf_counter() - start)
                    result = snapshot(root)
                    if reference is None:
                        reference = result
                    assert result == reference, (stage, mode)
                    if dry_run:
                        assert result == before
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "files": files_count, "repeats": repeats,
        "all_outputs_identical": True, "operation_counts": counts,
        "timings": {
            stage: {
                mode: {"median_seconds": median(samples), "samples_seconds": samples,
                       "relative_to_current": median(samples) / median(values["actual"])}
                for mode, samples in values.items()
            } for stage, values in times.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if min(args.files, args.repeats) < 1:
        parser.error("Los tamaños y las repeticiones deben ser positivos")
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        print(json.dumps(benchmark(args.files, args.repeats), indent=2))
    finally:
        logging.disable(previous)


if __name__ == "__main__":
    main()
