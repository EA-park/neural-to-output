# 설치

## 사전 준비

- 의존성 관리를 위한 [uv](https://docs.astral.sh/uv/)
- 로컬 환경 변수 로딩을 위한 [direnv](https://direnv.net/) (선택)
- Python `>=3.12`

## 설정

저장소를 클론하고 핵심 의존성을 설치합니다:

```bash
uv sync
```

환경 변수 템플릿을 복사하고 direnv가 불러오게 합니다:

```bash
cp .envrc.example .envrc
direnv allow
```

다음으로 할 작업에 맞는 [dependency group](index.md#dependency-group)을 설치하세요 —
예를 들어 튜토리얼 노트북을 진행하려면 `uv sync --group examples`를, 테스트 스위트를
실행하려면 `uv sync --group dev`를 사용합니다.
