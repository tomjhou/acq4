from PyQt5 import QtWidgets, uic
import sys

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__() # Call the inherited classes __init__ method

        x = 321

        if x == 0:
            uic.loadUi('acq4/modules/TaskRunner/TaskRunnerTemplate.ui', self)  # Load the .ui file
            uic.loadUi('acq4/modules/Patch/PatchTemplate.ui', self)  # Load the .ui file
        elif x == 2:
            uic.loadUi('test2_1.ui', self)  # Load the .ui file
        elif x == 3:
            uic.loadUi('test3.ui', self)
        elif x == 32:
            uic.loadUi('test3_2.ui', self)
        elif x == 321:
            uic.loadUi('test3_2_1.ui', self)
        elif x == 3211:
            uic.loadUi('test3_2_1_1.ui', self)
        elif x == 3212:
            uic.loadUi('test3_2_1_2.ui', self)
        elif x == 4:
            uic.loadUi('test4.ui', self)
        else:
            pass

        self.show()  # Show the GUI

app = QtWidgets.QApplication(sys.argv)

# app.setStyle('Fusion')

window = Ui()
app.exec_()
