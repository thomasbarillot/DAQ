# -*- coding: utf-8 -*-
"""
Created on Tue Mar 22 13:45:54 2016

@author: tbarillot
"""

"""
This example demonstrates the use of RemoteGraphicsView to improve performance in
applications with heavy load. It works by starting a second process to handle 
all graphics rendering, thus freeing up the main process to do its work.

In this example, the update() function is very expensive and is called frequently.
After update() generates a new set of data, it can either plot directly to a local
plot (bottom) or remotely via a RemoteGraphicsView (top), allowing speed comparison
between the two cases. IF you have a multi-core CPU, it should be obvious that the 
remote case is much faster.
"""
# -*- coding: utf-8 -*-
"""
Demonstrates common image analysis tools.

Many of the features demonstrated here are already provided by the ImageView
widget, but here we present a lower-level approach that provides finer control
over the user interface.
"""

import scipy.io as sio

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import os
import sys
import glob


import mmap
import ctypes
import time
from datetime import datetime

import thread
import threading




from pypylon import pylon
from pypylon import genicam


#sys.path.append('VMIcrtl_lib/x64/Debug')
#import VMIcrtl_ext

pg.mkQApp()
## Define main window class from template
#path = os.path.dirname(os.path.abspath(__file__))
#uiFile = os.path.join(path, 'designerExample.ui')
#WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)

sys.path.append('../../Toolbox/VMIAccumulation/')
#from PI_E750_CP_piezostageFunction import PI_E750_CP_piezostageFunction as dstage
from VMITraceProcessing import VMITraceProcessing

dt=datetime



## Def acq thread



class GrabImageWorker(pg.QtCore.QThread):
    newData = pg.QtCore.Signal(object)
    def __init__(self,VMIcrtl,mode,params):
        QtCore.QThread.__init__(self)
        
        self.mode=mode
        self.VMIcrtl=VMIcrtl
        self.Threshold=np.int(params[0])
        self.NbAcq=np.int(params[1])
        self.FlatCorrimg=params[2]
        
        if self.mode=='rec':
            self.Savepath=params[3]
            self.fname=params[4]
     
        
        self.stopMutex = threading.Lock()
        self._stop = False
        
    def run(self):
        
        if self.mode=='prev':
            while True:
                with self.stopMutex:
                    if self._stop:
                        break
                
                imgsum=np.zeros(self.FlatCorrimg.shape)
                self.VMIcrtl.StartGrabbingMax(self.NbAcq)
                NbAcquired=0
                try:
                    for i in range(0,self.NbAcq):
                        grabResult = self.VMIcrtl.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
                        if grabResult.GrabSucceeded():
                            
                            img = np.array(grabResult.Array)-self.FlatCorrimg
                            img[img<self.Threshold]=0
                            imgsum+=img  
                            NbAcquired+=1
                        else:
                            print("Error: ", grabResult.ErrorCode, grabResult.ErrorDescription)
                            
                        if i%10==0:
                            self.newData.emit((imgsum,NbAcquired))
                            
                except:
                    print 'error'
                #self.semaphore.acquire()
                self.newData.emit((imgsum,NbAcquired))
                #time.sleep(0.1)
                
        elif self.mode=='rec':
            
            with self.stopMutex:
<<<<<<< HEAD
                if self._stop:
                    return 0
=======
                 if self._stop:
                     return 0
>>>>>>> 3a5b67d0dd411bcb1a2ce82a73c89334cd03bbea
            
            imgsum=np.zeros(self.FlatCorrimg.shape)
            self.VMIcrtl.StartGrabbingMax(self.NbAcq)
            NbAcquired=0
            try:
                for i in range(0,self.NbAcq):
                    grabResult = self.VMIcrtl.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
                    if grabResult.GrabSucceeded():
                        
                        img = np.array(grabResult.Array)-self.FlatCorrimg
                        img[img<self.Threshold]=0
                        imgsum+=img
                        NbAcquired+=1
                    else:
                        print("Error: ", grabResult.ErrorCode, grabResult.ErrorDescription)
                        
                    if i%10==0:
                        self.newData.emit((imgsum,NbAcquired))
            except:
                print 'error'

            self.newData.emit((imgsum,NbAcquired))
            np.savetxt(os.path.join(self.Savepath,self.fname),np.concatenate(imgsum))

                
        elif self.mode=='flatcorr':
            
            imgsum=np.zeros(self.FlatCorrimg.shape)
            self.VMIcrtl.StartGrabbingMax(100)
            NbAcquired=0
            
            for i in range(0,100):
                grabResult = self.VMIcrtl.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
                if grabResult.GrabSucceeded():
                    img = np.array(grabResult.Array)
                    imgsum+=img  
                    
            self.newData.emit(imgsum/100.0)

    def stop(self):
        with self.stopMutex:
            self._stop = True



