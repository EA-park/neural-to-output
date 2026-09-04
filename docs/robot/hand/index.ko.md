# Hand

`n2o.robot.hand`의 구체 드라이버 문서입니다.

## `AmazingHand`

[`AmazingHand`][n2o.robot.hand.amazing_hand_right.AmazingHand]는 AmazingHand
오른손 그리퍼용으로 상용 제공되는
[`Part`](../index.ko.md#part)입니다 — `goal(cmd)`는 `cmd`를
`GESTURES`에서 조회할 뿐인 순수 계산(9개 이름 있는 포즈, I/O 없음)이고,
`move(cmd)`는 실물 `rustypot` 서보 SDK에 지연 연결(첫 호출 시, 모든 모터
torque-enable)한 뒤 각 모터의 제스처 값에 그 유닛 고유 캘리브레이션 오프셋을
더해 보내되, 하드코딩된 안전 범위로 clamp합니다(벤더 SDK 자체엔 그런 게
없습니다). `disconnect()`는 모든 모터를 torque-disable합니다.

```python
from n2o.robot.hand import AmazingHand

hand = AmazingHand(port="/dev/ttyACM0")
hand.move("grip")
hand.disconnect()
```

`rustypot`(`examples`/`demos` dependency group)가 필요하며 지연 import됩니다 —
`goal()`만 쓸 목적으로 `AmazingHand`를 만들고 쓰는 경우엔 설치돼 있지 않아도
됩니다.

## 왜 `_right`인가

번들된 CAD와 모터별 캘리브레이션은 특정 오른손 CAD 버전 전용입니다
(`NOTICE.md` 참고) — 나중에 왼손 버전이 추가된다면 이 패키지에 플래그를 다는
게 아니라 형제 패키지(`amazing_hand_left/`)가 될 것입니다. 캘리브레이션 상수
자체가 유닛/손마다 고유하기 때문입니다.

이 드라이버가 포팅된 원본 vendored 레퍼런스 드라이버는
[`third_party/AmazingHand/`](../../third-party/index.ko.md)에 있습니다 —
`AmazingHand`가 실행 시점에 import하는 건 아니고, 캘리브레이션 공식을 대조
검증하는 데만 썼습니다.

## 시뮬레이션

손을 시뮬레이션으로 구동하는 건 `AmazingHand`가 아니라 `Robot`의 역할입니다
— [Robot → `Simulator`로 시각화하기](../index.ko.md#simulator)
참고. 번들된 MJCF/Unity 자산은 드라이버 코드와 같은 폴더인
`hand/amazing_hand_right/`(`mjcf/`, `unity_model/`) 아래에 있습니다 — CAD
출처는 그 폴더의 `NOTICE.md`
([`pollen-robotics/AmazingHand`](https://github.com/pollen-robotics/AmazingHand))
참고.
