# Arm

`n2o.robot.arm`의 구체 드라이버 문서입니다.

## `SO101Arm`

[`SO101Arm`][n2o.robot.arm.so101.SO101Arm]는 SO-101 5-DOF 팔용으로 상용 제공되는
[`Part`](../index.ko.md#part)입니다 — `goal(cmd)`는 `cmd`를 `GESTURES`에서
조회할 뿐인 순수 계산(`"up"`/`"down"`, I/O 없음)이고, `move(cmd)`는 실물 하드웨어에
지연 연결(첫 호출 시)한 뒤 `shoulder_pan` 조인트만 관절-각도 공간에서 타깃까지
속도 제한(`MAX_JOINT_SPEED_DEG_S`)을 걸어 램프업합니다 — `lerobot` 자신의
`max_relative_target` 클램프를 스텝당 넘지 않도록 합니다.

```python
from n2o.robot.arm import SO101Arm

arm = SO101Arm(port="/dev/ttyACM0")
arm.move("up")
```

## 실물 하드웨어: vendored `lerobot_robot_so101_5dof/` 드라이버

이 SO-101 실물 구성은 그리퍼가 없는 5-모터 구성이라, `lerobot`이 기본 제공하는
6-모터 SO-101 클래스가 지원하지 않습니다 — 그래서 `SO101Arm`은 대신
`src/n2o/robot/arm/so101/lerobot_robot_so101_5dof/`를 통해 연결합니다: 프라이빗
로컬 패키지 3개 파일(`SO101Follower5Dof`/`SO101Follower5DofConfig`, `lerobot`
프레임워크의 `Robot`/`RobotConfig`이지 `n2o.robot.Part`가 아님)을 그대로 복사한
vendored copy로, pip/uv 의존성이 아니라 순수 소스입니다. `lerobot[feetech]`
(`examples`/`demos` dependency group)가 필요하며 지연 import됩니다 — `goal()`만
쓸 목적으로 `SO101Arm`을 만들고 쓰는 경우엔 설치돼 있지 않아도 됩니다.

주어진 `id`에 대한 캘리브레이션 파일이 아직 없으면, `move()`는 그걸 만드는 데
필요한 1회성 터미널 명령을 안내하는 `RuntimeError`를 발생시킵니다
(`so101_follower_5dof`는 등록된 `lerobot` 로봇 타입이 아니라서, 평범한
`lerobot-calibrate` CLI로는 바로 만들 수 없습니다).

## Cartesian IK: `SO101IKSolver`

[`SO101IKSolver`][n2o.robot.arm.so101.lerobot_robot_so101_5dof.solver.SO101IKSolver]는
순수 Cartesian 오프셋 IK(번들된 MJCF 모델 기준 감쇠 최소제곱)이며 하드웨어/시뮬
I/O가 전혀 없습니다. 아직 `SO101Arm.goal()`/`move()`에 연결돼 있지 않습니다 —
어떤 상용 [`Command`](../../command/index.ko.md)도 아직 `(ActionType, {"dx", "dy"})`
커맨드를 만들지 않기 때문입니다(`ROADMAP.md` 참고). `examples/08_mixed_classification_regression.ipynb`,
`examples/09_real_so101_arm_control.ipynb`처럼 직접 호출하세요:

```python
from n2o.robot.arm.so101.lerobot_robot_so101_5dof.solver import SO101IKSolver

solver = SO101IKSolver()
target_deg, ik_error = solver.solve(current_deg, dx=0.02, dy=0.0)
```

## 시뮬레이션과 출처

팔을 시뮬레이션으로 구동하는 건 [`SO101Arm`이 아니라 `Robot`의
역할입니다](../index.ko.md#simulator). 번들된 MJCF/Unity 자산은
드라이버 코드와 같은 폴더인 `arm/so101/`(`mjcf/`, `unity_model/`) 아래에
있습니다 — CAD 출처는 그 폴더의 `NOTICE.md`
([`TheRobotStudio/SO-ARM100`](https://github.com/TheRobotStudio/SO-ARM100)) 참고.
