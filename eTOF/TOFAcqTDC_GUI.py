import scipy.io as sio

import pyqtgraph as pg

from pyqtgraph.Qt import QtCore, QtGui, uic
import numpy as np
import sys
import os
import pandas as pd

import thread
import threading

#import sqlite3

import time
import datetime

import ctypes


from TDC_DAQ import TDC_DAQ as DAQ
from SCTDC_DAQ import SCTDC_DAQ as SCTDC

from WetLab_NewportDelayStage import DelayStage

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
class RunSCTDC(pg.QtCore.QThread):
    newDataDscan = pg.QtCore.Signal(object)
    newDelay = pg.QtCore.Signal(object)
    
    def __init__(self,SCTDC,Dstage,foldername,delaylist_mm,acqtime,Nmaxcycles,ROI):
        QtCore.QThread.__init__(self)
        
        self.SCTDC=SCTDC
        self.Dstage=Dstage
        self.acqtime=acqtime*1000
        self.ROI=ROI
        self.Nmaxcycles=Nmaxcycles
        self.delaylist=np.around(delaylist_mm,decimals=3)
        self.foldername=foldername
        
        
        self.stopMutex = threading.Lock()
        self._stop = False
        
    def run(self):
        
        self.SCTDC.ConnectSCTDC()
        ncycles=0
        delayindex=0
        
        DelayScan=np.zeros((len(self.delaylist),self.ROI[1]-self.ROI[0]-1))
        DelayunPumpedScan=np.zeros((len(self.delaylist),self.ROI[1]-self.ROI[0]-1))
        DelayPumpedScan=np.zeros((len(self.delaylist),self.ROI[1]-self.ROI[0]-1))
        
        while ncycles < self.Nmaxcycles:
            
            with self.stopMutex:
                    if self._stop:
                        break
                    
            DelayScan_tmp=np.zeros((len(self.delaylist),self.ROI[1]-self.ROI[0]-1))
            DelayunPumpedScan_tmp=np.zeros((len(self.delaylist),self.ROI[1]-self.ROI[0]-1))
            DelayPumpedScan_tmp=np.zeros((len(self.delaylist),self.ROI[1]-self.ROI[0]-1))
            
            delayindex=0
            
            while delayindex < len(self.delaylist):
                
                
                
                with self.stopMutex:
                    if self._stop:
                        break
                    
                self.newDelay.emit((delayindex,self.delaylist[delayindex],ncycles))  
                ## Move the stage
                self.Dstage.MoveAbs(self.delaylist[delayindex])
                time.sleep(1.0)
                
                # Launch Data recording
                self.SCTDC.SCTDCStart(self.acqtime)
                data = self.SCTDC.SCTDCRead(self.ROI)
                print len(data[0]),len(data[1])
                
                Hunpumped,ex=np.histogram(np.array(data[0]),bins=np.arange(self.ROI[0],self.ROI[1]))
                Hpumped,ex=np.histogram(np.array(data[1]),bins=np.arange(self.ROI[0],self.ROI[1]))
                
                DelayScan_tmp[delayindex,:]=Hpumped-Hunpumped
                DelayunPumpedScan_tmp[delayindex,:]=Hunpumped
                DelayPumpedScan_tmp[delayindex,:]=Hpumped
                
                
                DelayScan[delayindex,:]+=Hpumped-Hunpumped
                DelayunPumpedScan[delayindex,:]+=Hunpumped
                DelayPumpedScan[delayindex,:]+=Hpumped
                
                #Update plot
                self.newDataDscan.emit((DelayScan))
                
                delayindex+=1
                
            sio.savemat(self.foldername+'SCTDCmaps_repeat%i.mat'%ncycles,{'Diff':DelayScan_tmp,'Pumped':DelayPumpedScan_tmp,'Unpumped':DelayunPumpedScan_tmp})
                
            ncycles+=1
        
        self.SCTDC.__del__()
                
    def stop(self):
        with self.stopMutex:
            self._stop = True
            
        self.SCTDC.__del__()
            
            
