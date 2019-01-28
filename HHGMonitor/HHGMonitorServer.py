import scipy.io as sio

import pyqtgraph as pg

from pyqtgraph.Qt import QtCore, QtGui, uic
import numpy as np
import sys
import os


import thread
import threading

import socketserver
from socket import *

from WetLab_NewportDelayStage import DelayStage as Dstage
import time

from ADC_DAQ_v2 import ADC_DAQ as DAQ

from ctypes import *

from datetime import datetime
## Define main window class from template
#path = os.path.dirname(os.path.abspath(__file__))
#uiFile = os.path.join(path, 'designerExample.ui')
#WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)
Ui_MainWindow, QtBaseClass = uic.loadUiType('TAQD_GUI2.ui')

## Make the layout
dt=datetime
thislogfilename='%i%s%s_%s%s%s.log' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2), \
                                        str(dt.today().second).zfill(2))

f=open(thislogfilename,'w')



##############################################################
## Signal Acquisition Thread
class GrabSignal(pg.QtCore.QThread):
    newData = pg.QtCore.Signal(object) # signal to pull new data to the plots
    finishGrab = pg.QtCore.Signal(object) # signal to update the progress bar after a serie of measurement 
    finishAcq = pg.QtCore.Signal() # signal to announce the finish of recording and release blocked buttons
    
    def __init__(self,DAQ,mode,dirname='',ncycles=1,delaylist=(0,0),ROIB=(0,1)):
        QtCore.QThread.__init__(self)
        
        
        c=2.99792458e11
        self.mode=mode
        self.DAQ=DAQ
        self.ncycles=ncycles
        self.dirname=dirname
        self.delaylist_mm=(delaylist[0]*c)/2.0-delaylist[1] # first element is the list of delays and second is t0 in mm
        self.ROIB=ROIB
        
        
        #self.Threshold=np.int(params[0])
        #self.NbAcq=np.int(params[1])
        #self.FlatCorrimg=params[2]
        
        #if self.mode=='rec':
        #    self.Savepath=params[3]
        #    self.fname=params[4]
     
        
        self.stopMutex = threading.Lock()
        self._stop = False
        
    def run(self):
        
        if self.mode == 'prev':
            
            while True:
                self.DAQ.StartStream() 
                with self.stopMutex:
                    if self._stop:
                        break
                    
                dataA,dataB,ts = self.DAQ.RunStream()
                self.newData.emit((dataA,dataB,ts))
                self.DAQ.StopStream()
            
        elif self.mode=='rec':
            
            if self.DAQ.dscanmode==0:
                
                self.DAQ.StartRecording,(self.dirname)
                dataA,dataB,ts=self.DAQ.RunRecording(ROIB=self.ROIB)
                self.newData.emit((dataA,dataB,ts))
                self.DAQ.StopRecording()
                self.finishGrab.emit(self.DAQ.progressrecords)
            
            elif self.DAQ.dscanmode==1:
            
                Dstage0=Dstage()
                
                self.DAQ.StartRecording,(self.dirname)
                for i in range(self.ncycles):
                
                    with self.stopMutex:
                        if self._stop:
                            break
                    
                    for j,d in enumerate(self.delaylist_mm):
                        status=Dstage0.MoveAbs(d)
                        print status
                        with self.stopMutex:
                            if self._stop:
                                break
                            
                            dataA,dataB,ts=self.DAQ.RunRecording(j,i,ROIB=self.ROIB)
                            self.newData.emit((dataA,dataB,ts))
                            self.finishGrab.emit(self.DAQ.progressrecords)
                            
                            
                self.DAQ.StopRecording()
                self.finishGrab.emit(self.DAQ.progressrecords)
                
                Dstage0.__del__
  
    def stop(self):
        with self.stopMutex:
            self._stop = True

##############################################################               
## Broadcasting the signal in a thread

class BroadcastObject(pg.QtCore.QObject):
    
    def __init__(self,server):
        QtCore.QObject.__init__(self)
