from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig
from lerobot.robots.config import RobotConfig


@RobotConfig.register_subclass("so101_follower_5dof")
@dataclass
class SO101Follower5DofConfig(RobotConfig):
    """SO-101 follower config with only 5 motors (ids 1-5, no gripper).

    Use this when a third-party robotic hand replaces the stock gripper.
    """

    port: str
    disable_torque_on_disconnect: bool = True
    max_relative_target: float | dict[str, float] | None = None
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    use_degrees: bool = True
    position_p_coefficient: int = 16
    position_i_coefficient: int = 0
    position_d_coefficient: int = 32
