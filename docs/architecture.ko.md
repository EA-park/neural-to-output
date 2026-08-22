# Architecture

## 파이프라인

`n2o`는 서로 교체 가능한 네 가지 컴포넌트를 하나의 오케스트레이터 `N2O`로 연결합니다:
`signal` 소스가 `decoder`로 디코딩되어 원시 예측값이 되고, `command`가 이를 부품별
행동으로 변환해서 `robot`의 `arm`과 `hand`로 전달합니다.

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

`N2O.run()`은 `signal`에서 샘플 하나를 읽고, `decoder`로 디코딩한 뒤(`Decoder`
인스턴스는 호출 가능한 객체입니다 — `self.decoder(sample)`은
`self.decoder.decode(sample)`의 축약형입니다), decoder의 `output_type`에 따라
분기합니다:

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

이는 catch-all이 아니라 엄격한 검사입니다 — 모든 `Decoder` 서브클래스는
`output_type`을 `FeatureType.ACTION` 또는 `FeatureType.LANGUAGE` 중 하나로
반드시 선언해야 합니다([라우팅](#featuretype-languagecontroller) 참고). 그 외의
경우(선언하지 않은 기본값 `None` 포함)에는 `run()`이 `ValueError`를 발생시킵니다
— 암묵적인 대체 동작은 없습니다.

## `Command`: 디코더의 원시 출력을 부품별 행동으로 바꾸기

`Decoder`는 순수한 예측기로 남아야 합니다 — `decode()`는 `robot.arm`/`robot.hand`에
맞춰 이미 가공된 형태가 아니라, 원시 예측값(예: 라벨 문자열이나 회귀값 dict)을 그대로
반환합니다. 그 예측값을 가지고 각 로봇 부품이 무엇을 *해야 하는지* 결정하는 건
`n2o.command`에 설정하는 `Command`의 역할입니다:

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

기본 `Command.translate()`는 `decoded_signal`이 이미 로봇 부품별로 키가 매겨진
형태(`{"arm": ..., "hand": ...}` — 예: 부품별 독립 서브모델을 감싼 디코더)라고
가정합니다 — 디코더의 원시 출력을 그 형태로 실제로 변환해야 할 때마다(위 예시처럼)
`translate()`를 오버라이드해서 서브클래싱하세요. 별도의 "연속값" 버전은 없습니다 —
`translate()`를 오버라이드하는 것만으로 이산/연속 디코더 양쪽을 같은 `Command`
기반 클래스로 다룰 수 있기 때문입니다.

`command.translate(decoder, decoded_signal)`은 `"type"` 키(디코더의
`config.type`을 그대로 전달 — `move()`/`Controller.apply()`가 필요하면 이를 보고
분기할 수 있도록)와 로봇 부품별 키를 담은 dict를 반환합니다. 각 부품의 값은 이미
자기 설명적인 이름(예: `"grip"`)이거나 `(ActionType, value)` 튜플입니다 — raw
회귀값은 그 자체로는 의미를 설명하지 못하므로, 어떻게 해석해야 하는지 알려주는
`ActionType`과 짝지어집니다:

```python
from n2o.command import ActionType

command["arm"] = (
    ActionType.JOINT_ABSOLUTE,
    {"shoulder_lift": 0.31, "elbow_flex": -0.08},
)
```

`ActionType`(`n2o.command`)에는 `JOINT_ABSOLUTE`, `JOINT_RELATIVE`,
`CARTESIAN_ABSOLUTE`, `CARTESIAN_RELATIVE` 네 가지 값이 있습니다. 이는 값과 함께
전달되며, `"type"`에 담기는 디코더 자신의 `DecoderType`(`CLASSIFICATION`/
`REGRESSION`)과는 독립적입니다.

`N2O.run()`은 `command.translate(decoder, decoded_signal)`을 호출해서 각 부품에
결과값을 보냅니다: `robot.arm.move(actions["type"], actions["arm"])`,
`robot.hand.move(actions["type"], actions["hand"])`.

`robot.arm.move()`가 행동값을 받으면, 그걸 실제 모터 목표값이나 벤더 SDK 호출로
바꾸는 무언가가 여전히 필요합니다 — 그게 바로 (예전 `MotorWrapper`를 이름만 바꾼)
`n2o.robot.controller.Controller`이며, `RobotArm`/`RobotHand` 구현체 자신이
소유합니다: 보통 `move()`가 곧바로 `self.controller.apply(decoder_type, action)`에
위임합니다. 아래의 파이프라인 레벨 `LanguageController`와는 이름만 같을 뿐 다른
개념입니다 — 하나는 로봇 부품 하나에 대한 행동 하나를 디스패치하고, 다른 하나는
language 타입 명령 전체를 라우팅합니다.

## `run()` 전에 파이프라인 점검하기

각 `base.py` 인터페이스는 선택적인 `input_spec`/`output_spec` 클래스 속성(단순
`dict | None`, 기본값 `None` = "아직 정하지 않음")을 노출하므로, 구현체가 자신의
계약을 선언할 수 있습니다:

```python
class EEGWindowDecoder(Decoder):
    input_spec = {"channels": 59, "samples": 100}
    output_spec = {"x": "float", "y": "float"}
```

`CommandConfig`(`n2o.command`, `Command`와 같은 패키지)는 `command` 경계에 대한
선언적이고 `verify_report()` 전용인 계약입니다 — 원하는 형태를 정했다면 넘긴 뒤
그 `verify_report(n2o)` 메서드를 호출해서 `signal -> decoder -> command ->
robot.arm/hand`를 따라가며 각 경계의 스펙이 서로 맞는지 확인하고 표로 출력할 수
있습니다:

```python
from n2o.command import CommandConfig

n2o.command_config = CommandConfig(
    input_feature={"x": "float", "y": "float"},
    output_feature={"joint_targets": "dict[str, float]"},
)
report = n2o.command_config.verify_report(n2o)
print(report)  # 단계 | 출력 스펙 | -> | 단계 | 입력 스펙 | 상태 (OK/MISMATCH/미정)
report.ok  # 모든 경계가 확정적으로 일치할 때만 True
```

`N2O.verify()` 메서드는 없습니다 — 대신 `CommandConfig.verify_report()`가 `n2o`를
인자로 받습니다. 검사 로직이 애초에 `command` 단계에 속하기 때문입니다.
`command_config`를 설정하지 않으면 그 양쪽 경계가 모두 "미정"으로 표시되어, 아직
풀리지 않은 빈틈이 있다는 걸 시각적으로 바로 알 수 있습니다. `CommandConfig`는
`SignalConfig`/`DecoderConfig`/`RobotConfig`와 한 가족을 이룹니다(파이프라인
단계/경계마다 하나씩의 config 데이터클래스). `run()`에는 아무 영향이 없습니다 —
순전히 로직을 작성하기 전에 `command` 경계의 계약을 이웃 단계들과 미리
설계해보기 위한 선언적 용도입니다.

## `RobotConfig`로 로봇 만들기

위 예제는 각 로봇 부품을 직접 생성해서 대입하며, 이 방식은 항상 동작합니다 —
등록된 적 없는 임시/시뮬레이션용 컴포넌트(예: 노트북 하나를 위해 즉석에서 만든
`RobotHand` 서브클래스)에는 이 방법밖에 없습니다.

이름이 있는 재사용 가능한 하드웨어라면, `robot.arm`/`robot.hand`/`robot.camera`를
레지스트리를 통해 문자열 이름으로부터 만들 수도 있습니다. 모든 구체 클래스는
데코레이터로 스스로를 등록합니다:

```python
from n2o.robot.arm import ARM_REGISTRY

ARM_REGISTRY  # {"LeRobotSO101": LeRobotSO101, "Gello": Gello, "MockArm": MockArm}
```

`RobotConfig`가 각 부품의 이름을 담고, `Robot.from_config()`/`make_robot()`이
이를 인스턴스로 변환합니다:

```python
from n2o.robot import Robot, RobotConfig

robot = Robot.from_config(RobotConfig(arm="LeRobotSO101", hand="AmazingHand"))
```

이는 기존 방식을 대체하는 게 아니라 추가된 방법입니다 — 하드웨어를 바꾸는 일이
import + 인스턴스 생성 코드를 고치는 대신 config 한 줄만 바꾸면 되는 일이 되지만,
직접 대입하는 방식도 그대로 남아 있습니다. `RobotConfig.controller`는
([라우팅](#featuretype-languagecontroller)에서 설명할) `LanguageController`의
이름을 담지만, `make_robot()`/`Robot.from_config()`는 이 필드를 해석하지 않습니다
— `Robot`이 아니라 `N2O`에 속하기 때문입니다. 그 필드에는
`n2o.controller.make_controller()`를 사용하세요.

## 라우팅: `FeatureType`과 `LanguageController`

모든 `Decoder` 서브클래스는 `output_type` 클래스 속성을 반드시 선언해야 합니다 —
이 디코더가 어떤 종류의 예측값을 만드는지 나타내는 `FeatureType`(`SIGNAL`,
`LANGUAGE`, `ACTION`)입니다. `N2O.run()`은 실행 시점에 이 값을 읽습니다:

- `FeatureType.ACTION` — 위와 똑같이 예측값이 `n2o.command.translate()`를 거쳐
  `robot.arm.move()`/`robot.hand.move()`로 갑니다.
- `FeatureType.LANGUAGE` — VLA(vision-language-action) 스타일 지시 수행을 위해,
  대신 `n2o.controller.act(decoded_signal, n2o.robot)`로 라우팅됩니다.
- 그 외의 경우(선언하지 않은 기본값 `None` 포함)에는 `run()`이 `ValueError`를
  발생시킵니다 — 조용히 넘어가는 대체 동작은 없습니다.

```python
from n2o.decoder import Decoder, FeatureType


class MyLanguageDecoder(Decoder):
    output_type = FeatureType.LANGUAGE

    def decode(self, signal): ...


n2o.controller = ...  # LanguageController 인스턴스, 예: n2o.controller.VLAController()
```

`LanguageController`도 `robot.arm`/`robot.hand`/`robot.camera`와 동일한 레지스트리
패턴을 따릅니다(`@register_controller("Name")`, `n2o.controller.make_controller
("Name")`으로 해석). 다만 한 가지는 아직 선언적 수준에만 머물러 있습니다:
`CommandConfig.output_type`(`verify_report()`가 사용)과 디코더의 실행 시점
`output_type`은 서로 별개의 선언이며, 아직 둘을 교차 검증하지는 않습니다.

`Decoder`의 `config` 속성(`__init__`에서 설정하는 `DecoderConfig` 인스턴스이며,
`ClassVar`가 아닙니다)은 이 디코더가 `ACTION` 타입 예측값을 *어떻게* 만드는지를
별도로 설명합니다: `config.type`은 `DecoderType`(`CLASSIFICATION` 또는
`REGRESSION`)이거나, 하나 이상의 내부 모델을 감싼 디코더(예: trunk를 공유하지 않는
분류 모델 1개 + 회귀 모델 1개)라면 `tuple[DecoderType, ...]`일 수 있습니다.
`Command.translate()`는 `decoder.config.type`을 읽어서 `decoded_signal`을 어떻게
해석할지 정하고, 이를 `"type"` 키로 그대로 전달해서 `robot.arm/hand.move()`도 받을
수 있게 합니다.

## 패키지 구조

`src/n2o/`는 이 파이프라인을 형제 패키지들로 그대로 반영합니다. 각 패키지는 동일한
패턴을 따릅니다: 인터페이스를 정의하는 `base.py` 추상 클래스, 구현체마다 하나씩의
파일, 그리고 공개 이름을 re-export하는 `__init__.py`.

| 패키지                 | 인터페이스                                     | 기본 제공 구현체                    |
| --------------------- | ----------------------------------------------- | ------------------------------------ |
| `n2o.signal.dataset`   | `SignalDataset.read()`                          | `EEG` (비침습), `InvasiveEEG`, `EMG` |
| `n2o.signal.stream`    | `SignalStream.read()`                           | `EEGStream`, `EMGStream`             |
| `n2o.decoder`          | `Decoder.decode(signal)`                        | `EEGNet`, `EMGDecoder`               |
| `n2o.command`          | `Command.translate(decoder, decoded_signal)`    | —                                     |
| `n2o.robot.arm`        | `RobotArm.move(decoder_type, command)`          | `LeRobotSO101`, `Gello`, `MockArm`   |
| `n2o.robot.hand`       | `RobotHand.move(decoder_type, command)`         | `AmazingHand`, `MockHand`            |
| `n2o.robot.camera`     | `RobotCamera.capture()`                         | `MockCamera`                         |
| `n2o.controller`       | `LanguageController.act(command, robot)`        | `VLAController`                      |

`n2o.robot.Robot`은 `arm`, `hand`, `camera`를 묶는 단순한 컨테이너입니다.
`n2o.command`는 다른 패키지들과 달리 레지스트리 패턴을 따르지 않습니다 —
`Command` 서브클래스는 항상 파이프라인마다 직접 작성하는 것이라(한 디코더의
원시 출력을 한 로봇의 부품들로 매핑하는 방식을 그대로 인코딩하므로), 등록해둘
재사용 가능한 기본 구현이 없습니다.

`MockArm`/`MockHand`/`MockCamera`를 제외한 모든 구현체는 현재 인터페이스만
존재하는 스텁입니다(`raise NotImplementedError`) — 아직 실제 하드웨어/모델
연동은 없습니다. 실제 하드웨어 없이 전체 파이프라인을 실행해보려면 `Mock*`
클래스를 사용하세요.

새 데이터셋/디코더/로봇을 추가하는 방법은
[Tutorials → Adding a Component](tutorials/adding-a-component.md)를 참고하세요.
