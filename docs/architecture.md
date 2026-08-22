# Architecture

## Pipeline

`n2o` wires four interchangeable components into a single orchestrator, `N2O`: a
`signal` source is decoded by a `decoder` into a raw prediction, which a `command`
translates into per-part actions sent to a `robot`'s `arm` and `hand`.

```python
from n2o import N2O
from n2o.command import Command, CommandConfig
from n2o.signal.dataset import EEG
from n2o.decoder import EEGNet
from n2o.robot.arm import LeRobotSO101
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = EEG()
n2o.decoder = EEGNet()
n2o.command = Command()
n2o.robot.arm = LeRobotSO101()
n2o.robot.hand = AmazingHand()
n2o.run()
```

`N2O.run()` reads one sample from `signal`, decodes it via `decoder` (a `Decoder`
instance is callable — `self.decoder(sample)` is shorthand for
`self.decoder.decode(sample)`), then branches on the decoder's `output_type`:

```python
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
```

This is a strict check, not a catch-all — every `Decoder` subclass must declare an
`output_type` of either `FeatureType.ACTION` or `FeatureType.LANGUAGE` (see
[Routing](#routing-featuretype-and-languagecontroller) below); anything else,
including the undeclared default `None`, raises. There is no implicit fallback.

## `Command`: turning a decoder's raw output into per-part actions

A `Decoder` should stay a plain predictor — `decode()` returns its raw prediction
(e.g. a label string, or a dict of regression values), not a shape already tailored
to `robot.arm`/`robot.hand`. Deciding what each robot part should *do* with that
prediction is `Command`'s job, in `n2o.command`:

```python
from n2o.command import Command


class MotorImageryCommand(Command):
    def translate(self, decoder, decoded_signal):
        command = {"type": decoder.config.type, "arm": None, "hand": None}
        if decoded_signal == "left_hand":
            command["arm"], command["hand"] = "up", "grip"
        elif decoded_signal == "right_hand":
            command["arm"], command["hand"] = "down", "release"
        return command


n2o.command = MotorImageryCommand()
```

The base `Command.translate()` has a default that assumes `decoded_signal` is
*already* keyed by robot part (`{"arm": ..., "hand": ...}` — e.g. a decoder wrapping
independent per-part sub-models); subclass and override `translate()` whenever a
decoder's raw output needs real translation into that shape first, as above. There is
no separate "continuous" variant — the same `Command` base class covers both discrete
and continuous decoders, since overriding `translate()` handles either case.

`command.translate(decoder, decoded_signal)` returns a dict with a `"type"` key (the
decoder's `config.type`, passed through so `move()`/`Controller.apply()` can branch on
it if needed) plus one key per robot part. Each part's value is either a bare,
already self-describing name (e.g. `"grip"`) or an `(ActionType, value)` tuple — a raw
regression value isn't self-describing on its own, so it's paired with an `ActionType`
saying how to interpret it:

```python
from n2o.command import ActionType

command["arm"] = (
    ActionType.JOINT_ABSOLUTE,
    {"shoulder_lift": 0.31, "elbow_flex": -0.08},
)
```

`ActionType` (in `n2o.command`) has four members: `JOINT_ABSOLUTE`, `JOINT_RELATIVE`,
`CARTESIAN_ABSOLUTE`, `CARTESIAN_RELATIVE`. It travels with the value, independent of
the decoder's own `DecoderType` (`CLASSIFICATION`/`REGRESSION`) carried in `"type"`.

`N2O.run()` calls `command.translate(decoder, decoded_signal)` and sends each part its
own resulting value: `robot.arm.move(actions["type"], actions["arm"])`,
`robot.hand.move(actions["type"], actions["hand"])`.

Once `robot.arm.move()` receives an action, something still has to turn that into
actual motor targets or a vendor SDK call — that's `n2o.robot.controller.Controller`
(renamed from the earlier `MotorWrapper`), owned by the `RobotArm`/`RobotHand`
implementation itself: `move()` typically delegates straight to
`self.controller.apply(decoder_type, action)`. Not to be confused with the
pipeline-level `LanguageController` below, despite the shared word — one dispatches a
single action on one robot part, the other routes a whole language-typed command.

## Checking the pipeline before `run()`

Each `base.py` interface exposes optional `input_spec`/`output_spec` class attributes
(plain `dict | None`, default `None` — "not decided yet") so implementations can
declare their contract:

```python
class EEGWindowDecoder(Decoder):
    input_spec = {"channels": 59, "samples": 100}
    output_spec = {"x": "float", "y": "float"}
```

`CommandConfig` (in `n2o.command`, alongside `Command`) is a declarative,
`verify_report()`-only contract for the `command` boundary — pass one once you've
decided what shape you want, then call its `verify_report(n2o)` method to walk
`signal -> decoder -> command -> robot.arm/hand` and check each boundary's specs
against each other, printing a table:

```python
from n2o.command import CommandConfig

n2o.command_config = CommandConfig(
    input_feature={"x": "float", "y": "float"},
    output_feature={"joint_targets": "dict[str, float]"},
)
report = n2o.command_config.verify_report(n2o)
print(report)  # 단계 | 출력 스펙 | -> | 단계 | 입력 스펙 | 상태 (OK/MISMATCH/미정)
report.ok  # True only if every boundary is a confirmed match
```

There is no `N2O.verify()` method — `CommandConfig.verify_report()` takes `n2o` as an
argument instead, since the check logic already belongs to the `command` stage.
Leaving `command_config` unset reports both of its boundaries as "미정" — a visual
reminder that the gap is still unresolved. `CommandConfig` joins the `SignalConfig`/
`DecoderConfig`/`RobotConfig` family — one config dataclass per pipeline stage/
boundary. It has no effect on `run()` — it's declarative only, purely for planning
the `command` boundary's contract against its neighbors before writing any logic.

## Building a robot from a `RobotConfig`

The example above constructs and assigns each robot part directly, and that always
works — it's the only option for ad hoc or simulated components (e.g. a one-off
`RobotHand` subclass written for a single notebook) that were never registered.

For named, reusable hardware, `robot.arm`/`robot.hand`/`robot.camera` can instead be
built from a string name via a registry. Every concrete class registers itself with
a decorator:

```python
from n2o.robot.arm import ARM_REGISTRY

ARM_REGISTRY  # {"LeRobotSO101": LeRobotSO101, "Gello": Gello, "MockArm": MockArm}
```

`RobotConfig` names each part, and `Robot.from_config()`/`make_robot()` resolve them:

```python
from n2o.robot import Robot, RobotConfig

robot = Robot.from_config(RobotConfig(arm="LeRobotSO101", hand="AmazingHand"))
```

This is additive, not a replacement — swapping hardware becomes a one-line config
change instead of an import + instantiation edit, without taking away the direct
assignment style. `RobotConfig.controller` names a `LanguageController` (see
[Routing](#routing-featuretype-and-languagecontroller) below), but isn't resolved by
`make_robot()`/`Robot.from_config()`, since it lives on `N2O`, not `Robot` — use
`n2o.controller.make_controller()` for that field.

## Routing: `FeatureType` and `LanguageController`

Every `Decoder` subclass must declare an `output_type` class attribute — a
`FeatureType` (`SIGNAL`, `LANGUAGE`, `ACTION`) describing what kind of prediction it
produces. `N2O.run()` reads it at runtime:

- `FeatureType.ACTION` — the prediction goes through `n2o.command.translate()`, then
  to `robot.arm.move()`/`robot.hand.move()`, exactly as above.
- `FeatureType.LANGUAGE` — the prediction is routed through
  `n2o.controller.act(decoded_signal, n2o.robot)` instead, for VLA-style
  (vision-language-action) instruction-following.
- Anything else, including the undeclared default `None`, makes `run()` raise
  `ValueError` — there is no silent fallback.

```python
from n2o.decoder import Decoder, FeatureType


class MyLanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def decode(self, signal): ...


n2o.controller = (
    ...
)  # a LanguageController instance, e.g. n2o.controller.VLAController()
```

`LanguageController` follows the same registry pattern as `robot.arm`/`robot.hand`/
`robot.camera` (`@register_controller("Name")`, resolved by
`n2o.controller.make_controller("Name")`). This is currently declarative-only in one
respect: `CommandConfig.output_type` (used by `verify_report()`) and a decoder's
runtime `output_type` are two separate declarations, not yet cross-checked against
each other.

A `Decoder`'s `config` attribute (a `DecoderConfig` instance set in `__init__`, not a
`ClassVar`) separately describes *how* it produces an `ACTION`-typed prediction:
`config.type` is a `DecoderType` (`CLASSIFICATION` or `REGRESSION`), or a
`tuple[DecoderType, ...]` for a decoder wrapping more than one internal model (e.g.
one classifier + one regressor, sharing no trunk between them). `Command.translate()`
reads `decoder.config.type` to decide how to interpret `decoded_signal`, and passes it
through as the `"type"` key so `robot.arm/hand.move()` receives it too.

## Package layout

`src/n2o/` mirrors the pipeline as sibling packages. Each follows the same pattern: a
`base.py` abstract base class defining the interface, one file per concrete
implementation, and an `__init__.py` that re-exports the public names.

| Package               | Interface                                | Built-in implementations                   |
| ---------------------- | ----------------------------------------- | -------------------------------------------- |
| `n2o.signal.dataset`   | `SignalDataset.read()`                    | `EEG` (non-invasive), `InvasiveEEG`, `EMG`   |
| `n2o.signal.stream`    | `SignalStream.read()`                     | `EEGStream`, `EMGStream`                     |
| `n2o.decoder`          | `Decoder.decode(signal)`                  | `EEGNet`, `EMGDecoder`                       |
| `n2o.command`          | `Command.translate(decoder, decoded_signal)` | —                                          |
| `n2o.robot.arm`        | `RobotArm.move(decoder_type, command)`    | `LeRobotSO101`, `Gello`, `MockArm`           |
| `n2o.robot.hand`       | `RobotHand.move(decoder_type, command)`   | `AmazingHand`, `MockHand`                    |
| `n2o.robot.camera`     | `RobotCamera.capture()`                   | `MockCamera`                                 |
| `n2o.controller`       | `LanguageController.act(command, robot)`  | `VLAController`                              |

`n2o.robot.Robot` is a plain container binding one `arm` + `hand` + `camera` instance.
`n2o.command` doesn't follow the registry pattern the other packages do — a `Command`
subclass is always written per-pipeline (it encodes exactly how one decoder's raw
output maps to one robot's parts), so there's no reusable built-in to register.

Every implementation besides `MockArm`/`MockHand`/`MockCamera` is currently an
interface-only stub (`raise NotImplementedError`) — no real hardware or model
integration exists yet. Use the `Mock*` classes to exercise the full pipeline
without physical hardware.

See [Tutorials → Adding a Component](tutorials/adding-a-component.md) for how to add a
new dataset, decoder, or robot.
