import threading
from pathlib import Path

from ._mujoco_model import _MujocoModel
from .viewer import enable_live_view

_ASSETS = Path(__file__).parent / "assets"
_ARM_SCENE = _ASSETS / "so101" / "mjcf" / "scene.xml"
_HAND_SCENE = _ASSETS / "amazing_hand_right" / "mjcf" / "demo_scene.xml"
# The bare robot (no floor/skybox/lights of its own) -- used instead of
# `_HAND_SCENE` whenever the hand is merged alongside the arm into one spec, so the
# combined scene doesn't end up with two floors/skyboxes. `_HAND_SCENE`'s own
# ground-plane geom would also fail to compile once welded under the arm's (moving)
# gripper body -- MuJoCo only allows a plane geom in a static body.
_HAND_ROBOT = _ASSETS / "amazing_hand_right" / "mjcf" / "robot.xml"

_ARM_GRIPPER_SITE = "gripperframe"
# Where the hand sits when it's in the same scene/window as the arm but not welded
# to it -- just off to the side so it doesn't spawn on top of the arm's base.
_HAND_STANDALONE_OFFSET = (0.3, 0.0, 0.0)
_HAND_PREFIX = "hand_"
# `AmazingHand.GESTURES` pose entries (`src/n2o/robot/hand/amazing_hand.py`) are
# 8-length [index_m1, index_m2, middle_m1, middle_m2, ring_m1, ring_m2, thumb_m1,
# thumb_m2] lists with no names attached -- this is the actuator name each position
# corresponds to in `_HAND_ROBOT`/`_HAND_SCENE` (`robot.xml`'s own `<actuator>` order).
_HAND_ACTUATORS = (
    "finger1_motor1",
    "finger1_motor2",
    "finger2_motor1",
    "finger2_motor2",
    "finger3_motor1",
    "finger3_motor2",
    "finger4_motor1",
    "finger4_motor2",
)


class Simulator:
    """Visualizes `Part.goal()` targets in MuJoCo -- what `Robot.router()` calls in
    `ControllerType.SIMULATION` mode when `robot.simulator` is set. Independent from
    the real `Part` classes (`SO101Arm`/`AmazingHand`): those only ever compute
    targets via `goal()`, this is what actually drives a physics model with them.

    Every part passed to `parts` shares one `_MujocoModel` (one MJCF spec, one
    window) -- `Robot.router()` dispatches "arm"/"hand" concurrently on separate
    threads, but `Simulator.drive()` itself serializes access to that shared
    physics world (`self._physics_lock`) since a single `mujoco.MjData` can't be
    stepped from two threads at once, unlike the old one-`_MujocoModel`-per-part
    design.

    `drive()` never touches a GL context (safe to call headless/in CI); a viewer
    window only opens if `launch_viewer()` is called explicitly.
    """

    def __init__(self, parts=("arm",), *, attach_hand_to_arm=False):
        parts = tuple(parts)
        if not parts or any(part not in ("arm", "hand") for part in parts):
            raise ValueError(f"parts must be a non-empty subset of arm/hand: {parts!r}")
        self._parts = parts
        self._attach_hand_to_arm = attach_hand_to_arm
        # "arm" is always the base spec (unprefixed names); "hand" is only prefixed
        # once it's merged alongside the arm into that same spec -- solo, it keeps
        # its own bare names.
        self._prefixes = {"arm": "", "hand": _HAND_PREFIX if len(parts) > 1 else ""}
        self._physics_lock = threading.Lock()
        self._model = self._build_model()

    @property
    def model(self):
        """The shared `mujoco.MjModel` -- public so notebooks/tests can read back
        state (`jnt_range`, `qpos`, ...) without reaching into a private attribute."""
        return self._model.model

    @property
    def data(self):
        """The shared `mujoco.MjData` -- see `model` above."""
        return self._model.data

    def actuator_name(self, part, name):
        """The actual (possibly `hand_`-prefixed) actuator/joint name `part`'s
        `name` was compiled under in the shared model -- e.g.
        `actuator_name("hand", "finger1_motor1")`. Needed because merging the hand
        into the arm's spec (see `_build_model()`) renames every one of its
        elements with `_HAND_PREFIX`."""
        return self._prefixes[part] + name

    def _build_model(self):
        import mujoco

        if len(self._parts) == 1:
            (part,) = self._parts
            scene = _ARM_SCENE if part == "arm" else _HAND_SCENE
            return _MujocoModel(mujoco.MjModel.from_xml_path(str(scene)))

        arm_spec = mujoco.MjSpec.from_file(str(_ARM_SCENE))
        hand_spec = mujoco.MjSpec.from_file(str(_HAND_ROBOT))
        if self._attach_hand_to_arm:
            site = arm_spec.site(_ARM_GRIPPER_SITE)
            arm_spec.attach(hand_spec, prefix=_HAND_PREFIX, site=site)
        else:
            frame = arm_spec.worldbody.add_frame(pos=_HAND_STANDALONE_OFFSET)
            arm_spec.attach(hand_spec, prefix=_HAND_PREFIX, frame=frame)
        return _MujocoModel(arm_spec.compile())

    def drive(self, part, target):
        target_ctrl = (
            self._arm_ctrl(target) if part == "arm" else self._hand_ctrl(target)
        )
        with self._physics_lock:
            self._model.drive_ctrl(target_ctrl)

    def launch_viewer(self):
        self._model.launch_viewer()
        enable_live_view(self._model)
        return self._model.viewer

    def render(self):
        return self._model.render()

    def _arm_ctrl(self, target_deg):
        import mujoco

        from ..arm.lerobot_robot_so101_5dof.solver import real_deg_to_mj_rad

        target_rad = real_deg_to_mj_rad(target_deg)
        target_ctrl = self._model.data.ctrl.copy()
        for joint, rad in target_rad.items():
            actuator_id = mujoco.mj_name2id(
                self._model.model,
                mujoco.mjtObj.mjOBJ_ACTUATOR,
                self.actuator_name("arm", joint),
            )
            target_ctrl[actuator_id] = rad
        return target_ctrl

    def _hand_ctrl(self, target_pose):
        import mujoco

        target_ctrl = self._model.data.ctrl.copy()
        for name, value in zip(_HAND_ACTUATORS, target_pose, strict=True):
            actuator_id = mujoco.mj_name2id(
                self._model.model,
                mujoco.mjtObj.mjOBJ_ACTUATOR,
                self.actuator_name("hand", name),
            )
            target_ctrl[actuator_id] = value
        return target_ctrl
