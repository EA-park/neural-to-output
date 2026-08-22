from n2o.robot import Robot, RobotConfig, make_robot
from n2o.robot.arm import ARM_REGISTRY, MockArm
from n2o.robot.camera import CAMERA_REGISTRY, MockCamera
from n2o.robot.hand import HAND_REGISTRY, MockHand


def test_registries_contain_builtin_mocks():
    assert ARM_REGISTRY["MockArm"] is MockArm
    assert HAND_REGISTRY["MockHand"] is MockHand
    assert CAMERA_REGISTRY["MockCamera"] is MockCamera


def test_make_robot_builds_instances_for_set_fields():
    robot = make_robot(RobotConfig(arm="MockArm", hand="MockHand", camera="MockCamera"))
    assert isinstance(robot.arm, MockArm)
    assert isinstance(robot.hand, MockHand)
    assert isinstance(robot.camera, MockCamera)


def test_make_robot_leaves_unset_fields_none():
    robot = make_robot(RobotConfig(arm="MockArm"))
    assert isinstance(robot.arm, MockArm)
    assert robot.hand is None
    assert robot.camera is None


def test_robot_from_config_delegates_to_make_robot():
    robot = Robot.from_config(RobotConfig(hand="MockHand"))
    assert isinstance(robot.hand, MockHand)
    assert robot.arm is None


def test_direct_assignment_still_works_unconditionally():
    robot = Robot()
    robot.arm = MockArm()
    assert isinstance(robot.arm, MockArm)
