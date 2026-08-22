# Camera

`LanguageController`의 시각 입력으로 쓰이는 로봇 장착 카메라에 대한 문서입니다.

## `RobotCamera`

`RobotCamera`(`n2o.robot.camera`)는 최신 캡처 프레임을 반환하는 추상 메서드 `capture()` 하나만 가진 기본 인터페이스입니다. `RobotArm`/`RobotHand`와 동일한 구조를 따릅니다: `base.py` ABC, 구현체마다 하나씩의 파일, 그리고 `@register_camera("Name")`을 통한 등록:

```python
from n2o.robot.camera import CAMERA_REGISTRY

CAMERA_REGISTRY  # {"MockCamera": MockCamera}
```

`RobotConfig(camera="MockCamera")` + `Robot.from_config(...)`/`make_robot(...)`은 이름을 인스턴스로 변환하며, 직접 대입 방식(`robot.camera = SomeInstance()`)에 추가되는 방법입니다 — [아키텍처 → `RobotConfig`로 로봇 만들기](../../architecture.ko.md#robotconfig) 참고.

현재는 `MockCamera`만 존재합니다(캡처 대신 출력만 함) — 아직 실제 카메라 드라이버는 추가되지 않았습니다.
