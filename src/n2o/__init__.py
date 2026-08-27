import threading
import time

import mne

from n2o.command import Command, CommandConfig
from n2o.decoder.config import FeatureType
from n2o.robot import Robot

mne.set_log_level("ERROR")
# mne is a transitive dependency of the core moabb/braindecode stack (see
# signal/dataset/moabb_entry.py) -- its default INFO level floods every
# DatasetLoader.read()/Decoder.prepare() call with filter-design/annotation dumps
# ("Filtering raw data...", "Used Annotations descriptions...", etc.), unreadable
# alongside N2O.run()'s own per-cycle progress output. Set once, globally, here.

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
        self._sim_arm = None
        self._sim_hand = None

    def run(self, simulation: bool = False):
        """Run one or more read -> decode -> translate -> move step(s).

        How many times is `self.decoder.cycle` (default `1` -- see `Decoder.__init__()`).
        A decoder meant to drive a static offline recording through several different
        results per demo (e.g. `OfnerEEGNet`, `cycle = 3`) raises this; an ordinary
        decoder, or a real-time `StreamLoader`-style pipeline with nothing to "cycle"
        through, leaves it at `1`.

        Each simulated `move()` call is synchronous -- it doesn't return until the sim
        has actually finished that step's motion (see `SO101ArmSim._drive_ctrl()`/
        `AmazingHandSim._drive_ctrl()`) -- but that alone still finishes in about a
        second even with a live viewer attached (`VIEWER_STEP_DT_S`-paced), too fast
        to actually watch the result before the next cycle's inference starts. Real
        controllers (`SO101ArmRealController`/`AmazingHandRealController`) aren't
        synchronous with the hardware at all -- they issue a servo command and
        return, not blocking until it physically finishes moving there. Either way, a
        cycle that actually moved something waits before the next cycle's inference:
        `_SIMULATION_SETTLE_S` (3s) if `simulation=True`, `_REAL_HARDWARE_SETTLE_S`
        (5s) otherwise -- skipped after the last cycle, and whenever nothing moved
        that step.
        """
        cycle = getattr(self.decoder, "cycle", 1)
        for i in range(cycle):
            decoded_signal = self._decode_with_progress(
                f"[{i + 1}/{cycle}] 추론 진행 중"
            )
            result = decoded_signal
            labels = self.decoder.config.labels
            if labels is not None and isinstance(decoded_signal, int):
                result = labels[decoded_signal]
            print(f"[{i + 1}/{cycle}] 추론 결과: {result!r}")
            moved = False
            if self.decoder.output_type is FeatureType.LANGUAGE:
                self.controller.act(decoded_signal, self.robot)
            elif self.decoder.output_type is FeatureType.ACTION:
                actions = self.command.translate(self.decoder, decoded_signal)
                if self.robot.arm is not None and actions["arm"] is not None:
                    arm = self._simulated_arm() if simulation else self.robot.arm
                    arm.move(actions["type"], actions["arm"])
                    moved = True
                if self.robot.hand is not None and actions["hand"] is not None:
                    hand = self._simulated_hand() if simulation else self.robot.hand
                    hand.move(actions["type"], actions["hand"])
                    moved = True
            else:
                raise ValueError(
                    f"unsupported decoder.output_type: {self.decoder.output_type!r}"
                )

            if moved and i < cycle - 1:
                settle_s = (
                    self._SIMULATION_SETTLE_S
                    if simulation
                    else self._REAL_HARDWARE_SETTLE_S
                )
                target = "시뮬레이션" if simulation else "실물 로봇"
                print(f"[{i + 1}/{cycle}] {target} 정착 대기 중 ({settle_s:.0f}초)...")
                time.sleep(settle_s)

    _SIMULATION_SETTLE_S = 3.0
    _REAL_HARDWARE_SETTLE_S = 5.0

    _PROGRESS_TICK_S = 1.0

    def _decode_with_progress(self, label):
        """Run `self.signal.read()` + `self.decoder(sample)` on a background thread,
        printing `label` with a "." appended once per `_PROGRESS_TICK_S` (in place,
        via `\\r`) while it's still running -- so a slow read/decode (e.g.
        re-filtering a raw recording) doesn't just sit there looking stuck. Re-raises
        any exception the background thread hit, rather than silently swallowing it."""
        result = {}

        def _target():
            try:
                result["value"] = self.decoder(self.signal.read())
            except BaseException as exc:  # noqa: BLE001 -- re-raised on the caller's thread below
                result["error"] = exc

        thread = threading.Thread(target=_target)
        thread.start()
        dots = 0
        print(f"\r{label}{'.' * dots}{' ' * (3 - dots)}", end="", flush=True)
        while thread.is_alive():
            thread.join(timeout=self._PROGRESS_TICK_S)
            if thread.is_alive():
                dots = (dots + 1) % 4
                print(f"\r{label}{'.' * dots}{' ' * (3 - dots)}", end="", flush=True)
        print()  # move past the in-place progress line

        if "error" in result:
            raise result["error"]
        return result["value"]

    def _simulated_arm(self):
        if self._sim_arm is None:
            from n2o.robot.simulation import SO101ArmSim, enable_live_view

            self._sim_arm = SO101ArmSim()
            enable_live_view(self._sim_arm)
        return self._sim_arm

    def _simulated_hand(self):
        if self._sim_hand is None:
            from n2o.robot.simulation import AmazingHandSim, enable_live_view

            self._sim_hand = AmazingHandSim()
            enable_live_view(self._sim_hand)
        return self._sim_hand

    @property
    def simulated_arm(self):
        """The `SO101ArmSim` built (and cached) by `run(simulation=True)`, or `None`
        if that hasn't happened yet -- lets a caller `.render()` it afterwards. Never
        constructs one itself (unlike `_simulated_arm()`), since building a MuJoCo sim
        just to look at it before ever moving it isn't a meaningful use case."""
        return self._sim_arm

    @property
    def simulated_hand(self):
        """The `AmazingHandSim` built (and cached) by `run(simulation=True)`, or
        `None` if that hasn't happened yet -- see `simulated_arm`."""
        return self._sim_hand

    def enable_live_simulation_view(self):
        """Pre-build whichever part(s) `run(simulation=True)` will actually simulate
        (mirrors that method's own `self.robot.arm`/`self.robot.hand` `is not None`
        check) and open their live viewer window early -- `_simulated_arm()`/
        `_simulated_hand()` already do this automatically the first time
        `run(simulation=True)` needs them, so this is only useful for opening the
        window a moment *before* that first `move()`, rather than at the same time."""
        if self.robot.arm is not None:
            self._simulated_arm()
        if self.robot.hand is not None:
            self._simulated_hand()


def main() -> None:
    print("Hello from neural-to-output!")
