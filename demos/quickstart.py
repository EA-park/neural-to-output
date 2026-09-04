from n2o import N2O
from n2o.command import OfnerHandCommand
from n2o.decoder import OfnerEEGNet
from n2o.robot.hand import AmazingHand
from n2o.signal.dataset import DatasetLoader

n2o = N2O()
n2o.signal = DatasetLoader(name="Ofner2017")
n2o.decoder = OfnerEEGNet()
n2o.command = OfnerHandCommand()
n2o.robot.hand = AmazingHand(port="/dev/ttyACM1")
n2o.run(controller="simulation")
