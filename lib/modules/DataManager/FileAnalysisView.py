# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
import database
from AnalysisTemplate import *
import lib.Manager
import lib.analysis.modules as analysis
import lib.analysis.AnalysisHost as AnalysisHost

class FileAnalysisView(QtGui.QWidget):
    
    sigDbChanged = QtCore.Signal()
    
    def __init__(self, parent, mod):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.man = lib.Manager.getManager()
        #print self.window().objectName()
        #self.dm = self.window().dm  ## get module from window
        self.mod = mod
        self.dbFile = None
        self.db = None
        self.mods = []
        
        self.populateModuleList()
        
        self.connect(self.ui.openDbBtn, QtCore.SIGNAL('clicked()'), self.openDbClicked)
        self.connect(self.ui.createDbBtn, QtCore.SIGNAL('clicked()'), self.createDbClicked)
        self.connect(self.ui.addFileBtn, QtCore.SIGNAL('clicked()'), self.addFileClicked)
        self.connect(self.ui.analysisCombo, QtCore.SIGNAL('currentIndexChanged(int)'), self.loadModule)
        self.ui.refreshDbBtn.clicked.connect(self.refreshDb)
        
    def openDbClicked(self):
        fn = str(QtGui.QFileDialog.getOpenFileName(self, "Select Database File", self.man.getBaseDir().name(), "SQLite Database (*.sqlite)"))
        if fn == '':
            return
        self.ui.databaseText.setText(fn)
        self.dbFile = fn
        self.db = database.AnalysisDatabase(self.dbFile)
        self.sigDbChanged.emit()
        
    def createDbClicked(self):
        fn = str(QtGui.QFileDialog.getSaveFileName(self, "Create Database File", self.man.getBaseDir().name(), "SQLite Database (*.sqlite)", None, QtGui.QFileDialog.DontConfirmOverwrite))
        if fn is '':
            return
        self.ui.databaseText.setText(fn)
        self.dbFile = fn
        self.db = database.AnalysisDatabase(self.dbFile, self.man.getBaseDir())
        self.sigDbChanged.emit()
        
    def refreshDb(self):
        if self.db is None:
            return
        self.db._readTableList()
        
    def addFileClicked(self):
        cf = self.mod.selectedFile()
        self.db.addDir(cf)
        
    def populateModuleList(self):
        for m in analysis.listModules():
            self.ui.analysisCombo.addItem(m)
    
    def loadModule(self):
        if self.ui.analysisCombo.currentIndex() == 0:
            return
        modName = str(self.ui.analysisCombo.currentText())
        self.ui.analysisCombo.setCurrentIndex(0)
        mod = AnalysisHost.AnalysisHost(dataManager=self.mod, module=modName)
        self.mods.append(mod)

    def currentDatabase(self):
        return self.db

