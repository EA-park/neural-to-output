import pytest

pytest.importorskip("lerobot")

from n2o.robot.arm.so101_real import connect_so101


def test_raises_a_clear_error_without_a_calibration_file(tmp_path):
    with pytest.raises(RuntimeError, match="lerobot-calibrate"):
        connect_so101(
            "/dev/fake",
            id="test_calibration_never_exists",
            calibration_dir=tmp_path,
        )
