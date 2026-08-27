import threading

import mne

from n2o.command import Command, CommandConfig
from n2o.decoder.config import FeatureType
from n2o.robot import ControllerType, Robot

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
    """Top-level orchestrator binding a signal source, decoder, and robot together."""

    def __init__(self):
        self.signal = None
        self.decoder = None
        self.robot = Robot()
        self.command = None
        self.command_config = None

    def run(self, controller: str = "motor_driver"):
        """Run one or more read -> decode -> translate -> route step(s), one per
        `_run_cycle()` call.

        How many times is `self.decoder.cycle` (default `1` -- see `Decoder.__init__()`).
        A decoder meant to drive a static offline recording through several different
        results per demo (e.g. `OfnerEEGNet`, `cycle = 3`) raises this; an ordinary
        decoder, or a real-time `StreamLoader`-style pipeline with nothing to "cycle"
        through, leaves it at `1`.

        `controller` (a `ControllerType` value: `"motor_driver"`/`"simulation"`/
        `"vla"`) is written onto `self.robot.controller` before dispatching --
        `Robot.router()` reads it to decide whether a part's `goal()` (target values
        only, nothing physically moves) or `move()` (drives the real hardware) gets
        called. `controller="simulation"` also lazily builds a
        `n2o.robot.simulation.Simulator` onto `self.robot.simulator` (if one isn't
        already assigned) and opens a live viewer for every part actually assigned
        (`self.robot.arm`/`self.robot.hand`), so a bare `n2o.run(controller=
        "simulation")` is enough to watch it move -- `Simulator.drive()` itself never
        does this on its own (headless-safe).

        No settle sleep runs between cycles here anymore -- `Robot.router()` doesn't
        return until every dispatched part's `Part.done_event` is set, and that only
        happens once `move()`/`Simulator.drive()` actually finishes moving (real or
        simulated), not just once commands are issued. So the next cycle's inference
        can start the moment one `_run_cycle()` call returns."""
        cycle = getattr(self.decoder, "cycle", 1)
        self.robot.controller = ControllerType(controller)
        if (
            self.robot.controller is ControllerType.SIMULATION
            and self.robot.simulator is None
        ):
            from n2o.robot.simulation import Simulator

            self.robot.simulator = Simulator()
            for part in ("arm", "hand"):
                if getattr(self.robot, part) is not None:
                    self.robot.simulator.launch_viewer(part)
        try:
            for i in range(cycle):
                self._run_cycle(i, cycle)
        except KeyboardInterrupt:
            print("\n중단됨 (Ctrl+C) -- 정리하고 종료합니다.")

    def _run_cycle(self, i, cycle):
        """Run a single read -> decode -> translate -> route step (the `i`-th of
        `cycle`, both only used for the progress labels printed along the way).

        Factored out of `run()`'s loop body so a single cycle can be driven from
        somewhere other than that `for` loop later -- e.g. a `py_trees.behaviour.
        Behaviour.update()` could call this directly and map the outcome to
        `Status.RUNNING`/`SUCCESS`/`FAILURE`, instead of `run()`'s `cycle`-count loop
        being the only way to drive the pipeline. Nothing here depends on `run()`'s
        state beyond `self`, so it needs no changes to become that seam -- only a
        wrapper around it does."""
        decoded_signal = self._decode_with_progress(f"[{i + 1}/{cycle}] 추론 진행 중")
        result = decoded_signal
        labels = self.decoder.config.labels
        if labels is not None and isinstance(decoded_signal, int):
            result = labels[decoded_signal]
        print(f"[{i + 1}/{cycle}] 추론 결과: {result!r}")
        if self.decoder.output_type is FeatureType.LANGUAGE:
            raise NotImplementedError(
                "LANGUAGE routing needs a new controller design -- see CLAUDE.md"
            )
        elif self.decoder.output_type is FeatureType.ACTION:
            actions = self.command.translate(self.decoder, decoded_signal)
            self.robot.router(actions)
        else:
            raise ValueError(
                f"unsupported decoder.output_type: {self.decoder.output_type!r}"
            )

    _PROGRESS_TICK_S = 1.0

    def _decode_with_progress(self, label):
        """Run `self.signal.read()` + `self.decoder(sample)` on a background thread,
        printing `label` with a "." appended once per `_PROGRESS_TICK_S` (in place,
        via `\\r`) while it's still running -- so a slow read/decode (e.g.
        re-filtering a raw recording) doesn't just sit there looking stuck. Re-raises
        any exception the background thread hit, rather than silently swallowing it.

        The thread is a daemon: a `KeyboardInterrupt` raised in the main thread while
        blocked on `thread.join()` below (`run()` catches it) doesn't leave the
        process hanging on a still-running decode -- a non-daemon thread would keep
        the interpreter alive until it finished on its own."""
        result = {}

        def _target():
            try:
                result["value"] = self.decoder(self.signal.read())
            except BaseException as exc:  # noqa: BLE001 -- re-raised on the caller's thread below
                result["error"] = exc

        thread = threading.Thread(target=_target, daemon=True)
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


def main() -> None:
    print("Hello from neural-to-output!")
