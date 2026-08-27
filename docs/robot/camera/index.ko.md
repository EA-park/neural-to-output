# Camera

`controller`의 시각 입력으로 쓰이는, 로봇에 장착된 카메라 문서입니다.

## `RobotCamera`

`RobotCamera`(`n2o.robot.camera`)는 가장 최근 캡처된 프레임을 반환하는 단일 추상
메서드 `capture()`를 갖는 기본 인터페이스입니다. `RobotArm`/`RobotHand`와 같은
형태를 따릅니다: `base.py` ABC 하나, 구체 구현마다 파일 하나, 그리고
`@register_camera("Name")`을 통한 등록:

```python
from n2o.robot.camera import CAMERA_REGISTRY

CAMERA_REGISTRY  # {"MockCamera": MockCamera}
```

`RobotConfig(camera="MockCamera")` + `Robot.from_config(...)`/`make_robot(...)`는
이름을 인스턴스로 해석하며, 직접 속성 대입(`robot.camera = SomeInstance()`)에
추가되는 방식입니다 —
[아키텍처 → `RobotConfig`로 로봇 조립하기](../../architecture.ko.md#robotconfig)
참고.

오늘 기준으로는 `MockCamera`만 존재합니다(캡처 대신 출력만 합니다) — 아직 실물 카메라
드라이버는 추가되지 않았습니다.