## Make the layout

class MainWindow():

    def __init__(self):
        #TemplateBaseClass.__init__(self)
        
        # Initialize Camera
        tlFactory = pylon.TlFactory.GetInstance()
        devices=tlFactory.EnumerateDevices
        print devices()[1].GetModelName()
        self.VMIcrtl = pylon.InstantCamera(tlFactory.CreateDevice(devices()[1]))
        #self.VMIcrtl.open()
        
        
        ## initialize camera acquisition settings
        self.NbAcq=10
        self.NbAcquired=0
        self.Threshold=0
        
        
        #self.VMIcrtl=VMIcrtl_ext.VMIcrtl();
        #Init semaphore
        self.mutex = QtCore.QMutex()


        #Initialize window

        self.win =pg.LayoutWidget()  # Main layout
        self.win.setWindowTitle('VMI GUI')

#Loadfile button
        self.loadbutton=QtGui.QPushButton('Load Data')
        self.loadbutton.clicked.connect(self.OpenFile)
#Take reference button
        self.refbutton=QtGui.QPushButton('Save Reference')
        self.refbutton.clicked.connect(self.SaveReference)
        
        self.Prevbutton=QtGui.QPushButton('Preview')
        self.Prevbutton.clicked.connect(self.PrevAcq)
        self.FlatBGbutton=QtGui.QPushButton('Flat Corr')
        self.FlatBGbutton.clicked.connect(self.LoadFlatCorrection)
        self.Startbutton=QtGui.QPushButton('Start')
        self.Startbutton.clicked.connect(self.StartAcq)
        self.Stopbutton=QtGui.QPushButton('Stop')
        self.Stopbutton.clicked.connect(self.StopAcq)
#Checkboxes

        self.checkbox0=QtGui.QCheckBox('Reference') #View the data feeded by the digitizer
        self.checkbox0.clicked.connect(self.updatePlot)

        self.checkbox1=QtGui.QCheckBox('Refresh Viewer') #View the data feeded by the digitizer
        self.checkbox1.clicked.connect(self.StreamOnOff)
        self.checkbox1.setEnabled(False)
        
        self.checkbox2=QtGui.QCheckBox('Norm Radial Distribution')
        self.checkbox2.clicked.connect(self.NormalizeDscan)
        self.checkbox3=QtGui.QCheckBox('Norm TOF')
        self.checkbox3.clicked.connect(self.NormalizeTOF)

# Center control buttons
        self.cxlabel=QtGui.QLabel('Center X pos')
        self.spinbox1=QtGui.QDoubleSpinBox()
        self.spinbox1.valueChanged.connect(self.updateROI)
        self.spinbox1.setMaximum(1000.0)
        self.spinbox1.setMinimum(0.0)
        self.spinbox1.setValue(204.0)
        self.cylabel=QtGui.QLabel('Center Y pos')
        self.spinbox2=QtGui.QDoubleSpinBox()
        self.spinbox2.valueChanged.connect(self.updateROI)
        self.spinbox2.setMaximum(1000.0)
        self.spinbox2.setMinimum(0.0)
        self.spinbox2.setValue(197.0)

