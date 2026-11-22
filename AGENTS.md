# Repository Guidelines

## Project Structure & Module Organization

`main.py` provides the command-line entry point for scanning a configured drive and renaming files and directories. `core/actions.py` handles filesystem operations, collision resolution, and rename ordering; `core/config_loader.py` loads cached JSON configuration and builds directory trees; `core/scanner.py` coordinates tree snapshots. `utils/text_utils.py` normalizes names, while `utils/helpers.py` provides file metadata helpers. Tests reside in `tests/`, with shared fixtures in `tests/conftest.py`. Dependencies are declared in `pyproject.toml` and locked in `uv.lock`. There is no separate asset directory.

## Build, Test, and Development Commands

Use Python 3.13 or newer and run commands from the repository root:

- `uv sync`: install runtime and development dependencies into `.venv`.
- `uv run main.py`: preview renames using the default dry-run mode.
- `uv run main.py --run`: apply renames to the configured drive after reviewing the preview.
- `uv run pytest`: run the complete test suite.
- `uv run pytest tests/test_actions.py`: run filesystem action tests only.

No separate build step is configured.

## Coding Style & Naming Conventions

Use four-space indentation, `snake_case` for functions and variables, and uppercase names for module constants such as `_CONFIG_CACHE`. Prefix internal helpers with `_`. Add type hints to new or changed functions, use `pathlib.Path` for filesystem paths, and use `logging` for operational messages. Keep logging setup in `main.py`. No formatter or linter is currently configured; keep changes consistent with nearby code.

## Testing Guidelines

Tests use pytest and pytest-mock. Name files `test_<module>.py` and functions `test_<behavior>`. Mock disk enumeration and filesystem operations, or use pytest's `tmp_path` fixture for isolated files. Cover name normalization, collisions, ignore lists, configuration handling, and deepest-first ordering when changing those behaviors. No numeric coverage threshold is configured. Run the full suite before submitting.

## Commit & Pull Request Guidelines

History includes short `fix:` and `feat:` subjects alongside plain descriptive messages. Prefer concise, action-oriented subjects. Pull requests should explain the changed behavior, reference relevant issues, and report validation commands and results. For normalization changes, include representative before/after filenames.

## Configuration & Filesystem Safety

`config.json` controls `mount_point_label` and ignored directory names. Verify the selected mount point before using `--run`. Preserve collision avoidance, dry-run behavior, and child-before-parent ordering. Keep tests isolated from actual mounted drives and exclude generated caches and virtual environments from commits.
