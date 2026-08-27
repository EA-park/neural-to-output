# Controller

language 타입으로 디코딩된 예측값을 로봇으로 라우팅하는 문서입니다.

## `controller.act()` 계약

`output_type`이 `FeatureType.LANGUAGE`인 decoder에 대해, `N2O.run()`은
[`Command`](../command/index.md)를 완전히 건너뛰고 대신
`self.controller.act(decoded_signal, self.robot)`을 호출합니다 — 고정된 부위별 동작
형태로 변환할 수 없는 VLA 스타일(vision-language-action) 지시에 대한 답입니다:

```python
class LanguageController(ABC):
    def act(self, command, robot):
        """FeatureType.LANGUAGE로 디코딩된 예측값에 따라 `robot`을 구동합니다."""
```

참조를 저장하는 대신 `robot`을 인자로 받아, 다른 모든 파이프라인 단계와 마찬가지로
상태를 갖지 않게 유지합니다.
[아키텍처 → 라우팅](../architecture.ko.md#featuretype-controller) 참고.

!!! note
    현재 저장소 스냅샷에는 구체적인 `LanguageController` 구현이 포함되어 있지 않습니다
    — `n2o.controller`는 현재 재작업 중입니다. 그동안 `FeatureType.LANGUAGE` decoder를
    사용하려면 `act(decoded_signal, robot)`을 노출하는 아무 객체나 `n2o.controller`에
    설정하세요.

## `n2o.robot.controller.Controller`와는 다릅니다

두 클래스는 "controller"라는 이름을 공유하지만, 파이프라인의 서로 다른 지점에서 서로
다른 문제를 해결합니다:

|              | `controller.act()`                                | `n2o.robot.controller.Controller`                        |
| ------------ | ---------------------------------------------------- | -------------------------------------------------------------- |
| 소속          | `N2O`(`n2o.controller`)                               | `RobotArm`/`RobotHand` 구현체                                    |
| 처리 대상      | `FeatureType.LANGUAGE`로 디코딩된 예측값 전체            | 이미 해석된 부위별 동작 하나                                        |
| 호출 주체      | `N2O.run()`, `Command` 대신                            | `robot.arm.move()`/`robot.hand.move()`                          |
| 결과물        | 지시가 의미하는 로봇의 동작 전체                          | 벤더 SDK 호출 또는 raw 모터 타깃 ([Arm](../robot/arm/index.ko.md#move-controller) 참고) |

## 레지스트리와 `RobotConfig`

`robot.arm`/`robot.hand`/`robot.camera`와 마찬가지로, controller도
`@register_controller("Name")`을 통해 스스로를 등록하도록 되어 있으며,
`RobotConfig(controller="...")`가 파이프라인이 사용하려는 것을 지정합니다 —
`make_controller(...)`로 해석된 뒤 `n2o.controller`에 직접 대입됩니다(`RobotConfig`의
`controller` 필드는 `make_robot()`/`Robot.from_config()`가 해석하지 않습니다 — language
controller는 `Robot`이 아니라 `N2O`에 소속되기 때문입니다).
