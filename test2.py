from PyQt5 import QtWidgets, uic
import sys

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__() # Call the inherited classes __init__ method

        x = 2

        if x == 0:
            uic.loadUi('acq4/modules/TaskRunner/TaskRunnerTemplate.ui', self)  # Load the .ui file
        elif x == 1:
            uic.loadUi('acq4/modules/Patch/PatchTemplate.ui', self)  # Load the .ui file
        elif x == 2:
            uic.loadUi('test3_2_1_1.ui', self)
        else:
            uic.loadUi('test2_1.ui', self) # Load the .ui file
        self.show() # Show the GUI

app = QtWidgets.QApplication(sys.argv)

# app.setStyle('Fusion')

window = Ui()
app.exec_()
