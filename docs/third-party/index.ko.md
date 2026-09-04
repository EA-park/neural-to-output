# Third-Party

저장소 최상위 `third_party/` 아래에 보관하는, 업스트림 프로젝트의 vendored 복사본
문서입니다.

## 존재하는 이유

이 프로젝트가 구동하는 일부 하드웨어는 pip/uv로 설치할 수 있는 패키지가 아닌 참고
코드를 함께 제공합니다 — 업스트림에 루트 `pyproject.toml`/`setup.py`가 없고, 예제
스크립트, CAD, 문서만 있는 경우입니다. `third_party/`는 그 참고 자료를 그대로 복사해
보관하며, 각각 자신의 서브폴더와 출처(업스트림 repo/커밋, 무엇을 복사했는지, 라이선스)를
문서화하는 `NOTICE.md`를 갖습니다 — `braindecode`/`moabb`처럼 일반 의존성으로 끌어올
수 없기 때문입니다.

## 현재 항목: `third_party/AmazingHand/`

[pollen-robotics/AmazingHand](https://github.com/pollen-robotics/AmazingHand)의
`v1.0` 태그에서 `Demo/`, `PythonExample/`, `LICENSE`, `README.md`를 수정 없이 그대로
복사했습니다. 업스트림은 이중 라이선스입니다: 소프트웨어는 Apache-2.0, `Demo/AHSimulation/`
아래의 CAD/메쉬 파일은 CC BY 4.0. 전체 내역은
[`third_party/AmazingHand/NOTICE.md`](https://github.com/EA-park/neural-to-output/blob/main/third_party/AmazingHand/NOTICE.md)를
참고하세요.

[`AmazingHand.move()`](../robot/hand/index.ko.md)는
`PythonExample/AmazingHand_Demo.py`의 `rustypot` 사용법과 모터별 캘리브레이션 공식을
바탕으로 포팅되었습니다 — 그 매핑을 검증하기 위한 참고 자료로 여기 보관되어 있을 뿐,
`n2o`가 런타임에 import하지는 않습니다(`PythonExample/AmazingHand_Demo.py` 자체가
import 시점 부작용을 갖고 있습니다 — 모듈 로드 시 하드코딩된 시리얼 포트를 여는
코드가 있어서, import가 아니라 읽기용으로 의도된 파일입니다).

## 새 vendored 의존성 추가하기

1. 관련 업스트림 파일을 새 `third_party/<name>/` 서브폴더에 복사합니다.
2. 소스 repo, 정확히 vendored된 ref/커밋, 관련 라이선스를 문서화하는 `NOTICE.md`를
   그곳에 작성합니다 — `AmazingHand`의 것을 템플릿으로 참고하세요.
3. [`.claude/skills/generate-sbom/vendored_dependencies.json`](https://github.com/EA-park/neural-to-output/blob/main/.claude/skills/generate-sbom/vendored_dependencies.json)에
   항목을 추가해 [`sbom.md`](https://github.com/EA-park/neural-to-output/blob/main/sbom.md)의
   vendored-dependencies 표에 나타나도록 합니다 — `generate-sbom` 스킬은 `third_party/`
   서브폴더가 이 매니페스트에 없으면 경고를 남깁니다.