#background removal buttons
        self.BGbutton=QtGui.QPushButton('Load XUV BG')
        self.BGbutton.clicked.connect(self.LoadBG)
        self.bglabel=QtGui.QLabel('BG removal amount')
        self.spinbox3=QtGui.QDoubleSpinBox()
        self.spinbox3.valueChanged.connect(self.updateBG)
        self.spinbox3.setMaximum(10.0)
        self.spinbox3.setMinimum(0.0)
        self.spinbox3.setValue(1.0)
        self.checkbox4=QtGui.QCheckBox('BG removed ON/OFF')
        self.checkbox4.clicked.connect(self.updateBG)

        self.checkbox5=QtGui.QCheckBox('pixels to energy')
        self.checkbox5.clicked.connect(self.updatePlot)
        self.EnCaliblabel=QtGui.QLabel('Energy Calibration coeff (x1e-6)')
        self.spinbox4=QtGui.QDoubleSpinBox()
        self.spinbox4.valueChanged.connect(self.updatePlot)
        self.spinbox4.setMaximum(10000.0)
        self.spinbox4.setMinimum(0.0)
        self.spinbox4.setValue(894.30)
        
        self.NAcqLabel=QtGui.QLabel('Number of acquisitions')
        self.spinbox5=QtGui.QSpinBox()
        self.spinbox5.valueChanged.connect(self.UpdateParameters)
        self.spinbox5.setMaximum(100000)
        self.spinbox5.setMinimum(0)
        self.spinbox5.setValue(50)
        
        self.checkbox6=QtGui.QCheckBox('Dscan')
        
        self.Dstart=QtGui.QLabel('Dstart')
        self.spinbox6=QtGui.QDoubleSpinBox()
        #self.spinbox6.valueChanged.connect(self.updatePlot)
        self.spinbox6.setMaximum(80.0)
        self.spinbox6.setMinimum(0.0)
        self.spinbox6.setValue(0.0)
        
        self.Dstop=QtGui.QLabel('Dstop')
        self.spinbox7=QtGui.QDoubleSpinBox()
        self.spinbox7.setMaximum(80.0)
        self.spinbox7.setMinimum(0.0)
        self.spinbox7.setValue(80.0)
        
        self.Dstep=QtGui.QLabel('Dstep')
        self.spinbox8=QtGui.QDoubleSpinBox()
        self.spinbox8.setMaximum(80.0)
        self.spinbox8.setMinimum(0.0)
        self.spinbox8.setValue(1.0)
        
        self.ThLabel=QtGui.QLabel('Threshold')
        self.spinbox9=QtGui.QSpinBox()
        self.spinbox9.valueChanged.connect(self.UpdateParameters)
        self.spinbox9.setMaximum(5000)
        self.spinbox9.setMinimum(1)
        self.spinbox9.setValue(1)
        
        self.checkbox7=QtGui.QCheckBox('Median Filter')
        self.checkbox7.clicked.connect(self.UpdateParameters)
        self.checkbox8=QtGui.QCheckBox('Single Shot rec')
        self.checkbox8.clicked.connect(self.UpdateParameters)
        
        ## Trigger mode
        
        self.checkbox10=QtGui.QCheckBox('Trigger ON/OFF')
        self.checkbox10.clicked.connect(self.setTriggerMode)
        
        self.ExpoLabel=QtGui.QLabel('    Exposure (us)')
        self.spinbox10=QtGui.QSpinBox()
        self.spinbox10.valueChanged.connect(self.UpdateParameters)
        self.spinbox10.setMaximum(990)
        self.spinbox10.setMinimum(100)
        self.spinbox10.setValue(500.0)


        
        ## save path
        
        self.Savepath='20161130_0000.dat'
        self.SaveLabel=QtGui.QLabel('Save path:')
        self.Savepathbutton=QtGui.QPushButton('...')
        self.Savepathedit=QtGui.QLineEdit(self.Savepath)
        self.Savepathedit.textChanged.connect(self.UpdateParameters)
        self.Savepathbutton.clicked.connect(self.setDir)
        
        ## Progress bars
        self.DprogressLabel=QtGui.QLabel('Dscan progress')
        self.Dprogressbar=QtGui.QProgressBar()
        self.Dprogressbar.setRange(0,100)
        self.progressLabel=QtGui.QLabel('Acq progress')
        self.progressbar=QtGui.QProgressBar()
        self.progressbar.setRange(0,100)
        
        
        
       
        self.infos=QtGui.QLabel('Center Position : X0= 0.0 / Y0= 0.0 ; ROI radius = 100.0 px')
        self.graph = pg.GraphicsLayoutWidget()

