from n2o.command import Command, CommandConfig
from n2o.decoder.config import FeatureType
from n2o.robot import Robot

__all__ = [
    "N2O",
    "Command",
    "CommandConfig",
    "main",
]


class N2O:
    """Top-level orchestrator binding a signal source, decoder, robot, and controller together."""

    def __init__(self):
        self.signal = None
        self.decoder = None
        self.robot = Robot()
        self.controller = None
        self.command = None
        self.command_config = None

    def run(self):
        sample = self.signal.read()
        decoded_signal = self.decoder(sample)
        if self.decoder.output_type is FeatureType.LANGUAGE:
            self.controller.act(decoded_signal, self.robot)
        elif self.decoder.output_type is FeatureType.ACTION:
            actions = self.command.translate(self.decoder, decoded_signal)
            self.robot.arm.move(actions["type"], actions["arm"])
            self.robot.hand.move(actions["type"], actions["hand"])
        else:
            raise ValueError(
                f"unsupported decoder.output_type: {self.decoder.output_type!r}"
            )


def main() -> None:
    print("Hello from neural-to-output!")
