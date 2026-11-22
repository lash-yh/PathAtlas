from pathlib import Path
import logging
import subprocess
import sys

import pytest
from pytest_mock import MockerFixture

from main import main


@pytest.mark.parametrize("run", [False, True])
def test_cli_groups_file_and_directory_renames(
    tmp_path: Path, run: bool,
) -> None:
    (tmp_path / "config.json").write_text('{"ignore": []}')
    root = tmp_path / "selected"
    child = root / "Mi Carpeta"
    child.mkdir(parents=True)
    (child / "A.TXT").write_text("first")
    (child / "B.TXT").write_text("second")
    (child / "a.txt").write_text("existing")
    (root / "C.TXT").write_text("third")
    script = Path(__file__).resolve().parents[1] / "main.py"

    result = subprocess.run(
        [sys.executable, str(script), "path", str(root)] + (["--run"] if run else []),
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )

    assert result.stdout == ""
    assert result.stderr == (
        "INFO: Antes de la normalización: 4 archivos y 1 directorios\n"
        "INFO: Recorrido inicial: 3 archivos y 1 directorios pendientes de renombrar\n"
        f"{child}\n"
        "A.TXT -> a(1).txt\n"
        "B.TXT -> b.txt\n"
        f"{root}\n"
        "C.TXT -> c.txt\n"
        "Mi Carpeta -> mi-carpeta\n"
        "INFO: Después de la normalización: 4 archivos y 1 directorios\n"
        "INFO: Verificación de conteos: coinciden los totales de archivos y directorios\n"
        f"INFO: Recorrido final: {0 if run else 3} archivos y "
        f"{0 if run else 1} directorios pendientes de renombrar\n"
    )
    if run:
        assert (root / "mi-carpeta" / "a(1).txt").read_text() == "first"
        assert (root / "mi-carpeta" / "a.txt").read_text() == "existing"
    else:
        assert (child / "A.TXT").read_text() == "first"


@pytest.mark.parametrize('run_position', [None, 'before', 'after'])
def test_path_command_preserves_safety_and_ignores(
    tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch,
    run_position: str | None
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / 'Mis Archivos'
    child = root / 'Mi Carpeta'
    child.mkdir(parents=True)
    original = child / 'Mi Archivo.TXT'
    original.write_text('contenido')
    ignored = root / 'Ignorada'
    ignored.mkdir()
    ignored_file = ignored / 'No Cambiar.TXT'
    ignored_file.write_text('ignorado')
    (tmp_path / 'config.json').write_text('{"ignore": ["Ignorada"]}')
    mount = mocker.patch('main.find_ssd_mount_point')
    argv = ['main.py', 'path', 'Mis Archivos']
    if run_position == 'before':
        argv.insert(1, '--run')
    elif run_position == 'after':
        argv.append('--run')
    mocker.patch('sys.argv', argv)

    main()

    mount.assert_not_called()
    assert root.is_dir()
    assert ignored_file.read_text() == 'ignorado'
    renamed = root / 'mi-carpeta' / 'mi-archivo.txt'
    if run_position is None:
        assert original.read_text() == 'contenido'
        assert not renamed.exists()
    else:
        assert renamed.read_text() == 'contenido'
        assert not original.exists()


@pytest.mark.parametrize('invalid_path', ['missing', 'file'])
def test_path_command_rejects_invalid_directory(
    tmp_path: Path, mocker: MockerFixture, invalid_path: str
) -> None:
    file = tmp_path / 'file'
    file.touch()
    mocker.patch('sys.argv', ['main.py', 'path', str(tmp_path / invalid_path), '--run'])
    mount = mocker.patch('main.find_ssd_mount_point')
    rename = mocker.patch('main.rename_files_and_directories')

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    mount.assert_not_called()
    rename.assert_not_called()
    assert file.exists()


def test_path_command_requires_directory(mocker: MockerFixture) -> None:
    mocker.patch('sys.argv', ['main.py', 'path'])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


@pytest.mark.parametrize('run', [False, True])
def test_default_command_still_uses_configured_mount(
    tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, run: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'config.json').write_text('{"mount_point_label": "SSD", "ignore": []}')
    source = tmp_path / 'Mi Archivo.TXT'
    source.write_text('contenido')
    mount = mocker.patch('main.find_ssd_mount_point', return_value=tmp_path)
    mocker.patch('sys.argv', ['main.py'] + (['--run'] if run else []))

    main()

    mount.assert_called_once_with('SSD')
    if run:
        assert (tmp_path / 'mi-archivo.txt').read_text() == 'contenido'
    else:
        assert source.read_text() == 'contenido'


def test_path_command_expands_home(mocker: MockerFixture) -> None:
    mocker.patch('sys.argv', ['main.py', 'path', '~'])
    mocker.patch('main.load_config', return_value={'ignore': [], 'mount_point_label': None})
    files = mocker.patch('main.get_name_files', return_value=[])
    mocker.patch('main.get_name_directories', return_value=[])

    main()

    assert files.call_args.args[0] == Path('~').expanduser().resolve()


@pytest.mark.parametrize("path_mode", [False, True])
@pytest.mark.parametrize("run", [False, True])
def test_main_reads_config_once_for_all_queries_and_recursive_scans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture,
    path_mode: bool, run: bool,
) -> None:
    import json
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text('{"mount_point_label": "SSD", "ignore": ["Ignorada"]}')
    selected = tmp_path / "selected"
    child = selected / "Mi Carpeta" / "Sub Carpeta"
    child.mkdir(parents=True)
    (child / "Mi Archivo.TXT").write_text("content")
    ignored = selected / "Ignorada"
    ignored.mkdir()
    protected = ignored / "No Cambiar.TXT"
    protected.write_text("protected")
    mocker.patch("main.find_ssd_mount_point", return_value=selected)
    loader = mocker.spy(__import__("main"), "load_config")
    opened = mocker.spy(Path, "open")
    parsed = mocker.spy(json, "load")
    mocker.patch("sys.argv", ["main.py"] + (["path", str(selected)] if path_mode else []) + (["--run"] if run else []))
    main()
    loader.assert_called_once_with(config_path)
    opened.assert_called_once_with(config_path, 'r', encoding='utf-8')
    parsed.assert_called_once()
    assert protected.read_text() == "protected"
    renamed = selected / "mi-carpeta" / "sub-carpeta" / "mi-archivo.txt"
    assert renamed.exists() == run


