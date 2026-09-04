import json
from pathlib import Path

import pytest

pytest.importorskip("mujoco")

from n2o.robot.simulation.unity.solver import ClosedLoopRigSolver, rig_json_status

_MIXED_DRIVE_XML = """
<mujoco>
  <worldbody>
    <body name="motor_link">
      <joint name="motor_joint" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
      <site name="site_a" pos="0.1 0 0"/>
    </body>
    <body name="passive_link">
      <joint name="passive_joint" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
      <site name="site_b" pos="-0.1 0 0"/>
    </body>
  </worldbody>
  <actuator>
    <position name="a" joint="motor_joint"/>
  </actuator>
  <equality>
    <connect site1="site_a" site2="site_b"/>
  </equality>
</mujoco>
"""

_ALL_ACTUATED_OPEN_CHAIN_XML = """
<mujoco>
  <worldbody>
    <body name="link1">
      <joint name="j1" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
      <body name="link2">
        <joint name="j2" type="hinge" axis="0 0 1"/>
        <geom type="sphere" size="0.01"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="a1" joint="j1"/>
    <position name="a2" joint="j2"/>
  </actuator>
</mujoco>
"""


_ATTACH_BASE_XML = """
<mujoco>
  <worldbody>
    <body name="link1">
      <joint name="j1" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
      <site name="tip"/>
    </body>
  </worldbody>
  <actuator>
    <position name="a1" joint="j1"/>
  </actuator>
</mujoco>
"""

_ATTACH_HAND_XML = """
<mujoco>
  <worldbody>
    <body name="finger">
      <joint name="finger_joint" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
    </body>
  </worldbody>
  <actuator>
    <position name="fa" joint="finger_joint"/>
  </actuator>
</mujoco>
"""


def _write_mjcf(tmp_path, xml, name="model.xml"):
    path = tmp_path / name
    path.write_text(xml)
    return path


def test_solve_classifies_actuated_vs_guide_and_packages_bridge_constraint(tmp_path):
    mjcf_path = _write_mjcf(tmp_path, _MIXED_DRIVE_XML)

    rig = ClosedLoopRigSolver(mjcf_path).solve()

    drives = {b["name"]: b["joint"]["drive"] for b in rig["bodies"]}
    assert drives["motor_link"] == "actuated"
    assert drives["passive_link"] == "guide"
    assert len(rig["bridge_constraints"]) == 1
    assert rig["bridge_constraints"][0]["site1"]["name"] == "site_a"
    assert rig["bridge_constraints"][0]["site2"]["name"] == "site_b"


def test_solve_handles_the_all_actuated_zero_equality_degenerate_case(tmp_path):
    """The arm's own real shape: every joint driven, no closed loop at all --
    the schema's degenerate path, easy to leave accidentally untested if only
    the hand-shaped (rich) fixture above is covered."""
    mjcf_path = _write_mjcf(tmp_path, _ALL_ACTUATED_OPEN_CHAIN_XML)

    rig = ClosedLoopRigSolver(mjcf_path).solve()

    assert rig["bridge_constraints"] == []
    joints = [b["joint"] for b in rig["bodies"] if b["joint"]]
    assert len(joints) == 2
    assert all(j["drive"] == "actuated" for j in joints)


def test_solve_returns_the_expected_top_level_schema_shape(tmp_path):
    mjcf_path = _write_mjcf(tmp_path, _ALL_ACTUATED_OPEN_CHAIN_XML)

    rig = ClosedLoopRigSolver(mjcf_path).solve()

    assert rig["schema_version"] == 1
    assert rig["source_mjcf"] == mjcf_path.name
    assert rig["meshes"] == []
    assert isinstance(rig["bodies"], list) and len(rig["bodies"]) == 2


def test_solve_without_attach_has_no_attached_mjcf_key(tmp_path):
    mjcf_path = _write_mjcf(tmp_path, _ALL_ACTUATED_OPEN_CHAIN_XML)

    rig = ClosedLoopRigSolver(mjcf_path).solve()

    assert "attached_mjcf" not in rig


