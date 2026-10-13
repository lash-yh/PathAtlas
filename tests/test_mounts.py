from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from core.mounts import find_ssd_mount_point


def test_find_ssd_mount_point(mocker: MockerFixture) -> None:
    # Usar mocking para psutil.disk_partitions
    mock_partitions = mocker.patch("psutil.disk_partitions")

    # Configurar mock data
    part1 = MagicMock()
    part1.mountpoint = "/mnt/HDD"
    part2 = MagicMock()
    part2.mountpoint = "/mnt/MyData_SSD"

    mock_partitions.return_value = [part1, part2]

    # Validar que identifique correctamente el punto de montaje basado en el sufijo
    result = find_ssd_mount_point("SSD")
    assert result == Path("/mnt/MyData_SSD")

    # Validar caso de error sin etiqueta
    with pytest.raises(ValueError, match="label_ssd is empty"):
        find_ssd_mount_point("")

    # Validar que retorna None cuando no encuentra la etiqueta
    result_not_found = find_ssd_mount_point("NVME")
    assert result_not_found is None
