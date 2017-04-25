import scipy.io as sio

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, uic
import numpy as np
import sys
import os

#from VMIAcqFramegrabber import VMIAcqFramegrabber as VAQD

from ctypes import *
import VMIcrtl_ext

sys.path.append('../../VMIAccumulation')
from VMITraceProcessing import VMITraceProcessing

from datetime import datetime
## Define main window class from template
#path = os.path.dirname(os.path.abspath(__file__))
#uiFile = os.path.join(path, 'designerExample.ui')
#WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)
Ui_MainWindow, QtBaseClass = uic.loadUiType('VAQFG_GUI.ui')

## Make the layout
dt=datetime
thislogfilename='%i%s%s_%s%s%s.log' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2), \
                                        str(dt.today().second).zfill(2))

f=open(thislogfilename,'w')


class MainWindow(QtGui.QMainWindow, Ui_MainWindow):

#%%
    def __init__(self):
        
# Load an instance of the Digitizer control object

        ## Load the ui file for GUI
         QtGui.QMainWindow.__init__(self)
         Ui_MainWindow.__init__(self)
         self.setupUi(self)
         
         
         ## Link the buttons
         
         self.RecMode_button.clicked.connect(self.setAcquisitionParameters)
         self.RecSS_button.clicked.connect(self.setAcquisitionParameters)
         self.RecAvg_button.clicked.connect(self.setAcquisitionParameters)
         
         # Digitizer record parameters

         #self.Nsamples_button.valueChanged.connect(self.setAcquisitionParameters)
         self.Nrecords_button.valueChanged.connect(self.setAcquisitionParameters)
         
         #self.ChA_button.clicked.connect(self.setAcquisitionParameters)
         #self.ChB_button.clicked.connect(self.setAcquisitionParameters)
         
         self.TrigExt_button.clicked.connect(self.setAcquisitionParameters)
         #self.TrigA_button.clicked.connect(self.setAcquisitionParameters)
         #self.TrigB_button.clicked.connect(self.setAcquisitionParameters)
         
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

        ## Start/Stop
         self.StartAcq_button.clicked.connect(self.StartAcquisition)
         self.StopAcq_button.clicked.connect(self.StopAcquisition)
         print 'GUI loaded'
         f.write('GUI loaded')
         
         self.MetadataDict=[]
         
         ##Display graphs
         
         self.ViewWin =pg.LayoutWidget()  # Main layout
         self.ViewWin.setWindowTitle('VMI Viewer')
         self.graph = pg.GraphicsLayoutWidget()
         self.ViewWin.addWidget(self.graph,row=0,col=2,rowspan=17,colspan=5)
         self.ViewWin.resize(1250, 500)
         print 'GUI loaded'
         f.write('GUI loaded')
  
         self.Cartplot=self.graph.addPlot(row=0,col=0,rowspan=2)
         self.Cartplot.setLabel(axis='left',text='Py (pixel)')
         self.Cartplot.setLabel(axis='bottom',text='Py (pixel)')

        ## Item for displaying image data
         self.img = pg.ImageItem()
         self.Cartplot.addItem(self.img)
         self.Cartplot.setAspectLocked(True,ratio=1)

        ## Custom ROI for selecting an image region
         self.roi = pg.CircleROI([100, 100], [50, 50]) # first vector =[x0,y0], second vector =[lx,ly]
#        self.roi.addScaleHandle([0.5, 1], [0.5, 0.5])
#        self.roi.addScaleHandle([0, 0.5], [0.5, 0.5])
         self.Cartplot.addItem(self.roi)
         self.roi.setZValue(10)  # make sure ROI is drawn above image
         self.roi.sigRegionChanged.connect(self.updatePlot)
        
         print 'GUI loaded3'
         f.write('GUI loaded')

        ## Isocurve drawing
         self.iso = pg.IsocurveItem(level=0.8, pen='g')
         self.iso.setParentItem(self.img)
         self.iso.setZValue(5)

        ## Contrast/color control
         self.hist = pg.HistogramLUTItem()
         self.hist.setImageItem(self.img)
         self.graph.addItem(self.hist,row=0,col=1,rowspan=2)

        ## Draggable line for setting isocurve level
         self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
         self.hist.vb.addItem(self.isoLine)
         self.hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
         self.isoLine.setValue(0.8)
         self.isoLine.setZValue(1000) # bring iso line above contrast controls
         self.isoLine.sigDragged.connect(self.updateIsocurve)

        # Another plot area for displaying ROI data
         self.graph.nextRow()
         self.Polplot = self.graph.addPlot(row=0,col=3,colspan=2)
         self.Polplot.setLabel(axis='left',text='Radius (px)')
         self.Polplot.setLabel(axis='bottom',text='Angle ()')
         self.imgpol = pg.ImageItem()
         self.Polplot.addItem(self.imgpol)
         self.histpol = pg.HistogramLUTItem()
         self.histpol.setImageItem(self.imgpol)
         self.graph.addItem(self.histpol,row=0,col=5)
         self.histpol.setMaximumWidth(100)
        

         self.roipol = pg.ROI([10, 10], [5, 5]) # first vector =[x0,y0], second vector =[lx,ly]
         self.roipol.addScaleHandle([0.5, 1], [0.5, 0.5])
         self.roipol.addScaleHandle([0, 0.5], [0.5, 0.5])
         self.Polplot.addItem(self.roipol)
         self.roipol.setZValue(10)  # make sure ROI is drawn above image
         self.roipol.sigRegionChanged.connect(self.updatePlot)
         
         self.graph.nextCol()
         self.RadialDistplot = self.graph.addPlot(row=1,col=3,colspan=3)
         self.RadialDistplot.setLabel(axis='left',text='Signal (arb. u)')
         self.RadialDistplot.setLabel(axis='bottom',text='Momentum (pixel)')
        #self.p2.setMaximumHeight(250)
        
