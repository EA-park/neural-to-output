# Command

decoder의 원시 예측값을 로봇 부위별 동작으로 변환하는 문서입니다.

## `Command`

[`Command`][n2o.command.command.Command](`n2o.command.command`)는 선언적인 config가 아니라 오버라이드 가능한 일반
클래스입니다. 기본 `translate()`는 `decoded_signal`이 이미 로봇 부위별로 키가 잡혀
있다고 가정합니다:

```python
class Command:
    def translate(self, decoder, decoded_signal):
        return decoded_signal  # {"type": ..., "arm": ..., "hand": ...}
```

decoder의 원시 출력에 실제 변환이 필요할 때는 `translate(self, decoder,
decoded_signal)`을 서브클래싱해 오버라이드하세요 — 대부분의 decoder 원시 출력은 이미
`{"arm": ..., "hand": ...}` 형태가 아닙니다.

각 부위의 값은 그 자체로 의미가 통하는 이름(`"grip"`)이거나, 그 자체로는 의미가 통하지
않는 값(regression 숫자/딕셔너리)을 위한 `(ActionType, value)` 튜플입니다.
[`ActionType`][n2o.command.command.ActionType] — `JOINT_ABSOLUTE`, `JOINT_RELATIVE`, `CARTESIAN_ABSOLUTE`,
`CARTESIAN_RELATIVE` — 은 decoder 자신의 `DecoderType`과 무관하게 값과 함께
전달됩니다.

**`Decoder`는 순수한 예측기로 유지**하고(원시 예측값을 내보내는 것만), 예측값 →
부위별 동작 매핑은 `Command`에 두세요 — `Command`가 별도로 존재하는 이유가 바로
이것입니다.

## 포함된 서브클래스

`Command` 서브클래스는 보통 노트북 로컬로 작성됩니다 — 특정 decoder의 원시 출력을 특정
로봇의 부위로 매핑하는 것이기 때문입니다. `src/`에는 두 개가 포함되어 있습니다:

- **[`GripSpreadCommand`][n2o.command.grip_spread.GripSpreadCommand]**(`n2o/command/grip_spread.py`) — `BNCI2014_001`의 4개 원시
  motor-imagery 라벨(`feet`/`left_hand`/`right_hand`/`tongue`)을 [`AmazingHand`][n2o.robot.hand.amazing_hand.AmazingHand]의
  손가락별 4개 포즈로 매핑합니다. 같은 라벨 집합을 예측하는 어떤 decoder에서도 재사용할
  수 있습니다.
- **[`OfnerCommand`][n2o.command.ofner_command.OfnerCommand]**(`n2o/command/ofner_command.py`) — `OfnerEEGNet`의 7개 원시
  라벨을 `LABEL_TO_GESTURE`를 통해 arm-or-hand 제스처 하나씩으로 매핑합니다(먼저
  `decoder.config.labels[decoded_signal]`로 라벨 문자열을 복원합니다). 현재 매핑은
  검토를 거친 설계가 아니라 임시 자리표시자입니다 — 바뀔 수 있습니다.

## `CommandConfig`: `run()` 전에 파이프라인 확인하기

[`CommandConfig`][n2o.command.config.CommandConfig](`n2o.command.config`)는 `command` 경계를 위한 별도의 선언적 계약으로,
`SignalConfig`/`DecoderConfig`가 `signal`/`decoder`와 짝을 이루는 것과 같은 방식으로
`Command`와 짝을 이룹니다:

```python
n2o.command_config.verify_report(n2o)
```

`signal -> decoder -> command -> robot.arm/hand`를 따라가며 일치/불일치/미정 표를
출력합니다 — `N2O.verify()` 메서드는 없으므로 `verify_report()`를 직접 호출하세요.
`DecoderConfig.type`은 내부 모델을 두 개 이상 감싸는 decoder를 위해
`tuple[DecoderType, ...]`일 수 있습니다 — `Command.translate()`는 `decoder.config.type`
(인스턴스 속성)을 읽어 `decoded_signal`을 어떻게 해석할지 결정합니다.
