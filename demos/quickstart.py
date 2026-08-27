from n2o import N2O
from n2o.signal.dataset import DatasetLoader
from n2o.decoder import OfnerEEGNet
from n2o.command import OfnerCommand
from n2o.robot.hand import AmazingHand
from n2o.robot.hand.amazing_hand_real import AmazingHandRealController
from n2o.robot.arm import LeRobotSO101
from n2o.robot.arm.so101_real import SO101ArmRealController

n2o = N2O()
n2o.signal = DatasetLoader(name="Ofner2017")
n2o.decoder = OfnerEEGNet()
n2o.command = OfnerCommand()
n2o.robot.hand = AmazingHand(
    controller=AmazingHandRealController(serial_port="/dev/ttyACM1"))
n2o.robot.arm = LeRobotSO101(
    controller=SO101ArmRealController(serial_port="/dev/ttyACM0"))
n2o.run(simulation=False)