class RunTDC(pg.QtCore.QThread):
    
    newData = pg.QtCore.Signal(object)
    newDataDscan = pg.QtCore.Signal(object)
    newDelay = pg.QtCore.Signal(object)
    StreamFinished = pg.QtCore.Signal()
    
    def __init__(self,DAQ,dscanmode,isstream,Dstage=0,delaylist_mm=np.array([0]),Nmaxcycles=1):
        QtCore.QThread.__init__(self)
        
        self.DAQ=DAQ
        self.dscanmode=dscanmode
        self.isstream=isstream
        self.stopMutex = threading.Lock()
        self._stop = False
        self.Dstage=Dstage
        self.delaylist=np.around(delaylist_mm,decimals=3)
        self.Nmaxcycles=Nmaxcycles
        
    def run(self):
        
        if self.isstream==1:
            if os.path.isfile('PE_tmp_file.csv')==True:
                os.remove('PE_tmp_file.csv')
                
            else:
                self.DAQ.StartStream() 
                while True:

                    with self.stopMutex:
                        if self._stop:
                            break
                    try:
                        datastream=self.DAQ.RunStream()
                        datarange=self.DAQ.PollRange()
                        self.newData.emit((datastream,datarange))
                    except:
                        print 'going out of the stream loop'
                        break
                    
                    if os.path.isfile(self.DAQ.fname+'.csv')==True:
                        break
                 
                self.DAQ.StopStream() 
                self.StreamFinished.emit()
                
        
        else:
            if self.dscanmode == 0:
                
                self.DAQ.setFilename('PES')
                self.DAQ.setTDCParameters()
                self.DAQ.StartRecording() 
                
                while True:
                    
                    with self.stopMutex:
                        if self._stop:
                            break
                    try:
                        datastream=self.DAQ.RunStream()
                        datarange=self.DAQ.PollRange()
                        self.newData.emit((datastream,datarange))
                    except:
                        print 'going out of the stream loop'
                        break
                    
                    if os.path.isfile(self.DAQ.fname+'.csv')==True:
                        break
                 
                #self.DAQ.StopRecording()
            
            if self.dscanmode == 1:
                
                fname0=self.DAQ.fname
                ncycles=0
                
                print 0,self.delaylist[0]
                self.Dstage.MoveAbs(self.delaylist[0])
                time.sleep(5.0)  
                
                while ncycles < self.Nmaxcycles:
                
                    with self.stopMutex:
                        if self._stop:
                            break
                
                    delayindex=0
                
                    while delayindex < len(self.delaylist):
                        
                        with self.stopMutex:
                            if self._stop:
                                break
                            
                        self.newDelay.emit((delayindex,self.delaylist[delayindex],ncycles))    
                        print self.delaylist[delayindex]
                        self.Dstage.MoveAbs(self.delaylist[delayindex])
                        time.sleep(1.0)    
                        
                        self.DAQ.setFilename('DATA_r%s_d%s'%(str(ncycles).zfill(3),str(delayindex).zfill(3)))
                        self.DAQ.setTDCParameters()
                        self.DAQ.StartRecording() 
                        while os.path.isfile(self.DAQ.fname+'.csv')==False:
                            with self.stopMutex:
                                if self._stop:
                                    break
                                
                                
                                try:
                                    datastream=np.array(self.DAQ.RunStream())
                                    datarange=self.DAQ.PollRange()

                                    if (delayindex==0) and (ncycles==0):
                                        DelayScan=np.zeros((len(self.delaylist),datarange))
                                    
                                    if datastream[0:200].sum()>50: 
                                        self.DAQ.StopRecording()
                                        break

                                    DelayScan[delayindex,:]+=datastream
                                    self.newData.emit((datastream,datarange)) 
                                    self.newDataDscan.emit((DelayScan))
                                except:
                                    print 'going out of the stream loop'
                                    break
                                #if os.path.isfile(self.DAQ.fname+'.asc')==True:
                                #    break
                        
                        #self.DAQ.StopRecording()
                        
                        delayindex+=1
                    ncycles+=1
                    
                self.newDelay.emit((delayindex,self.delaylist[delayindex],ncycles))
        
                
