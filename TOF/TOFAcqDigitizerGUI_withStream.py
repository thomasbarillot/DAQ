import scipy.io as sio

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, uic
import numpy as np
import sys
import os

import thread

import time

from TOFAcqDigitizer_withStream import TOFAcqDigitizer as TAQD

from ctypes import *

from datetime import datetime
## Define main window class from template
#path = os.path.dirname(os.path.abspath(__file__))
#uiFile = os.path.join(path, 'designerExample.ui')
#WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)
Ui_MainWindow, QtBaseClass = uic.loadUiType('TAQD_GUI.ui')

## Make the layout
dt=datetime
thislogfilename='%i%s%s_%s%s%s.log' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2), \
                                        str(dt.today().second).zfill(2))

f=open(thislogfilename,'w')


class MainWindow(QtGui.QMainWindow, Ui_MainWindow):

    def __init__(self):
        
# Load an instance of the Digitizer control object
         
         

# Load the ui file for GUI
         QtGui.QMainWindow.__init__(self)
         Ui_MainWindow.__init__(self)
         self.setupUi(self)
         
         
# Window for real time streaming
         
         self.streamwindow=pg.LayoutWidget()
         self.plotchannels = pg.GraphicsLayoutWidget()
         self.streamwindow.addWidget(self.plotchannels,row=0,col=0,rowspan=1,colspan=1)
         
         
         self.plt_chA =self.plotchannels.addPlot(row=0,col=0)
         self.plt_chA.setLabel(axis='left',text='Signal')
         self.plt_chA.setLabel(axis='bottom',text='Tof (ns)')
        
         self.plt_chB =self.plotchannels.addPlot(row=1,col=0)
         self.plt_chB.setLabel(axis='left',text='Signal')
         self.plt_chB.setLabel(axis='bottom',text='Tof (ns)')
         self.streamwindow.show()

## Link the buttons
         
         self.RecMode_button.clicked.connect(self.setAcquisitionParameters)
         self.RecSS_button.clicked.connect(self.setAcquisitionParameters)
         self.RecAvg_button.clicked.connect(self.setAcquisitionParameters)
         
# Digitizer record parameters

         self.Nsamples_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Nrecords_button.valueChanged.connect(self.setAcquisitionParameters)
         
         self.ChA_button.clicked.connect(self.setAcquisitionParameters)
         self.ChB_button.clicked.connect(self.setAcquisitionParameters)
         
         self.TrigExt_button.clicked.connect(self.setAcquisitionParameters)
         self.TrigA_button.clicked.connect(self.setAcquisitionParameters)
         self.TrigB_button.clicked.connect(self.setAcquisitionParameters)
         
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
         self.FilePath='L:/atto/labdata/2016/20160411_Isopropanol'
         self.FilePathBrowser_button.clicked.connect(self.setDir)
#         
#         #self.DscanMode_button.stateChanged.connect(self.setAcquisitionParameters)
         self.DscanStart_button.valueChanged.connect(self.setAcquisitionParameters)
         self.DscanStop_button.valueChanged.connect(self.setAcquisitionParameters)
         self.DscanStep_button.valueChanged.connect(self.setAcquisitionParameters)
         
         #self.FilePath_button.textChanged.connect(self.setAcquisitionParameters)
         self.Delayfile=[]
         self.DelayfilePath=''
         self.DelayfileBrowser_button.clicked.connect(self.setDelayfile)

