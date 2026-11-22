"""Resolución de colisiones, orden y ejecución segura de renombrados."""

import logging
from collections.abc import Iterable
from itertools import count
from pathlib import Path

from utils.text_utils import clean_directory_name, clean_file_name


def _unique_path(
    base_path: Path, reserved_paths: set[Path] | None = None,
    is_directory: bool = False,
) -> Path:
    """Busca un destino libre en disco y en el plan, respetando enlaces rotos."""
    reserved = reserved_paths if reserved_paths is not None else set()
    if base_path not in reserved and not (base_path.is_symlink() or base_path.exists()):
        return base_path
    stem = base_path.name if is_directory else base_path.stem
    suffix = "" if is_directory else base_path.suffix
    for n in count(1):
        candidate = base_path.parent / f"{stem}({n}){suffix}"
        if candidate not in reserved and not (candidate.is_symlink() or candidate.exists()):
            return candidate
    raise RuntimeError("Could not find a unique path")


def resolve_name_path(
    base_path: Path, reserved_paths: set[Path] | None = None,
) -> Path | None:
    """Limpia el nombre y resuelve colisiones con disco y destinos reservados.

    Omite enlaces simbólicos como origen. Un nombre vacío o inválido genera
    ValueError para que el plan lo registre y continúe con el resto del lote.
    """
    if base_path.is_symlink():
        return None

    new_name = ""

    is_directory = base_path.is_dir()
    if is_directory:
        new_name: str = clean_directory_name(base_path)
    elif base_path.is_file():
        new_name: str = clean_file_name(base_path)

    if not new_name or new_name in {".", ".."}:
        raise ValueError(f"new name is empty: {base_path}")

    final_name: Path = base_path.parent / new_name

    if  final_name.name == base_path.name:
        return final_name

    if (
        final_name not in (reserved_paths or set())
        and not final_name.is_symlink()
        and final_name.exists()
        and final_name.samefile(base_path)
    ):
        return final_name

    return _unique_path(final_name, reserved_paths, is_directory)


def organize_for_depth_and_alphabetical(list_items: Iterable[Path]) -> list[Path]:
    return sorted(list(list_items), key=lambda part: (-len(part.parts), part))


def build_rename_plan(list_items: Iterable[Path]) -> list[tuple[Path, Path]]:
    """Valida el lote antes de modificarlo y reserva los destinos válidos."""
    plan: list[tuple[Path, Path]] = []
    reserved_paths: set[Path] = set()
    for item in list_items:
        try:
            new_path = resolve_name_path(item, reserved_paths)
            if new_path and new_path != item:
                reserved_paths.add(new_path)
                plan.append((item, new_path))
        except ValueError as error:
            logging.error("Invalid name — skipping %s: %s", item, error)
        except PermissionError:
            logging.error("Permission denied — cannot access item: %s", item)
        except OSError as error:
            logging.error("OS error while validating %s: %s", item, error)
    return plan


def _confirm_name_loss(item: Path, new_path: Path, is_dry_run: bool) -> bool:
    """Advierte de la reducción de longitud sin contar sufijos de colisión."""
    cleaned_name = clean_directory_name(item) if item.is_dir() else clean_file_name(item)
    lost_characters = len(item.name) - len(cleaned_name)
    if lost_characters <= 4:
        return True

    logging.warning(
        "Pérdida de caracteres en %s: original=%r (%d caracteres), "
        "nuevo=%r; nombre limpio=%r (%d caracteres). "
        "Pérdida: %d caracteres (%.1f%%), antes de sufijos de colisión.",
        item, item.name, len(item.name), new_path.name, cleaned_name,
        len(cleaned_name), lost_characters, lost_characters / len(item.name) * 100,
    )
    if is_dry_run:
        return True
    try:
        answer = input("¿Confirmar este renombrado? [s/N]: ").strip().casefold()
    except (EOFError, OSError):
        logging.warning("Sin respuesta disponible — se omite %s", item)
        return False
    if answer in {"s", "si", "sí", "y", "yes"}:
        return True
    logging.info("Renombrado rechazado — se omite %s", item)
    return False


def rename_files_and_directories(list_items: Iterable[Path], is_dry_run: bool) -> None:
    plan = build_rename_plan(list_items)
    for item, new_path in plan:
        try:
            if not _confirm_name_loss(item, new_path, is_dry_run):
                continue
            if is_dry_run:
                logging.info(
                    "[DRY RUN] Would rename: %s -> %s", item, new_path,
                    extra={"rename_source": item, "rename_target": new_path},
                )
                continue
            # Un destino puede aparecer después de validar el plan.
            # No recalcularlo: la ejecución debe respetar la vista previa.
            if new_path.is_symlink() or new_path.exists():
                if new_path.is_symlink() or not new_path.samefile(item):
                    logging.error("Destination is occupied — skipping %s -> %s", item, new_path)
                    continue
            if item.is_symlink():
                logging.error("Source is now a symbolic link — skipping %s", item)
                continue
            item.rename(new_path)
            logging.info(
                "[RENAME] %s -> %s", item, new_path,
                extra={"rename_source": item, "rename_target": new_path},
            )
        except PermissionError:
            logging.error("Permission denied — could not rename: %s -> %s", item, new_path)
        except OSError as error:
            logging.error("OS error while renaming %s: %s", item, error)