#    def savedata(self):
#        
#        np.savetxt()
        
        #print dataA.shape

    def stop(self):
        with self.stopMutex:
            self._stop = True

##############################################################               
## Broadcasting the signal in a thread



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
         
         
         self.plt_chA =self.plotchannels.addPlot(row=0,col=0)
         self.plt_chA.setLabel(axis='left',text='Signal')
         self.plt_chA.setLabel(axis='bottom',text='Tof (x0.5ns)')
         self.plt_chA.showGrid(1,1,alpha=0.5)
         self.plt_datachA=pg.PlotDataItem(np.arange(2000),np.zeros((2000)))
         self.plt_chA.addItem(self.plt_datachA)
         
         
         self.roiA = pg.LinearRegionItem(values=(500,1000),bounds=(-30000,30000)) # first vector =[x0,y0], second vector =[lx,ly]
         self.plt_chA.addItem(self.roiA)
         self.roiA.setZValue(10)  # make sure ROI is drawn above image
         #self.roiA.sigRegionChanged.connect(self.UpdatePlot)
         
         self.plt_intchA =self.plotchannels.addPlot(row=1,col=0)
         self.plt_intchA.setLabel(axis='left',text='Integrated Signal')
         self.plt_intchA.setLabel(axis='bottom',text='real time (ms)')
         self.plt_intchA.showGrid(1,1,alpha=0.5)
         
        
         self.ROIRate_button.display(0)
         
         
         self.plotchannelsSCTDC = pg.GraphicsLayoutWidget()
         self.StreamWindow_SCTDC.addWidget(self.plotchannelsSCTDC,row=0,col=0,rowspan=1,colspan=1)
         self.plotScan=self.plotchannelsSCTDC.addPlot(row=0,col=0)
         self.imgSCTDC = pg.ImageItem()
         self.plotScan.addItem(self.imgSCTDC)
         
         
         self.hist = pg.HistogramLUTItem()
         self.hist.setImageItem(self.imgSCTDC)
         self.plotchannelsSCTDC.addItem(self.hist,row=0,col=1)
         
         self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
         self.hist.vb.addItem(self.isoLine)
         self.hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
         self.isoLine.setValue(0.8)
         self.isoLine.setZValue(1000) # bring iso line above contrast controls
         

#Digitizer stream parameters

         self.StartStream_button.clicked.connect(self.StartStream)
         self.StopStream_button.clicked.connect(self.StopStream)
         self.SignalThresh_button.valueChanged.connect(self.setAcquisitionParameters)
         self.TOFT0_button.valueChanged.connect(self.setAcquisitionParameters)
         #self.ChA_broadcast_button.stateChanged.connect(self.
         


# Digitizer record parameters
        
         self.RecSS_button.clicked.connect(self.setAcquisitionParameters)
         self.RecAvg_button.clicked.connect(self.setAcquisitionParameters)
         self.progress=0.0

         self.Nsamples_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Nseconds_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Reprate_button.activated.connect(self.setAcquisitionParameters)
         
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
         #self.ChAlabel_button.textChanged.connect(self.setMetadata)
         #self.ChBlabel_button.textChanged.connect(self.setMetadata)
         
         #delay value for single tof (no dscan)
         self.Singledelay_button.valueChanged.connect(self.setMetadata)
         
         # Comments on the scan
         self.Comments_button.textChanged.connect(self.setMetadata)
         
# Path for file saving
         self.FilePath_button.textChanged.connect(self.setAcquisitionParameters)
         self.FilePath='//sb1files.epfl.ch/lsu/LSU_DATA/Wetlab/Data/Photoelectrons/20180809'
         self.FilePathBrowser_button.clicked.connect(self.setDir)
#         
         self.DscanMode_button.stateChanged.connect(self.setAcquisitionParameters)
         self.DscanStart_button.valueChanged.connect(self.setAcquisitionParameters)
         self.DscanStop_button.valueChanged.connect(self.setAcquisitionParameters)
         self.DscanStep_button.valueChanged.connect(self.setAcquisitionParameters)
         
         #self.FilePath_button.textChanged.connect(self.setAcquisitionParameters)
         self.Delayfile=[]
         self.DelayfilePath=''
         self.DelayfileBrowser_button.clicked.connect(self.setDelayfile)

