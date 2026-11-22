import json
from pathlib import Path
from unittest.mock import mock_open

from pytest_mock import MockerFixture

from core.structure_storage import save_structure_directories


def test_save_structure_directories(mocker: MockerFixture) -> None:
    config_path = Path("/mock/structure.json")
    mocker.patch.object(Path, "exists", return_value=True)

    old_data = '{"old_folder": {"file.txt": null}}'
    mocked_open = mock_open(read_data=old_data)
    mocker.patch("builtins.open", mocked_open)

    new_structure = {"new_folder": {"doc.txt": None}}

    save_structure_directories(config_path, new_structure)

    # Verificar que se intentó escribir la combinación
    expected_data = {
        "old_folder": {"file.txt": None},
        "new_folder": {"doc.txt": None}
    }

    # Capturar la data que se intentó escribir
    handle = mocked_open()
    written = "".join(call.args[0] for call in handle.write.call_args_list)

    # Verificar formato (indent=4)
    assert json.loads(written) == expected_data
    assert "    " in written # Verifica la indentación