#        
        self.server=server        

    @QtCore.pyqtSlot(str)
    def UpdateDB(self,signal):
        

        self.server.listen(1)
        clientsock,address=self.server.accept()
        #print  clientsock,address
        cmd=clientsock.recv(4)
        #print cmd
        if 'rqst' in str(cmd):
            clientsock.sendall(signal)

         



##############################################################
## Main Thread

class MainWindow(QtGui.QMainWindow, Ui_MainWindow):

    
    broadcastsignal=QtCore.pyqtSignal(str)
    
    def __init__(self):
        
# Load an instance of the Digitizer control object
         
        
# Load the ui file for GUI
         QtGui.QMainWindow.__init__(self)
         Ui_MainWindow.__init__(self)
         self.setupUi(self)
         self.mutex = QtCore.QMutex()

         
# Window for real time streaming
         pg.setConfigOption('background','w')
         pg.setConfigOption('foreground','k')
         self.pen=pg.mkPen(color=(0,0,0))
         self.pen2=pg.mkPen(color=(255,0,0))
         #self.pen=pg.mkPen(1)
         #self.streamwindow=pg.LayoutWidget()
         self.plotchannels = pg.GraphicsLayoutWidget()
         self.StreamWindow.addWidget(self.plotchannels,row=0,col=0,rowspan=1,colspan=1)
         
         
         self.plt_chA =self.plotchannels.addPlot(row=0,col=0,colspan=3)
         self.plt_chA.setLabel(axis='left',text='Signal')
         self.plt_chA.setLabel(axis='bottom',text='Tof (x0.5ns)')
         self.plt_chA.showGrid(1,1,alpha=0.5)
         self.plt_datachA=pg.PlotDataItem(np.arange(2000),np.zeros((2000)))
         self.plt_chA.addItem(self.plt_datachA)
         
         
         self.roiA = pg.LinearRegionItem(values=(500,1000),bounds=(-30000,30000)) # first vector =[x0,y0], second vector =[lx,ly]
         self.plt_chA.addItem(self.roiA)
         self.roiA.setZValue(10)  # make sure ROI is drawn above image
         #self.roiA.sigRegionChanged.connect(self.UpdatePlot)
         
         self.plt_intchA =self.plotchannels.addPlot(row=0,col=4,colspan=1)
         self.plt_intchA.setLabel(axis='left',text='Integrated Signal')
         self.plt_intchA.setLabel(axis='bottom',text='real time (ms)')
         self.plt_intchA.showGrid(1,1,alpha=0.5)
         
         
         self.plt_chB =self.plotchannels.addPlot(row=1,col=0,colspan=3)
         self.plt_chB.setLabel(axis='left',text='Signal')
         self.plt_chB.setLabel(axis='bottom',text='Tof (x0.5ns)')
         self.plt_chB.showGrid(1,1,alpha=0.5)
         self.plt_datachB=pg.PlotDataItem(np.arange(2000),np.zeros((2000)))
         self.plt_chB.addItem(self.plt_datachB)
         
         self.roiB = pg.LinearRegionItem(values=(500,1000)) # first vector =[x0,y0], second vector =[lx,ly]
         self.plt_chB.addItem(self.roiB)
         self.roiB.setZValue(10)  # make sure ROI is drawn above image
         #self.roiB.sigRegionChanged.connect(self.UpdatePlot)
         
         self.plt_intchB =self.plotchannels.addPlot(row=1,col=4,colspan=1)
         self.plt_intchB.setLabel(axis='left',text='Integrated Signal')
         self.plt_intchB.setLabel(axis='bottom',text='real time (ms)')
         self.plt_intchB.showGrid(1,1,alpha=0.5)
        
