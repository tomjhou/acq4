import pyqtgraph as pg

from acq4.util import Qt

Ui_DatabaseTemplate = Qt.importTemplate('.PressureControlWidget')


class PressureControlWidget(Qt.QWidget):
    """Presents a compact interface for controlling a pressure-control device."""

    def __init__(self, parent=None):
        Qt.QWidget.__init__(self)
        self.dev = None
        self.ui = Ui_DatabaseTemplate()
        self.ui.setupUi(self)
        self.ui.pressureSpin.setOpts(
            bounds=[None, None],
            decimals=0,
            suffix='Pa',
            siPrefix=True,
            step=1e3,
            format='{scaledValue:.3g} {siPrefix:s}{suffix:s}',
        )

    def connectPressureDevice(self, dev):
        self.dev = dev
        dev.sigPressureChanged.connect(self.pressureChanged)
        self.ui.regulatorPressureBtn.clicked.connect(self.regulatorPressureClicked)
        self.ui.userPressureBtn.clicked.connect(self.userPressureClicked)
        self.ui.atmospherePressureBtn.clicked.connect(self.atmospherePressureClicked)
        self.ui.pressureSpin.valueChanged.connect(self.pressureSpinChanged)

    def regulatorPressureClicked(self):
        self.dev.setPressure(source='regulator')

    def userPressureClicked(self):
        self.dev.setPressure(source='user')

    def atmospherePressureClicked(self):
        self.dev.setPressure(source='atmosphere')

    def pressureSpinChanged(self):
        self.dev.setPressure(pressure=self.ui.pressureSpin.value())

    def pressureChanged(self, dev, source, pressure):
        with pg.SignalBlock(self.ui.pressureSpin.valueChanged, self.pressureSpinChanged):
            self.ui.pressureSpin.setValue(pressure)
        self.ui.atmospherePressureBtn.setChecked(source == 'atmosphere')
        self.ui.userPressureBtn.setChecked(source == 'user')
        self.ui.regulatorPressureBtn.setChecked(source == 'regulator')

        style = {
            'regulator': 'background-color: #FCC; color: #000',
            'user': 'background-color: #CCF; color: #AAA',
            'atmosphere': 'color: #AAA',
        }.get(source, '')
        self.ui.pressureSpin.setStyleSheet(style)

    @property
    def pressureSpin(self):
        return self.ui.pressureSpin

    @property
    def regulatorPressureBtn(self):
        return self.ui.regulatorPressureBtn

    @property
    def userPressureBtn(self):
        return self.ui.userPressureBtn

    @property
    def atmospherePressureBtn(self):
        return self.ui.atmospherePressureBtn
