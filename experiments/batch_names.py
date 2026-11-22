"""Prototipo aislado: normalización por lotes de 50, con o sin hilos.

Ejecutar: .venv/bin/python -m experiments.batch_names
No cambia la CLI ni procesa rutas del usuario; solo usa directorios temporales.
"""

import argparse
import json
import logging
import os
import platform
import random
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from itertools import batched
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from core import actions
from core.traversal import get_name_directories, get_name_files
from utils.text_utils import clean_directory_name, clean_file_name

BATCH_SIZE = 50


def _clean_batch(batch: tuple[tuple[Path, bool], ...]) -> list[tuple[Path, str]]:
    return [
        (path, clean_directory_name(path) if directory else clean_file_name(path))
        for path, directory in batch
    ]


def prepare_names(items: list[tuple[Path, bool]], workers: int) -> dict[Path, str]:
    """workers=0 procesa lotes secuenciales; >0 crea un pool por operación."""
    batches = batched(items, BATCH_SIZE)
    if workers == 0:
        return dict(entry for batch in batches for entry in _clean_batch(batch))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return dict(entry for result in executor.map(_clean_batch, batches) for entry in result)


def run_tree(root: Path, workers: int | None, dry_run: bool = False) -> None:
    """Conserva reservas globales, confirmación y ejecución en el hilo principal.

    None usa el código actual sin caché. Las variantes por lotes reutilizan los
    nombres calculados en la planificación y en la comprobación de pérdida.
    """
    files = actions.organize_for_depth_and_alphabetical(get_name_files(root, {"Ignorada"}))
    directories = actions.organize_for_depth_and_alphabetical(
        get_name_directories(root, {"Ignorada"})
    )
    items = [*files, *directories]
    if workers is None:
        actions.rename_files_and_directories(items, dry_run)
        return
    names = prepare_names(
        [(path, False) for path in files] + [(path, True) for path in directories], workers
    )
    # Se inyectan funciones puras, sin alterar el código de producción.
    with (
        patch.object(actions, "clean_file_name", names.__getitem__),
        patch.object(actions, "clean_directory_name", names.__getitem__),
    ):
        actions.rename_files_and_directories(items, dry_run)


def make_tree(root: Path, count: int) -> None:
    """Incluye colisiones y carpetas anidadas; cada archivo tiene contenido único."""
    for index in range(count):
        parent = root / f"Carpeta {index // 200:03d}" / "Sub Carpeta"
        parent.mkdir(parents=True, exist_ok=True)
        title = "Informe" if index % 2 == 0 else "Ínforme"
        (parent / f"{title} {index // 2:05d}.TXT").write_text(str(index), encoding="utf-8")
    ignored = root / "Ignorada"
    ignored.mkdir()
    (ignored / "No Cambiar.TXT").write_text("ignorado", encoding="utf-8")


def snapshot(root: Path) -> dict[str, str | None]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8") if path.is_file() else None
        for path in root.rglob("*")
    }


def _measure(operation: Callable[[], object]) -> tuple[float, object]:
    start = perf_counter()
    result = operation()
    return perf_counter() - start, result


def benchmark(names_count: int, files_count: int, repeats: int) -> dict[str, object]:
    modes = {"actual": None, "lotes_50_secuencial_cache": 0,
             "lotes_50_2_hilos_cache": 2, "lotes_50_4_hilos_cache": 4,
             "lotes_50_8_hilos_cache": 8}
    names = [(Path(f"Copy of Programación C++ Número {index:06d}.TXT"), False)
             for index in range(names_count)]
    reference_names = {path: clean_file_name(path) for path, _ in names}
    # Calentamiento fuera de las mediciones.
    for workers in (0, 2, 4, 8):
        assert prepare_names(names[:100], workers) == dict(list(reference_names.items())[:100])
    timings: dict[str, dict[str, list[float]]] = {
        stage: {mode: [] for mode in modes} for stage in ("normalizacion", "flujo_completo")
    }
    expected_tree = None
    randomizer = random.Random(50)
    for _ in range(repeats):
        order = list(modes.items())
        randomizer.shuffle(order)
        for mode, workers in order:
            operation = (
                (lambda: {path: clean_file_name(path) for path, _ in names})
                if workers is None else (lambda: prepare_names(names, workers))
            )
            elapsed, normalized = _measure(operation)
            assert normalized == reference_names
            timings["normalizacion"][mode].append(elapsed)
            with TemporaryDirectory(prefix="rename-batch-50-") as temporary:
                root = Path(temporary)
                make_tree(root, files_count)
                # No se mide creación, borrado ni espera humana; sí escaneo,
                # creación del pool, normalización, planificación y renombrado.
                with patch("builtins.input", return_value="s"):
                    elapsed, _ = _measure(lambda: run_tree(root, workers))
                timings["flujo_completo"][mode].append(elapsed)
                result = snapshot(root)
                if expected_tree is None:
                    expected_tree = result
                assert result == expected_tree, f"Diferencias en {mode}"
                assert len([value for value in result.values() if value is not None]) == files_count + 1
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "cpu_count": os.cpu_count(), "gil_enabled": sys._is_gil_enabled(),
        "batch_size": BATCH_SIZE, "names": names_count, "files": files_count,
        "repeats": repeats, "all_outputs_identical": True,
        "results": {
            stage: {
                mode: {"median_seconds": median(samples), "samples_seconds": samples,
                       "relative_to_current": median(samples) / median(results["actual"])}
                for mode, samples in results.items()
            }
            for stage, results in timings.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--names", type=int, default=10000)
    parser.add_argument("--files", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if min(args.names, args.files, args.repeats) < 1:
        parser.error("Los tamaños y las repeticiones deben ser positivos")
    # Evita medir salida de consola y avisos, sin modificar logging de la CLI.
    logging.disable(logging.CRITICAL)
    try:
        print(json.dumps(benchmark(args.names, args.files, args.repeats), indent=2))
    finally:
        logging.disable(logging.NOTSET)


if __name__ == "__main__":
    main()