# GUI layout
        self.win.addWidget(self.loadbutton,row=0,col=0,colspan=1)
        self.win.addWidget(self.refbutton,row=1,col=0,colspan=1)
        self.win.addWidget(self.checkbox0,row=2,col=0,colspan=1)
        self.win.addWidget(self.checkbox1,row=3,col=0,colspan=1)
        self.win.addWidget(self.checkbox2,row=4,col=0,colspan=1)
        self.win.addWidget(self.checkbox3,row=5,col=0,colspan=1)

        self.win.addWidget(self.BGbutton,row=6,col=0)
        self.win.addWidget(self.checkbox4,row=7,col=0)
        self.win.addWidget(self.bglabel,row=8,col=0)
        self.win.addWidget(self.spinbox3,row=9,col=0)
        
        #self.win.addWidget(self.triggerlabel,row=11,col=2,colspan=1)
        self.win.addWidget(self.checkbox10,row=11,col=2,colspan=1)
        self.win.addWidget(self.ExpoLabel,row=12,col=2,colspan=1)
        self.win.addWidget(self.spinbox10,row=13,col=2,colspan=1)
        
        self.win.addWidget(self.cxlabel,row=10,col=0)
        self.win.addWidget(self.spinbox1,row=11,col=0)
        self.win.addWidget(self.cylabel,row=12,col=0)
        self.win.addWidget(self.spinbox2,row=13,col=0)
        
        self.win.addWidget(self.checkbox5,row=14,col=0)
        self.win.addWidget(self.EnCaliblabel,row=15,col=0)
        self.win.addWidget(self.spinbox4,row=16,col=0)
        
        self.win.addWidget(self.Prevbutton,row=0,col=1,colspan=1)
        self.win.addWidget(self.FlatBGbutton,row=0,col=2,colspan=1)
        self.win.addWidget(self.Startbutton,row=1,col=1,colspan=1)
        self.win.addWidget(self.Stopbutton,row=1,col=2,colspan=1)
        
        self.win.addWidget(self.NAcqLabel,row=2,col=1)
        self.win.addWidget(self.spinbox5,row=3,col=1,colspan=1)
        self.win.addWidget(self.checkbox7,row=4,col=1,colspan=1)
        self.win.addWidget(self.checkbox8,row=5,col=1,colspan=1)
        
        self.win.addWidget(self.ThLabel,row=2,col=2)
        self.win.addWidget(self.spinbox9,row=3,col=2,colspan=1)
        
        self.win.addWidget(self.checkbox6,row=4,col=2,colspan=1)
        self.win.addWidget(self.Dstart,row=5,col=2,colspan=1)
        self.win.addWidget(self.spinbox6,row=6,col=2,colspan=1)
        self.win.addWidget(self.Dstop,row=7,col=2,colspan=1)
        self.win.addWidget(self.spinbox7,row=8,col=2,colspan=1)
        self.win.addWidget(self.Dstep,row=9,col=2,colspan=1)
        self.win.addWidget(self.spinbox8,row=10,col=2,colspan=1)
        
        self.win.addWidget(self.SaveLabel,row=14,col=1,colspan=1)
        self.win.addWidget(self.Savepathbutton,row=14,col=2,colspan=1)
        self.win.addWidget(self.Savepathedit,row=15,col=1,colspan=2)
        
        
        self.win.addWidget(self.progressLabel,row=17,col=0,colspan=1)
        self.win.addWidget(self.progressbar,row=17,col=1,colspan=2)
        self.win.addWidget(self.DprogressLabel,row=18,col=0,colspan=1)
        self.win.addWidget(self.Dprogressbar,row=18,col=1,colspan=2)
        
        
        
        
        self.win.addWidget(self.infos,row=18,col=3)

        self.win.addWidget(self.graph,row=0,col=3,rowspan=18,colspan=6)
        self.win.resize(1500, 1000)
        #self.win.show()

# Graph layout for cartesian image

        self.p1 =self.graph.addPlot(row=0,col=0,rowspan=2)
        self.p1.setLabel(axis='left',text='Py (pixel)')
        self.p1.setLabel(axis='bottom',text='Py (pixel)')

# Item for displaying image data
        self.img = pg.ImageItem()
        self.p1.addItem(self.img)
        self.p1.setAspectLocked(True,ratio=1)