## Window for Dscan in real time

         self.plotchannelsDscan = pg.GraphicsLayoutWidget()
         self.StreamWindow_Dscan.addWidget(self.plotchannelsDscan,row=0,col=0,rowspan=1,colspan=1)
         self.plotDscan=self.plotchannelsDscan.addPlot(row=0,col=0)
         self.imgDscan = pg.ImageItem()
         
         self.plotDscan.addItem(self.imgDscan)
         self.hist = pg.HistogramLUTItem()
         self.hist.setImageItem(self.imgDscan)
         self.plotchannelsDscan.addItem(self.hist,row=0,col=1)
         self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
         self.hist.vb.addItem(self.isoLine)
         self.hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
         self.isoLine.setValue(0.8)
         self.isoLine.setZValue(1000) # bring iso line above contrast controls
         

#Digitizer stream parameters

         self.StartStream_button.clicked.connect(self.StartStream)
         self.StopStream_button.clicked.connect(self.StopStream)
         self.Navg_button.valueChanged.connect(self.setAcquisitionParameters)
         self.SignalThresh_button.valueChanged.connect(self.setAcquisitionParameters)
         
         self.ChA_broadcast_button.stateChanged.connect(self.setBroadcast)


# Digitizer record parameters
        
         self.RecSS_button.clicked.connect(self.setAcquisitionParameters)
         self.RecAvg_button.clicked.connect(self.setAcquisitionParameters)
         self.SaveSparse_button.stateChanged.connect(self.setAcquisitionParameters)
         self.progress=0.0


         self.Nsamples_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Nseconds_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Reprate_button.activated.connect(self.setAcquisitionParameters)
         
         self.ChA_button.clicked.connect(self.setAcquisitionParameters)
         self.ChB_button.clicked.connect(self.setAcquisitionParameters)
         
         self.TrigExt_button.clicked.connect(self.setTriggerSourceExt)
         self.TrigA_button.clicked.connect(self.setTriggerSourceChA)
         self.TrigB_button.clicked.connect(self.setTriggerSourceChB)
         
         self.TrigExtLvl_button.valueChanged.connect(self.setAcquisitionParameters)
         
         self.VrangeA_button.valueChanged.connect(self.setAcquisitionParameters)
         self.VrangeB_button.valueChanged.connect(self.setAcquisitionParameters)
        
         self.VbiasA_button.valueChanged.connect(self.setAcquisitionParameters)
         self.VbiasB_button.valueChanged.connect(self.setAcquisitionParameters)
         
         self.PretriggerVal_button.valueChanged.connect(self.setAcquisitionParameters)
         self.HoldoffVal_button.valueChanged.connect(self.setAcquisitionParameters)
         
         self.RecRef_button.clicked.connect(self.SaveTrace)
         
# Metadata record parameters
         # Voltages
         self.Vtofmcpf_button.valueChanged.connect(self.setMetadata)
         self.Vgrid_button.valueChanged.connect(self.setMetadata)
         self.Vtofdtube_button.valueChanged.connect(self.setMetadata)
         self.Vrep_button.valueChanged.connect(self.setMetadata)
         self.Vext_button.valueChanged.connect(self.setMetadata)
         self.Vcorr_button.valueChanged.connect(self.setMetadata)
         self.Vvmimcpf_button.valueChanged.connect(self.setMetadata)
         self.Vvmimcpb_button.valueChanged.connect(self.setMetadata)
         self.Vph_button.valueChanged.connect(self.setMetadata)
         
         # Channels labels
         self.ChAlabel_button.textChanged.connect(self.setMetadata)
         self.ChBlabel_button.textChanged.connect(self.setMetadata)
         
         #delay value for single tof (no dscan)
         self.Singledelay_button.valueChanged.connect(self.setMetadata)
         
         # Comments on the scan
         self.Comments_button.textChanged.connect(self.setMetadata)
         
# Path for file saving
         self.FilePath_button.textChanged.connect(self.setAcquisitionParameters)
         self.FilePath='//sb1files.epfl.ch/lsu/LSU_DATA/Wetlab/Data/Photoelectrons/20180809'
         self.FilePathBrowser_button.clicked.connect(self.setDir)
