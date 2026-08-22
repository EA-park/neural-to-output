# Controller

언어(language) 타입으로 디코딩된 명령을 로봇으로 라우팅하는 방법에 대한 문서입니다.

## `LanguageController`

`LanguageController`(`n2o.controller`)는 `FeatureType.LANGUAGE` 타입의 디코더 명령과 `robot.arm/hand.move()` 사이에 위치합니다 — 그동안 모호했던 "middleware" 단계가 VLA(vision-language-action) 스타일 지시에 대해 갖게 된 실제 답입니다. `FeatureType.ACTION` 명령은 영향받지 않고 그대로(선택적으로 `Command`를 거쳐 — [아키텍처 → `Command`](../architecture.ko.md#command) 참고) `robot.arm/hand.move()`로 직행합니다.

```python
from n2o.controller import LanguageController


class LanguageController(ABC):
    def act(self, command, robot):
        """FeatureType.LANGUAGE 명령에 따라 robot을 구동합니다."""
```

참조를 저장하는 대신 `robot`을 인자로 받아, 다른 모든 파이프라인 단계처럼 상태를 갖지 않습니다. `n2o.decoder.output_type`이 `FeatureType.LANGUAGE`이면 `N2O.run()`이 이를 자동으로 호출합니다 — [아키텍처 → 라우팅](../architecture.ko.md#featuretype-languagecontroller) 참고.

**`n2o.robot.controller.Controller`(예전 `MotorWrapper`)와는 다른 개념입니다** — 그건 로봇 부품 하나가 소유하는, 더 저수준의 무관한 개념입니다: 행동 하나(예: `"grip"` 또는 `(ActionType, value)` 튜플)를 `apply(decoder_type, action)`으로 벤더 SDK 호출이나 저수준 모터 목표값으로 바꾸는 부품별 디스패처로, `RobotArm`/`RobotHand` 구현체가 소유합니다. 두 클래스는 "controller"라는 단어만 같을 뿐, 파이프라인의 서로 다른 지점에서 서로 다른 문제를 풉니다.

## 레지스트리와 `RobotConfig`

`robot.arm`/`robot.hand`/`robot.camera`와 마찬가지로, `LanguageController`도 `@register_controller("Name")`을 통해 스스로를 등록하며, `RobotConfig(controller="VLA")`는 파이프라인이 어떤 것을 쓸지 이름으로 지정합니다(`n2o.controller.make_controller("VLA")`로 해석한 뒤 `n2o.controller`에 대입 — `RobotConfig`의 `controller` 필드는 `make_robot()`/`Robot.from_config()`가 해석하지 않습니다. `LanguageController`는 `Robot`이 아니라 `N2O`에 속하기 때문입니다).

현재는 `VLAController`만 존재하며, 인터페이스만 있는 스텁입니다(`raise NotImplementedError`).
