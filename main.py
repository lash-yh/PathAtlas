from pathlib import Path
import argparse
import logging
from core.actions import (
    organize_for_depth_and_alphabetical,
    rename_files_and_directories,
)
from core.config_loader import get_cached_config_value
from core.mounts import find_ssd_mount_point
from core.traversal import get_name_directories, get_name_files


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S"
                        )

    parser = argparse.ArgumentParser(description="Rename your files and directories")
    parser.add_argument('--run', action='store_true', help='Run the script')
    args = parser.parse_args()

    dry_run = not args.run

    config_path = Path.cwd() / "config.json"
    mount_label = get_cached_config_value(config_path, "mount_point_label")
    ignore_list = get_cached_config_value(config_path, "ignore") or []

    ssd_path = find_ssd_mount_point(mount_label)

    if not ssd_path:
        logging.error("Drive with label '%s' not found in disk partitions", mount_label)
        return


    files = organize_for_depth_and_alphabetical(
        get_name_files(ssd_path, config_path, "ignore_directories", ignore_list))

    directories = organize_for_depth_and_alphabetical(
        get_name_directories(ssd_path, config_path, "ignore_directories", ignore_list))

    rename_files_and_directories(files, dry_run)
    rename_files_and_directories(directories, dry_run)

if __name__ == "__main__":
    main()
