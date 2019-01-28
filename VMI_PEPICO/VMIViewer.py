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

import mmap
import ctypes



pg.mkQApp()
## Define main window class from template
#path = os.path.dirname(os.path.abspath(__file__))
#uiFile = os.path.join(path, 'designerExample.ui')
#WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)

sys.path.append('../../Toolbox/VMIAccumulation')

from VMITraceProcessing import VMITraceProcessing

## Make the layout

class MainWindow():

    def __init__(self):
        #TemplateBaseClass.__init__(self)

        self.win =pg.LayoutWidget()  # Main layout
        self.win.setWindowTitle('VMI Viewer')

#Loadfile button
        self.loadbutton=QtGui.QPushButton('Load Data')
        self.loadbutton.clicked.connect(self.OpenFile)
#Take reference button
        self.refbutton=QtGui.QPushButton('Save Reference')
        self.refbutton.clicked.connect(self.SaveReference)
#Checkboxes

        self.checkbox0=QtGui.QCheckBox('Reference') #View the data feeded by the digitizer
        self.checkbox0.clicked.connect(self.updatePlot)

        self.checkbox1=QtGui.QCheckBox('Stream mode') #View the data feeded by the digitizer
        self.checkbox1.clicked.connect(self.StreamOnOff)

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
        self.BGbutton=QtGui.QPushButton('Load BG')
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
        
        self.spinbox5=QtGui.QDoubleSpinBox()
        self.spinbox5.valueChanged.connect(self.updateROI)
        self.spinbox5.setMaximum(1000.0)
        self.spinbox5.setMinimum(1.0)
        self.spinbox4.setMaximum(10000.0)
        self.spinbox4.setMinimum(0.0)
        
        self.infos=QtGui.QLabel('Center Position : X0= 0.0 / Y0= 0.0 ; ROI radius = 100.0 px')
        self.graph = pg.GraphicsLayoutWidget()

# GUI layout
        self.win.addWidget(self.loadbutton,row=0,col=0,colspan=2)
        self.win.addWidget(self.refbutton,row=1,col=0,colspan=2)
        self.win.addWidget(self.checkbox0,row=2,col=0,colspan=2)
        self.win.addWidget(self.checkbox1,row=3,col=0,colspan=2)
        self.win.addWidget(self.checkbox2,row=4,col=0,colspan=2)
        self.win.addWidget(self.checkbox3,row=5,col=0,colspan=2)

        self.win.addWidget(self.BGbutton,row=6,col=0)
        self.win.addWidget(self.checkbox4,row=7,col=0)
        self.win.addWidget(self.bglabel,row=8,col=0)
        self.win.addWidget(self.spinbox3,row=9,col=0)
        
        self.win.addWidget(self.cxlabel,row=10,col=0)
        self.win.addWidget(self.spinbox1,row=11,col=0)
        self.win.addWidget(self.cylabel,row=12,col=0)
        self.win.addWidget(self.spinbox2,row=13,col=0)
        
        self.win.addWidget(self.checkbox5,row=14,col=0)
        self.win.addWidget(self.EnCaliblabel,row=15,col=0)
        self.win.addWidget(self.spinbox4,row=16,col=0)
        
        self.win.addWidget(self.spinbox5,row=19,col=0)
        
        
        self.win.addWidget(self.infos,row=18,col=2)

        self.win.addWidget(self.graph,row=0,col=2,rowspan=17,colspan=5)
        self.win.resize(1250, 500)
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
        self.p2 = self.graph.addPlot(row=1,col=3,colspan=3)
        self.p2.setLabel(axis='left',text='Signal (arb. u)')
        self.p2.setLabel(axis='bottom',text='Momentum (pixel)')
        #self.p2.setMaximumHeight(250)
        

        self.roipol = pg.ROI([10, 10], [5, 5]) # first vector =[x0,y0], second vector =[lx,ly]
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
        self.scan.DefineCenter([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0])
        self.scan.ImgCart2Pol(self.roi.size())
        self.imgpol.setImage(self.scan.imgpol)
        
# Infos from filedata
        self.pname=''
        self.pnameBG=''
        self.fname=''
        
# Initialise useful variables
        self.BGimg=[]
        self.normDscan=[]
        self.normTOF=[]
        self.refRadialDist=[]
        self.refx0=[]
        self.refy0=[]
        self.cx=[]
        self.cy=[]
        
#Timer object for realtime data

        self.timer=QtCore.QTimer()        
        self.timer.timeout.connect(self.updatePlot)
