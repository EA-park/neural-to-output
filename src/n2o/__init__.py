from n2o.robot import Robot


class N2O:
    """Top-level orchestrator binding a signal source, decoder, and robot together."""

    def __init__(self):
        self.signal = None
        self.decoder = None
        self.robot = Robot()

    def run(self):
        sample = self.signal.read()
        command = self.decoder.decode(sample)
        self.robot.arm.move(command)
        self.robot.hand.move(command)


def main() -> None:
    print("Hello from neural-to-output!")