#Initialize the image
        
         self.initimg = np.random.normal(size=(400, 400))
         self.initimg[380:420, 380:420] += 2.
         self.initimg = pg.gaussianFilter(self.initimg, (3, 3))
         self.initimg += np.random.normal(size=(400, 400)) * 0.1
         self.scan=VMITraceProcessing(self.initimg)
         self.activeimg=self.scan.imgcart_raw
        
         self.img.setImage(self.activeimg)
         self.img.scale(1,1)
         self.img.translate(0, 0)
         self.hist.setLevels(self.activeimg.min(), self.activeimg.max())
         self.Cartplot.autoRange()
        
         print 'GUI loaded4'
         f.write('GUI loaded')
         #self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0],self.roi.size())
         #self.imgpol.setImage(self.scan.imgpol).setLabel(axis='left',text='Py (pixel)')
         self.Cartplot.setLabel(axis='bottom',text='Py (pixel)')

         self.img.setImage(self.activeimg)
         self.img.scale(1,1)
         self.img.translate(0, 0)
         self.hist.setLevels(self.activeimg.min(), self.activeimg.max())
         self.Polplot.autoRange()

         self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0],self.roi.size())
         self.imgpol.setImage(self.scan.imgpol)
         
         self.ViewWin.show()
         ## Init the frame grabber
         #self.myVAQD=VMIcrtl_ext.VMIcrtl()
         f.write('init framegrabber done')
         print 'init framegrabber done'
 
#%%        

    def __del__(self):
        print 'detroy'
        #self.VAQD.__del__()
        
        
#%%
    def updatePlot(self):

        if self.checkbox1.checkState()==2:
            self.activeimg=self.scan.imgcart_raw
            
        #if self.roi.size()!=
        self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0],self.roi.size())
        Radialdist = self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(0)
        self.refx0,self.refy0=self.roipol.pos()
        self.infos.setText('Center Position : X0= %d / Y0= %d ; ROI radius = %d px' % (self.roi.pos()[0]+self.roi.size()[0]/2.0,self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.size()[0]/2.0))
                
        self.imgpol.setImage(self.scan.imgpol)
        
        
        if self.checkbox5.checkState()==2:
            self.RadialDistplot.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(Radialdist))+self.refy0)**2.0,Radialdist,clear=True)
            self.RadialDistplot.setLabel(axis='bottom',text='Energy (eV)')
        else:
            self.RadialDistplot.plot(np.arange(0,len(Radialdist))+self.refy0,Radialdist,clear=True)
            self.RadialDistplot.setLabel(axis='bottom',text='Momentum (px)')
        #self.p0.plot(self.scan.imgpol)
#        if self.checkbox2.checkState()==2:
#            self.normDscan=dscan.sum(axis=0)/max(dscan.sum(axis=0))
#            self.p0.plot(np.arange(0,len(dscan.sum(axis=0)))+y0,self.normDscan, clear=True)
#            self.p0.setLabel(axis='left',text='Normalized signal')
#        else:
#            self.p0.plot(np.arange(0,len(dscan.sum(axis=0)))+y0,dscan.sum(axis=0), clear=True)
#            self.p0.setLabel(axis='left',text='Signal (arb. u)')
#            
#        tof = self.activeimg
#        if self.checkbox3.checkState()==2:
#            self.normTOF=tof.sum(axis=1)/max(tof.sum(axis=1))
#            self.p2.plot(self.normTOF, clear=True)
#            self.p2.setLabel(axis='left',text='Normalized signal')
#        else:
#            self.p2.plot(tof.sum(axis=1), clear=True)
#            self.p2.setLabel(axis='left',text='Signal (arb. u)')
#            
        if self.checkbox0.checkState()==2:
            if np.size(self.refRadialDist)!=0:
                if self.checkbox5.checkState()==2:
                    self.RadialDistplot.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(Radialdist))+self.refy0)**2.0,self.refRadialDist,clear=False,pen='r')
                else:
                    self.RadialDistplot.plot(np.arange(0,len(self.refRadialDist))+self.refy0,self.refRadialDist,clear=False,pen='r')

#            if np.size(self.refTOF)!=0:
#                self.p2.plot(self.refTOF, clear=False,pen='r')        
        
#%%
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
        #self.myVAQD.setDigitizerParameters(ParametersArray)
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
                        'NLDelay':self.Delayfile,\
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
        #self.myVAQD.StartRecording(directoryname)
        print 'START1'
        f.write('START1\n')
        
    def StopAcquisition(self):
        
        #if self.StreamMode.CheckState()==2:
            #self.myTAQD.StopStream()
        #else:
        #self.myVAQD.StopRecording()
        f.write('STOP\n')
        print 'STOP'
        

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