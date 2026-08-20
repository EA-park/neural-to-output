# Installation

## 사전 준비

- 의존성 관리를 위한 [uv](https://docs.astral.sh/uv/)
- 로컬 환경 변수를 불러오기 위한 [direnv](https://direnv.net/) (선택)

## 설정

저장소를 클론하고 의존성을 설치합니다:

```bash
uv sync
```

환경 변수 템플릿을 복사하고 direnv로 불러옵니다:

```bash
cp .envrc.example .envrc
direnv allow
```
