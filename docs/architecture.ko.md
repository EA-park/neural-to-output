# 아키텍처

## 파이프라인

파이프라인은 고정되어 있습니다:

```
signal -> decoder -> command -> robot (arm / hand / camera)
                  \-> controller (decoder.output_type가 FeatureType.LANGUAGE인 경우)
```

`N2O`(`n2o/__init__.py`)는 `signal` + `decoder` + `command` + `robot` + `controller`를
하나로 엮어 `run(simulation: bool = False)`으로 구동합니다:

1. `self.signal.read()`가 샘플을 반환합니다 — 일반적인 매 스텝 케이스에서는 윈도잉된
   배열이고, (오프라인의 경우) 윈도잉되지 않은 raw 데이터셋이면 decoder가 자동으로
   `prepare()`합니다.
2. `self.decoder(sample)`이 이를 원시 예측값으로 디코딩합니다 (`self.decoder(sample)`은
   `Decoder.__call__()`을 통한 `.decode(sample)`의 축약형입니다).
3. 모든 `Decoder` 서브클래스는 `output_type` ClassVar(`FeatureType.ACTION` 또는
   `FeatureType.LANGUAGE`)를 선언하며, 이것이 다음 단계를 결정합니다:
      - `FeatureType.ACTION`은 `Command.translate()`(아래 참고)를 거친 뒤, 대상이 되는
        부위에 대해 `robot.arm.move()`/`robot.hand.move()`로 이어집니다.
      - `FeatureType.LANGUAGE`는 바로 `controller.act(decoded_signal, robot)`로
        전달됩니다.
4. `run()`은 `getattr(self.decoder, "cycle", 1)`만큼 이를 반복합니다 — 대부분의 decoder는
   `cycle`을 기본값 `1`로 둡니다(매 호출마다 가장 최근 샘플을 디코딩). 정적 오프라인
   레코딩 하나로 `run()` 한 번에 여러 결과를 시연하려는 decoder(예: `OfnerEEGNet`)는 자신의
   `__init__()`에서 이 값을 올립니다.

## `Command`: decoder의 원시 출력을 부위별 동작으로 변환하기

`Command.translate(decoder, decoded_signal)`은 decoder의 원시 예측값이 로봇 동작으로
매핑되는 유일한 지점입니다 — [`Decoder`][n2o.decoder.base.Decoder]는 순수한 예측기로 유지하고, 그 매핑은 decoder가
아니라 [`Command`][n2o.command.command.Command]에 두세요. 기본 `translate()`는 `decoded_signal`이 이미 로봇 부위별로
키가 잡혀 있다고(`{"arm": ..., "hand": ...}`) 가정합니다 — decoder의 원시 출력에 실제
변환이 필요하다면 오버라이드하세요.

각 부위의 결과값은 그 자체로 의미가 통하는 이름(예: `"grip"`)이거나, 그 자체로는 의미가
통하지 않는 raw 값(예: regression 숫자/딕셔너리)을 위한 `(ActionType, value)` 튜플입니다 —
[`ActionType`][n2o.command.command.ActionType](`JOINT_ABSOLUTE`, `JOINT_RELATIVE`, `CARTESIAN_ABSOLUTE`,
`CARTESIAN_RELATIVE`)은 decoder 자신의 `DecoderType`과 무관하게 값과 함께 전달됩니다.

`Command` 서브클래스는 보통 노트북 로컬로 작성됩니다 — 특정 decoder의 원시 출력을 특정
로봇의 부위로 매핑하는 것이기 때문입니다. `src/`에는 두 개가 포함되어 있습니다:
[`GripSpreadCommand`][n2o.command.grip_spread.GripSpreadCommand](motor-imagery 라벨 → [`AmazingHand`][n2o.robot.hand.amazing_hand.AmazingHand]의 손가락별 포즈)와
[`OfnerCommand`][n2o.command.ofner_command.OfnerCommand](`OfnerEEGNet`의 7개 원시 라벨 → arm-or-hand 제스처 하나씩).

자세한 내용은 [Decoder](decoder/index.md)와 [Command](command/index.md)를 참고하세요.

## `run()` 전에 파이프라인 확인하기

[`CommandConfig`][n2o.command.config.CommandConfig](`command` 경계를 위한 별도의 선언적 계약으로, `SignalConfig`/
`DecoderConfig`가 `signal`/`decoder`와 짝을 이루는 것과 같은 방식으로 `Command`와
짝을 이룹니다)를 사용하면 `run()`하기 전에 연결된 파이프라인을 점검할 수 있습니다:

```python
n2o.command_config.verify_report(n2o)
```

`signal -> decoder -> command -> robot.arm/hand`를 따라가며 일치/불일치/미정 표를
출력합니다 — `N2O.verify()` 메서드는 없으므로 이걸 직접 호출하세요.

## `RobotConfig`로 로봇 조립하기

`robot.arm`/`robot.hand`/`robot.camera`/`controller`는 각각 레지스트리를 통해 이름으로
빌드할 수 있습니다 — `@register_arm("Name")`(및 `hand`/`camera`/`controller`용 동일
데코레이터)로 클래스를 등록하고:

```python
from n2o.robot import RobotConfig, make_robot

config = RobotConfig(arm="LeRobotSO101", hand="AmazingHand", camera="MockCamera")
robot = make_robot(config)
```

이는 **추가적인** 방식입니다 — ad hoc/시뮬레이션 컴포넌트는 절대 레지스트리에 등록되지
않으므로, 직접 속성을 대입하는 방식(`robot.arm = SomeInstance()`)도 항상 그대로
작동합니다.

## 라우팅: `FeatureType`과 `controller`

[`FeatureType`][n2o.decoder.config.FeatureType]`.LANGUAGE` 타입의 decoder는 `Command` 대신 `controller.act(decoded_signal,
robot)`로 라우팅됩니다 — 의도된 형태는 [Controller](controller/index.md)를 참고하세요
(이름은 같지만 `n2o.robot.controller.Controller`는 *다른*, 더 낮은 레벨의 개념입니다 —
`RobotArm`/`RobotHand` 구현체가 소유하는 부위별 dispatcher입니다).

## 패키지 구조

`src/n2o/`는 파이프라인을 형제 패키지들로 그대로 반영합니다:

- `signal/dataset/`, `signal/stream/` — 오프라인/인덱싱된 신호 소스와 실시간 신호 소스
- `decoder/`, 그리고 그 아래의 `classification/`, `regression/`, `utils/` 서브패키지 —
  signal → 원시 예측값
- `command/` — 원시 예측값 → 부위별 동작
- `robot/arm/`, `robot/hand/`, `robot/camera/` — 액추에이터/센서, 그리고
  `robot/simulation/`(번들된 MuJoCo 레퍼런스 시뮬레이터)와 `robot/controller.py`
  (부위별 `Controller` ABC)
- `third_party/`(저장소 최상위) — pip/uv로 설치할 수 없는 업스트림 프로젝트의 vendored
  복사본. [Third-Party](third-party/index.md) 참고

대부분의 패키지는 같은 확장 패턴을 따릅니다: `base.py` ABC 하나에 구체 구현마다 파일
하나씩을 두고, 해당 패키지의 `__init__.py`에서 다시 export합니다. 예외 사항과 세부
내용은 각 섹션의 페이지를 참고하세요.
