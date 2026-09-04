from __future__ import annotations

from pathlib import Path

from ....solver import Solver
from ..utils import (
    read_bodies,
    read_equality_constraints,
    read_mesh_files,
    read_mesh_files_merged,
)


class ClosedLoopRigSolver(Solver):
    """Turns an MJCF model into a JSON rig descriptor for the Unity-native PhysX
    engine's `RigLoader.cs` (in the companion `neural-to-output-unity` repo --
    this repo ships no Unity project or C# source itself, only this generator)
    -- bodies/joints/meshes read verbatim from MuJoCo's own *compiled* model (no
    hand-reimplementation of MJCF's default-class inheritance or orientation
    formats), plus the two things that are genuinely this solver's own job:

    1. Rigging the closed-loop mechanism the same way NVIDIA Isaac Sim's
       official guide does (`DECISIONS.md`'s 2026-09-04 entry, subsection 2) --
       classify each joint as `"actuated"` (driven by a real actuator) or
       `"guide"` (everything else -- Isaac Sim's exact term for a passive joint
       left with zero stiffness/damping so it doesn't fight the loop-closure
       constraint), and package every `<equality><connect>` as a
       `"bridge_constraints"` entry -- the two points a `ConfigurableJoint`
       needs to weld together in `RigLoader.cs`, since `ArticulationBody` alone
       can't express a closed loop (Unity's own docs: "if you need kinematic
       loops, use regular joints").
    2. Optionally merging a second part (e.g. AmazingHand) onto the first's
       (e.g. SO101Arm's) own named site via `attach=` -- see `__init__` --
       mirroring `n2o.robot.simulation.mujoco.simulator.Simulator`'s own
       `attach_hand_to_arm=True`, so both engines describe the identical
       physical rig. Unlike the closed-loop bridge above, welding a hand onto
       an arm's end-effector is a plain rigid parent-child attachment, not a
       kinematic loop -- `RigLoader.cs` needs no changes to render it, since it
       already builds its tree generically off each body's own `"parent"`.

    Mirrors `SO101IKSolver`'s shape: I/O (loading the MJCF) happens once here in
    `__init__`, not inside `solve()` -- `solve()` itself touches no disk, matching
    the `Solver` ABC's "pure computation... no side effects" contract."""

    def __init__(self, mjcf_path, *, attach=None):
        """`attach`, given as `(attach_mjcf_path, site_name, prefix)`, merges a
        second MJCF onto `mjcf_path`'s own named site before extracting the rig
        -- e.g. `(amazing_hand_mjcf, "gripperframe", "hand_")` welds AmazingHand
        onto SO101Arm's gripper site, matching `n2o.robot.simulation.mujoco.
        simulator.ARM_GRIPPER_SITE`/`HAND_PREFIX` exactly (import those rather
        than re-typing the site name/prefix, so the two engines can never
        silently drift onto different attachment points). `None` (default)
        keeps the original single-part behavior unchanged -- `self.model` is
        loaded directly via `MjModel.from_xml_path`, no `MjSpec` merge step."""
        import mujoco

        self.mjcf_path = mjcf_path
        self.attach = attach
        if attach is None:
            self.model = mujoco.MjModel.from_xml_path(str(mjcf_path))
        else:
            attach_mjcf_path, site_name, prefix = attach
            base_spec = mujoco.MjSpec.from_file(str(mjcf_path))
            attach_spec = mujoco.MjSpec.from_file(str(attach_mjcf_path))
            base_spec.attach(attach_spec, prefix=prefix, site=base_spec.site(site_name))
            self.model = base_spec.compile()

    def solve(self) -> dict:
        """Return the full rig descriptor -- no arguments, no disk I/O; the
        caller (see this module's CLI below) decides whether/where to write it."""
        import mujoco

        bodies = read_bodies(self.model)
        actuated_joint_ids = {
            int(self.model.actuator_trnid[a][0])
            for a in range(self.model.nu)
            if mujoco.mjtTrn(self.model.actuator_trntype[a]) == mujoco.mjtTrn.mjTRN_JOINT
        }
        for body in bodies:
            joint = body["joint"]
            if joint is None:
                continue
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint["name"])
            joint["drive"] = "actuated" if jid in actuated_joint_ids else "guide"

        if self.attach is None:
            meshes = read_mesh_files(self.mjcf_path, self.model)
        else:
            meshes = read_mesh_files_merged([self.mjcf_path, self.attach[0]], self.model)

        rig = {
            "schema_version": 1,
            "source_mjcf": Path(self.mjcf_path).name,
            "meshes": meshes,
            "bodies": bodies,
            "bridge_constraints": read_equality_constraints(self.model),
        }
        if self.attach is not None:
            # Presence of this key is itself the "merged rig" signal --
            # rig_json_status() below reads it back the same way it reads
            # source_mjcf.
            rig["attached_mjcf"] = Path(self.attach[0]).name
        return rig


