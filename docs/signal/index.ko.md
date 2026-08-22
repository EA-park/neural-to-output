# Signal

지원되는 생체 전기 신호 종류(예: EEG, EMG)와 수집 방법에 대한 문서입니다.

## Dataset vs. Stream

신호 소스는 두 가지 형태로 나뉘며, 각각 `n2o.signal` 아래에 별도의 기본 인터페이스를 가집니다:

- **`n2o.signal.dataset`** — `SignalDataset.read()`는 저장된 파일 같은, 길이가 확정된 오프라인 녹화 데이터를 읽습니다. 기본 제공: `EEG`(비침습), `InvasiveEEG`, `EMG`.
- **`n2o.signal.stream`** — `SignalStream.read()`는 실시간 장치 연결 같은, 끝이 없는 소스에서 최신 청크를 읽습니다. 기본 제공: `EEGStream`, `EMGStream`.

`SignalStream`은 `SignalDataset`의 서브클래스가 아니라 형제 인터페이스입니다 — 둘은 의미가 실제로 다릅니다(유한한 녹화 데이터에 대한 인덱싱 접근 vs. 링 버퍼 폴링). 이는 MNE 생태계의 `mne.io.Raw`와 `mne_lsl.stream.StreamLSL`의 구분을 그대로 따온 것입니다. 두 인터페이스 모두 동일한 `output_spec` 클래스 속성을 노출하므로, `CommandConfig.verify_report()`는 어느 쪽 소스든 decoder의 `input_spec`과 동일하게 비교합니다.

## `SignalConfig`

`SignalConfig`(`n2o.signal`)는 전극 수, 채널 이름, 샘플링 레이트, 그리고 침습형(`SignalType.INVASIVE`)인지 비침습형(`SignalType.NON_INVASIVE`)인지 등 수집 설정에 대한 설명용 메타데이터로, `output_spec`의 형태 계약과는 별개입니다:

```python
from n2o.signal import SignalConfig, SignalType

signal_config = SignalConfig(
    num_electrode=14, name=("Fz", "Cz", "Pz"), hz=128, type=SignalType.NON_INVASIVE
)
```

`type`은 어떤 클래스를 쓰는지(`EEG` vs `InvasiveEEG`는 이미 클래스 자체로 이를 나타냅니다)와는 독립적입니다 — `SignalConfig`가 이를 스스로도 선언할 수 있게 해줍니다. `read()`가 직접 `SignalConfig`를 소비하지는 않습니다 — `DecoderConfig`, `RobotConfig`, `CommandConfig`와 함께 `*Config` 계열의 일부로서, 신호 소스의 수집 설정을 문서화/계획하기 위한 용도입니다.

여기 있는 모든 구체 클래스는 현재 인터페이스만 존재하는 스텁입니다(`raise NotImplementedError`).
