from n2o.robot import ControllerType, Part, Robot


class _RecordingPart(Part):
    def __init__(self):
        self.goal_called_with = None
        self.moved_with = None

    def goal(self, cmd):
        self.goal_called_with = cmd
        return f"target-for-{cmd}"

    def move(self, cmd):
        self.moved_with = cmd


class _RecordingSimulator:
    def __init__(self):
        self.driven = {}

    def drive(self, part, target):
        self.driven[part] = target


def test_part_controllers_override_falls_back_to_global_controller():
    robot = Robot()
    robot.controller = ControllerType.MOTOR_DRIVER
    robot.part_controllers = {"hand": ControllerType.SIMULATION}
    robot.arm = _RecordingPart()
    robot.hand = _RecordingPart()

    robot.router({"arm": "up", "hand": "grip"})

    assert robot.arm.moved_with == "up"  # no override -- falls back to MOTOR_DRIVER
    assert robot.arm.goal_called_with is None
    assert robot.hand.goal_called_with == "grip"  # per-part override to SIMULATION
    assert robot.hand.moved_with is None


def test_part_simulators_override_falls_back_to_global_simulator():
    robot = Robot()
    robot.controller = ControllerType.SIMULATION
    global_sim = _RecordingSimulator()
    hand_sim = _RecordingSimulator()
    robot.simulator = global_sim
    robot.part_simulators = {"hand": hand_sim}
    robot.arm = _RecordingPart()
    robot.hand = _RecordingPart()

    robot.router({"arm": "up", "hand": "grip"})

    assert "arm" in global_sim.driven
    assert "hand" not in global_sim.driven
    assert "hand" in hand_sim.driven