# Start/Stop
         
         
         
         self.data_chA = np.zeros((self.Nsamples_button.value()),dtype=np.int64)
         self.RecData_chA=np.zeros((self.Nsamples_button.value()*2),dtype=np.int64)
         
         self.diff_data=0
         self.prev_data=0
         
         self.rolling_dataA = np.zeros((500,2)) # rolling array for integrated signal in real time from CHA
         self.rolling_count = 0
         self.t0 = 0 # first timeStamp recording

         self.SavedData_chA = np.zeros((self.Nsamples_button.value()),dtype=np.int64)
         
         self.StartAcq_button.clicked.connect(self.StartAcquisition)
         self.StopAcq_button.clicked.connect(self.StopAcquisition)
         self.AcqStart=0
         
         print 'GUI loaded'
         f.write('GUI loaded')
         
         self.timer=QtCore.QTimer()        
         self.timer.timeout.connect(self.UpdateRecording)
         
         self.MetadataDict=[]
         self.thread=[]
         self.SCTDCthread=[]
         self.TDCthread=[]
         self.broadcastthread=[]
         
         
         self.DAQ=DAQ()
         self.SCTDC=[]
         self.Dstage=DelayStage()
         
         
         
         self.KineticEnergy=np.zeros((self.Nsamples_button.value()))
         self.delaylist=np.zeros((1))
         
         f.write('init digitizer done')
         print 'init digitizer done'

    def __del__(self):
        self.DAQ.__del__()
        self.Dstage.__del__()
        
    def setAcquisitionParameters(self):
        f.write('Callback set Acq Param\n')
        ParametersArray=[]
        
        
        ## Streaming parameters
        #
        #self.DAQ.setStreamRecords(self.Navg_button.value())
        

        # Set the recording range in in ns
        N_SAMPLES=self.Nsamples_button.value()
        self.DAQ.setNsamples(N_SAMPLES)
        ParametersArray.append(N_SAMPLES)
        
        # Set the number of records (or number of sweeps)
        N_RECORDS=self.Nseconds_button.value()*int(self.Reprate_button.currentText())*1000
        self.DAQ.setNRecords(N_RECORDS)
        ParametersArray.append(N_RECORDS)
        
        #Set the saving mode: 3 for list and csv; 1 for csv only and 4 for list only
        if self.RecSS_button.isChecked():
            SAVERECORDS=3
        elif self.RecAvg_button.isChecked():
            SAVERECORDS=1
        self.DAQ.setAcqMode(SAVERECORDS)
        
        #TDCTHRESH=self.SignalThresh_button.value()
        #self.DAQ.setSignalThreshold(TDCTHRESH)
        
        TRIGLVL=self.TrigExtLvl_button.value()
        self.DAQ.setExtTriggerlevel(TRIGLVL)

        DSCAN_ON=1
        DSCAN_OFF=0
        if self.DscanMode_button.checkState()==2:
            self.DAQ.setDscanMode(DSCAN_ON)
        else:
            self.DAQ.setDscanMode(DSCAN_OFF)
            
        
        DSCAN_START=self.DscanStart_button.value()
        DSCAN_STOP=self.DscanStop_button.value()
        DSCAN_STEP=self.DscanStep_button.value()
        
        
        if self.Delayfile_button.checkState() == 2:
            self.delaylist_fs=self.Delayfile*1e-15
        else:
            self.delaylist_fs=np.arange(DSCAN_START,DSCAN_STOP+DSCAN_STEP,DSCAN_STEP)*1e-15
            
        
        self.delaylist_mm=self.delaylist_fs*((299792458.0*1000.0)/2.0)+self.T0_um_button.value()*1e-3
        
        #print 'delay list mm',self.delaylist_mm
        #print 'delay list mm first value',self.delaylist_mm[0],type(self.delaylist_mm[0])
        #Add the delay array to the parameters
        if self.Delayfile_button.checkState()==2 and self.DscanForward_button.checkState()==2:
            ParametersArray.append(self.Delayfile)
        elif self.Delayfile_button.checkState()==2 and self.DscanBackward_button.checkState()==2:
            ParametersArray.append(np.fliplr(self.Delayfile)[0])
        elif self.Delayfile_button.checkState()==0:
            ParametersArray.append([])
            
        
        #Pretrigger and hold off
        PRETRIGGER=self.PretriggerVal_button.value()
        HOLDOFF=self.HoldoffVal_button.value()
        if self.Pretrigger_button.checkState()==2:
            ParametersArray.append(PRETRIGGER)
        else:
            ParametersArray.append(0)
        if self.Holdoff_button.checkState()==2:
            ParametersArray.append(HOLDOFF)
        else:
            ParametersArray.append(0)
        
        
        #Record the file save path
        
        self.FilePath=self.FilePath_button.text()
       
        #Load the parameters on the acquisition card
        f.write('Call Digit parameters setup,length param: %i\n' % len(ParametersArray))
        #self.DAQ.setDigitizerParameters(ParametersArray)
        f.write('Call Digit parameters done\n')
        
        
    def getCalibrationFactor(self):
        
        
        try:
            Calibfile=np.load('ElensCalibFile.npz')
            idx1=np.where(Calibfile['V1']==V1_button.value())[0][0]
            idx2=np.where(Calibfile['V2']==V2_button.value())[0][0]
            idx3=np.where(Calibfile['V3']==V3_button.value())[0][0]
            
            self.Coeff_info.setText('Suggested correction Coeff: %0.4f'%Calibfile['ElensCalib'][idx1,idx2,idx3])
        except:
            self.Coeff_info.setText('Suggested correction Coeff: ???')
            
            
    def setCalibration(self,data):
        
        me=9.0938356e-31
        
        L=self.TOFlength_button.value()
        if self.VOnOff_button.checkState() == 2:
            Leff=L*self.CalibCoeff_button.value()
            #self.Coeff_info.setText('Suggested correction Coeff: %0.4f'%)
        else:
            Leff=L
            
        T0=self.TOFT0_button.value()*1e-9
            
        SCTDCbinsize=27.4e-12
        TDCbinsize=100.0e-12
        SCTDCoffset=self.SCTDCOffset_button.value()*1e-9
        TDCoffset=self.TDCOffset_button.value()*1e-9
        
        if self.SCTDC_button.checkState() == 2:
            T=np.arange(0,data.shape[1])*SCTDCbinsize+SCTDCoffset
            E=6.24e18*0.5*me*(Leff**2)/((T-T0)**2)
            
            
        else:
        
            #if len(data.shape)==2:
            #    T=np.arange(0,data.shape[1])*TDCbinsize+TDCoffset
            #    E=6.24e18*0.5*me*(Leff**2)/((T-T0)**2)
                
            #elif len(data.shape)==1:
            T=np.arange(0,data[0])*TDCbinsize+TDCoffset
            E=6.24e18*0.5*me*(Leff**2)/((T-T0)**2)
                
            #else:
            #    return 0
            
        self.KineticEnergy=E
        
        
        
        
        
    def setDelayfile(self):
        
        FNAME = QtGui.QFileDialog.getOpenFileName()
        self.DelayfilePath=FNAME
        print FNAME
        self.Delayfile=np.loadtxt(FNAME[0]).astype(float)
        print self.Delayfile
        self.delaylist_fs=self.Delayfile*1e-15
        self.setAcquisitionParameters()
    
    def setDir(self):

        PATHNAME = QtGui.QFileDialog.getExistingDirectory()
        self.FilePath_button.setText(PATHNAME)
        f.write('reset parameters\n')
        self.DAQ.setFoldername(PATHNAME)
        #self.setAcquisitionParameters()
        
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
        
        STREAM_OFF=0
        
        directoryname=self.FilePath+'/'+str(dt.today().year)\
                                        +str(dt.today().month).zfill(2)\
                                        +str(dt.today().day).zfill(2)+'_'\
                                        +str(dt.today().hour).zfill(2)\
                                        +str(dt.today().minute).zfill(2)+'_Scan/'

        if not os.path.exists(directoryname):
            os.makedirs(directoryname)
            
        self.Filename_val.setText(str(dt.today().year)\
                                        +str(dt.today().month).zfill(2)\
                                        +str(dt.today().day).zfill(2)+'_'\
                                        +str(dt.today().hour).zfill(2)\
                                        +str(dt.today().minute).zfill(2)+'_Scan')
        
        ## Disable buttons to avoid any issue
        
        self.DisableButtons()
        
        
        # for showing the data
        
        self.rolling_dataA=np.zeros((500,2))
        self.rolling_dataB=np.zeros((500,2))
        self.rolling_count=0    
        
        f.write('Save Scan parameters\n')
        self.DAQ.setFoldername(directoryname) # Save the metadata of the Scan prior to the acquisition in a separate file
        np.savetxt(directoryname+'delaylist.txt',self.delaylist_mm)
        
        if self.SCTDC_button.checkState() == 2:
            
            self.SCTDC=SCTDC()
            
            ROI=(0,self.Nsamples_button.value()*10)
            self.SCTDCthread = RunSCTDC(self.SCTDC,self.Dstage,directoryname,self.delaylist_mm,self.Nseconds_button.value(),self.Ncycles_button.value(),ROI)
            self.SCTDCthread.newDataDscan.connect(self.UpdateDscan)
            self.SCTDCthread.newDelay.connect(self.UpdateInfos)
            self.SCTDCthread.start()
            
            return 0
            
        
        else:
        #Launch starting of scan command
        #self.increment=0
            if self.DscanMode_button.checkState() == 2:
                
                np.savetxt(directoryname+'delaylist.txt',self.delaylist_mm)
                #self.ProgressBar_button.setEnable(True)
                
                status=self.Dstage.MoveAbs(self.delaylist_mm[0])
                time.sleep(1.0);
            
                self.TDCthread = RunTDC(self.DAQ,1,STREAM_OFF,self.Dstage,self.delaylist_mm,self.Ncycles_button.value())
                self.TDCthread.newData.connect(self.UpdateRecording)
                self.TDCthread.newDataDscan.connect(self.UpdateDscan)
                self.TDCthread.newDelay.connect(self.UpdateInfos)
                self.TDCthread.start()
                
                return 0
            
            else:
                self.TDCthread = RunTDC(self.DAQ,0,STREAM_OFF)
                self.TDCthread.newData.connect(self.UpdateRecording)
                self.TDCthread.start()
                
                return 0
                
            
            
