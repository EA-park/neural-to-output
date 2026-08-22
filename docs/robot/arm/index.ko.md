# Arm

디코딩된 명령을 로봇 팔 구동으로 매핑하는 방법에 대한 문서입니다.

## 레지스트리와 `RobotConfig`

모든 구체 `RobotArm`은 `@register_arm("Name")`을 통해 이름으로 자기 자신을 등록합니다:

```python
from n2o.robot.arm import ARM_REGISTRY

ARM_REGISTRY  # {"LeRobotSO101": LeRobotSO101, "Gello": Gello, "MockArm": MockArm}
```

`RobotConfig(arm="LeRobotSO101")` + `Robot.from_config(...)`/`make_robot(...)`은 이름을 인스턴스로 변환합니다 — [아키텍처 → `RobotConfig`로 로봇 만들기](../../architecture.ko.md#robotconfig) 참고. 이는 추가적인(additive) 방법입니다: 인스턴스를 직접 대입하는 방식(`robot.arm = LeRobotSO101()`)은 항상 그대로 동작하며, 등록된 적 없는 임시/시뮬레이션용 팔에는 이 방법만 사용할 수 있습니다.

`MockArm`을 제외한 모든 구체 팔 클래스는 현재 인터페이스만 존재하는 스텁입니다(`raise NotImplementedError`).