# Custom ROI for selecting an image region
        self.roi = pg.CircleROI([100, 100], [50, 50]) # first vector =[x0,y0], second vector =[lx,ly]
#        self.roi.addScaleHandle([0.5, 1], [0.5, 0.5])
#        self.roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        self.p1.addItem(self.roi)
        self.roi.setZValue(10)  # make sure ROI is drawn above image
        self.roi.sigRegionChanged.connect(self.updatePlot)
        
        

# Isocurve drawing
        self.iso = pg.IsocurveItem(level=0.8, pen='g')
        self.iso.setParentItem(self.img)
        self.iso.setZValue(5)

# Contrast/color control
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img)
        self.graph.addItem(self.hist,row=0,col=1,rowspan=2)

# Draggable line for setting isocurve level
        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.hist.vb.addItem(self.isoLine)
        self.hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        self.isoLine.setValue(0.8)
        self.isoLine.setZValue(1000) # bring iso line above contrast controls
        self.isoLine.sigDragged.connect(self.updateIsocurve)

# Another plot area for displaying ROI data
        self.graph.nextRow()
        self.p0 = self.graph.addPlot(row=0,col=3,colspan=2)
        self.p0.setLabel(axis='left',text='Radius (px)')
        self.p0.setLabel(axis='bottom',text='Angle (°)')
        self.imgpol = pg.ImageItem()
        self.p0.addItem(self.imgpol)
        self.histpol = pg.HistogramLUTItem()
        self.histpol.setImageItem(self.imgpol)
        self.graph.addItem(self.histpol,row=0,col=5)
        self.histpol.setMaximumWidth(100)
        

        self.graph.nextCol()
        self.p2 = self.graph.addPlot(row=1,col=3,colspan=2)
        self.p2.setLabel(axis='left',text='Signal (arb. u)')
        self.p2.setLabel(axis='bottom',text='Momentum (pixel)')
        
        self.graph.nextRow()
        self.p3 = self.graph.addPlot(row=3,col=0,colspan=5)
        self.p3.setLabel(axis='bottom',text='Delay (fs)')
        self.p3.setLabel(axis='left',text='Momentum (px)')
        self.Dscan = pg.ImageItem()
        self.p3.addItem(self.Dscan)
        self.histpol2 = pg.HistogramLUTItem()
        self.histpol2.setImageItem(self.Dscan)
        self.graph.addItem(self.histpol2,row=3,col=5)
        self.histpol2.setMaximumWidth(100)

        self.roipol = pg.ROI([50, 1], [30, 150]) # first vector =[x0,y0], second vector =[lx,ly]
        self.roipol.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roipol.addScaleHandle([0, 0.5], [0.5, 0.5])
        self.p0.addItem(self.roipol)
        self.roipol.setZValue(10)  # make sure ROI is drawn above image
        self.roipol.sigRegionChanged.connect(self.updatePlot)
        
#Initialize the image
        
        self.initimg = np.random.normal(size=(1000, 1000))
        self.initimg[380:420, 380:420] += 2.
        self.initimg = pg.gaussianFilter(self.initimg, (3, 3))
        self.initimg += np.random.normal(size=(1000, 1000)) * 0.1
        self.scan=VMITraceProcessing(self.initimg)
        self.activeimg=self.scan.imgcart_raw
        
        self.img.setImage(self.activeimg)
        self.img.scale(1,1)
        self.img.translate(0, 0)
        self.hist.setLevels(self.activeimg.min(), self.activeimg.max())
        self.p1.autoRange()
        
        
        #self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0],self.roi.size())
        #self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0])
        self.scan.DefineCenter([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0])
        self.scan.ImgCart2Pol(self.roi.size())
        
        
        
        print self.roi.size()[0], 'test'
        #self.scan.ImgCart2Pol([self.roi.size()[0]])
        
        self.imgpol.setImage(self.scan.imgpol)
        
        #self.imgDscan=np.zeros((1000,80))
        
# Infos from filedata
        self.pname=''
        self.pnameBG=''
        self.fname=''
        
        
        
        
# Initialise useful variables
        self.FlatCorrimg=np.zeros((1000,1000))
        self.BGimg=np.zeros((1000,1000))
        self.normDscan=[]
        self.normTOF=[]
        self.refRadialDist=[]
        self.refx0=[]
        self.refy0=[]
        self.cx=[]
        self.cy=[]
        
        