#            self.DAQ.StartRecording(self.increment)           
#        elif self.DscanMode_button.checkState()==0:
#            self.DAQ.StartRecording(0)
#            
#        self.diff_data=np.zeros((self.DAQ.PollRange()))
#        self.prev_data=np.zeros((self.DAQ.PollRange()))
#        
#        #self.acqthread = RunAcquisition(self.DAQ)
#        #self.acqthread.start()
#        #time.sleep(1)
#        self.timer.timeout.connect(self.UpdateRecording)
#        self.timer.start(500)
        #self.thread = GrabSignal(self.DAQ) #Start the grabSignal thread to pull the data and plot it
        #self.thread.newData.connect(self.UpdateStream)
        #self.thread.start()
        
        f.write('START0\n')
        print 'START0'
        self.AcqStart=1
        
        
        print 'START1'
        f.write('START1\n')
        
    def StopAcquisition(self):
        
        if self.SCTDC_button.checkState() == 2:
            self.SCTDCthread.stop()
        else:
            self.TDCthread.stop()
        
        self.EnableButtons()
#        self.timer.stop()
#        self.DAQ.StopRecording()
#        f.write('STOP\n')
        print 'STOP'
        
        
        
    def StartStream(self):
        
        STREAM_ON=1
        
        self.StartAcq_button.setEnabled(False)
        self.StartStream_button.setEnabled(False)
        self.StopAcq_button.setEnabled(False)
        
        self.RecParams_Group.setEnabled(False)
        self.DscanParams_Group.setEnabled(False)
        
        if self.SCTDC_button.checkState()==2:
            self.SCTDC_button.setcheckState(0)
        
        directoryname=''

        #if not os.path.exists(directoryname):
        #    os.makedirs(directoryname)
        
        # for showing the data
        
        self.rolling_dataA=np.zeros((500,2))
        #self.rolling_dataB=np.zeros((500,2))
        self.rolling_count=0    
        
        f.write('Save Scan parameters\n')
        self.DAQ.setFoldername(directoryname) # Save the metadata of the Scan prior to the acquisition in a separate file
        
        
        self.TDCthread = RunTDC(self.DAQ,0,STREAM_ON)
        self.TDCthread.newData.connect(self.UpdateRecording)
        self.TDCthread.StreamFinished.connect(self.StopStream)
        self.TDCthread.start()
                
        return 0
                
            
    def StopStream(self):
        
        self.TDCthread.stop()
        
        self.StartAcq_button.setEnabled(True)
        self.StartStream_button.setEnabled(True)
        self.StopAcq_button.setEnabled(True)
        
        self.RecParams_Group.setEnabled(True)
        self.DscanParams_Group.setEnabled(True)
        
        return 0
