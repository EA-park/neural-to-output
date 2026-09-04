# Camera

`robot/camera/`는 아직 빈 placeholder입니다 — 구체 [`Part`](../index.ko.md#part)
구현이 아직 없습니다(`ROADMAP.md` 참고). 나중에 카메라 드라이버가 추가되면
`arm`/`hand`와 같은 형태를 따를 예정입니다: `robot/camera/` 아래에 `Part`
서브클래스를 두고 `robot/camera/__init__.py`에서 재노출합니다.

카메라는 앞으로 [`ControllerType.VLA`](../index.ko.md#controllertype)
(vision-language-action) 라우팅에 입력으로 쓰일 예정입니다 — 이것도 아직
미구현입니다.
