# Arm

변환된 command를 로봇 팔 구동으로 매핑하는 문서입니다.

## 레지스트리와 `RobotConfig`

모든 구체 `RobotArm`은 `@register_arm("Name")`을 통해 이름으로 자신을 등록합니다:

```python
from n2o.robot.arm import ARM_REGISTRY

ARM_REGISTRY  # {"LeRobotSO101": LeRobotSO101, "Gello": Gello, "MockArm": MockArm}
```

`RobotConfig(arm="LeRobotSO101")` + `Robot.from_config(...)`/`make_robot(...)`는 이름을
인스턴스로 해석합니다 —
[아키텍처 → `RobotConfig`로 로봇 조립하기](../../architecture.ko.md#robotconfig)
참고. 이는 추가적인 방식입니다: 직접 인스턴스를 대입하는 것(`robot.arm =
LeRobotSO101()`)도 항상 그대로 작동하며, 등록된 적 없는 ad hoc/시뮬레이션 팔에는 이
방법뿐입니다.

## `move()`와 `Controller`

`LeRobotSO101`은 선택적으로 `controller: Controller`를 받으며, `move()`는 바로
`self.controller.apply(decoder_type, command)`로 위임합니다 — 아무것도 할당되지
않았다면 `NotImplementedError`가 아니라 `RuntimeError`를 발생시킵니다. `Controller`는
더 낮은 레벨의 부위별 dispatcher(`apply(decoder_type, action)`)로, 하나의 동작을 벤더
SDK 호출이나 raw 모터 타깃으로 변환합니다 — [Controller](../../controller/index.md) 참고.

## 실물 하드웨어: `so101_real`

`src/n2o/robot/arm/so101_real/`는 실물(비시뮬레이션) SO-101 5-DOF 드라이버입니다:

- `lerobot_robot_so101_5dof/` — 프라이빗 로컬 패키지 3개 파일을 그대로 복사한
  vendored copy로, pip/uv 의존성이 아니라 순수 소스입니다.
- `connect_so101(port, **kwargs)`는 생성 + 연결을 하나로 감쌉니다.
- `SO101ArmRealController(Controller)`는 제스처 이름이나 `(ActionType, {"dx",
  "dy"})`를 joint-degree 타깃으로 변환한 뒤, 각 조인트의 스텝당 변화량이
  `lerobot` 자신의 `max_relative_target` 클램프를 넘지 않도록 속도를 제한하며 각
  조인트를 그 타깃까지 램프업합니다.

```python
from n2o.robot.arm import LeRobotSO101
from n2o.robot.arm.so101_real import SO101ArmRealController

arm = LeRobotSO101(controller=SO101ArmRealController(port="/dev/ttyACM0"))
```

`lerobot[feetech]`(`examples`/`demos` dependency group)가 필요하며, 지연 import됩니다.

## 시뮬레이션

`src/n2o/robot/simulation/`은 번들된 MuJoCo 레퍼런스 시뮬레이터를 제공합니다 —
`SO101ArmSim(RobotArm)`은 실제 MJCF 모델로 구동됩니다. `N2O.run(simulation=True)`는
`robot.arm`/`robot.hand` 대신 이를 구동하며, `N2O` 인스턴스마다 지연 생성 후
캐시합니다. `mujoco`는 `examples`/`demos` 그룹 전용 의존성입니다 — `n2o.robot` 아래
어디에서도 `robot/simulation/`을 즉시 import하지 않습니다.