#       
        
    def DisableButtons(self):
        
        self.StartStream_button.setEnabled(False)
        self.StopStream_button.setEnabled(False)
        
        self.StartAcq_button.setEnabled(False)
        
        self.RecParams_Group.setEnabled(False)
        self.DscanParams_Group.setEnabled(False)
       
        
    def EnableButtons(self):
        
        self.StartStream_button.setEnabled(True)
        self.StopStream_button.setEnabled(True)
        
        self.StartAcq_button.setEnabled(True)
        
        self.RecParams_Group.setEnabled(True)
        self.DscanParams_Group.setEnabled(True)
       
        
        
    def UpdateRecording(self,data):
        
        
        if self.SCTDC_button.checkState() == 2:
            
            self.UpdatePlot(data)
            return 0
        
        else:
            if self.rolling_count == 0:
                
                self.diff_data=np.zeros((data[1]))
                self.prev_data=np.zeros((data[1]))
                self.rolling_dataA=np.zeros((500,2))
                #self.rolling_dataB=np.zeros((500,2))
                
            self.rolling_count+=1
            self.UpdatePlot(data)
            
            return 0
                
#        if os.path.isfile(self.DAQ.fname+'.asc')==True:
#            print 'ACQ DONE'
#            self.timer.stop()
#            self.DAQ.StopRecording()
#            
#            #return 0
#            
#            
#            if self.DscanMode_button.checkState()==2:
#                self.increment+=1
#                self.Dstage.MoveAbs(self.delaylist_mm[self.increment])
##                moved=self.Dstage.QueryMotion()
##                print moved
##                if moved==False:
##                    self.increment=0
##                    print 'Problem moving delay stage'
##                    return 0
#                time.sleep(1.0);
 
                
                
