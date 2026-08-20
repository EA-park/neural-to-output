# Getting Started

프로젝트를 로컬에서 설정하려면 [Installation](installation.md)을 참고하세요.

## 실행

```bash
uv run neural-to-output
```

## 문서 작업하기

docs 의존성 그룹을 설치하고 로컬에서 실시간으로 미리보기:

```bash
uv sync --group docs
uv run mkdocs serve
```

이후 [http://127.0.0.1:8000](http://127.0.0.1:8000)을 엽니다.
