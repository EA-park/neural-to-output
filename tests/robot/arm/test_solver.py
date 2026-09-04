import numpy as np
import pytest

pytest.importorskip("mujoco")

from n2o.robot.arm.so101.lerobot_robot_so101_5dof.solver import (
    ARM_JOINTS,
    SO101IKSolver,
    mj_rad_to_real_deg,
    real_deg_to_mj_rad,
)


def test_solve_converges_close_to_the_target():
    solver = SO101IKSolver()
    # elbow_flex=40 puts the gripperframe's x inside the solver's default x_range
    # (0.26-0.34m) to start with, so dx isn't immediately clamped away below.
    current_deg = dict(dict.fromkeys(ARM_JOINTS, 0.0), elbow_flex=40.0)

    target_deg, residual = solver.solve(current_deg, dx=0.02, dy=0.0)

    assert residual < 1e-2
    new_xyz = solver.gripperframe_xyz(target_deg)
    start_xyz = solver.gripperframe_xyz(current_deg)
    assert new_xyz[0] == pytest.approx(start_xyz[0] + 0.02, abs=1e-2)


def test_solve_only_changes_ik_joints_not_wrist():
    solver = SO101IKSolver()
    current_deg = dict.fromkeys(ARM_JOINTS, 0.0)

    target_deg, _residual = solver.solve(current_deg, dx=0.02, dy=0.01)

    assert target_deg["wrist_flex"] == pytest.approx(current_deg["wrist_flex"])
    assert target_deg["wrist_roll"] == pytest.approx(current_deg["wrist_roll"])


def test_solve_clamps_the_target_into_the_configured_range():
    solver = SO101IKSolver(x_range=(0.26, 0.34), y_range=(-0.10, 0.10), z=0.15)
    current_deg = dict.fromkeys(ARM_JOINTS, 0.0)

    target_deg, _residual = solver.solve(current_deg, dx=10.0, dy=0.0)

    new_xyz = solver.gripperframe_xyz(target_deg)
    assert new_xyz[0] <= solver.x_range[1] + 1e-2


def test_real_deg_to_mj_rad_and_back_round_trip():
    deg_by_joint = dict.fromkeys(ARM_JOINTS, 12.5)

    round_tripped = mj_rad_to_real_deg(real_deg_to_mj_rad(deg_by_joint))

    for joint in ARM_JOINTS:
        assert round_tripped[joint] == pytest.approx(deg_by_joint[joint])


def test_real_deg_to_mj_rad_matches_plain_radians():
    deg_by_joint = {"shoulder_pan": 90.0}

    rad_by_joint = real_deg_to_mj_rad(deg_by_joint)

    assert rad_by_joint["shoulder_pan"] == pytest.approx(np.radians(90.0))