#                self.DAQ.StartRecording(self.increment)
#                self.timer.timeout.connect(self.UpdateRecording)
#                self.timer.start(500)
                
            
            # move the delayline here
            #self.DAQ.StartRecording()
                   
        
        
#        data = np.array(self.DAQ.RunStream())
       
    def UpdateInfos(self,data):
        
        self.CurrentDelay_val.setText('%0.4f; idx:%i'%(data[1],data[0]))
        self.CurrentRep_val.setText('%i'%(data[2]))
        progress=int(100*(self.delaylist_mm.shape[0]*data[2]+data[0])/(self.Ncycles_button.value()*self.delaylist_mm.shape[0]))
        print progress
        
        self.ProgressBar_button.setValue(progress)
        rectimeleft=(self.Nseconds_button.value()+1)*((self.Ncycles_button.value()*self.delaylist_mm.shape[0])-(self.delaylist_mm.shape[0]*data[2]+data[0]))+5.0
        self.RecTime_val.setText(time.strftime("%H:%M:%S", time.gmtime(rectimeleft)))
        
    def UpdateDscan(self,data):
        
    
        self.imgSCTDC.setImage(data.astype(np.float),border=self.pen,autoLevels=False,autoHistogramRange=False)
#        self.plotScan.setXRange(self.delaylist_fs[0],self.delaylist_fs[-1])
#        self.plotScan.setLabel(axis='bottom',text='Delay (fs)')
#        if self.ShowEnergy_button.checkState() == 2:
#            self.plotScan.setYRange(self.KineticEnergy[-1],self.KineticEnergy[0])
#            self.plotScan.mapFromViewToItem(self.imgSCTDC)
#            self.plotScan.setLabel(axis='left',text='Kinetic energy (fs)')
#        else: 
#            self.plotScan.setLabel(axis='left',text='Bins')
#        
#        self.plotScan.mapFromViewToItem(self.imgSCTDC)
        return 0
        
        
    def UpdatePlot(self,data):
        
        
        if self.SCTDC_button.checkState() == 2:
            self.imgSCTDC.setImage(data.astype(np.float),border=self.pen,autoLevels=False,autoHistogramRange=False)
