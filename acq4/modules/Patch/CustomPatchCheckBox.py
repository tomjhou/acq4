from __future__ import annotations


from acq4.util import Qt
from pyqtgraph import QtGui, QtWidgets


class CustomCheckBox(Qt.QCheckBox):
    """
    We need a custom box because the standard one does not seem to
    respond to .css directives.
    """
    def paintEvent_Mock(self, pe):
        """
        All documentation says we need to implement paintEvent() ourselves
        in order to get .css styles to work.

        However, I couldn't make it work. But ... I changed its name to paintEvent_Mock
        to prevent it from taking effect, then somehow the custom checkbox now responds to
        .css styles!!! I'm not complaining, but this is very weird.
        """

        # PyQt4 versions replaced by PyQt5 and above:
        # opt = QtGui.QStyleOption()
        # p = QtGui.QPainter(self)
        # s = self.style()
        # opt.init(self)
        # s.drawPrimitive(QtGui.QStyle.PE_Widget, opt, p, self)

        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        p = QtGui.QPainter(self)
        s = self.style()
        s.drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, p, self)