def test_solve_with_attach_merges_a_second_mjcf_onto_the_named_site(tmp_path):
    base_path = _write_mjcf(tmp_path, _ATTACH_BASE_XML, name="base.xml")
    hand_path = _write_mjcf(tmp_path, _ATTACH_HAND_XML, name="hand.xml")

    rig = ClosedLoopRigSolver(base_path, attach=(hand_path, "tip", "hand_")).solve()

    names = {b["name"] for b in rig["bodies"]}
    assert "link1" in names
    assert "hand_finger" in names
    attached_body = next(b for b in rig["bodies"] if b["name"] == "hand_finger")
    assert attached_body["parent"] == "link1"
    assert attached_body["joint"]["drive"] == "actuated"
    assert rig["source_mjcf"] == base_path.name
    assert rig["attached_mjcf"] == hand_path.name


def test_solve_with_attach_merges_real_bundled_arm_and_hand_mjcf():
    """End-to-end against the actual SO101Arm/AmazingHand MJCF (not synthetic
    fixtures) -- the merged rig's body/mesh counts should be exactly the sum of
    each part's own standalone rig, and the hand's root body should land as a
    child of the arm's own gripper site's body."""
    import inspect

    from n2o.robot.arm.so101 import SO101Arm
    from n2o.robot.hand.amazing_hand_right import AmazingHand
    from n2o.robot.simulation.mujoco.simulator import ARM_GRIPPER_SITE, HAND_PREFIX

    arm_mjcf = Path(inspect.getfile(SO101Arm)).parent / "mjcf" / "so101_new_calib.xml"
    hand_mjcf = Path(inspect.getfile(AmazingHand)).parent / "mjcf" / "robot.xml"

    arm_only = ClosedLoopRigSolver(arm_mjcf).solve()
    hand_only = ClosedLoopRigSolver(hand_mjcf).solve()
    merged = ClosedLoopRigSolver(
        arm_mjcf, attach=(hand_mjcf, ARM_GRIPPER_SITE, HAND_PREFIX)
    ).solve()

    assert len(merged["bodies"]) == len(arm_only["bodies"]) + len(hand_only["bodies"])
    assert len(merged["meshes"]) == len(arm_only["meshes"]) + len(hand_only["meshes"])
    assert len(merged["bridge_constraints"]) == len(hand_only["bridge_constraints"])
    assert merged["attached_mjcf"] == hand_mjcf.name

    hand_root_names = {
        f"{HAND_PREFIX}{b['name']}" for b in hand_only["bodies"] if b["parent"] is None
    }
    merged_by_name = {b["name"]: b for b in merged["bodies"]}
    assert hand_root_names <= merged_by_name.keys()
    assert all(merged_by_name[name]["parent"] is not None for name in hand_root_names)


def test_rig_json_status_missing_when_file_does_not_exist(tmp_path):
    assert rig_json_status(tmp_path / "nope.json", "model.xml") == "missing"


def test_rig_json_status_missing_when_not_our_schema(tmp_path):
    path = tmp_path / "rig.json"
    path.write_text(json.dumps({"hello": "world"}))

    assert rig_json_status(path, "model.xml") == "missing"


def test_rig_json_status_current_when_source_matches(tmp_path):
    mjcf_path = _write_mjcf(tmp_path, _ALL_ACTUATED_OPEN_CHAIN_XML)
    rig_path = tmp_path / "rig.json"
    rig_path.write_text(json.dumps(ClosedLoopRigSolver(mjcf_path).solve()))

    assert rig_json_status(rig_path, mjcf_path) == "current"


def test_rig_json_status_stale_when_source_mjcf_differs(tmp_path):
    mjcf_path = _write_mjcf(tmp_path, _ALL_ACTUATED_OPEN_CHAIN_XML)
    other_path = tmp_path / "other.xml"
    rig_path = tmp_path / "rig.json"
    rig_path.write_text(json.dumps(ClosedLoopRigSolver(mjcf_path).solve()))

    assert rig_json_status(rig_path, other_path) == "stale"


def test_rig_json_status_merged_rig(tmp_path):
    base_path = _write_mjcf(tmp_path, _ATTACH_BASE_XML, name="base.xml")
    hand_path = _write_mjcf(tmp_path, _ATTACH_HAND_XML, name="hand.xml")
    rig_path = tmp_path / "rig.json"
    rig = ClosedLoopRigSolver(base_path, attach=(hand_path, "tip", "hand_")).solve()
    rig_path.write_text(json.dumps(rig))

    assert rig_json_status(rig_path, base_path, hand_path) == "current"
    # Omitting the expected attached_mjcf_path means "expect a standalone rig" --
    # a merged one on disk is stale relative to that expectation.
    assert rig_json_status(rig_path, base_path) == "stale"
