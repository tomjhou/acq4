from __future__ import print_function

import os
from collections import OrderedDict

import numpy as np
import pandas as pd

import pyqtgraph as pg
import acq4.util.debug as debug
from acq4.analysis.AnalysisModule import AnalysisModule
from pyqtgraph.flowchart import Flowchart
from acq4.util import Qt
from acq4.util.Qt import QtGui, QtWidgets
from acq4.util.DatabaseGui.DatabaseGui import DatabaseGui

from acq4.filetypes.MetaArray import MetaArray


deviceNames = {
    'Clamp': ('Clamp1', 'Clamp2', 'AxoPatch200', 'AxoProbe', 'MultiClamp1', 'MultiClamp2'),
    'Camera': ('Camera',),
    'Laser': ('Laser-UV', 'Laser-Blue', 'Laser-2P'),
    'LED-Blue': ('LED-Blue',),
}


def getClampFile(protoDH):
    """
    Given a protocol directory handle, return the clamp file handle within.
    If there are multiple clamps, only the first one encountered in deviceNames is returned.
    Return None if no clamps are found.
    """
    if protoDH.name()[-8:] == 'DS_Store':  ## OS X filesystem puts .DS_Store files in all directories
        return None
    files = protoDH.ls()
    for n in deviceNames['Clamp']:
        if n in files:
            return protoDH[n]
        if n + '.ma' in files:
            return protoDH[n + '.ma']

        # Simulated device filenames will have Daq suffix
        if n + 'Daq.ma' in files:
            return protoDH[n + 'Daq.ma']

    # print 'getClampFile: did not find protocol for clamp: ', files
    # print 'valid devices: ', deviceNames['Clamp']
    return None