#Update the gui
        self.win.show()

    def updatePlot(self):

        if self.checkbox1.checkState()==2:
            self.activeimg=self.scan.imgcart_raw
            
        #if self.roi.size()!=
        #self.scan.ImgCart2Pol([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0],self.roi.size())
        self.scan.DefineCenter([self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.pos()[0]+self.roi.size()[0]/2.0])
        self.scan.ImgCart2Pol(self.roi.size())
        Radialdist = self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(0)
        self.refx0,self.refy0=self.roipol.pos()
        self.infos.setText('Center Position : X0= %d / Y0= %d ; ROI radius = %d px' % (self.roi.pos()[0]+self.roi.size()[0]/2.0,self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.size()[0]/2.0))
                
        self.imgpol.setImage(self.scan.imgpol)
        
        
        if self.checkbox5.checkState()==2:
            self.p2.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(Radialdist))+self.refy0)**2.0,Radialdist,clear=True)
            self.p2.setLabel(axis='bottom',text='Energy (eV)')
        else:
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

        
    def LoadBG(self):
        
        PathName = QtGui.QFileDialog.getOpenFileName(directory='D:/')
        #pathname
        self.pnameBG=PathName[0]
        self.BGimg=np.reshape(np.loadtxt(self.pnameBG),(1000,1000)).astype(np.float32)
        
        if self.checkbox4.checkState()==2:
            self.scan.setImage(self.scan.imgcart_raw-self.BGimg*self.spinbox3.value())
            self.activeimg=self.scan.imgcart
            
        self.img.setImage(self.activeimg)
        
        self.updatePlot
        
    def updateBG(self):
        
        if self.checkbox4.checkState()==2:
            self.scan.setImage(self.scan.imgcart_raw-self.BGimg*self.spinbox3.value())
            self.activeimg=self.scan.imgcart
        elif self.checkbox4.checkState()==0:
            self.activeimg=self.scan.imgcart_raw
            
        self.img.setImage(self.activeimg)
        
        self.updatePlot
        
    def updateROI(self):
        
        self.cx=self.spinbox1.value()
        self.cy=self.spinbox2.value()
        
        
        
        self.roi.setSize([self.spinbox5.value(),self.spinbox5.value()])
        d=self.roi.size()[0]
        self.roi.setPos([self.cx-d/2.0,self.cy-d/2.0])
        self.infos.setText('Center Position : X0= %d / Y0= %d ; ROI radius = %d px' % (self.roi.pos()[0]+self.roi.size()[0]/2.0,self.roi.pos()[1]+self.roi.size()[0]/2.0,self.roi.size()[0]/2.0))
                
        #self.updatePlot
                
    def updateIsocurve(self):
    
        self.iso.setLevel(self.isoLine.value())

    def OpenFile(self):

        PathName = QtGui.QFileDialog.getOpenFileName(directory='D:/')
        print PathName[0]
        self.pname=PathName[0]
        print self.pname[0]
        loadimage=np.reshape(np.loadtxt(self.pname),(1000,1000))
        self.scan.setImageRaw(loadimage)
        self.activeimg=self.scan.imgcart_raw
        self.img.setImage(self.activeimg)
        self.hist.setLevels(self.activeimg.min(),self.activeimg.max())
        
        self.updatePlot
        self.updateIsocurve
        
        print(self.pname)
        
    def SaveReference(self):

        self.refRadialDist=self.roipol.getArrayRegion(self.scan.imgpol,self.imgpol).sum(axis=0)
        self.refx0,self.refy0=self.roipol.pos()
        
#        self.refTOF=self.activeimg.sum(axis=1)
        self.updatePlot
#        if self.checkbox2.checkState()==2:
#            self.refDscan=self.normDscan
#        if self.checkbox3.checkState()==2:
#            self.refTOF=self.normTOF
            
        
        if self.checkbox5.checkState()==2:
            self.p2.plot(1e-6*self.spinbox4.value()*(np.arange(0,len(Radialdist))+self.refy0)**2.0,self.refRadialDist,clear=False,pen='r')
        else:
            self.p2.plot(np.arange(0,len(self.refRadialDist))+self.refy0,self.refRadialDist,clear=False,pen='r')


    def StreamOnOff(self):

        if self.checkbox1.checkState()==2:
            print 'Stream on'
            try:
                print 'bp0'
#                sharedmem=mmap.mmap(0, ctypes.sizeof(ctypes.c_int8*1000*1000),'SharedDisplayMemory')
#                print 'bp1'
#                data=ctypes.c_int8.from_buffer(sharedmem)
#                #data=np.frombuffer(sharedmem)
#                
#                print 'bp2'
#                print data
#                tmp=data[:-4000]
#                self.activeimg=tmp.reshape((1000,1000))
#                print self.activeimg.shape
#                print 'bp3'
#                self.updatePlot
#                print 'bp4'
#                self.updateIsocurve
#                print 'bp5'
#                self.timer.timeout.connect(self.UpdateStream(sharedmem))
#                print 'bp6'
#                self.timer.start(1.0)
#                print 'bp7'
#                
            except:
                print "Error accessing shared memory"
            
        elif self.checkbox1.checkState()==0:
            print 'Stream off'
            self.timer.stop()
            
    def UpdateStream(self,sharedmemory):
        print 'bpp1'
#        data=np.frombuffer(sharedmemory)
#        print 'bpp2'
#        self.activeimg=np.reshape(data[:-4000],(1000,1000))
#        print 'bpp3'
#        self.updatePlot
#        print 'bpp4'
#        self.updateIsocurve
#        print 'bpp5'
#            

    def NormalizeDscan(self):

        if self.checkbox2.checkState()==2:
            self.updatePlot

    def NormalizeTOF(self):

        if self.checkbox3.checkState()==2:
            self.updatePlot


Viewer=MainWindow()
## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
