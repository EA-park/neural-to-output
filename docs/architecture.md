# Architecture

## Pipeline

The pipeline is fixed:

```
signal -> decoder -> command -> robot (arm / hand / camera)
                  \-> controller (when decoder.output_type is FeatureType.LANGUAGE)
```

`N2O` (in `n2o/__init__.py`) wires a `signal` + `decoder` + `command` + `robot` +
`controller` together and drives it with `run(simulation: bool = False)`:

1. `self.signal.read()` returns a sample — a windowed array in the common
   per-step case, or (offline) a raw, unwindowed dataset the decoder auto-`prepare()`s.
2. `self.decoder(sample)` decodes it into a raw prediction (`self.decoder(sample)` is
   shorthand for `.decode(sample)`, via `Decoder.__call__()`).
3. Every `Decoder` subclass declares an `output_type` ClassVar
   (`FeatureType.ACTION` or `FeatureType.LANGUAGE`) that decides the next step:
      - `FeatureType.ACTION` goes through `Command.translate()` (see below), then
        `robot.arm.move()`/`robot.hand.move()` for whichever part(s) it targets.
      - `FeatureType.LANGUAGE` goes straight to `controller.act(decoded_signal, robot)`.
4. `run()` loops this `getattr(self.decoder, "cycle", 1)` times — most decoders leave
   `cycle` at its default `1` (decode the newest sample each call); a decoder meant to
   demo several results per `run()` off one static offline recording (e.g.
   `OfnerEEGNet`) raises it in its own `__init__()`.

## `Command`: turning a decoder's raw output into per-part actions

`Command.translate(decoder, decoded_signal)` is the only place a decoder's raw
prediction gets mapped into robot actions — keep a [`Decoder`][n2o.decoder.base.Decoder] a plain predictor and put
that mapping in [`Command`][n2o.command.command.Command], not in the decoder. The default `translate()` assumes
`decoded_signal` is already keyed by robot part (`{"arm": ..., "hand": ...}`); override
it whenever a decoder's raw output needs real translation first.

Each part's resulting value is either a bare, already self-describing name (e.g.
`"grip"`) or an `(ActionType, value)` tuple for raw values that aren't self-describing
on their own (e.g. a regression number/dict) — [`ActionType`][n2o.command.command.ActionType] (`JOINT_ABSOLUTE`,
`JOINT_RELATIVE`, `CARTESIAN_ABSOLUTE`, `CARTESIAN_RELATIVE`) travels with the value,
independent of the decoder's own `DecoderType`.

A `Command` subclass is usually notebook-local, since it encodes one specific decoder's
raw output → one specific robot's parts. Two are shipped in `src/`: [`GripSpreadCommand`][n2o.command.grip_spread.GripSpreadCommand]
(motor-imagery labels → [`AmazingHand`][n2o.robot.hand.amazing_hand.AmazingHand] single-finger poses) and [`OfnerCommand`][n2o.command.ofner_command.OfnerCommand]
(`OfnerEEGNet`'s seven raw labels → one arm-or-hand gesture each).

See [Decoder](decoder/index.md) and [Command](command/index.md) for more.

## Checking the pipeline before `run()`

[`CommandConfig`][n2o.command.config.CommandConfig] (a separate, declarative contract for the `command` boundary, pairing
with `Command` the same way `SignalConfig`/`DecoderConfig` pair with `signal`/`decoder`)
lets you sanity-check a wired-up pipeline before running it:

```python
n2o.command_config.verify_report(n2o)
```

Walks `signal -> decoder -> command -> robot.arm/hand` and prints a match/mismatch/미정
table — there's no `N2O.verify()` method; call this directly instead.

## Building a robot from a `RobotConfig`

`robot.arm`/`robot.hand`/`robot.camera`/`controller` can each be built from a name via
a registry — `@register_arm("Name")` (and the `hand`/`camera`/`controller`
equivalents) register a class, and:

```python
from n2o.robot import RobotConfig, make_robot

config = RobotConfig(arm="LeRobotSO101", hand="AmazingHand", camera="MockCamera")
robot = make_robot(config)
```

This is **additive** — direct attribute assignment (`robot.arm = SomeInstance()`)
always still works, since ad hoc/simulated components are never registered.

## Routing: `FeatureType` and `controller`

[`FeatureType`][n2o.decoder.config.FeatureType]`.LANGUAGE`-typed decoders route through `controller.act(decoded_signal,
robot)` instead of `Command` — see [Controller](controller/index.md) for the intended
shape (`n2o.robot.controller.Controller`, the per-robot-part dispatcher a
`RobotArm`/`RobotHand` implementation owns, is a *different*, lower-level concept
despite the shared name).

## Package layout

`src/n2o/` mirrors the pipeline as sibling packages:

- `signal/dataset/`, `signal/stream/` — offline/indexed and realtime signal sources
- `decoder/`, with `classification/`, `regression/`, `utils/` subpackages — signal →
  raw prediction
- `command/` — raw prediction → per-part actions
- `robot/arm/`, `robot/hand/`, `robot/camera/` — actuators/sensors, plus
  `robot/simulation/` (a bundled MuJoCo reference simulator) and `robot/controller.py`
  (the per-part `Controller` ABC)
- `third_party/` (repo root) — vendored copies of upstream projects that aren't
  pip/uv-installable packages; see [Third-Party](third-party/index.md)

Most packages follow the same extension pattern: a `base.py` ABC plus one file per
concrete implementation, re-exported from that package's `__init__.py`. See each
section's own page for the exceptions and specifics.