#            self.plotScan.setXRange(self.delaylist_fs[0],self.delaylist_fs[-1])
#            self.plotScan.setLabel(axis='bottom',text='Delay (fs)')
#            if self.ShowEnergy_button.checkState() == 2:
#                self.plotScan.setYRange(self.KineticEnergy[-1],self.KineticEnergy[0])
#                self.plotScan.setLabel(axis='left',text='Kinetic energy (fs)')
#            else: 
#                self.plotScan.setLabel(axis='left',text='Bins')
#            self.plotScan.mapFromViewToItem(self.imgSCTDC)
            return 0
        
        else:
            self.diff_data=np.array(data[0])-self.prev_data
            self.prev_data=np.array(data[0])
            
            if self.ShowEnergy_button.checkState() == 2:
                self.setCalibration((data[1],))
                self.plt_datachA.setData(self.KineticEnergy,np.array(data[0]),pen=self.pen)
                self.plt_chA.setLabel(axis='bottom',text='Kinetic energy (eV)')
                self.plt_chA.setLimits(xMin=0,xMax=50.0)
                self.plt_chA.setLimits(minXRange=0.01,maxXRange=50.0)
            else:
                self.plt_datachA.setData(np.array(data[0]),pen=self.pen)
                self.plt_chA.setLabel(axis='bottom',text='Tof (x0.1 ns)')
                self.plt_chA.setLimits(xMin=0,xMax=20000.0)
                self.plt_chA.setLimits(minXRange=0.01,maxXRange=20000.0)
            
            
            if self.ShowRef_button.checkState()==2:
                self.plt_chA.plot(self.RecData_chA,autoLevels=False,clear=False,pen=self.pen2)
            
            self.dataChA=np.array(data[0])
        
        
            boundsA=np.array(self.roiA.getRegion()).astype(int)
           
            ## Rolling plot
            
            
            if self.rolling_count == 1:
                #self.t0 = data[2]
                self.rolling_dataA[:,0] = self.diff_data[boundsA[0]:boundsA[1]].sum()/0.5
                self.ROIRate_button.display(self.rolling_dataA[0,0])
           
            if self.rolling_count<500:
                self.rolling_dataA[self.rolling_count,0]=self.diff_data[boundsA[0]:boundsA[1]].sum()/0.5
                self.ROIRate_button.display(self.rolling_dataA[self.rolling_count,0])
                
            else:
                self.rolling_dataA[0,0]=self.diff_data[boundsA[0]:boundsA[1]].sum()/0.5
                self.rolling_dataA[:,0]=np.roll(self.rolling_dataA[:,0],-1)
                self.ROIRate_button.display(self.rolling_dataA[-1,0])
                
            
            self.plt_intchA.plot(self.rolling_dataA[:,0],clear=True,autoLevels=False,pen=self.pen)
            
        
        
    
            
    def SaveTrace(self):
        
        
        self.RecData_chA = self.dataChA
        

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