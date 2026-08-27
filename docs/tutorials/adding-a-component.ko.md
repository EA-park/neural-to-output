# 컴포넌트 추가하기

## 새 데이터셋, 스트림, 로봇 부위, 또는 decoder

`src/n2o/`의 대부분은 같은 확장 패턴을 따릅니다:

1. 해당 패키지의 기존 파일들 옆에 새 파일을 만듭니다(예:
   `src/n2o/robot/camera/my_camera.py`).
2. 해당 패키지의 `base.py` ABC(`decoder/base.py`, `robot/camera/base.py`, ...)를
   서브클래싱하고 추상 메서드를 구현합니다 — decoder라면
   [`Classification` 또는 `Regression`](../decoder/index.ko.md#classification-vs-regression)을
   서브클래싱하세요(`preprocess()`/`window()`가 둘 다 제공하지 않는 진짜 세 번째
   형태가 필요한 경우가 아니라면 `Decoder`를 직접 서브클래싱하지 마세요).
3. 해당 패키지의 `__init__.py`에서 새 클래스를 다시 export합니다.
4. ad hoc이나 시뮬레이션용 대체물이 아니라 이름이 있는 재사용 가능한 하드웨어라면,
   `RobotConfig`를 통해 선택할 수 있도록 `@register_arm("Name")`(패키지에 맞게
   `@register_hand`/`@register_camera`/`@register_controller`)을 붙이세요 —
   [아키텍처 → `RobotConfig`로 로봇 조립하기](../architecture.ko.md#robotconfig)
   참고. 이 단계는 선택 사항입니다: 직접 인스턴스화하고 속성을 대입하는 방식은 이것
   없이도 항상 작동합니다.

새 로봇 부위(예: 미래의 휴머노이드를 위한 다리나 머리)는 `arm`/`hand`/`camera`와
나란히 `n2o.robot` 아래에 새 형제 패키지를 추가하는 동일한 패턴을 따릅니다. 하나의
물리적 연결로 팔과 손을 동시에 구동하는 통합 디바이스는 구조 변경이 필요 없습니다 —
`RobotArm`과 `RobotHand`를 모두 상속하는 클래스 하나를 구현하고, 같은 인스턴스를
`robot.arm`과 `robot.hand`에 동시에 대입하세요.

`signal/dataset/`는 부분적인 예외입니다: 새로운 **moabb** 데이터셋은 코드가 필요
없습니다(이미 `moabb.datasets.utils.dataset_list`에 클래스 이름으로 등록되어
있습니다 — `DatasetLoader.list_libraries()`로 확인하세요). moabb가 다루지 않는
데이터셋은 대신 `@register_dataset("Name")`을 붙인 손으로 작성한
`DatasetLibraryEntry` 서브클래스가 필요합니다 — 또는, 재배포 가능한 데이터셋이 아니라
로컬 레코딩이라면 레지스트리를 아예 건너뛰고
`n2o.signal.dataset.write_metadata_template(path)` + `DatasetLoader(path=...)`를
사용하세요.

## 새 `Command`

위와 달리 `Command`는 `base.py`+구체 구현 패턴이 아닙니다 — 특정 decoder의 원시
출력을 특정 로봇의 부위로 매핑하기 때문에 보통 노트북 로컬로 서브클래싱하는 일반
클래스입니다. `Command` 서브클래스는 노트북을 넘나들며 진짜로 재사용 가능한 경우에만
(`GripSpreadCommand`/`OfnerCommand`처럼 — [Command](../command/index.ko.md) 참고)
`src/n2o/command/`로 승격하세요.

## Vendored(비-pip) 의존성

추가하려는 하드웨어 드라이버가 pip/uv로 설치할 수 없는 참고 코드를 제공한다면, 일반
의존성으로 추가하려 하지 말고 `third_party/`에 vendor하는 방법을
[Third-Party](../third-party/index.ko.md)에서 확인하세요.
