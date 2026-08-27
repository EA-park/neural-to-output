# Decoder

신호를 원시 예측값으로 변환하는 디코딩 알고리즘 문서입니다.

## `DecoderConfig`

[`DecoderConfig`][n2o.decoder.config.DecoderConfig](`n2o.decoder`)는 decoder의 형태와 동작을 담고 있으며, 생성 시점에 한 번
설정되어 파이프라인 전체에서 다시 읽힙니다:

```python
from n2o.decoder import DecoderConfig, DecoderType

decoder_config = DecoderConfig(
    type=DecoderType.CLASSIFICATION,
    input_feature=59,
    output_feature=4,
    windowing_kwargs={"start_offset_sec": 0.0, "stop_offset_sec": 2.0},
)
```

- `type` — `DecoderType.CLASSIFICATION` 또는 `.REGRESSION`, 또는 공유되는 trunk 없이
  내부 모델을 두 개 이상 감싸는 decoder를 위한 `tuple[DecoderType, ...]`.
- `n_times` / `windowing_kwargs` / `preprocessing_kwargs` — `Decoder.prepare()`(아래)에
  전달됩니다. `windowing_kwargs`가 한 번도 설정되지 않았다면 `prepare()`는 에러를
  발생시킵니다 — 데이터셋에 무관한 기본값은 없습니다.
- `labels` — 클래스 인덱스 순서의 라벨 목록으로, `Classification` decoder 자신의
  `window()`가 자동으로 채웁니다. `Regression`에서는 항상 `None`입니다(연속적인
  타깃에는 이산적인 라벨 목록이 없습니다). 이 값이 설정되면 `Command.translate()`가
  `decoder.config.labels[decoded_signal]`를 읽습니다.

## `prepare()`: raw 레코딩 -> decoder에 넣을 수 있는 윈도우

`Decoder.__call__()`(`decode()`가 아니라 `N2O.run()`이 실제로 호출하는 대상)은
윈도잉되지 않은 raw 레코딩 — `DatasetLoader.read()`/`StreamLoader.read()`가 반환하는
형태 — 을 자동으로 감지해 한 번만 `prepare()`를 호출하고 그 결과를 캐시합니다:

```python
def prepare(self, raw_dataset):
    self.preprocess(raw_dataset, **self.config.preprocessing_kwargs)
    return self.window(raw_dataset, **self.config.windowing_kwargs)
```

이미 윈도잉된 배열(실시간 스트림의 일반적인 매 스텝 케이스)은 이 과정을 건너뛰고 바로
`decode()`로 갑니다. `self.cycle`(기본값 `1`)은 이후 `__call__()`이 어떤 준비된
윈도우를 선택할지 결정합니다 — `cycle <= 1`이면 항상 가장 최근 윈도우를 디코딩하고,
`cycle > 1`이면 준비된 세트 전체에 고르게 분산된 `cycle`개의 윈도우 중 하나를 매 호출마다
전진(및 순환)하며 선택합니다. `N2O.run()`은 `getattr(self.decoder, "cycle", 1)`을 읽어
몇 스텝을 반복할지 결정합니다.

## `Classification` vs. `Regression`

모든 구체 decoder는 [`Decoder`][n2o.decoder.base.Decoder]를 직접 서브클래싱하는 대신 [`Classification`][n2o.decoder.classification.base.Classification] 또는
[`Regression`][n2o.decoder.regression.base.Regression](`n2o.decoder.classification`/`n2o.decoder.regression`)을 서브클래싱합니다 —
`preprocess()`/`window()`가 둘 다 제공하지 않는 진짜 세 번째 형태가 필요한 경우만
예외입니다. 둘 다 `preprocess()`는 동일하게 구현되어 있지만(`bandpass_standardize()` —
4-38Hz bandpass + exponential-moving-standardize), `window()`는 타깃의 형태에 따라
다릅니다:

- `Classification.window()` = [`window_by_event()`][n2o.decoder.utils.windowing.window_by_event] — 트라이얼당 이벤트 기준 윈도우
  하나, 트라이얼당 라벨 하나. 여기서 `config.labels`가 설정됩니다.
- `Regression.window()` = [`window_by_sliding()`][n2o.decoder.utils.windowing.window_by_sliding] — 레코딩 전체에 걸쳐 타일링된, 겹치는
  고정 길이 윈도우로, 트라이얼/이벤트 경계를 무시합니다(관절 각도 같은 연속적인 타깃은
  트라이얼당 값 하나를 갖지 않습니다).

`n2o.decoder.utils`(`preprocessing.py`/`windowing.py`)는 이를 일반 함수로 제공하며,
`signal.read()`가 반환한 것에 직접 사용할 수도 있습니다:

```python
from n2o.decoder.utils import bandpass_standardize, window_by_event, label_names

bandpass_standardize(raw_dataset)
windows = window_by_event(raw_dataset, start_offset_sec=...)
labels = label_names(windows)
```

## 이름으로 모델 만들기: `BraindecodeDecoder`

`n2o.decoder.classification.braindecode_entry`는 데이터셋 레지스트리가
`braindecode.models`에 대해 취하는 방식을 그대로 반영합니다: 모든
`braindecode.models.EEGModuleMixin` 서브클래스(~60개 아키텍처)가 import 시점에
등록되고, [`BraindecodeDecoder`][n2o.decoder.classification.braindecode_entry.BraindecodeDecoder]`(Classification)`이 이름으로 그중 무엇이든 빌드합니다:

```python
from n2o.decoder.classification import BraindecodeDecoder, list_models
from n2o.decoder.utils import expected_window_samples

n_times = expected_window_samples(
    raw_dataset, start_offset_sec=0.0, stop_offset_sec=2.0
)
decoder = BraindecodeDecoder("EEGNetv4", n_chans=22, n_outputs=4, n_times=n_times)
```

[`expected_window_samples()`][n2o.decoder.utils.windowing.expected_window_samples]는 실제로 윈도잉하지 않고도 `window_by_event()`가 만들어낼
결과를 예측하므로, 모델의 레이어 형태(`n_chans`/`n_outputs`/`n_times`는 필수 생성자
인자입니다 — moabb 데이터셋 클래스와 달리 모델은 인자 없이 생성할 수 없습니다)를
`prepare()`를 호출하기 전에 고정할 수 있습니다.

`BraindecodeDecoder.from_pretrained(name, repo_id, **kwargs)`는 braindecode 자체의
`model.push_to_hub()`로 게시된 체크포인트(Hub repo에 실제 `config.json`이 있는 경우)만
지원합니다 — shape와 가중치가 모두 자동으로 로드됩니다. skorch의
`EEGClassifier.save_params()`로 저장된 체크포인트는 shape를 복원할 방법이 없으므로,
이런 경우에는 일반 생성자로 빌드하세요(`examples/03_explore_eegnet_decoder.ipynb` 참고).

## 라우팅: `output_type`

`DecoderConfig`와는 별개로, 모든 `Decoder` 서브클래스는 `output_type` ClassVar를
선언해야 합니다 — 어떤 종류의 예측값을 만드는지 나타내는 [`FeatureType`][n2o.decoder.config.FeatureType](`ACTION` 또는
`LANGUAGE`)입니다:

```python
from n2o.decoder import Decoder, FeatureType


class MyLanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def decode(self, signal): ...
```

`N2O.run()`은 런타임에 이를 읽어 다음 파이프라인 단계를 결정합니다 —
[아키텍처 → 라우팅](../architecture.ko.md#featuretype-controller) 참고.
선언하지 않은 기본값을 포함해 그 외의 값은 `run()`이 `ValueError`를 발생시킵니다 —
조용한 폴백은 없습니다.
