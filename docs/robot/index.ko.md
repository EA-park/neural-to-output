# Robot

[`Robot`][n2o.robot.Robot]은 로봇의 각 파츠(`arm`/`hand`/`camera`)를 묶는 허브입니다. [`Command.translate()`](../command/index.ko.md)가
만든 명령 딕셔너리를 받아:

1. 어느 파츠로 보낼지,
2. 그리고 `ControllerType`을 통해 그 파츠를 *어떻게* 구동할지(실물 하드웨어 /
   시뮬레이션 / VLA)를 결정합니다.

## `Part` 인터페이스

`Robot`이 라우팅할 수 있는 모든 파츠(예: `AmazingHand`)는 [`n2o.robot.Part`][n2o.robot.part.Part]를
구현합니다:

```python
class Part(ABC):
    def goal(self, cmd):
        """목표값만 계산합니다 -- I/O 없음, 아무것도 물리적으로 움직이지 않습니다."""

    def move(self, cmd):
        """`cmd`를 향해 실제 하드웨어를 구동합니다."""
```

- `goal(cmd)` — 순수 계산입니다. 하드웨어를 건드리지 않고 목표값만 미리 확인할 때
  씁니다 — I/O 없음, 아무것도 물리적으로 움직이지 않습니다.
- `move(cmd)` — 실제로 하드웨어를 구동합니다.
- `done_event`(`threading.Event`, `Part`에 이미 구현돼 있어 서브클래스가 따로 만들
  필요 없음) — `Robot.router()`가 이 파츠를 디스패치하기 직전에 `clear()`, 목표
  위치로 이동을 마치면(`SIMULATION`이면 `Simulator.drive()` 이후, `MOTOR_DRIVER`면
  `move()` 이후 — 실패해도 마찬가지) `set()`합니다. 다른 코드가
  `part.done_event.wait()`/`.is_set()`으로 그 파츠의 완료 여부를 기다리거나 확인할
  수 있습니다 — 아래 "파츠별 동시 구동" 절, `ROADMAP.md`의 "시퀀싱을 py_trees로"
  항목 참고.

`move(cmd)`는 명령을 *보내기만* 하고 바로 리턴하면 안 됩니다 — `done_event`가
"진짜 다 움직였다"는 뜻이 되려면 `move()` 자신이 실제(또는 실측 기반 추정)
이동 시간만큼 블록해야 합니다. `SO101Arm`은 실시간 ramp로, `AmazingHand`는
`MOVE_SETTLE_S`만큼의 추정 sleep으로 이걸 보장합니다.

파츠 구현체가 자기 하드웨어 연결을 직접 소유합니다(예: `AmazingHand`는 `rustypot`
시리얼 연결을 지연 생성해 직접 소유) — `Robot` 자신은 하드웨어와 직접 통신하지
않습니다.

## `ControllerType`과 라우팅

`Robot.controller`는 [`ControllerType`][n2o.robot.ControllerType](`SIMULATION`/`MOTOR_DRIVER`/`VLA`) 값입니다.
`Robot.router(actions)`는 호출마다 이 값을 한 번 읽어서, `actions`에 담긴 각 파츠에
대해 `goal()`을 부를지 `move()`를 부를지 결정합니다:

| `ControllerType`  | `router()`가 호출하는 것            | 상태                              |
| ------------------ | ------------------------------------- | ----------------------------------- |
| `SIMULATION`       | `part.goal(cmd)` — 목표값만, `robot.simulator`가 있으면 그걸로 시각화까지 | 구현됨 |
| `MOTOR_DRIVER`      | `part.move(cmd)` — 실물 하드웨어 구동    | 구현됨                              |
| `VLA`                | *(예정)* camera 입력과 함께 `part.<명령어>()` | 미구현 — 호출 시 `NotImplementedError` |

```python
from n2o.robot import ControllerType, Robot
from n2o.robot.arm.so101 import SO101Arm

robot = Robot()
robot.arm = SO101Arm(port="/dev/ttyACM0")
robot.controller = ControllerType.MOTOR_DRIVER
robot.router({"arm": "up", "hand": None})
```

`N2O.run(controller=...)`은 `router()`를 호출하기 전에 `robot.controller`를 대신
설정해 줍니다:

- `"motor_driver"`
- `"simulation"` — `robot.simulator`가 비어 있을 때 자동으로 `Simulator()`를 만들어
  대입하고, 실제로 할당된 파츠의 뷰어까지 미리 엽니다. 자세한 내용은 아래
  `Simulator` 절 참고.
- `"vla"`

## 파츠별 동시 구동

`router()`는 `actions`에 담긴 각 파츠를 **자기 스레드에서** 구동합니다 — 스레드
생성/시작/join은 전부 `Robot`이 직접 담당합니다(`N2O`도 아니고 `Part` 자신도 아님).
매 호출마다 파츠 개수만큼 스레드를 새로 만들고 반환 전에 전부 join하므로, 호출하는
쪽에서 보기엔 여전히 동기 함수입니다.

