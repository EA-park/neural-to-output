import threading

import mne
import urllib3

from n2o.command import Command, CommandConfig
from n2o.decoder.config import FeatureType
from n2o.robot import ControllerType, Robot

mne.set_log_level("ERROR")
# mne is a transitive dependency of the core moabb/braindecode stack (see
# signal/dataset/moabb_entry.py) -- its default INFO level floods every
# DatasetLoader.read()/Decoder.prepare() call with filter-design/annotation dumps
# ("Filtering raw data...", "Used Annotations descriptions...", etc.), unreadable
# alongside N2O.run()'s own per-cycle progress output. Set once, globally, here.

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# moabb.datasets.download.data_dl() deliberately passes verify=False to its
# downloader (some dataset hosts have cert issues moabb chose to work around) --
# that's moabb's own call, not something DatasetLoader.read() can override without
# monkeypatching a third-party internal. All that's left in our control is the
# resulting per-request "Unverified HTTPS request" warning it prints, which is just
# noise here -- moabb makes the same verify=False choice every time regardless.

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

    def prepare(self, controller: str = "motor_driver"):
        """Write `controller` onto `self.robot.controller` and, for `"simulation"`,
        lazily build/open the viewer -- split out of `run()` so a caller (e.g. a
        desktop UI) can open the simulation window as its own step, before
        committing to actually driving the pipeline. `run()` calls this itself, so
        a bare `n2o.run(controller=...)` still does both in one call, same as
        before this split.

        `controller` (a `ControllerType` value: `"motor_driver"`/`"simulation"`/
        `"vla"`) is written onto `self.robot.controller` -- `Robot.router()` reads
        it (per part, falling back to this scalar -- see `Robot.part_controllers`)
        to decide whether a part's `goal()` (target values only, nothing physically
        moves) or `move()` (drives the real hardware) gets called.

        Also lazily builds a `n2o.robot.simulation.Simulator` onto `self.robot.
        simulator` for whichever assigned parts actually resolve to `SIMULATION`
        (via `self.robot.part_controllers`, falling back to the scalar `controller`
        just written) and don't already have their own entry in `self.robot.
        part_simulators` -- a caller that pre-assigns a part's own simulator (e.g.
        a `UnitySimulator`, or a per-part mix built by the caller itself) keeps it
        untouched here. Honors `self.robot.attach_hand_to_arm`, then opens one live
        viewer window for the simulator it just built -- so a bare `n2o.
        run(controller="simulation")` is enough to watch it move -- `Simulator.
        drive()` itself never does this on its own (headless-safe).

        `launch_viewer()` only runs in the branch that just built a fresh
        `Simulator` here, not unconditionally -- `_MujocoModel.launch_viewer()`
        opens a brand new GLFW window on every call with no guard of its own, so
        calling this twice on the same simulator (e.g. `prepare()` from a UI, then
        `run()`'s own internal `prepare()` call) would otherwise leak a second
        window rather than reusing the first."""
        self.robot.controller = ControllerType(controller)
        sim_parts = [
            p
            for p in ("arm", "hand")
            if getattr(self.robot, p) is not None
            and self.robot.part_controllers.get(p, self.robot.controller)
            is ControllerType.SIMULATION
            and p not in self.robot.part_simulators
        ]
        if sim_parts and self.robot.simulator is None:
            from n2o.robot.simulation import Simulator

            self.robot.simulator = Simulator(
                sim_parts, attach_hand_to_arm=self.robot.attach_hand_to_arm
            )
            self.robot.simulator.launch_viewer()

    def run(self, controller: str = "motor_driver"):
        """Run one or more read -> decode -> translate -> route step(s), one per
        `_run_cycle()` call.

        How many times is `self.decoder.cycle` (default `1` -- see `Decoder.__init__()`).
        A decoder meant to drive a static offline recording through several different
        results per demo (e.g. `OfnerEEGNet`, `cycle = 3`) raises this; an ordinary
        decoder, or a real-time `StreamLoader`-style pipeline with nothing to "cycle"
        through, leaves it at `1`.

        Calls `self.prepare(controller)` first -- see its own docstring for what
        that covers (`self.robot.controller`, simulator build/viewer-launch).
        Calling `prepare()` yourself first (e.g. to open the simulation window
        before the user commits to running) makes this call a no-op for that part,
        since `self.robot.simulator` is then already assigned.

        No settle sleep runs between cycles here anymore -- `Robot.router()` doesn't
        return until every dispatched part's `Part.done_event` is set, and that only
        happens once `move()`/`Simulator.drive()` actually finishes moving (real or
        simulated), not just once commands are issued. So the next cycle's inference
        can start the moment one `_run_cycle()` call returns."""
        cycle = getattr(self.decoder, "cycle", 1)
        self.prepare(controller)
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
        """Run `self.signal.read()` then `self.decoder(sample)` on a background
        thread, printing `label` with a "." appended once per `_PROGRESS_TICK_S`
        (in place, via `\\r`) once `read()` has returned and `decode()` is actually
        running -- so a slow decode (e.g. re-filtering a raw recording) doesn't just
        sit there looking stuck. Re-raises any exception the background thread hit,
        rather than silently swallowing it.

        Nothing is printed here while `read()` itself is still running -- a
        `DatasetLoader.read()` that needs to download its dataset first (see
        `signal/dataset/moabb_entry.py`) already prints its own real progress
        (pooch/tqdm, on stderr) for that; ticking `label`'s dots at the same time
        would just interleave two unrelated progress indicators on top of each
        other. This way each phase shows exactly one progress indicator at a time:
        the download's own while reading, `label`'s dots while decoding.

        The thread is a daemon: a `KeyboardInterrupt` raised in the main thread while
        blocked on `thread.join()` below (`run()` catches it) doesn't leave the
        process hanging on a still-running decode -- a non-daemon thread would keep
        the interpreter alive until it finished on its own."""
        result = {}
        reading_done = threading.Event()

        def _target():
            try:
                sample = self.signal.read()
                reading_done.set()
                result["value"] = self.decoder(sample)
            except BaseException as exc:  # noqa: BLE001 -- re-raised on the caller's thread below
                reading_done.set()
                result["error"] = exc

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        reading_done.wait()
        if "error" in result:
            raise result["error"]

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