#Load previous config if available:
        
        isconfig=glob.glob('config.npz')
#        if isconfig!=[]:
#            
#            conf=np.load('config.npz')
#            self.Threshold=conf['Threshold']
#            self.NbAcq=conf['NbAcq']
#            self.FlatCorrimg=conf['Flatcorr']
#            self.SavePath=conf['Savepath']
            
#Instanciate acquisition Thread
            
        self.thread=[]
        
#Timer object for realtime data

        self.timer=QtCore.QTimer()        
        self.timer.timeout.connect(self.updatePlot)
#Update the gui
        self.win.show()

      
      

      
    def PrevAcq(self):
        
        #elf.VMIcrtl.StartAcquisitionPrev()
        
        self.Startbutton.setEnabled(False)
        #self.semaphore.acquire(1)
        self.PrevFlag=True
        #self.semaphore.release(1)
        self.thread = GrabImageWorker(self.VMIcrtl,'prev',(self.Threshold,self.NbAcq,self.FlatCorrimg))
        self.thread.newData.connect(self.UpdateStream)
        self.thread.start()
        
    
    def StartAcq(self):
        
        
        
        if self.checkbox6.checkState()==0:
            
            self.fname='%i%s%s_%s%s.dat' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2))
            
            self.Prevbutton.setEnabled(False)
            self.RecFlag=True
            
            self.thread = GrabImageWorker(self.VMIcrtl,'rec',(self.Threshold,self.NbAcq,self.FlatCorrimg,self.Savepath,self.fname))
            self.thread.newData.connect(self.UpdateStream)
            self.thread.start()
        
            
        elif self.checkbox6.checkState()==2:
            
            print 'Work in progress'
            #delayvals=np.arange(self.spinbox6.value(),self.spinbox7.value(),self.spinbox8.value())
            #Radialdist = self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(0)
            #self.imgDscan=np.zeros((len(delayvals),len(Radialdist)))

            #thread.start_new_thread(self.DscanThread,())
            
#    def DscanThread(self):
#        delayvals=np.arange(self.spinbox6.value(),self.spinbox7.value(),self.spinbox8.value())
#        fnameroot='%i%s%s_%s%s' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
#                                        str(dt.today().hour).zfill(2), \
#                                        str(dt.today().minute).zfill(2))
#        for i,dval in enumerate(delayvals):
#            self.fname=fnameroot+'_%s.dat' % (str(i).zfill(4))
#            self.VMIcrtl.setFilename(self.fname)
#            
#            dstage('//155.198.197.13/CEP_remotecontrol/',dval)
#            time.sleep(3)
#            self.VMIcrtl.StartAcquisition()
#            self.Prevbutton.setEnabled(False)
#            exitflag=False
#            while exitflag==False:
#                time.sleep(1)
#                exitflag=self.VMIcrtl.getStatusIFG()
#            self.VMIcrtl.StopAcquisition()
#            Radialdist = self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(0)
#            self.imgDscan[i,:]=Radialdist/sum(Radialdist)
#                #DscanDisplay.setImage(self.imgDscan,autoLevels=False,autoHistogramRange=False)
#            self.Dcounts=np.round(100*i/len(delayvals))
#        

        
        
    def StopAcq(self):
        
        #self.VMIcrtl.StopAcquisition()
        
        self.thread.stop()
        self.Prevbutton.setEnabled(True)
        self.Startbutton.setEnabled(True)
        
    def setDir(self):

        PATHNAME = QtGui.QFileDialog.getExistingDirectory()
        self.Savepathedit.setText(PATHNAME)
        self.UpdateParameters()
        
    def UpdateParameters(self):
        
        self.NbAcq=np.int(self.spinbox5.value())
        self.Threshold=np.int(self.spinbox9.value())
        self.Savepath=self.Savepathedit.text()
        
        
        
        config={'NbAcq':self.NbAcq,\
                'Threshold':self.Threshold,\
                'Flatcorr':self.FlatCorrimg,\
                'Savepath':self.Savepath,\
                'Cx':self.roi.pos()[1]+self.roi.size()[0]/2.0,\
                'Cy':self.roi.pos()[0]+self.roi.size()[0]/2.0,\
                'Rpos':1,\
                'Tpos':1}
        
        np.savez('config.npz',config)
        
        #self.VMIcrtl.setFilename(str(self.Savepath))
        #if self.checkbox7.checkState()==2:
        #    self.VMIcrtl.setMedianFilter(1)
        #elif self.checkbox7.checkState()==0:
        #    self.VMIcrtl.setMedianFilter(0)
        #if self.checkbox8.checkState()==2:
        #    self.VMIcrtl.setSingleShot(1)
        #elif self.checkbox8.checkState()==0:
        #    self.VMIcrtl.setSingleShot(0)
        #self.semaphore.release()
            
        
    def updatePlot(self):
        
        #self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0],self.roi.size())
        self.scan.DefineCenter([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0])
        self.scan.ImgCart2Pol(self.roi.size())
        
        
        Radialdist = self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(0)
        self.refx0,self.refy0=self.roipol.pos()
        self.infos.setText('Center Position : X0= %d / Y0= %d ; ROI radius = %d px' % (self.roi.pos()[0]+self.roi.size()[0]/2.0,self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.size()[0]/2.0))
                
        self.imgpol.setImage(self.scan.imgpol,autoLevels=False,autoHistogramRange=False)
        
