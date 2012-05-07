# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from lib.analysis.AnalysisModule import AnalysisModule
import lib.analysis.modules.EventDetector as EventDetector
from pyqtgraph.flowchart import *
import os
from collections import OrderedDict
import debug
import ColorMapper
import pyqtgraph as pg
#import pyqtgraph.ProgressDialog as ProgressDialog
from HelpfulException import HelpfulException
from Scan import Scan
from DBCtrl import DBCtrl
from ScatterPlotter import ScatterPlotter
from Canvas import items
import Canvas

class Photostim(AnalysisModule):
    """
    This module analyzes raw data from photostimulation scanning protocols to produce colored maps of features detected in the data. This analysis consists of multiple components:
      1) Data is (optionally) processed through an event detector to determine the time, amplitude, and other characteristics of the recroded events. The exact analysis in this stage is fully customizable by a flowchart. Results of this analysis are stored to a DB table (named 'photostim_events' by default) for use in further analysis.
      2) Each photostimulation is analyzed to determine the strength of evoked events, probability of presynaptic connection, probability of direct stimulation, etc. The exact analysis in this stage is fully customizable by a flowchart and results are stored to a DB table (named 'photostim_sites' by default) for use in further analysis.
      3) Multiple scans may (optionally) be combined to produce a single map with repeated measures and/or extended area.
      4) The values generated in steps 2 and 3 are mapped to colors which are displayed in a canvas.
    """
    def __init__(self, host):
        AnalysisModule.__init__(self, host)
        if self.dataModel is None:
            raise Exception("Photostim analysis module requires a data model, but none is loaded yet.")
        self.dbIdentity = "Photostim"  ## how we identify to the database; this determines which tables we own
        self.selectedSpot = None
        


        ## setup analysis flowchart
        modPath = os.path.abspath(os.path.split(__file__)[0])
        flowchartDir = os.path.join(modPath, "analysis_fc")
        self.flowchart = Flowchart(filePath=flowchartDir)
        self.flowchart.addInput('events')
        self.flowchart.addInput('regions')
        self.flowchart.addInput('fileHandle')
        self.flowchart.addOutput('dataOut')
        self.analysisCtrl = self.flowchart.widget()
        
        ## color mapper
        self.mapper = ColorMapper.ColorMapper(filePath=os.path.join(modPath, "colormaps"))
        self.mapCtrl = QtGui.QWidget()
        self.mapLayout = QtGui.QVBoxLayout()
        self.mapCtrl.setLayout(self.mapLayout)
        self.recolorBtn = QtGui.QPushButton("Recolor")
        self.mapLayout.splitter = QtGui.QSplitter()
        self.mapLayout.splitter.setOrientation(QtCore.Qt.Vertical)
        self.mapLayout.splitter.setContentsMargins(0,0,0,0)
        self.mapLayout.addWidget(self.mapLayout.splitter)
        self.mapLayout.splitter.addWidget(self.analysisCtrl)
        #self.mapLayout.splitter.addWidget(QtGui.QSplitter())
        self.mapLayout.splitter.addWidget(self.mapper)
        self.mapLayout.splitter.addWidget(self.recolorBtn)
        
        ## scatter plot
        self.scatterPlot = ScatterPlotter()
        self.scatterPlot.sigClicked.connect(self.scatterPlotClicked)
        
        ## setup map DB ctrl
        self.dbCtrl = DBCtrl(self, self.dbIdentity)
        
        ## storage for map data
        #self.scanItems = {}
        self.scans = []
        #self.seriesScans = {}
        self.maps = []
        
        ## create event detector
        fcDir = os.path.join(os.path.abspath(os.path.split(__file__)[0]), "detector_fc")
        self.detector = EventDetector.EventDetector(host, flowchartDir=fcDir, dbIdentity=self.dbIdentity+'.events')
        
        ## override some of its elements
        self.detector.setElement('File Loader', self)
        self.detector.setElement('Database', self.dbCtrl)
        
            
        ## Create element list, importing some gui elements from event detector
        elems = self.detector.listElements()
        self._elements_ = OrderedDict([
            ('Database', {'type': 'ctrl', 'object': self.dbCtrl, 'size': (300, 600)}),
            ('Scatter Plot', {'type': 'ctrl', 'object': self.scatterPlot, 'pos': ('right',), 'size': (700,400)}),
            ('Canvas', {'type': 'canvas', 'pos': ('above', 'Scatter Plot'), 'size': (700,400), 'allowTransforms': False, 'hideCtrl': True, 'args': {'name': 'Photostim'}}),
            #('Maps', {'type': 'ctrl', 'pos': ('bottom', 'Database'), 'size': (200,200), 'object': self.mapDBCtrl}),
            ('Map Opts', {'type': 'ctrl', 'object': self.mapCtrl, 'pos': ('above', 'Database'), 'size': (300,600)}),
            ('Detection Opts', elems['Detection Opts'].setParams(pos=('above', 'Map Opts'), size= (300,600))),
            ('File Loader', {'type': 'fileInput', 'size': (300, 300), 'pos': ('above', 'Detection Opts'), 'host': self, 'showFileTree': False}),
            ('Data Plot', elems['Data Plot'].setParams(pos=('bottom', 'Canvas'), size=(700,200))),
            ('Filter Plot', elems['Filter Plot'].setParams(pos=('bottom', 'Data Plot'), size=(700,200))),
            ('Event Table', elems['Output Table'].setParams(pos=('below', 'Filter Plot'), size=(700,200))),
            ('Stats', {'type': 'dataTree', 'size': (700,200), 'pos': ('below', 'Event Table')}),
        ])

        self.initializeElements()
        
        try:
            ## load default chart
            self.flowchart.loadFile(os.path.join(flowchartDir, 'default.fc'))
        except:
            debug.printExc('Error loading default flowchart:')
        
        
        self.detector.flowchart.sigOutputChanged.connect(self.detectorOutputChanged)
        self.flowchart.sigOutputChanged.connect(self.analyzerOutputChanged)
        self.detector.flowchart.sigStateChanged.connect(self.detectorStateChanged)
        self.flowchart.sigStateChanged.connect(self.analyzerStateChanged)
        self.recolorBtn.clicked.connect(self.recolor)
        
        
    def quit(self):
        self.scans = []
        self.maps = []
        return AnalysisModule.quit(self)
        
    def elementChanged(self, element, old, new):
        name = element.name()
        
        ## connect plots to flowchart, link X axes
        if name == 'File Loader':
            new.sigBaseChanged.connect(self.baseDirChanged)
            new.ui.dirTree.sigSelectionChanged.connect(self.fileSelected)
            self.baseDirChanged(new.baseDir())

    def fileSelected(self):
        fhl = self.getElement('File Loader').ui.dirTree.selectedFiles()
        if len(fhl) == 0:
            return
        fh = fhl[0]
        if fh is not None and fh.isDir():
            print Scan.describe(self.dataModel, fh)


    def baseDirChanged(self, dh):
        if dh is None:
            return ## should clear out map list here?
        
        if 'dirType' not in dh.info():
            return
        typ = dh.info()['dirType']
        if typ == 'Slice':
            cells = [dh[d] for d in dh.subDirs() if dh[d].info().get('dirType',None) == 'Cell']
        elif typ == 'Cell':
            cells = [dh]
        else:
            return
        for cell in cells:
            self.dbCtrl.listMaps(cell)

            

    def loadFileRequested(self, fhList):
        canvas = self.getElement('Canvas')
        model = self.dataModel

        for fh in fhList:
            try:
                ## TODO: use more clever detection of Scan data here.
                if fh.isFile() or model.dirType(fh) == 'Cell':
                    canvas.addFile(fh)
                else:
                    self.loadScan(fh)
                return True
            except:
                debug.printExc("Error loading file %s" % fh.name())
                return False

    def loadScan(self, fh):
        ret = []
        
        ## first see if we've already loaded this file
        for scan in self.scans:
            if scan.source() is fh:
                ret.append(scan)   ## if so, return all scans sourced by this file
        if len(ret) > 0:
            return ret
        
        ## Load the file, possibly generating multiple scans.
        canvas = self.getElement('Canvas')
        
        ret = []
        
        if self.dataModel.isSequence(fh):  ## If we are loading a sequence, there will be multiple spot locations and/or multiple scans.
            ## get sequence parameters
            params = self.dataModel.listSequenceParams(fh).deepcopy()  ## copy is required since this info is read-only.
            if ('Scanner', 'targets') in params:
                #params.remove(('Scanner', 'targets'))  ## removing this key enables us to process other sequence variables independently
                del params[('Scanner', 'targets')]
        
            ## If the scan has sequence parameters other than the spot position, 
            ## load each sub-scan separately.
            if len(params) > 0:
                seq = True
                parent = canvas.addGroup(fh.shortName())
            else:
                seq = False
                parent = None
                
            ## Determine the set of subdirs for each scan present in the sequence
            ## (most sequences will have only one scan)
            scans = {}
            for dhName in fh.subDirs():
                dh = fh[dhName]
                key = '_'.join([str(dh.info()[p]) for p in params])
                if key not in scans:
                    scans[key] = []
                scans[key].append(dh)

        else:  ## If we are not loading a sequence, then there is only a single spot
            scans = {None: [fh]}
            seq = False
            parent = None


        ## Add each scan
        
        for key, subDirs in scans.iteritems():
            if seq:
                name = key
                sname = fh.shortName() + '.' + key
            else:
                name = fh.shortName()
                sname = name
            canvasItem = Canvas.ScanCanvasItem(handle=fh, subDirs=subDirs, name=name, parent=parent)
            canvas.addItem(canvasItem)
            canvasItem.graphicsItem().sigClicked.connect(self.scanPointClicked)
            scan = Scan(self, fh, canvasItem, name=sname)
            self.scans.append(scan)
            ret.append(scan)
            self.dbCtrl.scanLoaded(scan)
            self.scatterPlot.addScan(scan)
        
        #canvasItems = canvas.addFile(fh, separateParams=True)  ## returns list when fh is a scan
        #for citem in canvasItems:
            #scan = Scan(self, fh, citem, name=citem.opts['name'])
            #self.scans.append(scan)
            #citem.item.sigPointClicked.connect(self.scanPointClicked)
            #self.dbCtrl.scanLoaded(scan)
            #ret.append(scan)
            #self.scatterPlot.addScan(scan)
        return ret
                

    def registerMap(self, map):
        #if map in self.maps:
            #return
        canvas = self.getElement('Canvas')
        map.canvasItem = canvas.addGraphicsItem(map.sPlotItem, name=map.name())
        self.maps.append(map)
        map.sPlotItem.sigClicked.connect(self.mapPointClicked)
        
    def unregisterMap(self, map):
        if hasattr(map, 'canvasItem'):
            canvas = self.getElement('Canvas')
            canvas.removeItem(map.canvasItem)
        if map in self.maps:
            self.maps.remove(map)
            
        try:
            map.sPlotItem.sigClicked.disconnect(self.mapPointClicked)
        except TypeError:
            pass
    

    def scanPointClicked(self, plotItem, points):
        try:
            point = points[0]
            QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
            print "clicked:", point.data
            plot = self.getElement("Data Plot")
            #plot.clear()
            self.selectedSpot = point
            self.selectedScan = plotItem.scan
            fh = self.dataModel.getClampFile(point.data)
            self.detector.loadFileRequested(fh)
            #self.dbCtrl.scanSpotClicked(fh)
        finally:
            QtGui.QApplication.restoreOverrideCursor()
            
        
    def mapPointClicked(self, scan, points):
        data = []
        for p in points:
            for source in p.data:
                data.append([source[0], self.dataModel.getClampFile(source[1])])
            #data.extend(p.data)
        self.redisplayData(data)
        ##self.dbCtrl.mapSpotClicked(point.data)  ## Did this method exist at some point?

    def scatterPlotClicked(self, plot, points):
        #scan, fh, time = point.data
        self.redisplayData([p.data for p in points])
        #self.scatterLine =

    def redisplayData(self, points):  ## data must be [(scan, fh, <event time>), ...]  
        #raise Exception('blah')
        try:
            QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
            plot = self.getElement("Data Plot")
            plot.clear()
            eTable = self.getElement("Event Table")
            sTable = self.getElement("Stats")
            self.mapTicks = []
            
            #num = len(point.data)
            num = len(points)
            statList = []
            evList = []
            for i in range(num):
                color = pg.intColor(i, num)
                #scan, fh = point.data[i]
                try:
                    scan, fh = points[i][:2]
                except:
                    print points[i]
                    raise
                if isinstance(fh, basestring):
                    fh = scan.source()[fh]
                
                ## plot all data, incl. events
                data = fh.read()['primary']
                pc = plot.plot(data, pen=color, clear=False)
                
                ## show stats
                stats = scan.getStats(fh.parent())
                statList.append(stats)
                events = scan.getEvents(fh)['events']
                evList.append(events)

                ## mark location of event if an event index was given
                if len(points[i]) == 3:
                    evTime = points[i][2]
                    #pos = float(index)/len(data)
                    pos = evTime / data.xvals('Time')[-1]
                    #print evTime, data.xvals('Time')[-1], pos
                    #print index
                    self.arrow = pg.CurveArrow(pc, pos=pos)
                    plot.addItem(self.arrow)
                

                ## draw ticks over all detected events
                if len(events) > 0:
                    times = events['fitTime']
                    ticks = pg.VTickGroup(times, [0.85, 1.0], pen=color)
                    plot.addItem(ticks)
                    self.mapTicks.append(ticks)
            
            sTable.setData(statList)
            try:
                eTable.setData(np.concatenate(evList))
            except:
                for i in range(1,len(evList)):
                    for j in range(len(evList[i].dtype)):
                        if evList[i-1].dtype[j] != evList[i].dtype[j]:
                            for l in evList:
                                print l
                            print "Warning: can not concatenate--field '%s' has inconsistent types %s, %s  (data printed above)" % (evList[i].dtype.names[j], str(evList[i-1].dtype[j]), str(evList[i].dtype[j]))
                raise
        finally:
            QtGui.QApplication.restoreOverrideCursor()
    
    
    def detectorStateChanged(self):
        #print "STATE CHANGE"
        #print "Detector state changed"
        for scan in self.scans:
            scan.forgetEvents()
        
    def detectorOutputChanged(self):
        if self.selectedSpot==None:
            return
        output = self.detector.flowchart.output()
        output['fileHandle']=self.selectedSpot.data
        self.flowchart.setInput(**output)

    def analyzerStateChanged(self):
        #print "Analyzer state changed."
        for scan in self.scans:
            scan.forgetStats()
        
    def analyzerOutputChanged(self):
        table = self.getElement('Stats')
        stats = self.processStats()  ## gets current stats
        table.setData(stats)
        if stats is None:
            return
        self.mapper.setArgList(stats.keys())
        
    #def getCurrentStats(self):
        #stats = self.flowchart.output()['dataOut']
        #spot = self.selectedSpot
        #pos = spot.scenePos()
        #stats['xPos'] = pos.x()
        #stats['yPos'] = pos.y()
        #return stats
        
        
    def recolor(self):

        ## Select only visible scans and maps for recoloring
        allScans = [s for s in self.scans if s.isVisible()]
        allScans.extend([s for s in self.maps if s.isVisible()])
        for i in range(len(allScans)):
            allScans[i].recolor(i, len(allScans))
        
        #for i in range(len(self.scans)):
            #self.scans[i].recolor(i, len(self.scans))
        #for i in range(len(self.maps)):
            #self.maps[i].recolor(self, i, len(self.maps))

    def getColor(self, stats):
        #print "STATS:", stats
        return self.mapper.getColor(stats)

    def processEvents(self, fh):
        print "Process Events:", fh
        return self.detector.process(fh)

    def processStats(self, data=None, spot=None):
        ## Process output of stats flowchart for a single spot, add spot position fields.
        ## data  is the input to the stats flowchart
        ##       if data is omitted, then the stats for the currently selected spot are returned
        ##         (this is just the pre-existing output of the stats flowchart)
        ## spot  is used to determine the x,y coords of the spot
        if data is None:
            stats = self.flowchart.output()['dataOut']
            spot = self.selectedSpot
            if spot is None:
                return
            dh = spot.data
        else:
            if 'regions' not in data:
                data['regions'] = self.detector.flowchart.output()['regions']
            dh = spot.data
            data['fileHandle'] = dh
            #if dh is None:
                #data['fileHandle'] = self.selectedSpot.data
            #else:
                #data['fileHandle'] = fh
            stats = self.flowchart.process(**data)['dataOut']
            
        if stats is None:
            raise Exception('No data returned from analysis (check flowchart for errors).')
            
        pos = spot.viewPos()
        stats['xPos'] = pos.x()
        stats['yPos'] = pos.y()
        
        #d = spot.data.parent()
        #size = d.info().get('Scanner', {}).get('spotSize', 100e-6)
        #stats['spotSize'] = size
        #print "Process Stats:", spot.data
        
        #stats['SourceFile'] = self.dataModel.getClampFile(dh)
        stats['ProtocolDir'] = dh  ## stats should be stored with the protocol dir, not the clamp file.
        stats['ProtocolSequenceDir'] = self.dataModel.getParent(dh, 'ProtocolSequence')
        #parent = dh.parent()
        #if self.dataModel.dirType(parent) != 'ProtocolSequence':
            #parent = None
        
        #stats['ProtocolSequenceDir'] = parent
        
        return stats



    def storeDBSpot(self):
        """Stores data for selected spot immediately, using current flowchart outputs"""
        dbui = self.getElement('Database')
        db = dbui.getDb()
        
        ## get events and stats for selected spot
        spot = self.selectedSpot
        if spot is None:
            raise Exception("No spot selected")
        print "Store spot:", spot.data
        #parentDir = spot.data
        #p2 = parentDir.parent()
        #if self.dataModel.dirType(p2) == 'ProtocolSequence':
            #parentDir = p2
            
        ## ask eventdetector to store events for us.
        #print parentDir
        self.detector.storeToDB()
        events = self.detector.output()

        ## store stats
        stats = self.processStats(spot=spot)  ## gets current stats if no processing is requested
        
        self.storeStats(stats)
        
        ## update data in Map
        self.selectedScan.updateSpot(spot.data, events, stats)
        

    def storeDBScan(self, scan):
        """Store all data for a scan, using cached values if possible"""
        p = debug.Profiler("Photostim.storeDBScan", disabled=True)
        
        #dh = scan.source()
        print "Store scan:", scan.source().name()
        events = []
        stats = []
        spots = scan.spots()
        with pg.ProgressDialog("Preparing data for %s" % scan.name(), 0, len(spots)+1) as dlg:
            
            ## collect events and stats from all spots in the scan
            for i in xrange(len(spots)):
                s = spots[i]
                fh = self.dataModel.getClampFile(s.data)
                try:
                    ev = scan.getEvents(fh)['events']
                    events.append(ev)
                except:
                    print fh, scan.getEvents(fh)
                    raise
                st = scan.getStats(s.data)
                stats.append(st)
                dlg.setValue(i)
                if dlg.wasCanceled():
                    raise HelpfulException("Scan store canceled by user.", msgType='status')
                
            p.mark("Prepared data")
            
        ## Store all events for this scan
        events = [x for x in events if len(x) > 0] ## dtypes are incorrect if there are no events; these must be excluded before concatenating.
            
        ev = np.concatenate(events)
        p.mark("concatenate events")
        self.detector.storeToDB(ev)
        p.mark("stored all events")
        
        ## Store spot data
        self.storeStats(stats)
        p.mark("stored all stats")
        p.finish()
        print "   scan %s is now locked" % scan.source().name()
        scan.lock()

    def rewriteSpotPositions(self, scan):
        ## for now, let's just rewrite everything.
        #self.storeDBScan(scan)
        ## attempt to actually make this work
        dbui = self.getElement('Database')
        db = dbui.getDb()   
        identity = self.dbIdentity+'.sites'
        table = dbui.getTableName(identity)        
        #dh = scan.source()
        for spot in scan.spots():
            protocolID = db('Select rowid from DirTable_Protocol where Dir="%s"'%(spot.data.name(relativeTo=db.baseDir())))
            if len(protocolID) <1:
                continue
            protocolID = protocolID[0]['rowid']
            pos = spot.viewPos()
            db('UPDATE %s SET xPos=%f, yPos=%f WHERE ProtocolDir=%i' % (table, pos.x(), pos.y(), protocolID))
            
    def clearDBScan(self, scan):
        dbui = self.getElement('Database')
        db = dbui.getDb()
        #loader = self.getElement('File Loader')
        #dh = loader.selectedFile()
        #scan = self.scans[dh]
        dh = scan.source()
        print "Clear scan", dh
        #pRow = db.getDirRowID(dh)
        colName = self.dataModel.dirType(dh)+'Dir'
            
        identity = self.dbIdentity+'.sites'
        table = dbui.getTableName(identity)
        #db.delete(table, "SourceDir=%d" % pRow)
        if table in db.listTables():
            db.delete(table, where={colName: dh})
        
        identity = self.dbIdentity+'.events'
        table = dbui.getTableName(identity)
        if table in db.listTables():
            db.delete(table, where={colName: dh})
        #db.delete(table, "SourceDir=%d" % pRow)
            
        scan.unlock()


    def storeStats(self, data):
        ## Store a list of dict records, one per spot.
        ## data: {'SourceFile': clamp file handle, 'xPos':, 'yPos':, ...other fields from stats flowchart...}
        ## parentDir: protocolSequence dir handle (or protocol for single spots)
        
        #print "Store stats:", fh
        
        ## If only one record was given, make it into a list of one record
        if isinstance(data, dict):
            data = [data]
        
        dbui = self.getElement('Database')
        identity = self.dbIdentity+'.sites'
        table = dbui.getTableName(identity)
        db = dbui.getDb()

        if db is None:
            raise Exception("No DB selected")

        #pTable, pRow = db.addDir(parentDir)
        
        #data = data.copy()  ## don't overwrite anything we shouldn't.. 
        #data['SourceFile'] = name
        #data['SourceDir'] = pRow
        
        ## Fix up records (convert file handles to names relative to parent) and add new columns
        #records = []
        #for rec in data:
            #sf = rec['SourceFile']
            #if not isinstance(sf, basestring):
                #sf = sf.name(relativeTo=parentDir)
            #rec2 = rec.copy()
            #rec2.update(SourceFile=sf, SourceDir=pRow)
            #records.append(rec2)
        
        ## determine the set of fields we expect to find in the table
        
        fields = db.describeData(data)
        
        ## override directory fields since describeData can't guess these for us
        fields['ProtocolDir'] = 'directory:Protocol'
        fields['ProtocolSequenceDir'] = 'directory:ProtocolSequence'
        
        #fields = OrderedDict([
            #('SourceDir', 'int'),
            #('SourceFile', 'text'),
        #])
        #fields.update(db.describeData(data))
        
        ## Make sure target table exists and has correct columns, links to input file
        db.checkTable(table, owner=identity, columns=fields, create=True, addUnknownColumns=True)
        
        # delete old
        for source in set([d['ProtocolDir'] for d in data]):
            #name = rec['SourceFile']
            db.delete(table, where={'ProtocolDir': source})

        # write new
        with pg.ProgressDialog("Storing spot stats...", 0, 100) as dlg:
            for n, nmax in db.iterInsert(table, data):
                dlg.setMaximum(nmax)
                dlg.setValue(n)
                if dlg.wasCanceled():
                    raise HelpfulException("Scan store canceled by user.", msgType='status')
            

    def loadSpotFromDB(self, dh):
        dbui = self.getElement('Database')
        db = dbui.getDb()

        if db is None:
            raise Exception("No DB selected")
        
        #fh = self.getClampFile(dh)
        fh = self.dataModel.getClampFile(dh)
        parentDir = fh.parent()
        #p2 = parentDir.parent()
        #if db.dirTypeName(p2) == 'ProtocolSequence':
            #parentDir = p2
            
        
        #pRow = db.getDirRowID(parentDir)
        #if pRow is None:
            #return None, None
            
        identity = self.dbIdentity+'.sites'
        table = dbui.getTableName(identity)
        if not db.hasTable(table):
            return None, None
            
        stats = db.select(table, '*', where={'ProtocolDir': parentDir})
        events = self.detector.readFromDb(sourceFile=fh)
        
        return events, stats

    
    def loadScanFromDB(self, sourceDir):
        ## sourceDir should be protocolsequence
        dbui = self.getElement('Database')
        db = dbui.getDb()

        if db is None:
            raise Exception("No DB selected")
        
        #fh = self.getClampFile(dh)
        #fh = self.dataModel.getClampFile(dh)
        #parentDir = fh.parent()
        #p2 = parentDir.parent()
        #if db.dirTypeName(p2) == 'ProtocolSequence':
            #parentDir = p2
            
        
        #pRow = db.getDirRowID(sourceDir)
        #if pRow is None:
            #return None, None
            
        identity = self.dbIdentity+'.sites'
        table = dbui.getTableName(identity)
        if not db.hasTable(table):
            return None, None
            
        stats = db.select(table, '*', where={'ProtocolSequenceDir': sourceDir})
        events = self.detector.readFromDb(sequenceDir=sourceDir)
        
        return events, stats
    
    
    def getDb(self):
        dbui = self.getElement('Database')
        db = dbui.getDb()
        return db


