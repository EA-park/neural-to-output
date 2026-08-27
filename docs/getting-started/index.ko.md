# 시작하기

로컬에 프로젝트를 설치하려면 [설치](installation.md)를 참고하세요.

## Dependency group

핵심 의존성(`pyproject.toml`의 `project.dependencies`)은 `braindecode`/`moabb`뿐입니다 —
그 외에는 모두 `uv` dependency group 뒤에 있으며, `uv sync --group <이름>`으로 설치합니다:

| Group      | 용도                                                                          |
| ---------- | ------------------------------------------------------------------------------ |
| `dev`      | `pytest`, `ruff` — 테스트 실행 및 린트                                          |
| `license`  | `pip-licenses` — [`sbom.md`](https://github.com/EA-park/neural-to-output/blob/main/sbom.md) 참고 |
| `docs`     | `mkdocs`, `mkdocs-material`, `mkdocs-static-i18n` — 이 사이트                    |
| `examples` | `jupyter`, `mujoco`, `lerobot`, `rustypot`, `torchaudio` — 튜토리얼 노트북 및 로봇 시뮬레이션/하드웨어 드라이버 |
| `demos`    | `examples`의 스택 + `flask` — `demos/` 아래의 독립 애플리케이션                   |

`uv sync --all-groups`로 한 번에 전부 설치할 수 있습니다 (CI와 동일한 환경을 확인할 때
유용하지만, `torch`/`mujoco`/`lerobot`이 커서 느립니다).

## 번호가 매겨진 튜토리얼 실행하기

```bash
uv sync --group examples
uv run jupyter lab examples/
```

`examples/01_explore_eeg_dataset.ipynb`부터 순서대로 진행하세요 — 전체 목록과 권장
순서는 [`examples/README.md`](https://github.com/EA-park/neural-to-output/blob/main/examples/README.md)를
참고하세요.

## 테스트 스위트 실행하기

```bash
uv sync --group dev
uv run pytest
```

## 이 사이트 작업하기

`docs` dependency group을 설치하고 로컬에서 live reload로 서빙합니다:

```bash
uv sync --group docs
uv run mkdocs serve
```

이후 [http://127.0.0.1:8000](http://127.0.0.1:8000)을 엽니다.