파이썬은 GIL 때문에 스레드로 CPU-bound 연산을 진짜 병렬로 못 돌리는 걸로 잘 알려져
있지만, `Part.move()`(시리얼 I/O + `time.sleep()` 램핑)와 `Simulator.drive()`
(`mujoco.mj_step()`)는 둘 다 대기 중에 GIL을 놓아주는 I/O-bound 작업이라 — 이 경우엔
스레드가 실제로 이득입니다. 팔과 손이 순차가 아니라 **동시에** 물리적으로 움직입니다.

```python
import time
robot.arm.move("up")     # 순차로 부르면 ~0.5s + ~0.5s
robot.hand.move("grip")  # (직접 부르는 건 예시일 뿐 -- router()가 스레드로 처리함)
```
`router({"arm": "up", "hand": "grip"})`로 부르면 위 예시가 순차로 걸리는 시간이 아니라
더 느린 쪽 하나만큼만 걸립니다.

!!! note "한계"
    한 호출에서 arm과 hand 둘 다 실패하면, `router()`는 그중 하나(`arm` 우선)만
    다시 던집니다 — 나머지 에러는 조용히 버려집니다. 지금은 흔한 상황이 아니라서
    감수한 단순화입니다.

`router()`의 반환 자체가 이미 "모든 파츠가 끝남"을 의미하지만(join까지 끝난 뒤
반환), 파츠 하나만 따로 기다리거나 다른 스레드에서 완료 여부만 확인하고 싶을 때는
`part.done_event`를 직접 씁니다:

```python
robot.arm.done_event.wait()  # 팔이 이번 목표까지 이동을 마칠 때까지 블록
```

## `Simulator`로 시각화하기

`robot.simulator`가 `None`이 아니면, `SIMULATION` 모드에서 `router()`가 계산한
`goal()` 값을 `Simulator.drive(part, target)`(`n2o.robot.simulation.Simulator`)로
넘겨 MuJoCo로 실제 시각화합니다:

> `mujoco`는 `examples`/`demos` 그룹 전용 의존성이라 `Robot`은 이걸 강제로
> import하지 않습니다 — 직접 대입해야 합니다.

```python
from n2o.robot import ControllerType, Robot
from n2o.robot.hand.amazing_hand import AmazingHand
from n2o.robot.simulation import Simulator

robot = Robot()
robot.hand = AmazingHand()
robot.controller = ControllerType.SIMULATION
robot.simulator = Simulator()
robot.simulator.launch_viewer("hand")  # 생략하면 창 없이 헤드리스로 물리만 진행
robot.router({"hand": "grip", "arm": None})
```

`Simulator.drive()` 자체는 GL 컨텍스트를 전혀 건드리지 않아 헤드리스 환경(CI 등)에서도
안전하며, `launch_viewer(part)`를 명시적으로 호출해야만 창이 열립니다. `N2O.run(
controller="simulation")`은 이 두 단계(`Simulator()` 생성 + `launch_viewer()`)를
자동으로 해 줍니다.

!!! note "다른 `controller`와 헷갈리지 마세요"
    `Robot.controller`(`ControllerType`)는 이미 파츠 단위로 해석된 명령을 어느
    *백엔드*로 보낼지 고르는 값입니다. `FeatureType.LANGUAGE` 예측값 전체를 처리하는
    `n2o.controller`(`LanguageController`)와는 다른 개념입니다 — 그 구분은
    [Controller](../controller/index.ko.md) 문서를 참고하세요.

!!! warning "Arm/Hand/Camera 문서는 아직 이전 설계 기준입니다"
    [Arm](arm/index.ko.md), [Hand](hand/index.ko.md), [Camera](camera/index.ko.md)
    문서는 아직 이전 `RobotArm`/`RobotHand`/`RobotCamera` + 레지스트리 설계
    (`@register_arm`, `RobotConfig`, `Controller.apply()`)를 기준으로 쓰여
    있습니다. 여기서 설명하는 `Part`/`ControllerType`/`Robot.router()` 설계에 맞춰
    아직 업데이트되지 않았습니다.

## 로드맵 { #roadmap }

아직 구현되지 않은 것들 — 자세한 내용은
[ROADMAP.md](https://github.com/EA-park/neural-to-output/blob/main/ROADMAP.md) 참고:

- **파츠별 설정** (`.yml`로도 입력 가능): controller 설정, solver 설정, 모터 아이디,
  dof, 시뮬레이션 모델 위치, 고정 가능한 port ID, 캘리브레이션 파일 위치/행렬
- **같은 종류의 파츠 여러 개** (예: `left_arm`/`right_arm`) — 손을 별도 파츠가 아니라
  자기 팔에서 직접 제어하는 구성도 포함
- **파츠 간 실행 상태 조율** — 기본 신호(`Part.done_event`)는 구현됨. 남은 건 그
  신호를 실제로 활용해 전후 관계가 있는 태스크나 협조 태스크를 순서대로/조건부로
  엮는 것 — `py_trees` 도입 검토 중, 자세한 내용은 `ROADMAP.md`의 "시퀀싱을
  py_trees로" 참고
- **`VLA` 라우팅** — camera 입력을 붙여서 각 파츠 자신의 명령 메서드를 호출
