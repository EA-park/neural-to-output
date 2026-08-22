# Decoder

원시 신호를 의도/명령으로 변환하는 디코딩 알고리즘에 대한 문서입니다.

## `DecoderConfig`

`DecoderConfig`(`n2o.decoder`)는 태스크 종류에 따라 디코더의 입출력 형태를 설명합니다:

```python
from n2o.decoder import DecoderConfig, DecoderType

decoder_config = DecoderConfig(
    type=DecoderType.CLASSIFICATION,
    input_feature=59,  # 입력 크기
    output_feature=4,  # 클래스 개수(CLASSIFICATION) 또는 타깃 크기(REGRESSION)
)
```

`DecoderType`은 `CLASSIFICATION` 또는 `REGRESSION`입니다. `type`은 하나 이상의
내부 모델을 감싼 디코더(예: trunk를 공유하지 않는 분류 모델 1개 + 회귀 모델 1개)라면
`tuple[DecoderType, ...]`일 수도 있습니다 —
[아키텍처 → 라우팅](../architecture.ko.md#featuretype-languagecontroller) 참고.
`input_feature`/`output_feature`는 아직 확정된 형태가 아닙니다 — 실제 디코더가
나오기 전까지는 크기/개수를 나타내는 자리표시자로 봐주세요.

`Decoder` 인스턴스의 `config` 속성(`__init__`에서 설정하며, `ClassVar`가 아닙니다)은
그 디코더 자신의 `DecoderConfig`를 담습니다 — `n2o.command.Command.translate()`는
`decoder.config.type`을 읽어서 디코더 출력을 어떻게 해석할지 정합니다.

## 라우팅: `output_type`

형태만 다루는 `DecoderConfig`와 달리, 모든 `Decoder` 서브클래스는 `output_type`
클래스 속성도 반드시 선언해야 합니다 — 이 디코더가 어떤 *종류*의 예측값을
만드는지 나타내는 `FeatureType`(`SIGNAL`, `LANGUAGE`, `ACTION`)입니다:

```python
from n2o.decoder import Decoder, FeatureType


class MyLanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def decode(self, signal): ...
```

`N2O.run()`은 실행 시점에 이 값을 읽습니다: `FeatureType.LANGUAGE`면 디코딩된
예측값을 `n2o.controller.act()`로 라우팅하고, `FeatureType.ACTION`이면
`n2o.command.translate()`를 거쳐 `robot.arm/hand.move()`로 라우팅합니다. 그 외의
경우(선언하지 않은 기본값 `None` 포함)에는 `run()`이 `ValueError`를 발생시킵니다 —
조용히 넘어가는 대체 동작은 없습니다.
[아키텍처 → 라우팅](../architecture.ko.md#featuretype-languagecontroller) 참고.

이는 `CommandConfig.output_type`과는 별개입니다 — 그쪽은
`CommandConfig.verify_report()`가 확인하는 설계 시점의 선언일 뿐이며, 아직 둘을
서로 교차 검증하지는 않습니다. `Command`(이 `output_type`이 라우팅하는 예측값을
가지고 `robot.arm`/`robot.hand`가 무엇을 할지 결정하는 실제 런타임 매핑 —
[아키텍처 → `Command`](../architecture.ko.md#command)
참고)와도 별개입니다.

여기 있는 모든 구체 디코더는 현재 인터페이스만 존재하는 스텁입니다(`raise NotImplementedError`).
