import struct

import pytest

pytest.importorskip("mujoco")

import mujoco

from n2o.robot.simulation.unity.utils.mjcf_reader import (
    read_bodies,
    read_equality_constraints,
    read_mesh_files,
    read_mesh_files_merged,
)

_TETRAHEDRON_VERTICES = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
_TETRAHEDRON_FACES = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]


def _stub_stl_bytes() -> bytes:
    """A minimal valid binary STL (a tetrahedron) -- MuJoCo's mesh loader needs
    at least 4 non-coplanar vertices to build a convex hull, so a single
    triangle isn't enough."""
    facets = b""
    for face in _TETRAHEDRON_FACES:
        verts = [coord for v in face for coord in _TETRAHEDRON_VERTICES[v]]
        facets += struct.pack("<12fH", 0, 0, 0, *verts, 0)
    return b"\x00" * 80 + struct.pack("<I", len(_TETRAHEDRON_FACES)) + facets


def _write_stub_stl(path):
    path.write_bytes(_stub_stl_bytes())

_HINGE_CHAIN_XML = """
<mujoco>
  <compiler angle="radian"/>
  <worldbody>
    <body name="base" pos="0 0 0">
      <geom type="sphere" size="0.01"/>
      <body name="arm" pos="0.1 0 0" quat="1 0 0 0">
        <joint name="hinge1" type="hinge" axis="0 0 1" range="-1 1" limited="true"/>
        <geom type="sphere" size="0.01"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""

_BALL_JOINT_XML = """
<mujoco>
  <worldbody>
    <body name="base">
      <body name="wrist">
        <joint name="ball1" type="ball"/>
        <geom type="sphere" size="0.01"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""

_MULTI_JOINT_BODY_XML = """
<mujoco>
  <worldbody>
    <body name="base">
      <body name="bad">
        <joint name="j1" type="hinge" axis="1 0 0"/>
        <joint name="j2" type="hinge" axis="0 1 0"/>
        <geom type="sphere" size="0.01"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""

_FREE_JOINT_XML = """
<mujoco>
  <worldbody>
    <body name="floating">
      <joint name="free1" type="free"/>
      <geom type="sphere" size="0.01"/>
    </body>
  </worldbody>
</mujoco>
"""

_VISUAL_COLLISION_DUP_XML = """
<mujoco>
  <asset>
    <mesh name="part" vertex="0 0 0  1 0 0  0 1 0  0 0 1" face="0 1 2  0 1 3  0 2 3  1 2 3"/>
  </asset>
  <worldbody>
    <body name="base">
      <geom type="mesh" mesh="part" pos="0 0 0" quat="1 0 0 0" group="2" contype="0"/>
      <geom type="mesh" mesh="part" pos="0 0 0" quat="1 0 0 0" group="3"/>
    </body>
  </worldbody>
</mujoco>
"""

_EQUALITY_CONNECT_XML = """
<mujoco>
  <worldbody>
    <body name="branch_a">
      <joint name="ja" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
      <site name="site_a" pos="0.1 0 0"/>
    </body>
    <body name="branch_b">
      <joint name="jb" type="hinge" axis="0 0 1"/>
      <geom type="sphere" size="0.01"/>
      <site name="site_b" pos="-0.1 0 0"/>
    </body>
  </worldbody>
  <equality>
    <connect site1="site_a" site2="site_b"/>
  </equality>
