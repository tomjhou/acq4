import time
import traceback
import sys

from PyQt4 import QtGui, QtCore
import LogWidgetTemplate
from FeedbackButton import FeedbackButton
import configfile
from DataManager import DirHandle
from HelpfulException import HelpfulException
from Mutex import Mutex
#from lib.Manager import getManager

WIN = None

class LogButton(FeedbackButton):

    def __init__(self, *args):
        FeedbackButton.__init__(self, *args)
        #self.setMaximumHeight(30)
        global WIN
        self.clicked.connect(WIN.show)
        WIN.buttons.append(self)
        
        

class LogWindow(QtGui.QMainWindow):
    
    #sigDisplayEntry = QtCore.Signal(object) ## for thread-safetyness
    
    def __init__(self, manager):
        QtGui.QMainWindow.__init__(self)
        self.wid = QtGui.QWidget()
        self.ui = LogWidgetTemplate.Ui_Form()
        self.ui.setupUi(self.wid)
        self.setCentralWidget(self.wid)
        self.resize(1000, 500)
        self.manager = manager
        global WIN
        WIN = self
        #self.msgCount = 0
        self.logCount=0
        self.logFile = None
        configfile.writeConfigFile('', self.fileName())  ## start a new temp log file, destroying anything left over from the last session.
        self.buttons = [] ## all Log Buttons get added to this list, so it's easy to make them all do things, like flash red.
        self.lock = Mutex()
        self.logPrinter = LogPrinter(self.ui.output)
        
        ## self.ui.input is a QLineEdit
        ## self.ui.output is a QPlainTextEdit
        
        self.ui.input.returnPressed.connect(self.textEntered)
        self.ui.makeErrorBtn.clicked.connect(self.makeError1)
        #self.sigDisplayEntry.connect(self.displayEntry)
        
        
    def logMsg(self, msg, importance=5, msgType='status', **kwargs):
        """msgTypes: user, status, error, warning
           importance: 0-9 (0 is low importance, 9 is high)
           other keywords:
              exception: a tuple (type, exception, traceback) as returned by sys.exc_info()
              docs: a list of strings where documentation related to the message can be found
              reasons: a list of reasons (as strings) for the message
              traceback: ??? not supported yet
        """
        if msgType == 'error':
            self.flashButtons()
        
        try:
            currentDir = self.manager.getCurrentDir()
        except:
            currentDir = None
        if isinstance(currentDir, DirHandle):
            kwargs['currentDir'] = currentDir.name()
        
        now = str(time.strftime('%Y.%m.%d %H:%M:%S'))
        name = 'LogEntry_' + str(time.strftime('%Y.%m.%d %H.%M.%S'))  ## TODO: not unique
        #self.msgCount += 1
        entry = {
            #'docs': None,
            #'reasons': None,
            'message': msg,
            'timestamp': now,
            'importance': importance,
            'msgType': msgType,
            #'exception': exception,
        }
        for k in kwargs:
            entry[k] = kwargs[k]
            
        self.processEntry(entry)
        self.saveEntry({name:entry})
        self.logPrinter.displayEntry(entry)
        
        
    def logExc(self, *args, **kwargs):
        kwargs['exception'] = sys.exc_info()
        self.logMsg(*args, **kwargs)
        
    def processEntry(self, entry):
        ## pre-processing common to saveEntry and displayEntry
        if entry.get('exception', None) is not None:
            exc_info = entry.pop('exception')
            #exType, exc, tb = exc_info
            entry['exception'] = self.exceptionToDict(*exc_info)
            
            #if isinstance(exc, HelpfulException):
                #error, tb, docs = self.formatHelpfulException(*exc_info)
                #entry['message'] += error
                #entry['docs'] += docs
                ##self.logMsg(error, msgType='error', exception=tb, documentation=docs **kwargs)
            #else: 
                #error, tb = self.formatException(*exc_info)
                #entry['message'] += '\n' + error
                ##entry['msgType'] = 'error'
                ##self.logMsg(message+error, msgType='error', exception=tb, **kwargs)
            #entry['traceback'] = tb
        
    #def logExc(self, *args, **kwargs):
        #self.flashButtons()
        #exc_info = kwargs.pop('exc_info', sys.exc_info())
        #exc = exc_info[1]
        #if isinstance(exc, HelpfulException):
            #error, tb, docs = self.formatHelpfulException(*exc_info)
            #self.logMsg(error, msgType='error', exception=tb, documentation=docs **kwargs)
        #else: 
            #message = kwargs.get('message', '')
            #if message is not '':
                #kwargs.pop('message')
                #message += '\n'
            #error, tb = self.formatException(*exc_info)
            #self.logMsg(message+error, msgType='error', exception=tb, **kwargs)
    
        
    def textEntered(self):
        msg = str(self.ui.input.text())
        try:
            currentDir = self.manager.getCurrentDir()
        except:
            currentDir = None
        self.logMsg(msg, importance=8, msgType='user', currentDir=currentDir)
        self.ui.input.clear()
        
    #def enterModuleMessage(self, msg):
     #   self.displayText(msg, colorStr = 'green')
            
    #@staticmethod
    #def displayEntry(self, entry, output=None):
        ### for thread-safetyness:
        #isGuiThread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        #if not isGuiThread:
            #self.sigDisplayEntry.emit(entry)
            #return
            
        
        #else:
            ### determine message color:
            #if entry['msgType'] == 'status':
                #i = entry['importance']
                #if i < 4:
                    #color = 'grey'
                #elif i > 6:
                    #color = 'black'
                #else:
                    #color = 'green'
            #elif entry['msgType'] == 'user':
                #color = 'blue'
            #elif entry['msgType'] == 'error':
                #color = 'red'
            #elif entry['msgType'] == 'warning':
                #color = '#DD4400' ## orange
            #else:
                #color = 'black'
                
                
            
                
            #if entry.has_key('exception') or entry.has_key('docs') or entry.has_key('reasons'):
                #self.displayComplexMessage(entry, color, output=output)
            #else: 
                #self.displayText(entry['message'], color, timeStamp=entry['timestamp'], output=output)
            
            ##elif entry['msgType'] == 'warning':
                ##self.displayText(entry['message'], '#AA8800', timeStamp = entry['timestamp'])
            ##elif entry['msgType'] == 'error':
                ##self.displayText(entry['message'], 'red', timeStamp = entry['timestamp'])
            ##elif entry['msgType'] == 'status':
                ##i = entry['importance']
                ##if i < 4:
                    ##self.displayText(entry['message'], 'gray', timeStamp = entry['timestamp'])
                ##elif i > 6:
                    ##self.displayText(entry['message'], 'black', timeStamp = entry['timestamp'])
                ##else:
                    ##self.displayText(entry['message'], 'green', timeStamp = entry['timestamp'])
 
            ##else:
                ##self.displayText(entry['message'], 'black', timeStamp = entry['timestamp'])
                
            ##elif entry['msgType'] == 'status':
                ##colorStr = 'green'
                ##self.displayText(entry['message'], colorStr=colorStr, timeStamp=entry['timestamp'])
            ##elif entry['msgType'] == 'error':
                ##self.displayText(entry['message'], colorStr='#AA0000', timeStamp=entry['timestamp'], reasons=entry.get('reasons', None), docs=entry.get('documentation', None))
                ##self.displayTraceback(entry['traceback'])
                ##self.flashButtons()
                
            ##elif entry['msgType'] == 'warning':
                ##self.displayText(entry['message'], colorStr='orange', timeStamp=entry['timestamp'])
            ##else:
                ##self.displayText(entry['message'], colorStr='black', timeStamp=entry['timestamp'])
                
    #def displayComplexMessage(self, entry, color='black', output=None):
        ##if entry['msgType'] == 'status':
            ##color = 'green'
        ##elif entry['msgType'] == 'error':
            ##color = 'red'
        ##elif entry['msgType'] == 'warning':
            ##color = '#AA8800' ## orange
        ##else:
            ##color = 'black'
        
        #self.displayText(entry['message'], color, timeStamp = entry['timestamp'], output=output)
        #if entry.has_key('reasons'):
            #reasons = self.formatReasonStrForHTML(entry['reasons'])
            #self.displayText(reasons, 'black', output=output)
        #if entry.has_key('docs'):
            #docs = self.formatDocsStrForHTML(entry['docs'])
            #self.displayText(docs, 'black', output=output)
        #if entry.has_key('exception'):
            #self.displayException(entry['exception'], 'black', output=output)
            

    
    #def displayException(self, exception, color, count=None, tracebacks=None, output=None):
        #### Here, exception is a dict that holds the message, reasons, docs, traceback and oldExceptions (which are also dicts, with the same entries)
        ### the count and tracebacks keywords are for calling recursively
        
        #if count is None:
            #count = 1
        #else:
            #count += 1
        
        #if tracebacks is None:
            #tracebacks = []
            
        #indent = 10
        
        
        #if exception.has_key('oldExc'):    
            #self.displayText("&nbsp;"*indent + str(count)+'. ' + exception['message'], color, output=output)
        #else:
            #self.displayText("&nbsp;"*indent + str(count)+'. Original error: ' +exception['message'], color, output=output)
            
        #tracebacks.append(exception['traceback'])
        
        #if exception.has_key('reasons'):
            #reasons = self.formatReasonsStrForHTML(exception['reasons'])
            #self.displayText(reasons, color, output=output)
        #if exception.has_key('docs'):
            #docs = self.formatDocsStrForHTML(exception['docs'])
            #self.displayText(docs, color, output=output)
        
        #if exception.has_key('oldExc'):
            #self.displayException(exception['oldExc'], color, count=count, tracebacks=tracebacks)
        #else:
            #for i, tb in enumerate(tracebacks):
                #self.displayTraceback(tb, number=i+1, output=output)
        
        
        
    
    
    #def displayText(self, msg, colorStr = 'black', timeStamp=None, output=None):
        ##if reasons is not None:
            ##msg += "Reasons: " + reasons + '\n'
        ##if docs is not None:
            ##msg += "Documentation: " + docs
        #if output == None:
            #output = self.ui.output
        
        #if msg[-1:] == '\n':
            #msg = msg[:-1]     
        #msg = '<br />'.join(msg.split('\n'))
        #if timeStamp is not None:
            #strn = '<b style="color:black"> %s </b> <span style="color:%s"> %s </span>' % (timeStamp, colorStr, msg)
        #else:
            #strn = '<span style="color:%s"> %s </span>' % (colorStr, msg)
        #output.appendHtml(strn)
        
    #def formatException(self, *args):
        #tb = traceback.format_exception(*args)
        #error = tb.pop(-1)
        #return (error,tb)
    
    def exceptionToDict(self, exType, exc, tb):
        excDict = {}
        excDict['message'] = traceback.format_exception(exType, exc, tb)[-1]
        excDict['traceback'] = traceback.format_exception(exType, exc, tb)[:-1]
        if hasattr(exc, 'docs'):
            if len(exc.docs) > 0:
                excDict['docs'] = exc.docs
        if hasattr(exc, 'reasons'):
            if len(exc.reasons) > 0:
                excDict['reasons'] = exc.reasons
        if hasattr(exc, 'kwargs'):
            for k in exc.kwargs:
                excDict[k] = exc.kwargs[k]
        if hasattr(exc, 'oldExc'):
            excDict['oldExc'] = self.exceptionToDict(*exc.oldExc)
        return excDict
        
        
    
    #def formatHelpfulException(self, *args):
        #### so ugly.....
        #number = 1
        #tbs = []
        #exc = args[1]
        #errors, tbs = self.formatException(*args)
        #tbs.insert(0, str(number)+'. ')
        #errors = str(number) + '. ' + exc.messages[0]
        #errors += '  Reasons: ' 
        #for i in exc.reasons:
            #errors += str(i) + ' '
        #errors += '\n More documentation at: ' + exc.docs[0]
        #for i, e in enumerate(exc.excs):
            #number += 1
            #error, tb = self.formatException(*e)
            #if e != exc.excs[-1]:
                #errors += str(number) + '. ' + exc.messages[i+1]
                #errors += '  Reasons: '
                #for i in exc.reasons[i+1]:
                    #errors += str(i) + ' '
                #errors += '\n More documentation at: ', exc.docs[i+1]                
            #else:
                #errors += str(number) + '. ' + error
            #tbs.append(str(number) + '. ')
            #tbs.extend(tb) 
        #return (errors, tbs)
        
    #def displayTraceback(self, tb, color='grey', number=1, output=None):
        ##tb = traceback.format_exception(*args)
        ##self.displayText(tb[0], 'red')
        #lines = []
        #indent = 16
        #for l in ''.join(tb).split('\n'):
            #prefix = ''
            #if l == '':
                #continue
            #if l[:9] == "Traceback":
                #prefix = str(number) + '. '
            #spaceCount = 0
            #while l[spaceCount] == ' ':
                #spaceCount += 1
            #lines.append("&nbsp;"*(indent+spaceCount*4) + prefix + l)
        #self.displayText('<br>'.join(lines), color, output=output)
        
    #def formatReasonsStrForHTML(self, reasons):
        #indent = 6
        #letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        #reasonStr = "&nbsp;"*16 + "Possible reasons include: <br>"
        #for i, r in enumerate(reasons):
            #reasonStr += "&nbsp;"*22 + letters[i] + ". " + r + "<br>"
        #return reasonStr[:-4]
    
    #def formatDocsStrForHTML(self, docs):
        #indent = 6
        #docStr = "&nbsp;"*16 + "Relevant documentation: <br>"
        #letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        #for i, d in enumerate(docs):
            #docStr += "&nbsp;"*22 + letters[i] + ". " + d + "<br>"
        #return docStr[:-4]

    def flashButtons(self):
        for b in self.buttons:
            b.failure(tip='An error occurred. Please see the log.', limitedTime = False)
            
    def resetButtons(self):
        for b in self.buttons:
            b.reset()
        
    def makeError1(self):
        try:
            self.makeError2()
            #print x
        except:
            t, exc, tb = sys.exc_info()
            #logExc(message="This button doesn't work", reasons='reason a, reason b', docs='documentation')
            #if isinstance(exc, HelpfulException):
                #exc.prependErr("Button doesn't work", (t,exc,tb), reasons = ["It's supposed to raise an error for testing purposes", "You're doing it wrong."])
                #raise
            #else:
            raise HelpfulException(message='This button does not work.', exc=(t, exc, tb), reasons=["It's supposed to raise an error for testing purposes", "You're doing it wrong."])
    
    def makeError2(self):
        try:
            print y
        except:
            t, exc, tb = sys.exc_info()
            raise HelpfulException(message='msg from makeError', exc=(t, exc, tb), reasons=["reason one", "reason 2"], docs=['what, you expect documentation?'])
            
    def show(self):
        QtGui.QMainWindow.show(self)
        self.activateWindow()
        self.raise_()
        self.resetButtons()
        
    def fileName(self):
        ## return the log file currently used
        if self.logFile is None:
            return "tempLog.txt"
        else:
            return self.logFile.name()
        
    def setLogDir(self, dh):
        if self.fileName() == dh.name():
            return
        
        oldfName = self.fileName()
        
        self.logMsg('Moving log storage to %s.' % (dh.name(relativeTo=self.manager.baseDir))) ## make this note before we change the log file, so when a log ends, you know where it went after.
        
        if dh.exists('log.txt'):
            self.logFile = dh['log.txt']
        else:
            self.logFile = dh.createFile('log.txt')
        
        
        if oldfName == 'tempLog.txt':
            temp = configfile.readConfigFile(oldfName)
            self.saveEntry(temp)
        self.logMsg('Moved log storage from %s to %s.' % (oldfName, self.fileName()))
        self.ui.storageDirLabel.setText(self.fileName())
        self.manager.sigLogDirChanged.emit(dh)
        
    def getLogDir(self):
        if self.logFile is None:
            return None
        else:
            return self.logFile.parent()
        
    def saveEntry(self, entry):
        ## in foldertypes.cfg make a way to specify a folder type as an experimental unit. Then whenever one of these units is created, give it a new log file (perhaps numbered if it's not the first one made in that run of the experiment?). Also, make a way in the Data Manager to specify where a log file is stored (so you can store it another place if you really want to...).  
        with self.lock:
            configfile.appendConfigFile(entry, self.fileName())
            
