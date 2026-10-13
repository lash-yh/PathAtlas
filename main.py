from pathlib import Path
import argparse
import logging
from core.actions import (
    organize_for_depth_and_alphabetical,
    rename_files_and_directories,
)
from core.config_loader import load_config
from core.mounts import find_ssd_mount_point
from core.traversal import get_name_directories, get_name_files


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


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S"
                        )

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

    files = organize_for_depth_and_alphabetical(
        get_name_files(source_path, ignore_list))

    directories = organize_for_depth_and_alphabetical(
        get_name_directories(source_path, ignore_list))

    rename_files_and_directories([*files, *directories], dry_run)

if __name__ == "__main__":
    main()