</mujoco>
"""


def test_read_bodies_reports_hinge_joint_and_parent():
    model = mujoco.MjModel.from_xml_string(_HINGE_CHAIN_XML)

    bodies = read_bodies(model)

    base, arm = bodies
    assert base["name"] == "base"
    assert base["parent"] is None
    assert base["joint"] is None
    assert arm["name"] == "arm"
    assert arm["parent"] == "base"
    assert arm["joint"]["name"] == "hinge1"
    assert arm["joint"]["type"] == "hinge"
    assert arm["joint"]["axis"] == [0.0, 0.0, 1.0]
    assert arm["joint"]["limited"] is True
    assert arm["joint"]["range"] == pytest.approx([-1.0, 1.0])


def test_read_bodies_reports_ball_joint_with_no_axis():
    model = mujoco.MjModel.from_xml_string(_BALL_JOINT_XML)

    bodies = read_bodies(model)

    wrist = next(b for b in bodies if b["name"] == "wrist")
    assert wrist["joint"]["type"] == "ball"
    assert wrist["joint"]["axis"] is None


def test_read_bodies_rejects_a_body_with_more_than_one_joint():
    model = mujoco.MjModel.from_xml_string(_MULTI_JOINT_BODY_XML)

    with pytest.raises(ValueError, match="2 joints"):
        read_bodies(model)


def test_read_bodies_rejects_a_free_joint():
    model = mujoco.MjModel.from_xml_string(_FREE_JOINT_XML)

    with pytest.raises(NotImplementedError, match="free joint"):
        read_bodies(model)


def test_read_bodies_dedupes_visual_and_collision_copies_of_the_same_mesh():
    model = mujoco.MjModel.from_xml_string(_VISUAL_COLLISION_DUP_XML)

    bodies = read_bodies(model)

    base = bodies[0]
    assert len(base["meshes"]) == 1


def test_read_mesh_files_matches_asset_declaration_order(tmp_path):
    xml = """
    <mujoco>
      <asset>
        <mesh file="first.stl"/>
        <mesh file="second.stl"/>
      </asset>
      <worldbody>
        <body name="base">
          <geom type="mesh" mesh="first"/>
          <geom type="mesh" mesh="second"/>
        </body>
      </worldbody>
    </mujoco>
    """
    _write_stub_stl(tmp_path / "first.stl")
    _write_stub_stl(tmp_path / "second.stl")
    mjcf_path = tmp_path / "model.xml"
    mjcf_path.write_text(xml)
    model = mujoco.MjModel.from_xml_path(str(mjcf_path))

    assert read_mesh_files(str(mjcf_path), model) == ["first.stl", "second.stl"]


def test_read_mesh_files_raises_if_asset_block_is_missing(tmp_path):
    xml = """
    <mujoco>
      <asset>
        <mesh file="only.stl"/>
      </asset>
      <worldbody>
        <body name="base">
          <geom type="mesh" mesh="only"/>
        </body>
      </worldbody>
    </mujoco>
    """
    _write_stub_stl(tmp_path / "only.stl")
    mjcf_path = tmp_path / "model.xml"
    mjcf_path.write_text(xml)
    model = mujoco.MjModel.from_xml_path(str(mjcf_path))
    other_path = tmp_path / "empty.xml"
    other_path.write_text("<mujoco><worldbody/></mujoco>")

    with pytest.raises(ValueError, match="found 0"):
        read_mesh_files(str(other_path), model)


def test_read_mesh_files_merged_concatenates_in_attach_order(tmp_path):
    _write_stub_stl(tmp_path / "first.stl")
    _write_stub_stl(tmp_path / "second.stl")
    base_xml = """
    <mujoco>
      <asset><mesh file="first.stl"/></asset>
      <worldbody>
        <body name="base"><geom type="mesh" mesh="first"/></body>
      </worldbody>
    </mujoco>
    """
    attach_xml = """
    <mujoco>
      <asset><mesh file="second.stl"/></asset>
      <worldbody>
        <body name="attached"><geom type="mesh" mesh="second"/></body>
      </worldbody>
    </mujoco>
    """
    base_path = tmp_path / "base.xml"
    base_path.write_text(base_xml)
    attach_path = tmp_path / "attach.xml"
    attach_path.write_text(attach_xml)

    base_spec = mujoco.MjSpec.from_file(str(base_path))
    attach_spec = mujoco.MjSpec.from_file(str(attach_path))
    base_spec.attach(attach_spec, prefix="x_", frame=base_spec.worldbody.add_frame())
    model = base_spec.compile()

    assert read_mesh_files_merged([str(base_path), str(attach_path)], model) == [
        "first.stl",
        "second.stl",
    ]


def test_read_mesh_files_merged_raises_on_count_mismatch(tmp_path):
    _write_stub_stl(tmp_path / "first.stl")
    _write_stub_stl(tmp_path / "second.stl")
    base_xml = """
    <mujoco>
      <asset><mesh file="first.stl"/></asset>
      <worldbody>
        <body name="base"><geom type="mesh" mesh="first"/></body>
      </worldbody>
    </mujoco>
    """
    attach_xml = """
    <mujoco>
      <asset><mesh file="second.stl"/></asset>
      <worldbody>
        <body name="attached"><geom type="mesh" mesh="second"/></body>
      </worldbody>
    </mujoco>
    """
    base_path = tmp_path / "base.xml"
    base_path.write_text(base_xml)
    attach_path = tmp_path / "attach.xml"
    attach_path.write_text(attach_xml)

    base_spec = mujoco.MjSpec.from_file(str(base_path))
    attach_spec = mujoco.MjSpec.from_file(str(attach_path))
    base_spec.attach(attach_spec, prefix="x_", frame=base_spec.worldbody.add_frame())
    model = base_spec.compile()

    with pytest.raises(ValueError, match="found 1 total"):
        read_mesh_files_merged([str(base_path)], model)


def test_read_equality_constraints_reads_both_sites():
    model = mujoco.MjModel.from_xml_string(_EQUALITY_CONNECT_XML)

    constraints = read_equality_constraints(model)

    assert len(constraints) == 1
    constraint = constraints[0]
    assert constraint["type"] == "connect"
    assert constraint["site1"] == {
        "name": "site_a",
        "body": "branch_a",
        "pos": pytest.approx([0.1, 0.0, 0.0]),
    }
    assert constraint["site2"] == {
        "name": "site_b",
        "body": "branch_b",
        "pos": pytest.approx([-0.1, 0.0, 0.0]),
    }
