# Signal

전기생리학적 신호 소스(EEG, EMG 등) — 오프라인 데이터셋과 실시간 스트림 — 문서입니다.

## Dataset vs. Stream

신호 소스는 두 가지 형태로 나뉘며, 각각 `n2o.signal` 아래에 자신만의 인터페이스를
갖습니다:

- **[`n2o.signal.dataset.DatasetLoader`][n2o.signal.dataset.loader.DatasetLoader]** — 오프라인/인덱싱된 소스. ABC가 아닌 구체
  클래스로, `path`(로컬 폴더) 또는 `name`(등록된 데이터셋 라이브러리, 예:
  `"Ofner2017"`) 중 정확히 하나로 생성합니다.
- **[`n2o.signal.stream.StreamLoader`][n2o.signal.stream.loader.StreamLoader]** — 실시간/디바이스 소스. `DatasetLoader`의
  서브클래스가 아니라 형제 클래스입니다(MNE 생태계의 `mne.io.Raw` vs.
  `mne_lsl.stream.StreamLSL`을 그대로 반영). 아직 구체 구현은 없습니다.

## `DatasetLoader`

```python
from n2o.signal.dataset import DatasetLoader

loader = DatasetLoader(name="BNCI2014_001")
info = loader.info()          # DatasetInfo: 출처, cue 기준 데이터 범위, 채널 수
raw_dataset = loader.read()   # 윈도잉되지 않은 raw 레코딩
```

`DatasetLoader.list_libraries()` / `library_tree()`로 등록된 항목을 확인할 수 있습니다 —
레지스트리(`DATASET_LIBRARY`)는 거의 전부 import 시점에 `moabb.datasets`로부터
채워지므로(moabb 데이터셋 클래스마다 동적 항목 하나씩, 약 150개), 대부분의 공개 BCI
데이터셋은 코드 추가 없이 바로 사용할 수 있습니다. `library_tree()`는 `inline_limit`
(기본값 30)을 넘으면 `to_file=`로 파일에 쓰도록 지정하지 않는 한 전체 트리를 인라인으로
반환하지 않습니다.

`read()`는 오직 *로드*만 합니다 — raw 레코딩을 가져와 그대로 반환합니다. 이를
decoder에 넣을 수 있는 윈도우로 만드는 것은 신호 소스가 아니라
[decoder](../decoder/index.md)의 역할입니다.

### `path=` 모드

로컬 레코딩은 메타데이터를 가져올 레지스트리 항목이 없으므로, `DatasetLoader(path=...)`는
`path` 안에 `dataset_info.py` 파일이 이미 존재해야 합니다(지연 실패가 아니라 생성 시점에
`FileNotFoundError`가 발생합니다). [`write_metadata_template()`][n2o.signal.dataset.metadata_template.write_template]로 생성할 수 있습니다:

```python
import n2o.signal.dataset as dataset

dataset.write_metadata_template(path)  # 비어 있는, 손으로 채울 수 있는 템플릿을 씁니다
```

채운 뒤 `DatasetLoader(path=...)`를 생성하세요. 이 모드에서 `read()`는 여전히
`NotImplementedError` 스텁입니다.

## `StreamLoader`

`DatasetLoader`와 같은 "샘플 읽기" 형태이지만 무한한 실시간 소스를 대상으로 합니다(유한
레코딩에 대한 인덱싱 접근이 아니라 최신 청크를 폴링) — 아직 구체 구현이 없으므로, 실제
디바이스 연동이 추가되기 전까지는 기본 인터페이스 외에 더할 내용이 없습니다.

## `SignalConfig`

[`SignalConfig`][n2o.signal.config.SignalConfig](`n2o.signal`)는 획득 설정에 대한 서술적 메타데이터입니다 — 전극 수, 채널
이름, 샘플레이트, 그리고 `SignalType.INVASIVE`인지 `SignalType.NON_INVASIVE`인지:

```python
from n2o.signal import SignalConfig, SignalType

signal_config = SignalConfig(
    num_electrode=14, name=("Fz", "Cz", "Pz"), hz=128, type=SignalType.NON_INVASIVE
)
```

`read()` 자체에서 소비되지는 않습니다 — `*Config` 계열(`DecoderConfig`, `RobotConfig`,
`CommandConfig`)의 나머지와 함께, 신호 소스의 설정을 문서화/계획하기 위한 것입니다.
