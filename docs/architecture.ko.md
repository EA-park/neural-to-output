# Architecture

## 파이프라인

`n2o`는 서로 교체 가능한 세 가지 컴포넌트를 하나의 오케스트레이터 `N2O`로 연결합니다:
`signal` 소스가 `decoder`로 디코딩되어 명령이 되고, 이 명령이 `robot`의 `arm`과
`hand`로 전달됩니다.

```python
from n2o import N2O
from n2o.signal.dataset import EEG
from n2o.decoder import EEGNet
from n2o.robot.arm import LeRobotSO101
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = EEG()
n2o.decoder = EEGNet()
n2o.robot.arm = LeRobotSO101()
n2o.robot.hand = AmazingHand()
n2o.run()
```

`N2O.run()`은 `signal`에서 샘플 하나를 읽고, `decoder`로 명령을 디코딩한 뒤, 그
명령을 `robot.arm`과 `robot.hand` 양쪽으로 보냅니다.

## 패키지 구조

`src/n2o/`는 이 파이프라인을 형제 패키지들로 그대로 반영합니다. 각 패키지는 동일한
패턴을 따릅니다: 인터페이스를 정의하는 `base.py` 추상 클래스, 구현체마다 하나씩의
파일, 그리고 공개 이름을 re-export하는 `__init__.py`.

| 패키지                 | 인터페이스                | 기본 제공 구현체                           |
| --------------------- | ----------------------- | -------------------------------------------- |
| `n2o.signal.dataset`   | `SignalDataset.read()`   | `EEG` (비침습), `InvasiveEEG`, `EMG`         |
| `n2o.decoder`          | `Decoder.decode(signal)` | `EEGNet`, `EMGDecoder`                       |
| `n2o.robot.arm`        | `RobotArm.move(command)` | `LeRobotSO101`, `Gello`, `MockArm`           |
| `n2o.robot.hand`       | `RobotHand.move(command)`| `AmazingHand`, `MockHand`                    |

`n2o.robot.Robot`은 `arm` 하나와 `hand` 하나를 묶는 단순한 컨테이너입니다.

`MockArm`/`MockHand`를 제외한 모든 구현체는 현재 인터페이스만 존재하는 스텁입니다
(`raise NotImplementedError`) — 아직 실제 하드웨어/모델 연동은 없습니다. 실제
하드웨어 없이 전체 파이프라인을 실행해보려면 `Mock*` 클래스를 사용하세요.

새 데이터셋/디코더/로봇을 추가하는 방법은
[Tutorials → Adding a Component](tutorials/adding-a-component.md)를 참고하세요.
