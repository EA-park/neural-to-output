from . import arm, hand


class Robot:
    """Container that binds a robot arm and hand together."""

    def __init__(self):
        self.arm = None
        self.hand = None


__all__ = ["Robot", "arm", "hand"]