#        if self.checkbox6.checkState()==2:
#            self.Dscan.setImage(self.imgDscan,autoLevels=False,autoHistogramRange=False,clear=True)
            
            
        
        self.p2.plot(np.arange(0,len(Radialdist))+self.refy0,Radialdist,clear=True)
            
        if self.checkbox5.checkState()==2:
            self.p2.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(Radialdist))+self.refy0)**2.0,Radialdist,clear=True)
            self.p2.setLabel(axis='bottom',text='Energy (eV)')
        elif self.checkbox5.checkState()==0:
            self.p2.plot(np.arange(0,len(Radialdist))+self.refy0,Radialdist,clear=True)
            self.p2.setLabel(axis='bottom',text='Momentum (px)')
        
        
        
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
                    self.p2.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(Radialdist))+self.refy0)**2.0,self.refRadialDist,clear=False,pen='r')
                else:
                    self.p2.plot(np.arange(0,len(self.refRadialDist))+self.refy0,self.refRadialDist,clear=False,pen='r')
        
#            if np.size(self.refTOF)!=0:
#                self.p2.plot(self.refTOF, clear=False,pen='r')
                    
                    
    def RecFlatCorrection(self,img):
        
        self.FlatCorrimg=img
        
    def LoadFlatCorrection(self):
        
        self.thread = GrabImageWorker(self.VMIcrtl,'flatcorr',(self.Threshold,self.NbAcq,self.FlatCorrimg))
        self.thread.newData.connect(self.RecFlatCorrection)
        self.thread.start()   
         
     
      
        
    def LoadBG(self):
        
        PathName = QtGui.QFileDialog.getOpenFileName(directory='/Volumes/qolslc/atto/labdata/2015/20151106_Isopropanol/')
        self.pnameBG=PathName
        self.BGimg=np.reshape(np.loadtxt(self.pnameBG),(1000,1000))
        if self.checkbox4.checkState()==2:
            self.scan.setImage(self.scan.imgcart_raw-self.BGimg*self.spinbox3.value())
            self.activeimg=self.scan.imgcart
            
        self.img.setImage(self.activeimg)
        
        
        self.updatePlot()
        
    def updateBG(self):
        
        if self.checkbox4.checkState()==2:
            self.scan.setImage(self.scan.imgcart_raw-self.BGimg*self.spinbox3.value())
            self.activeimg=self.scan.imgcart
        elif self.checkbox4.checkState()==0:
            self.activeimg=self.scan.imgcart_raw
            
        self.img.setImage(self.activeimg)
        
        self.updatePlot()
        
    def updateROI(self):
        
        self.cx=self.spinbox1.value()
        self.cy=self.spinbox2.value()
        
        d=self.roi.size()[0]
        self.roi.setPos([self.cx-d/2.0,self.cy-d/2.0])
        self.infos.setText('Center Position : X0= %d / Y0= %d ; ROI radius = %d px' % (self.roi.pos()[0]+self.roi.size()[0]/2.0,self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.size()[0]/2.0))
                
        #self.updatePlot
                
    def updateIsocurve(self):
    
        self.iso.setLevel(self.isoLine.value())

    def OpenFile(self):

        PathName = QtGui.QFileDialog.getOpenFileName(directory='/Volumes/qolslc/atto/labdata/2015/20151106_Isopropanol/')
        self.pname=PathName
        loadimage=np.reshape(np.loadtxt(self.pname),(1000,1000))
        self.scan.setImageRaw(loadimage)
        self.activeimg=self.scan.imgcart_raw
        self.img.setImage(self.activeimg)
        self.hist.setLevels(self.activeimg.min(),self.activeimg.max())
        
        self.updatePlot()
        self.updateIsocurve()
        
        print(self.pname)
        
    def setTriggerMode(self):
        
        if self.checkbox10.checkState()==2:
            self.VMIcrtl.setTriggerMode(np.int(1))
        else:
            self.VMIcrtl.setTriggerMode(np.int(0))
        
    def SaveReference(self):

        self.refRadialDist=self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(axis=0)
        self.refx0,self.refy0=self.roipol.pos()

        self.updatePlot()     
        
        if self.checkbox5.checkState()==2:
            self.p2.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(self.refRadialDist))+self.refy0)**2.0,self.refRadialDist,clear=False,pen='r')
        else:
            self.p2.plot(np.arange(0,len(self.refRadialDist))+self.refy0,self.refRadialDist,clear=False,pen='r')


    def StreamOnOff(self):

        if self.checkbox1.checkState()==2:
            print 'Stream on'
            try:
                #data=np.array(self.VMIcrtl.RecallImagePrev(),dtype=np.int)
                #self.scan.setImageRaw(np.reshape(data,[400,400]))
                self.activeimg=self.scan.imgcart_raw
                self.img.setImage(self.activeimg,autoLevels=False,autoHistogramRange=False)
                #self.hist.setLevels(self.activeimg.min(),self.activeimg.max())

                #print self.activeimg
                self.updatePlot()
                self.updateIsocurve()
                self.timer.timeout.connect(self.UpdateStream)
                self.timer.start(0.25)

                
            except:
                print "Error accessing image in buffer"
                
            #try:
            #    NFrames=np.round(100*self.VMIcrtl.GetFrames()/np.float(self.spinbox5.value()))
            #    self.progressbar.setValue(NFrames)
