from __future__ import annotations

import xml.etree.ElementTree as ET


def read_bodies(model) -> list[dict]:
    """One entry per real body in `model` (skips body 0, MuJoCo's own implicit
    `"world"`), each carrying its pos/quat relative to its parent (already
    resolved by MuJoCo's own compiler -- no default-class/orientation-format
    handling needed here, unlike hand-parsing raw MJCF would require), its single
    joint (if any -- see below), and its visual mesh geoms.

    Raises if a body ever has more than one joint: neither the SO-101 arm nor
    AmazingHand MJCF has this, and silently keeping only the first would produce
    a rig missing real degrees of freedom instead of failing loudly.

    Mesh geoms are deduped by `(dataid, rounded pos, rounded quat)` rather than
    by hardcoding `geom_group == 2` (the "visual" convention these two MJCF files
    happen to use) -- a duplicate at the identical mesh/pose is almost certainly
    the same onshape-to-robot visual+collision pair, regardless of what group
    number a given MJCF author chose."""
    bodies = []
    for i in range(1, model.nbody):
        parent_id = model.body_parentid[i]
        parent = None if parent_id == 0 else model.body(parent_id).name

        jntnum = model.body_jntnum[i]
        if jntnum > 1:
            raise ValueError(
                f"body {model.body(i).name!r} has {jntnum} joints -- only 0 or 1"
                " is supported"
            )
        joint = _read_joint(model, model.body_jntadr[i]) if jntnum == 1 else None

        bodies.append(
            {
                "name": model.body(i).name,
                "parent": parent,
                "pos": model.body_pos[i].tolist(),
                "quat": model.body_quat[i].tolist(),
                "joint": joint,
                "meshes": _read_meshes(model, i),
            }
        )
    return bodies


_JOINT_TYPE_NAMES = {
    0: "free",
    1: "ball",
    2: "slide",
    3: "hinge",
}


def _read_joint(model, jid: int) -> dict:
    jtype = _JOINT_TYPE_NAMES[int(model.jnt_type[jid])]
    if jtype == "free":
        raise NotImplementedError(
            f"joint {model.joint(jid).name!r} is a free joint -- not supported"
            " (neither target model uses one)"
        )
    limited = bool(model.jnt_limited[jid])
    return {
        "name": model.joint(jid).name,
        "type": jtype,
        "axis": model.jnt_axis[jid].tolist() if jtype in ("hinge", "slide") else None,
        "pos": model.jnt_pos[jid].tolist(),
        "limited": limited,
        "range": model.jnt_range[jid].tolist() if limited else None,
    }


def _read_meshes(model, body_id: int) -> list[dict]:
    import mujoco

    meshes = []
    seen = set()
    start = model.body_geomadr[body_id]
    for g in range(start, start + model.body_geomnum[body_id]):
        if model.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        pos = model.geom_pos[g].tolist()
        quat = model.geom_quat[g].tolist()
        key = (
            int(model.geom_dataid[g]),
            tuple(round(v, 9) for v in pos),
            tuple(round(v, 9) for v in quat),
        )
        if key in seen:
            continue
        seen.add(key)
        meshes.append({"mesh": int(model.geom_dataid[g]), "pos": pos, "quat": quat})
    return meshes


def _read_asset_mesh_files(mjcf_path) -> list[str]:
    """One file's own `<asset>` block's `<mesh file="...">` declaration order,
    with no check against any compiled model -- the check (against a specific
    model's `nmesh`) is each caller's own job below, since a merged model (see
    `read_mesh_files_merged()`) has more meshes than any single source file
    declares."""
    root = ET.parse(mjcf_path).getroot()
    asset = root.find("asset")
    return [mesh.get("file") for mesh in asset.findall("mesh")] if asset is not None else []


def read_mesh_files(mjcf_path, model) -> list[str]:
    """Filenames for `model`'s compiled meshes, index-matched to
    `model.geom_dataid`/`read_bodies()`'s own `"mesh"` indices.

    Reads only the `<asset>` block's `<mesh file="...">` declaration order via
    plain `xml.etree.ElementTree` -- no MJCF semantic parsing (defaults,
    includes) needed, since asset declaration order is exactly `MjModel`'s own
    mesh index order. Self-checks that count against `model.nmesh` and raises if
    they disagree, which would mean the `<asset>` block isn't actually in
    `mjcf_path` itself (e.g. pulled in via `<include>` from another file) --
    silently returning a misaligned list would be worse than failing here."""
    files = _read_asset_mesh_files(mjcf_path)
    if len(files) != model.nmesh:
        raise ValueError(
            f"found {len(files)} <mesh> declarations in {mjcf_path!r}'s own <asset>"
            f" block but the compiled model has {model.nmesh} meshes -- likely"
            " pulled in via <include> from a different file"
        )
    return files


def read_mesh_files_merged(mjcf_paths, model) -> list[str]:
    """Like `read_mesh_files()`, but for a `model` compiled from more than one
    MJCF merged together (see `ClosedLoopRigSolver`'s `attach=` option, mirroring
    `n2o.robot.simulation.mujoco.simulator.Simulator`'s own `attach_hand_to_arm=
    True` merge). `mujoco.MjSpec.attach()` appends the attached spec's own
    elements (bodies, meshes, ...) after the base spec's, in the same relative
    order each one's own `<asset>` block declares -- so concatenating each
    file's own declaration order, in the same order they were attached
    (`mjcf_paths[0]` first), reproduces the compiled model's real mesh index
    order. Self-checks the combined count against `model.nmesh`, same reasoning
    as `read_mesh_files()`."""
    files = []
    for path in mjcf_paths:
        files.extend(_read_asset_mesh_files(path))
    if len(files) != model.nmesh:
        raise ValueError(
            f"found {len(files)} total <mesh> declarations across {list(mjcf_paths)!r}"
            f" but the compiled model has {model.nmesh} meshes"
        )
    return files


def read_equality_constraints(model) -> list[dict]:
    """Every `<equality><connect>` in `model`, as the two sites it welds together.

    Only the site-referencing form (`eq_objtype == mjOBJ_SITE`) is supported --
    the only form either target MJCF uses. Raises on any other equality type or
    the body-anchor form of `connect` rather than silently dropping it, since
    dropping a real constraint would produce a rig missing part of its actual
    kinematics with no indication anything was lost."""
    import mujoco

    constraints = []
    for e in range(model.neq):
        eq_type = mujoco.mjtEq(model.eq_type[e])
        if eq_type != mujoco.mjtEq.mjEQ_CONNECT:
            raise NotImplementedError(f"unsupported equality constraint type: {eq_type.name}")
        if mujoco.mjtObj(model.eq_objtype[e]) != mujoco.mjtObj.mjOBJ_SITE:
            raise NotImplementedError(
                "only site-based <connect> constraints are supported (found a"
                " body-anchor one)"
            )
        constraints.append(
            {
                "type": "connect",
                "site1": _read_site(model, model.eq_obj1id[e]),
                "site2": _read_site(model, model.eq_obj2id[e]),
            }
        )
    return constraints


def _read_site(model, site_id: int) -> dict:
    return {
        "name": model.site(site_id).name,
        "body": model.body(model.site_bodyid[site_id]).name,
        "pos": model.site_pos[site_id].tolist(),
    }