@pytest.mark.parametrize("payload", [None, "{invalid", "[]", '{"ignore": ".git"}'])
def test_main_stops_before_scanning_when_config_cannot_be_loaded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture, payload: str | None,
) -> None:
    monkeypatch.chdir(tmp_path)
    if payload is not None:
        (tmp_path / "config.json").write_text(payload)
    mocker.patch("sys.argv", ["main.py", "path", str(tmp_path), "--run"])
    files = mocker.patch("main.get_name_files")
    directories = mocker.patch("main.get_name_directories")
    rename = mocker.patch("main.rename_files_and_directories")
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    files.assert_not_called()
    directories.assert_not_called()
    rename.assert_not_called()
    assert "Cannot load config" in caplog.text


def test_default_command_reports_missing_mount_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text('{"ignore": []}')
    mocker.patch("sys.argv", ["main.py"])
    mount = mocker.patch("main.find_ssd_mount_point")
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    mount.assert_not_called()


@pytest.mark.parametrize("removed_kind", ["file", "directory"])
def test_main_warns_when_total_counts_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture, removed_kind: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text('{"ignore": []}')
    root = tmp_path / "selected"
    root.mkdir()
    file = root / "Mi Archivo.TXT"
    file.touch()
    directory = root / "Mi Carpeta"
    directory.mkdir()
    mocker.patch("sys.argv", ["main.py", "path", str(root), "--run"])

    def simulate_missing_entry(items: list[Path], dry_run: bool) -> None:
        assert not dry_run
        assert set(items) == {file, directory}
        if removed_kind == "file":
            file.unlink()
        else:
            directory.rmdir()

    mocker.patch("main.rename_files_and_directories", side_effect=simulate_missing_entry)

    with caplog.at_level(logging.INFO):
        main()

    after_files = 0 if removed_kind == "file" else 1
    after_directories = 0 if removed_kind == "directory" else 1
    assert "Antes de la normalización: 1 archivos y 1 directorios" in caplog.text
    assert (
        f"Después de la normalización: {after_files} archivos y "
        f"{after_directories} directorios"
    ) in caplog.text
    assert any(
        record.levelno == logging.WARNING
        and record.getMessage() == (
            "Verificación de conteos: los totales han cambiado "
            f"(archivos: 1 -> {after_files}; directorios: 1 -> {after_directories})"
        )
        for record in caplog.records
    )
    assert "coinciden los totales" not in caplog.text