# Start/Stop
         self.StartStream_button.clicked.connect(self.StartStream)
         self.StopStream_button.clicked.connect(self.StopStream)
         
         
         self.data_chA = np.zeros((self.Nsamples_button.value()),dtype=np.int16)
         self.data_chB = np.zeros((self.Nsamples_button.value()),dtype=np.int16)

         self.StartAcq_button.clicked.connect(self.StartAcquisition)
         self.StopAcq_button.clicked.connect(self.StopAcquisition)
         print 'GUI loaded'
         f.write('GUI loaded')
         
         self.timer=QtCore.QTimer()        
         self.timer.timeout.connect(self.UpdatePlot)
         
         self.MetadataDict=[]
         
         self.myTAQD=TAQD(f)
         f.write('init digitizer done')
         print 'init digitizer done'

    def __del__(self):
        self.TAQD.__del__()
        
    def setAcquisitionParameters(self):
        f.write('Callback set Acq Param\n')
        ParametersArray=[]

        N_SAMPLES=self.Nsamples_button.value()
        N_RECORDS=self.Nrecords_button.value()
        ParametersArray.append(N_SAMPLES)
        ParametersArray.append(N_RECORDS)

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
            self.TrigA_button.setChecked(False)
            self.TrigB_button.setChecked(False)
            ParametersArray.append(TRIG_EXT)
        elif (self.TrigA_button.isChecked()==True):
            self.TrigExt_button.setChecked(False)
            self.TrigB_button.setChecked(False)
            ParametersArray.append(TRIG_CHA)
        elif (self.TrigB_button.isChecked()==True):
            self.TrigA_button.setChecked(False)
            self.TrigExt_button.setChecked(False)
            ParametersArray.append(TRIG_CHB)

        DSCAN_ON=1
        DSCAN_OFF=0
        if self.DscanMode_button.checkState()==2:
            ParametersArray.append(DSCAN_ON)
        else:
            ParametersArray.append(DSCAN_OFF)

        DSCAN_START=self.DscanStart_button.value()
        DSCAN_STOP=self.DscanStop_button.value()
        DSCAN_STEP=self.DscanStep_button.value()
        ParametersArray.append(DSCAN_START)
        ParametersArray.append(DSCAN_STOP)
        ParametersArray.append(DSCAN_STEP)
        
        REC_SS=0
        REC_AVG=1
        if (self.RecSS_button.isChecked()==True and self.RecAvg_button.isChecked()==False):
            ParametersArray.append(REC_SS)
        elif (self.RecSS_button.isChecked()==False and self.RecAvg_button.isChecked()==True):
            ParametersArray.append(REC_AVG)
        else:
            ParametersArray.append(REC_SS)

        #Add the delay array to the parameters
        if self.Delayfile_button.checkState()==2 and self.DscanForward_button.checkState()==2:
            ParametersArray.append(self.Delayfile)
        elif self.Delayfile_button.checkState()==2 and self.DscanBackward_button.checkState()==2:
            ParametersArray.append(np.fliplr(self.Delayfile)[0])
        elif self.Delayfile_button.checkState()==0:
            ParametersArray.append([])

        self.FilePath=self.FilePath_button.text()
        f.write('Call Digit parameters setup,lenght param: %i\n' % len(ParametersArray))
        self.myTAQD.setDigitizerParameters(ParametersArray)
        f.write('Call Digit parameters done\n')
        
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
        
        ScanParamsDict={'NRecords':self.Nrecords_button.value(), \
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
            
        f.write('Save Scan parameters\n')
        self.saveScanParameters(directoryname) # Save the metadata of the Scan prior to the acquisition in a separate file
        
        f.write('START0\n')
        print 'START0'
        self.myTAQD.StartRecording(directoryname)
        print 'START1'
        f.write('START1\n')
        
    def StopAcquisition(self):
        
        #if self.StreamMode.CheckState()==2:
            #self.myTAQD.StopStream()
        #else:
        self.myTAQD.StopRecording()
        f.write('STOP\n')
        print 'STOP'
        
    def StartStream(self):
        
        self.streamstatus=1
        self.myTAQD.StartStream()
        thread.start_new_thread(self.UpdateStream,())
        self.UpdatePlot
        self.timer.timeout.connect(self.UpdatePlot)
        self.timer.start(0.25)
        #self.UpdateStream()
        #thread.start_new_thread(UpdateStream,())
        
    def UpdateStream(self):
        count=0
        tmpchA = np.zeros((self.Nsamples_button.value()),dtype=np.int16)
        tmpchB = np.zeros((self.Nsamples_button.value()),dtype=np.int16)
        while self.streamstatus==1:
            try:
                data_chA,data_chB=self.myTAQD.UpdateStream()
                if len(data_chA)==0 or len(data_chB)==0:
                    data_chA = np.zeros((self.Nsamples_button.value()),dtype=np.int16)
                    data_chB = np.zeros((self.Nsamples_button.value()),dtype=np.int16)
                print 'data stream recorded'♥
                count+=1
                if self.streamavg_button.isChecked()==True:
                    print 'Rec data stream avg'
                    if count>=self.Navg_button.value():
                        self.data_chA=tmpchA/np.float(self.Navg_button.value())
                        self.data_chB=tmpchB/np.float(self.Navg_button.value())
                        tmpchA = data_chA
                        tmpchB = data_chB
                        count=0
                    else:
                        tmpchA+=data_chA
                        tmpchB+=data_chB

                else:
					self.data_chA=data_chA
					self.data_chB=data_chB
                
                #time.sleep(0.5)
                print 'updating the streaming'
            except:
                print 'error updating the streaming'
        
        self.myTAQD.StopStream()
    
    def UpdatePlot(self):
        try:
            self.plt_chA.plot(self.data_chA,clear=True,autoLevels=False)
            self.plt_chB.plot(self.data_chB,clear=True,autoLevels=False)
        except:
            print 'error'
        #self.plt_chA.draw()
        #self.plt_chB.draw()
        
    def StopStream(self):
        try:
            self.streamstatus=0
            self.timer.stop()
        except:
            print 'memory conflict; retry'
            time.sleep(1.0)
            self.streamstatus=0
            self.timer.stop()

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