def rig_json_status(rig_json_path, mjcf_path, attached_mjcf_path=None) -> str:
    """`"missing"` / `"stale"` / `"current"` for whether `rig_json_path` (if it
    exists at all) still matches `mjcf_path` (plus `attached_mjcf_path`, for a
    merged arm+hand rig -- see `ClosedLoopRigSolver.__init__`'s `attach=`) --
    reads back the `"source_mjcf"`/`"attached_mjcf"` marker `solve()` itself
    always writes, instead of trusting a rig.json's mere presence or a
    separately-maintained "I made this" flag (fragile -- a third-party
    converter has no reason to set one). A file that isn't valid JSON, or
    doesn't carry this project's own schema at all (`schema_version`/
    `source_mjcf` missing -- e.g. a hand-authored or vendor JSON), is treated
    the same as `"missing"`: there's nothing here we can actually verify, so
    it's never silently accepted as `"current"`.

    Used by `apps/console.py`'s part settings dialog to show a non-blocking
    status next to the "rig.json 재생성" button -- never gates which engines
    are offered (that would create a chicken-and-egg UX: you'd need a rig.json
    to unlock the button that creates one)."""
    import json

    path = Path(rig_json_path)
    if not path.exists():
        return "missing"
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, ValueError):
        return "missing"
    if data.get("schema_version") != 1 or "source_mjcf" not in data:
        return "missing"
    if data["source_mjcf"] != Path(mjcf_path).name:
        return "stale"
    expected_attached = Path(attached_mjcf_path).name if attached_mjcf_path else None
    if data.get("attached_mjcf") != expected_attached:
        return "stale"
    return "current"


def _main():
    """CLI entry point -- run as `python -m n2o.robot.simulation.unity.solver
    <mjcf_path> [-o output.json] [--attach-mjcf ... --attach-site ...]` (via
    `solver/__main__.py`, not this module directly -- running `-m
    ...solver.closed_loop_rig` re-imports a module `solver/__init__.py` already
    imported, which Python warns about)."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Convert an MJCF model into a JSON rig descriptor for "
        "RigLoader.cs (Unity-native PhysX engine)."
    )
    parser.add_argument("mjcf_path", help="Path to the source .xml MJCF file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON path (default: same name as mjcf_path, .json extension, "
        "same directory)",
    )
    parser.add_argument(
        "--attach-mjcf",
        help="Optional second MJCF to merge onto --attach-site (e.g. AmazingHand's "
        "robot.xml welded onto SO101Arm's gripperframe site) -- mirrors "
        "Simulator's own attach_hand_to_arm=True.",
    )
    parser.add_argument(
        "--attach-site",
        help="Site name on mjcf_path to attach --attach-mjcf onto (required with "
        "--attach-mjcf).",
    )
    parser.add_argument(
        "--attach-prefix",
        default="",
        help="Rename prefix for --attach-mjcf's elements once merged (default: none).",
    )
    args = parser.parse_args()

    attach = None
    if args.attach_mjcf:
        if not args.attach_site:
            parser.error("--attach-mjcf requires --attach-site")
        attach = (args.attach_mjcf, args.attach_site, args.attach_prefix)

    output = args.output or str(Path(args.mjcf_path).with_suffix(".json"))
    rig = ClosedLoopRigSolver(args.mjcf_path, attach=attach).solve()
    with open(output, "w") as f:
        json.dump(rig, f, indent=2)
    print(f"wrote {output}")
