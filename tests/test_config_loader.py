import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from core.config_loader import load_config


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    path.write_text('{"mount_point_label": "SSD", "ignore": [".git", "Carpeta Ñ"]}', encoding="utf-8")
    return path


def test_load_and_repeated_queries_open_and_parse_once(config_path: Path, mocker: MockerFixture) -> None:
    opened = mocker.spy(Path, "open")
    parsed = mocker.spy(json, "load")
    config = load_config(config_path)
    for _ in range(10):
        assert config["mount_point_label"] == "SSD"
        assert config["ignore"] == [".git", "Carpeta Ñ"]
        assert config.get("missing") is None
    opened.assert_called_once_with(config_path, 'r', encoding='utf-8')
    parsed.assert_called_once()
    assert parsed.call_args.args[0].closed


def test_loaded_config_survives_file_changes_and_deletion(config_path: Path) -> None:
    config = load_config(config_path)
    config_path.write_text('{"mount_point_label": "OTHER", "ignore": []}', encoding="utf-8")
    assert config["mount_point_label"] == "SSD"
    config_path.unlink()
    assert config["ignore"] == [".git", "Carpeta Ñ"]


def test_explicit_reload_reads_current_file_and_has_no_global_cache(config_path: Path, mocker: MockerFixture) -> None:
    parsed = mocker.spy(json, "load")
    first = load_config(config_path)
    config_path.write_text('{"mount_point_label": "OTHER", "ignore": []}', encoding="utf-8")
    second = load_config(config_path)
    assert first == {"mount_point_label": "SSD", "ignore": [".git", "Carpeta Ñ"]}
    assert second == {"mount_point_label": "OTHER", "ignore": []}
    second["ignore"].append("new")
    assert first["ignore"] == [".git", "Carpeta Ñ"]
    assert parsed.call_count == 2


def test_optional_keys_and_comments(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"_comment": "documentación"}', encoding="utf-8")
    assert load_config(path) == {"mount_point_label": None, "ignore": []}


@pytest.mark.parametrize("data", [
    [], None, "text", 123,
    {"ignore": ".git"}, {"ignore": [".git", 123]}, {"ignore": None},
    {"mount_point_label": 123}, {"mount_point_label": ""}, {"mount_point_label": "  "},
])
def test_invalid_schema_is_rejected(tmp_path: Path, data: object) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_config(path)


def test_missing_file_has_consistent_error(tmp_path: Path) -> None:
    for _ in range(2):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "missing.json")


def test_permission_error_is_propagated(tmp_path: Path, mocker: MockerFixture) -> None:
    opened = mocker.patch.object(Path, "open", side_effect=PermissionError("denied"))
    with pytest.raises(PermissionError):
        load_config(tmp_path / "config.json")
    opened.assert_called_once()


def test_invalid_utf8_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        load_config(path)


def test_json_content_is_read_once_then_queries_do_not_read(mocker: MockerFixture) -> None:
    opened = mocker.mock_open(read_data='{"mount_point_label": "SSD", "ignore": [".git"]}')
    mocker.patch.object(Path, "open", opened)
    config = load_config(Path("config.json"))
    opened.assert_called_once_with('r', encoding='utf-8')
    handle = opened.return_value
    handle.read.assert_called_once_with()
    for _ in range(10):
        assert config["ignore"] == [".git"]
        assert config["mount_point_label"] == "SSD"
    handle.read.assert_called_once_with()
