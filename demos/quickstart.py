from n2o import N2O
from n2o.signal.dataset import DatasetLoader
from n2o.decoder import OfnerEEGNet
from n2o.command import OfnerCommand
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = DatasetLoader(name="Ofner2017")
n2o.decoder = OfnerEEGNet()
n2o.command = OfnerCommand()
n2o.robot.hand = AmazingHand(port="/dev/ttyACM1")
n2o.run(controller="simulation")