#         
#         #self.DscanMode_button.stateChanged.connect(self.setAcquisitionParameters)
         self.DscanStart_button.valueChanged.connect(self.setAcquisitionParameters)
         self.DscanStop_button.valueChanged.connect(self.setAcquisitionParameters)
         self.DscanStep_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Ncycles_button.valueChanged.connect(self.setAcquisitionParameters)
         
         self.delaylist=[]
         
         #self.FilePath_button.textChanged.connect(self.setAcquisitionParameters)
         self.Delayfile=[]
         self.DelayfilePath=''
         self.DelayfileBrowser_button.clicked.connect(self.setDelayfile)

# Start/Stop
         
         
         
         self.data_chA = np.zeros((self.Nsamples_button.value()),dtype=np.int64)
         self.data_chB = np.zeros((self.Nsamples_button.value()),dtype=np.int64)
         
         
         self.rolling_dataA = np.zeros((500,2)) # rolling array for integrated signal in real time from CHA
         self.rolling_dataB = np.zeros((500,2)) # rolling array for integrated signal in real time from CHA
         self.rolling_count = 0
         self.t0 = 0 # first timeStamp recording
         
# broadcast server database creation
         self.server=[]
         
#         self.dbconnect=pymysql.connect(host='128.178.68.57',db='HHGFlux')
#         self.cursor=self.dbconnect.cursor()
#         self.cursor.execute("DROP TABLE IF EXISTS hhgflux")
#         self.cursor.execute("CREATE TABLE hhgflux (flux FLOAT, timestamp FLOAT)")
         
         
         #self.streamwindow.show()
         
         
         self.SavedData_chA = np.zeros((self.Nsamples_button.value()),dtype=np.int64)
         self.SavedData_chB = np.zeros((self.Nsamples_button.value()),dtype=np.int64)

         self.StartAcq_button.clicked.connect(self.StartAcquisition)
         self.StopAcq_button.clicked.connect(self.StopAcquisition)
         self.AcqStart=0
         
         print 'GUI loaded'
         f.write('GUI loaded')
         
         self.timer=QtCore.QTimer()        
         self.timer.timeout.connect(self.UpdatePlot)
         
         self.MetadataDict=[]
         self.recthread=[]
         self.prevthread=[]
         self.broadcastthread=[]
         
         
         self.DAQ=DAQ(f)
         
         f.write('init digitizer done')
         print 'init digitizer done'

    def __del__(self):
        self.DAQ.__del__()
        
    def setAcquisitionParameters(self):
        f.write('Callback set Acq Param\n')
        ParametersArray=[]
        
        
        ## Streaming parameters
        
        self.DAQ.setStreamRecords(self.Navg_button.value())
        

        N_SAMPLES=self.Nsamples_button.value()
        #reset the array size in memory
        self.data_chA = np.zeros((N_SAMPLES),dtype=np.int64)
        self.data_chB = np.zeros((N_SAMPLES),dtype=np.int64)
        self.SavedData_chA = np.zeros((N_SAMPLES),dtype=np.int64)
        self.SavedData_chB = np.zeros((N_SAMPLES),dtype=np.int64)
        
        N_RECORDS=self.Nseconds_button.value()*int(self.Reprate_button.currentText())*1000
        ParametersArray.append(N_SAMPLES)
        self.DAQ.setNRecords(N_RECORDS)
        ParametersArray.append(N_RECORDS)
        
        
        SIGTHRESH=self.SignalThresh_button.value()
        self.DAQ.setSignalThreshold(SIGTHRESH)
        
        REC_FULL=0
        REC_SPARSE=1
        if self.SaveSparse_button.checkState()==2:
            self.DAQ.setSaveSparse(REC_SPARSE)
        elif self.SaveSparse_button.checkState()==0:
            self.DAQ.setSaveSparse(REC_FULL)
            
        REC_CHA=0
        REC_CHB=1
        REC_CHAB=2
        if (self.ChA_button.checkState()==2 and self.ChB_button.checkState()==0):
            ParametersArray.append(REC_CHA)
        elif (self.ChA_button.checkState()==0 and self.ChB_button.checkState()==2):
            ParametersArray.append(REC_CHB)
        elif (self.ChA_button.checkState()==2 and self.ChB_button.checkState()==2):
            ParametersArray.append(REC_CHAB)
        elif (self.ChA_button.checkState()==0 and self.ChB_button.checkState()==0):
            ParametersArray.append(REC_CHA)
            

        TRIG_EXT=2
        TRIG_CHA=3
        TRIG_CHB=3
        if (self.TrigExt_button.isChecked()==True):
            ParametersArray.append(TRIG_EXT)
        elif (self.TrigA_button.isChecked()==True):
            ParametersArray.append(TRIG_CHA)
        elif (self.TrigB_button.isChecked()==True):
            ParametersArray.append(TRIG_CHB)
        
        TRIGLVL=self.TrigExtLvl_button.value()
        self.DAQ.setExtTriggerlevel(TRIGLVL)

        DSCAN_ON=1
        DSCAN_OFF=0
        if self.DscanMode_button.checkState()==2:
            ParametersArray.append(DSCAN_ON)
        else:
            ParametersArray.append(DSCAN_OFF)

        DSCAN_START=self.DscanStart_button.value()
        DSCAN_STOP=self.DscanStop_button.value()
        DSCAN_STEP=self.DscanStep_button.value()
        DSCAN_T0=self.DscanT0_button.value()
        # Create the delaylist Tuple
        self.delaylist=(np.arange(DSCAN_START,DSCAN_STOP+DSCAN_STEP,DSCAN_STEP),DSCAN_T0)
        
        ParametersArray.append(DSCAN_START)
        ParametersArray.append(DSCAN_STOP)
        ParametersArray.append(DSCAN_STEP)
        
        #NCYCLES=self.Ncycles_button.value()
        #self.DAQ.set(NCYCLES)
        
        
        REC_SS=0
        REC_AVG=1
        if (self.RecSS_button.isChecked()==True and self.RecAvg_button.isChecked()==False):
            self.DAQ.setAcqMode(REC_SS)
            ParametersArray.append(REC_SS)
        elif (self.RecSS_button.isChecked()==False and self.RecAvg_button.isChecked()==True):
            self.DAQ.setAcqMode(REC_AVG)
            ParametersArray.append(REC_AVG)
        else:
            self.DAQ.setAcqMode(REC_SS)
            ParametersArray.append(REC_SS)

        #Add the delay array to the parameters
        if self.Delayfile_button.checkState()==2 and self.DscanForward_button.checkState()==2:
            ParametersArray.append(self.Delayfile)
        elif self.Delayfile_button.checkState()==2 and self.DscanBackward_button.checkState()==2:
            ParametersArray.append(np.fliplr(self.Delayfile)[0])
        elif self.Delayfile_button.checkState()==0:
            ParametersArray.append([])
            
        #Voltage range and bias setup
        VRANGE_CHA=self.VrangeA_button.value()
        print VRANGE_CHA
        VRANGE_CHB=self.VrangeB_button.value()
        ParametersArray.append(VRANGE_CHA)
        ParametersArray.append(VRANGE_CHB)
        
        VBIAS_CHA=self.VbiasA_button.value()
        VBIAS_CHB=self.VbiasB_button.value()
        ParametersArray.append(VBIAS_CHA)
        ParametersArray.append(VBIAS_CHB)
        
        #Pretrigger and hold off
        PRETRIGGER=self.PretriggerVal_button.value()
        HOLDOFF=self.HoldoffVal_button.value()
        if self.Pretrigger_button.checkState()==2:
            ParametersArray.append(PRETRIGGER)
        else:
            ParametersArray.append(0)
        if self.Holdoff_button.checkState()==2:
            self.DAQ.setHoldOff(HOLDOFF)
        else:
            self.DAQ.setHoldOff(0)
        
        
        #Record the file save path
        self.FilePath=self.FilePath_button.text()
        
        #Load the parameters on the acquisition card
        f.write('Call Digit parameters setup,length param: %i\n' % len(ParametersArray))
        #self.DAQ.setDigitizerParameters(ParametersArray)
        f.write('Call Digit parameters done\n')
        
        
    def setTriggerSourceExt(self):
            self.TrigExt_button.setChecked(True)
            self.TrigA_button.setChecked(False)
            self.TrigB_button.setChecked(False)
            self.setAcquisitionParameters  
    def setTriggerSourceChA(self):
            self.TrigExt_button.setChecked(False)
            self.TrigA_button.setChecked(True)
            self.TrigB_button.setChecked(False)
            self.setAcquisitionParameters
    def setTriggerSourceChB(self):
            self.TrigExt_button.setChecked(False)
            self.TrigA_button.setChecked(False)
            self.TrigB_button.setChecked(True)
            self.setAcquisitionParameters
        
        
        
        
    def setDelayfile(self):
        
        FNAME = QtGui.QFileDialog.getOpenFileName()
        self.DelayfilePath=FNAME
        self.Delayfile=np.loadtxt(FNAME)
        self.setAcquisitionParameters()
    
    def setDir(self):

        PATHNAME = QtGui.QFileDialog.getExistingDirectory()
        self.FilePath_button.setText(PATHNAME)
        f.write('reset parameters\n')
        self.setAcquisitionParameters()
        
    def setMetadata(self):
        
        f.write('Record Metadata\n')
        self.MetadataDict={'Vtofmpf':self.Vtofmcpf_button.value(), \
                 'Vgrid':self.Vgrid_button.value(), \
                 'Vtofdtube':self.Vtofdtube_button.value(), \
                 'Vrep':self.Vrep_button.value(), \
                 'Vext':self.Vext_button.value(), \
                 'Vcorr':self.Vcorr_button.value(), \
                 'Vvmimcp':self.Vvmimcpf_button.value(), \
                 'Vvmimcpb':self.Vvmimcpb_button.value(), \
                 'Vph':self.Vph_button.value(), \
                 'ChAlabel':self.ChAlabel_button.text(), \
                 'ChBlabel':self.ChBlabel_button.text(), \
                 'Singledelay':self.Singledelay_button.value(), \
                 'Comments':self.Comments_button.toPlainText()}
    
    def saveScanParameters(self,dirname):
        #Saves all the parameters of the run (scan or single TOF).
        f.write('Saving parameters of the run \n')
        
        self.setMetadata()
        
        ScanParamsDict={'NRecords':self.Nseconds_button.value()*int(self.Reprate_button.currentText())*1000, \
                        'NSamples':self.Nsamples_button.value(), \
                        'Scanstart':self.DscanStart_button.value(), \
                        'Scanstop':self.DscanStop_button.value(), \
                        'Scanstep':self.DscanStep_button.value(), \
                        'Metadata':self.MetadataDict}
                        
        ScanParamsSavename_mat='%s/%i%s%s_%s%s_ScanParameters.mat' % (dirname,dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2))
        ScanParamsSavename_npz='%s/%i%s%s_%s%s_ScanParameters.npz' % (dirname,dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2))
                                        
        sio.savemat(ScanParamsSavename_mat,ScanParamsDict)
        np.savez(ScanParamsSavename_npz,**ScanParamsDict)
        
    def StartAcquisition(self):
        
        directoryname=self.FilePath+'/'+str(dt.today().year)\
                                        +str(dt.today().month).zfill(2)\
                                        +str(dt.today().day).zfill(2)+'_'\
                                        +str(dt.today().hour).zfill(2)\
                                        +str(dt.today().minute).zfill(2)+'_Scan'

        if not os.path.exists(directoryname):
            os.makedirs(directoryname)
            
        self.saveScanParameters(directoryname) # Save the metadata of the Scan prior to the acquisition in a separate file
        
        f.write('START0\n')
        print 'START0'
        self.AcqStart=1
        
        self.DisableButtons()
        
        f.write('Save Scan parameters\n')
        self.recthread = GrabSignal(self.DAQ,'rec',directoryname,self.Ncycles_button.value(),self.roiB.getRegion())
        if self.DscanMode_button.checkState()==2:
            self.recthread.newData.connect(self.UpdateDscan)
            self.recthread.finishGrab.connect(self.UpdateProgressBar)
            self.recthread.finishAcq.connect(self.EnableButtons)
        else:
            self.recthread.newData.connect(self.UpdateSingleRecord)
            self.recthread.finishGrab.connect(self.UpdateProgressBar)
            self.recthread.finishAcq.connect(self.EnableButtons)
        self.recthread.start()
        
        print 'START1'
        f.write('START1\n')
        
    def StopAcquisition(self):
        
        try:
           self.recthread.stop()
        except:
        
            print 'error'
        
    def setBroadcast(self):

        if self.ChA_broadcast_button.isChecked()==True:
            
            self.server=socket(AF_INET,SOCK_STREAM)
            self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

            self.server.bind((gethostname(),8085))
            self.broadcastobject=BroadcastObject(self.server)
            
        if self.ChA_broadcast_button.isChecked() == False:
            self.server.close()
        
        
    def StartStream(self):
        
        self.streamstatus=1
        self.AcqStart==0
        
        self.rolling_dataA=np.zeros((500,2))
        self.rolling_dataB=np.zeros((500,2))
        self.rolling_count=0
        #self.DAQ.StartStream()
        #thread.start_new_thread(self.UpdateStream,())
        self.prevthread = GrabSignal(self.DAQ,'prev')
        self.prevthread.newData.connect(self.UpdateStream)
        self.prevthread.start()
        
        data=(0,0)
        if self.ChA_broadcast_button.isChecked() == True:
            self.broadcastthread = QtCore.QThread()
            self.broadcastobject.moveToThread(self.broadcastthread)
        
            self.broadcastsignal.connect(self.broadcastobject.UpdateDB)
            self.broadcastthread.start()
        #thread.start_new_thread(UpdateStream,())
        
    def StopStream(self):
        try:
            self.prevthread.stop()
        except:
            print 'no acq thread instanciated'
        if self.ChA_broadcast_button.isChecked() == True:    
            try:
                self.broadcastthread.terminate()
            except:
                print 'no broadcast thread instanciated'
                
                
    def DisableButtons(self):
        
        self.StartStream_button.setEnabled(False)
        self.StopStream_button.setEnabled(False)
        
        self.DscanStart_button.setEnabled(False)
        self.DscanStop_button.setEnabled(False)
        self.DscanStep_button.setEnabled(False)
        self.DscanT0_button.setEnabled(False)
        self.Ncycles_button.setEnabled(False)
        
        self.StartAcq_button.setEnabled(False)
        
        
    def EnableButtons(self):
        
        self.StartStream_button.setEnabled(True)
        self.StopStream_button.setEnabled(True)
        
        self.DscanStart_button.setEnabled(True)
        self.DscanStop_button.setEnabled(True)
        self.DscanStep_button.setEnabled(True)
        self.DscanT0_button.setEnabled(True)
        self.Ncycles_button.setEnabled(True)
        
        self.StartAcq_button.setEnabled(True)

        
        
      
    def UpdateDscan(self,data):
        
        self.imgDscan.setImage(data[0].astype(np.float),autoLevels=False,autoHistogramRange=False)
        
        return 0
    
    def UpdateSingleRecord(self,data):
        
        return 0
        
    def UpdateStream(self,data):
        
        data_ChA=data[0]-np.median(data[0][:1000])
        data_ChB=data[1]-np.median(data[1][:1000])
        
        
        self.rolling_count+=1
        ts=float(data[2]*1e-3-self.t0)
        self.broadcastdata=(data_ChA.sum(),ts)
        
        if self.ChA_broadcast_button.isChecked() == True:
            self.broadcastsignal.emit(str(data_ChA.sum())+';'+str(ts))
            
        self.UpdatePlot((data_ChA,data_ChB,ts))
        
        
    def UpdatePlot(self,data=(np.zeros((2000)),np.zeros((2000)),0)):
        
        self.plt_datachA.setData(data[0],pen=self.pen)
        self.plt_datachB.setData(data[1],pen=self.pen)
        
        
        boundsA=np.array(self.roiA.getRegion()).astype(int)
        boundsB=np.array(self.roiB.getRegion()).astype(int)
        
        ## Rolling plot
        
        
        if self.rolling_count == 1:
            self.t0 = data[2]
            self.rolling_dataA[:,0] = data[0][boundsA[0]:boundsA[1]].sum() 
            self.rolling_dataA[:,1] = data[2]-self.t0
            self.rolling_dataB[:,0] = data[1].sum() 
            self.rolling_dataB[:,1] = data[2]-self.t0
            
        if self.rolling_count<500:
            self.rolling_dataA[self.rolling_count,0]=data[0][boundsA[0]:boundsA[1]].sum()
            self.rolling_dataA[self.rolling_count,1]=data[2]-self.t0
            
            self.rolling_dataB[self.rolling_count,0]=data[1].sum()
            self.rolling_dataB[self.rolling_count,1]=data[2]-self.t0
        else:
            self.rolling_dataA[0,0]=data[0][boundsA[0]:boundsA[1]].sum()
            self.rolling_dataA[:,0]=np.roll(self.rolling_dataA[:,0],-1)
            self.rolling_dataA[0,1]=data[2]-self.t0
            self.rolling_dataA[:,1]=np.roll(self.rolling_dataA[:,1],-1)
            
            self.rolling_dataB[0,0]=data[1].sum()
            self.rolling_dataB[:,0]=np.roll(self.rolling_dataB[:,0],-1)
            self.rolling_dataB[0,1]=data[2]-self.t0
            self.rolling_dataB[:,1]=np.roll(self.rolling_dataB[:,1],-1)
        
        self.plt_intchA.plot(self.rolling_dataA[:,1],self.rolling_dataA[:,0],clear=True,autoLevels=False,pen=self.pen)
        self.plt_intchB.plot(self.rolling_dataB[:,1],self.rolling_dataB[:,0],clear=True,autoLevels=False,pen=self.pen)
        
