# Adding a Component

새 데이터셋, 디코더, 로봇을 추가하려면:

1. 해당 패키지 안에 기존 파일들과 같은 위치에 새 파일을 만듭니다 (예:
   `src/n2o/decoder/my_decoder.py`).
2. 그 패키지의 `base.py` ABC를 상속하고 추상 메서드를 구현합니다.
3. 새 클래스를 해당 패키지의 `__init__.py`에서 re-export합니다.

새로운 로봇 부위(예: 향후 휴머노이드를 위한 다리나 머리)도 `n2o.robot` 아래의 형제
패키지로 동일한 패턴을 따르면 됩니다. 하나의 물리적 연결로 arm과 hand를 동시에
구동하는 통합형 장치는 구조를 바꿀 필요가 없습니다 — `RobotArm`과 `RobotHand`를
모두 상속하는 클래스 하나를 구현하고, 같은 인스턴스를 `robot.arm`과 `robot.hand`
양쪽에 할당하면 됩니다.
