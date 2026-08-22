# Decoder

Documentation for decoding algorithms that translate raw signals into intent/commands.

## `DecoderConfig`

`DecoderConfig` (in `n2o.decoder`) describes a decoder's I/O shape, keyed by task type:

```python
from n2o.decoder import DecoderConfig, DecoderType

decoder_config = DecoderConfig(
    type=DecoderType.CLASSIFICATION,
    input_feature=59,  # input size
    output_feature=4,  # class count (CLASSIFICATION) or target size (REGRESSION)
)
```

`DecoderType` is `CLASSIFICATION` or `REGRESSION`. `type` can also be a
`tuple[DecoderType, ...]` for a decoder wrapping more than one internal model (e.g.
one classifier + one regressor, sharing no trunk between them) — see
[Architecture → Routing](../architecture.md#routing-featuretype-and-languagecontroller).
`input_feature`/`output_feature` aren't a finalized shape yet — treat them as a
size/count placeholder until real decoders exist.

A `Decoder` instance's `config` attribute (set in `__init__`, not a `ClassVar`) holds
its own `DecoderConfig` — `n2o.command.Command.translate()` reads `decoder.config.type`
to decide how to interpret the decoder's output.

## Routing: `output_type`

Unlike `DecoderConfig`, which is purely about shape, every `Decoder` subclass must
also declare an `output_type` class attribute — a `FeatureType` (`SIGNAL`, `LANGUAGE`,
`ACTION`) describing what *kind* of prediction it produces:

```python
from n2o.decoder import Decoder, FeatureType


class MyLanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def decode(self, signal): ...
```

`N2O.run()` reads this at runtime: `FeatureType.LANGUAGE` routes the decoded
prediction through `n2o.controller.act()`; `FeatureType.ACTION` routes it through
`n2o.command.translate()` to `robot.arm/hand.move()`. Anything else — including the
undeclared default `None` — makes `run()` raise `ValueError`; there is no silent
fallback. See
[Architecture → Routing](../architecture.md#routing-featuretype-and-languagecontroller).

Note this is separate from `CommandConfig.output_type`, which is a design-time
declaration checked by `CommandConfig.verify_report()` — the two aren't cross-checked
against each other yet. It's also separate from `Command` (the runtime
prediction → per-part-action mapping — see
[Architecture → `Command`](../architecture.md#command-turning-a-decoders-raw-output-into-per-part-actions)),
which decides what `robot.arm`/`robot.hand` should do with the prediction this
`output_type` field routes.

Every concrete decoder here is currently an interface-only stub (`raise NotImplementedError`).