#        try:
#            if self.AcqStart==1:
#                if self.DAQ.progressflag==1:
#                    self.timer.stop()
#                if not np.all(self.DAQ.data_chA==0):
#                    self.ProgressBar_button.setValue(np.round(100*self.DAQ.progressrecords))
#                    self.plt_chA.plot(self.DAQ.data_chA,clear=True,autoLevels=False,pen=self.pen)
#                    self.plt_chB.plot(self.DAQ.data_chB,clear=True,autoLevels=False,pen=self.pen)
#            else:
#                self.plt_chA.plot(self.data_chA,clear=True,autoLevels=False,pen=self.pen)
#                self.plt_chB.plot(self.data_chB,clear=True,autoLevels=False,pen=self.pen)
#                
#            if self.ShowRef_button.checkState()==2:
#                self.plt_chA.plot(self.SavedData_chA,clear=False,autoLevels=False,pen=self.pen2)
#                self.plt_chB.plot(self.SavedData_chB,clear=False,autoLevels=False,pen=self.pen2)
#                
#                
#        except:
#            print 'error'
        #self.plt_chA.draw()
        #self.plt_chB.draw()
        
    def UpdateProgressBar(self,data):
        self.ProgressBar_button.setValue(int(data))
        
            
    def SaveTrace(self):
        self.SavedData_chA = self.DAQ.data_chA
        self.SavedData_chB = self.DAQ.data_chB

## Start Qt event loop unless running in interactive mode or using pyside.

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
#if __name__ == '__main__':
#    import sys
#    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
#        QtGui.QApplication.instance().exec_()