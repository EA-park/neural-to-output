# N2O: Neural to Output

사람의 전기생리학적 신호를 로봇 동작으로 변환하는 오픈소스 프레임워크입니다.

## 개요

`neural-to-output`은 EEG/EMG 같은 원시 전기생리학적 신호를 로봇 동작으로 변환하는 데 필요한
빌딩 블록을 제공합니다. 파이프라인은 고정되어 있습니다: **signal** 소스를 **decoder**가
원시 예측값으로 디코딩하고, 이를 **command**가 **robot**의 arm/hand/camera에 대한 부위별
동작으로 변환합니다 — 단, decoder의 출력이 language 타입인 경우에는 대신 **controller**로
라우팅됩니다.

로컬에 프로젝트를 설치하려면 [시작하기](getting-started/index.md)를, 파이프라인이 어떻게
맞물리는지는 [아키텍처](architecture.md)를 참고하세요.

## 다음으로 볼 곳

- **바로 실행해보고 싶다면**: [`examples/`](https://github.com/EA-park/neural-to-output/tree/main/examples)에
  번호가 매겨진, 그 자체로 완결된 Jupyter 노트북들이 있습니다 — 이 프로젝트의 튜토리얼
  콘텐츠로, 순서대로 따라가며 실습할 수 있습니다.
- **각 구성 요소가 어떻게 연결되는지 이해하고 싶다면**: 이 사이트가 바로 그 용도입니다 —
  노트북 내용을 반복하는 대신, 파이프라인 각 단계에 대한 사용법 문서를 제공합니다.
