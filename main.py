from pathlib import Path
import argparse
import logging
from collections.abc import Collection
from core.actions import (
    organize_for_depth_and_alphabetical,
    rename_files_and_directories,
)
from core.config_loader import load_config
from core.mounts import find_ssd_mount_point
from core.traversal import get_name_directories, get_name_files


class _RenameLogFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(levelname)s: %(message)s")
        self._last_directory: Path | None = None

    def format(self, record: logging.LogRecord) -> str:
        source = getattr(record, "rename_source", None)
        target = getattr(record, "rename_target", None)
        if source is None or target is None:
            self._last_directory = None
            return super().format(record)

        rename = f"{source.name} -> {target.name}"
        if source.parent == self._last_directory:
            return rename
        self._last_directory = source.parent
        return f"{source.parent}\n{rename}"


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_RenameLogFormatter())
    handler.addFilter(
        lambda record: record.levelno >= logging.WARNING
        or hasattr(record, "rename_source")
        or getattr(record, "scan_summary", False)
    )
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def _directory_path(value: str) -> Path:
    try:
        path = Path(value).expanduser().resolve()
        if path.is_dir():
            return path
    except (OSError, RuntimeError) as error:
        raise argparse.ArgumentTypeError(f"Cannot access directory: {value}") from error
    raise argparse.ArgumentTypeError(f"Path does not exist or is not a directory: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rename your files and directories")
    parser.add_argument('--run', action='store_true', help='Apply renames')
    subcommands = parser.add_subparsers(dest='command')
    path_parser = subcommands.add_parser('path', help='Work on a directory supplied explicitly')
    path_parser.add_argument('directory', type=_directory_path, help='Directory to scan recursively')
    path_parser.add_argument(
        '--run', action='store_true', default=argparse.SUPPRESS, help='Apply renames'
    )
    return parser


def _count_entries(source_path: Path, ignore_list: Collection[str]) -> tuple[int, int]:
    files = sum(1 for _ in get_name_files(source_path, ignore_list, only_pending=False))
    directories = sum(
        1 for _ in get_name_directories(source_path, ignore_list, only_pending=False)
    )
    return files, directories


def main() -> None:
    _configure_logging()

    parser = _build_parser()
    args = parser.parse_args()

    dry_run = not args.run

    config_path = Path.cwd() / "config.json"
    try:
        config = load_config(config_path)
    except (OSError, ValueError) as error:
        logging.error("Cannot load config from %s: %s", config_path, error)
        parser.exit(2)
    ignore_list = frozenset(config["ignore"])

    if args.command == 'path':
        source_path = args.directory
    else:
        mount_label = config["mount_point_label"]
        if not mount_label:
            logging.error("Config 'mount_point_label' is required for drive detection")
            parser.exit(2)
        source_path = find_ssd_mount_point(mount_label)
        if not source_path:
            logging.error("Drive with label '%s' not found in disk partitions", mount_label)
            return

    before_files, before_directories = _count_entries(source_path, ignore_list)
    logging.info(
        "Antes de la normalización: %d archivos y %d directorios",
        before_files, before_directories, extra={"scan_summary": True},
    )

    files = organize_for_depth_and_alphabetical(
        get_name_files(source_path, ignore_list))

    directories = organize_for_depth_and_alphabetical(
        get_name_directories(source_path, ignore_list))

    logging.info(
        "Recorrido inicial: %d archivos y %d directorios pendientes de renombrar",
        len(files), len(directories), extra={"scan_summary": True},
    )

    rename_files_and_directories([*files, *directories], dry_run)

    after_files, after_directories = _count_entries(source_path, ignore_list)
    logging.info(
        "Después de la normalización: %d archivos y %d directorios",
        after_files, after_directories, extra={"scan_summary": True},
    )
    if (before_files, before_directories) == (after_files, after_directories):
        logging.info(
            "Verificación de conteos: coinciden los totales de archivos y directorios",
            extra={"scan_summary": True},
        )
    else:
        logging.warning(
            "Verificación de conteos: los totales han cambiado "
            "(archivos: %d -> %d; directorios: %d -> %d)",
            before_files, after_files, before_directories, after_directories,
            extra={"scan_summary": True},
        )

    remaining_files = sum(1 for _ in get_name_files(source_path, ignore_list))
    remaining_directories = sum(1 for _ in get_name_directories(source_path, ignore_list))
    logging.info(
        "Recorrido final: %d archivos y %d directorios pendientes de renombrar",
        remaining_files, remaining_directories, extra={"scan_summary": True},
    )

if __name__ == "__main__":
    main()