class LogPrinter(QtCore.QObject):
    
    sigDisplayEntry = QtCore.Signal(object) ## for thread-safetyness
    
    def __init__(self, output):
        QtCore.QObject.__init__(self)
        self.output = output
        self.sigDisplayEntry.connect(self.displayEntry)
        
    def displayEntry(self, entry):
        ## for thread-safetyness:
        isGuiThread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not isGuiThread:
            self.sigDisplayEntry.emit(entry)
            return
            
        
        else:
            ## determine message color:
            if entry['msgType'] == 'status':
                i = entry['importance']
                if i < 4:
                    color = 'grey'
                elif i > 6:
                    color = 'black'
                else:
                    color = 'green'
            elif entry['msgType'] == 'user':
                color = 'blue'
            elif entry['msgType'] == 'error':
                color = 'red'
            elif entry['msgType'] == 'warning':
                color = '#DD4400' ## orange
            else:
                color = 'black'
                
                
            
                
            if entry.has_key('exception') or entry.has_key('docs') or entry.has_key('reasons'):
                self.displayComplexMessage(entry, color)
            else: 
                self.displayText(entry['message'], color, timeStamp=entry['timestamp'])
            
    def displayComplexMessage(self, entry, color='black'):
        #if entry['msgType'] == 'status':
            #color = 'green'
        #elif entry['msgType'] == 'error':
            #color = 'red'
        #elif entry['msgType'] == 'warning':
            #color = '#AA8800' ## orange
        #else:
            #color = 'black'
        
        self.displayText(entry['message'], color, timeStamp = entry['timestamp'])
        if entry.has_key('reasons'):
            reasons = self.formatReasonStrForHTML(entry['reasons'])
            self.displayText(reasons, 'black')
        if entry.has_key('docs'):
            docs = self.formatDocsStrForHTML(entry['docs'])
            self.displayText(docs, 'black')
        if entry.get('exception', None) is not None:
            self.displayException(entry['exception'], 'black')
            

    
    def displayException(self, exception, color, count=None, tracebacks=None):
        ### Here, exception is a dict that holds the message, reasons, docs, traceback and oldExceptions (which are also dicts, with the same entries)
        ## the count and tracebacks keywords are for calling recursively
        
        if count is None:
            count = 1
        else:
            count += 1
        
        if tracebacks is None:
            tracebacks = []
            
        indent = 10
        
        
        if exception.has_key('oldExc'):    
            self.displayText("&nbsp;"*indent + str(count)+'. ' + exception['message'], color)
        else:
            self.displayText("&nbsp;"*indent + str(count)+'. Original error: ' +exception['message'], color)
            
        tracebacks.append(exception['traceback'])
        
        if exception.has_key('reasons'):
            reasons = self.formatReasonsStrForHTML(exception['reasons'])
            self.displayText(reasons, color)
        if exception.has_key('docs'):
            docs = self.formatDocsStrForHTML(exception['docs'])
            self.displayText(docs, color)
        
        if exception.has_key('oldExc'):
            self.displayException(exception['oldExc'], color, count=count, tracebacks=tracebacks)
        else:
            for i, tb in enumerate(tracebacks):
                self.displayTraceback(tb, number=i+1)
        
        
    def displayText(self, msg, colorStr = 'black', timeStamp=None):
        #if reasons is not None:
            #msg += "Reasons: " + reasons + '\n'
        #if docs is not None:
            #msg += "Documentation: " + docs
        
        if msg[-1:] == '\n':
            msg = msg[:-1]     
        msg = '<br />'.join(msg.split('\n'))
        if timeStamp is not None:
            strn = '<b style="color:black"> %s </b> <span style="color:%s"> %s </span>' % (timeStamp, colorStr, msg)
        else:
            strn = '<span style="color:%s"> %s </span>' % (colorStr, msg)
        self.output.appendHtml(strn)
            
    def displayTraceback(self, tb, color='grey', number=1):
        #tb = traceback.format_exception(*args)
        #self.displayText(tb[0], 'red')
        lines = []
        indent = 16
        for l in ''.join(tb).split('\n'):
            prefix = ''
            if l == '':
                continue
            if l[:9] == "Traceback":
                prefix = str(number) + '. '
            spaceCount = 0
            while l[spaceCount] == ' ':
                spaceCount += 1
            lines.append("&nbsp;"*(indent+spaceCount*4) + prefix + l)
        self.displayText('<br>'.join(lines), color)
        
    def formatReasonsStrForHTML(self, reasons):
        indent = 6
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        reasonStr = "&nbsp;"*16 + "Possible reasons include: <br>"
        for i, r in enumerate(reasons):
            reasonStr += "&nbsp;"*22 + letters[i] + ". " + r + "<br>"
        return reasonStr[:-4]
    
    def formatDocsStrForHTML(self, docs):
        indent = 6
        docStr = "&nbsp;"*16 + "Relevant documentation: <br>"
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        for i, d in enumerate(docs):
            docStr += "&nbsp;"*22 + letters[i] + ". " + d + "<br>"
        return docStr[:-4]
        
if __name__ == "__main__":
    import sys
    app = QtGui.QApplication([])
    log = LogWindow()
    log.show()
    original_excepthook = sys.excepthook
    
    def excepthook(*args):
        global original_excepthook
        log.displayException(*args)
        ret = original_excepthook(*args)
        sys.last_traceback = None           ## the important bit
        
    
    sys.excepthook = excepthook

    app.exec_()