class ExportCSV(AnalysisModule):

    """A generic module for analyzing features of repeated traces over time."""

    dbIdentity = "ExportCSV"

    def __init__(self, host):
        AnalysisModule.__init__(self, host)

        self.parent_dir = None
        flowchartDir = os.path.join(os.path.abspath(os.path.split(__file__)[0]), "flowcharts")
        self.flowchart = Flowchart(filePath=flowchartDir)
        self.flowchart.addInput('dataIn')
        self.flowchart.addOutput('results')
        self.flowchart.outputNode._allowAddInput = False ## make sure all data is coming out of output['results']
        

        try:
            ## load default chart
            self.flowchart.loadFile(os.path.join(flowchartDir, 'default.fc'))
        except:
            debug.printExc('Error loading default flowchart:')

        tables = OrderedDict([(self.dbIdentity+'.traces', 'ExportCSV_traces')])
        self.dbGui = DatabaseGui(dm=host.dataManager(), tables=tables)

        self.ctrl = Qt.QWidget()
        self.ctrl.setLayout(Qt.QVBoxLayout())
        self.analyzeBtn = Qt.QPushButton('Analyze')
        self.storeToCSV = Qt.QPushButton('Save to CSV')
        self.ctrl.layout().addWidget(self.analyzeBtn)
        self.ctrl.layout().addWidget(self.storeToCSV)


        self._elements_ = OrderedDict([
            ('Database', {'type':'ctrl', 'object': self.dbGui, 'size':(100,100)}),
            ('Analysis Options', {'type':'ctrl', 'object': self.flowchart.widget(), 'pos':('above', 'Database'),'size': (100, 400)}),
            ('File Loader', {'type':'fileInput', 'size': (100, 100), 'pos':('above', 'Analysis Options'),'host': self}),
            ('Experiment Plot', {'type':'plot', 'pos':('right', 'File Loader'), 'size':(400, 100)}),
            ('Traces Plot', {'type': 'plot', 'pos':('bottom', 'Experiment Plot'), 'size':(400,200)}),
            ('Results Plot', {'type': 'plot', 'pos':('bottom', 'Traces Plot'), 'size':(400,200)}),
            ('Results Table', {'type':'table', 'pos':('bottom', 'Traces Plot'), 'size': (400,200)}),
            ('Store Ctrl', {'type': 'ctrl', 'object':self.ctrl, 'size':(100,100), 'pos':('bottom', 'File Loader')})
        ])
        self.initializeElements()

        self.fileLoader= self.getElement('File Loader', create=True)
        self.exptPlot = self.getElement('Experiment Plot', create=True)
        self.tracesPlot = self.getElement('Traces Plot', create=True)
        self.resultsTable = self.getElement('Results Table', create=True)
        self.resultsTable.setSortingEnabled(False)
        self.resultsPlot = self.getElement('Results Plot', create=True)
        self.resultsPlot.getViewBox().setXLink(self.exptPlot.getViewBox()) ## link the x-axes of the exptPlot and the resultsPlot

        ### initialize variables
        self.expStart = 0
        self.traces = np.array([], dtype=[('timestamp', float), ('data', object), ('fileHandle', object), ('results', object)])
        self.files = []


        self.traceSelectRgn = pg.LinearRegionItem()
        self.traceSelectRgn.setRegion([0, 60])
        self.exptPlot.addItem(self.traceSelectRgn)
        self.traceSelectRgn.sigRegionChanged.connect(self.updateTracesPlot)
        #self.traceSelectRgn.sigRegionChangeFinished.connect(self.updateAnalysis)
        #self.flowchart.sigOutputChanged.connect(self.flowchartOutputChanged)

        #self.addRegionParam = pg.parametertree.Parameter.create(name="Add Region", type='action')
        #self.paramTree.addParameters(self.addRegionParam)
        #self.addRegionParam.sigActivated.connect(self.newRegionRequested)
        self.analyzeBtn.clicked.connect(self.analyzeBtnClicked)
        self.storeToCSV.clicked.connect(self.storeToCSV_Clicked)
        self.flowchart.sigChartLoaded.connect(self.connectPlots)
        self.fileLoader.sigClearRequested.connect(self.clearFilesRequested)

    def tableColumnSelected(self, column):
        #print "ColumnSelected -- ", column
        key = self.resultsTable.horizontalHeaderItem(column).text()
        
        self.resultsPlot.clear()
        self.resultsPlot.getPlotItem().setLabel('left', text=str(key))
        self.resultsPlot.plot([{'x':t['time'], 'y':t[str(key)]} for t in self.traces['results']], pen=None, symbol='o', symbolPen=None)

    def connectPlots(self):
        dp = self.getElement('Traces Plot', create=False)
        #fp = self.getElement('Filter Plot', create=False)
        if dp is not None and 'Plot_000' in self.flowchart.nodes().keys():
            self.flowchart.nodes()['Plot_000'].setPlot(dp)
        #if fp is not None and 'Plot_001' in self.flowchart.nodes().keys():
        #    self.flowchart.nodes()['Plot_001'].setPlot(fp)

    def clearFilesRequested(self):
        print("clear files called.")
        self.expStart = 0
        self.traces = np.array([], dtype=[('timestamp', float), ('data', object), ('fileHandle', object), ('results', object)])
        self.files = []
        self.updateExptPlot()
        self.traceSelectRgn.setRegion([0, 60])
        self.tracesPlot.clear()
        self.resultsTable.clear()
        self.resultsPlot.clear()

    def loadFileRequested(self, files):
        """Called by FileLoader when the load EPSP file button is clicked, once for each selected file.
                files - a list of the file currently selected in FileLoader
        """
        
        if files is None:
            return False

        if not files[0].isDir():
            # Need to select a folder, not file
            Qt.ShowMessage("Select directory")
            return False

        n = len(files[0].ls())

        self.parent_dir = files[0]

        with pg.ProgressDialog("Loading data..", 0, n) as dlg:
            for f in files:
                arr = np.zeros((len(f.ls())), dtype=[('timestamp', float), ('data', object), ('fileHandle', object), ('results', object)])
                maxi = -1
                for i, protoDir in enumerate(f.ls()):
                    if not f[protoDir].isDir():
                        print("Skipping file %s" %f[protoDir].name())
                        continue

                    df = getClampFile(f[protoDir])

                    if df is None:
                        print('Error in reading data file %s' % f[protoDir].name())
                        #break
                        continue

                    data = df.read()
                    timestamp = data.infoCopy()[-1]['startTime']
                    arr[i]['fileHandle'] = df
                    arr[i]['timestamp'] = timestamp
                    arr[i]['data'] = data
                    maxi += 1  # keep track of successfully read traces
                    dlg += 1
                    if dlg.wasCanceled():
                        return False
                self.traces = np.concatenate((self.traces, arr[:maxi]))  # only concatenate successfully read traces
                #self.lastAverageState = {}
                self.files.append(f)

        if len(self.traces) == 0:
            Qt.ShowMessage("No traces read.")
            return False

        self.expStart = self.traces['timestamp'].min()
        #self.averageCtrlChanged()
        self.updateExptPlot()
        self.updateTracesPlot()
        return True

    def updateExptPlot(self):
        """Update the experiment plots with markers for the timestamps of
        all loaded EPSP traces, and averages (if selected in the UI)."""

        self.exptPlot.clear()
        self.exptPlot.addItem(self.traceSelectRgn)

        if len(self.traces) == 0:
            return

        self.exptPlot.plot(x=self.traces['timestamp']-self.expStart, y=[1]*len(self.traces), pen=None, symbol='o', symbolSize=6)

    def updateTracesPlot(self):
        """Update the Trace display plot to show the traces corresponding to
         the timestamps selected by the region in the experiment plot."""

        rgn = self.traceSelectRgn.getRegion()
        self.tracesPlot.clear()

        ### plot all the traces with timestamps within the selected region (according to self.traceSelectRgn)
        data = self.traces[(self.traces['timestamp'] > rgn[0]+self.expStart)
                          *(self.traces['timestamp'] < rgn[1]+self.expStart)]
        
        for i, d in enumerate(data['data']):
            self.tracesPlot.plot(d['primary'], pen=pg.intColor(i, len(data)))

        if len(data) > 0:
            self.flowchart.setInput(dataIn=data[0]['fileHandle'])

    def analyzeBtnClicked(self, *args):
        self.resultsTable.clear()
        with pg.ProgressDialog("Analyzing..", 0, len(self.traces)) as dlg:
            for i, t in enumerate(self.traces):
                results = self.flowchart.process(dataIn=t['fileHandle'])['results']
                ## make sure results has these fields regardless of what's in the flowchart
                results['timestamp'] = t['timestamp']
                results['time'] = results['timestamp'] - self.expStart
                self.resultsTable.appendData([results])
                results['ProtocolDir'] = self.dataModel.getParent(t['fileHandle'], 'Protocol')
                results['ProtocolSequenceDir'] = self.dataModel.getParent(t['fileHandle'], 'ProtocolSequence')
                results['CellDir'] = self.dataModel.getParent(t['fileHandle'], 'Cell')
                t['results'] = results
                dlg += 1
                if dlg.wasCanceled():
                    self.resultsTable.horizontalHeader().sectionClicked.connect(self.tableColumnSelected)
                    return

        self.resultsTable.horizontalHeader().sectionClicked.connect(self.tableColumnSelected)

    def storeToCSV_Clicked(self, *args):

        out_command = None
        out_wave = None
        header1 = ''
        header2 = ''
        for i, t in enumerate(self.traces):
            data_types = t.dtype
            vals: MetaArray = t['data']  # Also have 'timestamp', 'fileHandle', and 'results'
            a = np.array(vals).T
            command = a[:, [0]]  # Note extra brackets, which gives us column vector instead of 1D array
            wave = a[:, [1]]
            if out_command is None:
                out_command = command
                out_wave = wave
            else:
                out_command = np.concatenate((out_command, command), axis=1)
                out_wave = np.concatenate((out_wave, wave), axis=1)
                header1 += ', '
                header2 += ', '

            header1 += 'cmd_' + str(i + 1)
            header2 += 'wav_' + str(i + 1)

        num_points = a.shape[0]

        win = Qt.QApplication.topLevelWidgets()
        win = win[win is Qt.QMainWindow]

        if win is not None:
            name = QtWidgets.QFileDialog.getSaveFileName(win, 'Save File', self.parent_dir.path + "out.csv")

            try:
                np.savetxt(name[0], np.concatenate((out_command, out_wave), axis=1),
                           fmt='%5.6g', delimiter=',', header=header1 + ', ' + header2)
                Qt.ShowMessage("Successfully saved file.", "Status")
            except Exception as ex:
                Qt.ShowMessage(f"Error saving file: {str(ex)}")