#                if self.checkbox6.checkState()==2:
#                    self.Dprogressbar.setValue(self.Dcounts)
                
            #except:
            #    print 'error reading acquired images'
            
        elif self.checkbox1.checkState()==0:
            print 'Stream off'
            self.timer.stop()
            
    def UpdateStream(self,data):

        NFrames=np.round(100*data[1]/np.float(self.spinbox5.value()))
        if self.spinbox5.value()>10: 
            if NFrames>90:
                #data=np.array(self.GrabImages(),dtype=np.int)
                self.scan.setImageRaw(data[0])
                self.activeimg=self.scan.imgcart_raw
                self.img.setImage(self.activeimg,autoLevels=False,autoHistogramRange=False)
                self.updatePlot()
                self.updateIsocurve()
                
        else:
            #data=np.array(self.VMIcrtl.RecallImagePrev(),dtype=np.int)
            self.scan.setImageRaw(data[0])
            self.activeimg=self.scan.imgcart_raw
            self.img.setImage(self.activeimg,autoLevels=False,autoHistogramRange=False)
            self.updatePlot()
            self.updateIsocurve()
        
        try:
            NFrames=np.round(100*data[1]/np.float(self.spinbox5.value()))
            self.progressbar.setValue(NFrames)
#            if self.checkbox6.checkState()==2:
#                self.Dprogressbar.setValue(self.Dcounts)
        except:
            print 'error reading acquired images'
 
            

    def NormalizeDscan(self):

        if self.checkbox2.checkState()==2:
            self.updatePlot()

    def NormalizeTOF(self):

        if self.checkbox3.checkState()==2:
            self.updatePlot()
            
    def SaveDscan(self):
         print 'Work in progress'       
#        np.savetxt()
        

        


Viewer=MainWindow()
## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
