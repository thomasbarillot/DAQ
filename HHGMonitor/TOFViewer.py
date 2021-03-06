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
#import os

pg.mkQApp()
## Define main window class from template
#path = os.path.dirname(os.path.abspath(__file__))
#uiFile = os.path.join(path, 'designerExample.ui')
#WindowTemplate, TemplateBaseClass = pg.Qt.loadUiType(uiFile)


## Make the layout

class MainWindow():

    def __init__(self):
        #TemplateBaseClass.__init__(self)

        #self.win =QtGui.QGridLayout()
        self.win =pg.LayoutWidget()  # Main layout
        self.win.setWindowTitle('TOF Scan Viewer')

#Loadfile button
        self.loadbutton=QtGui.QPushButton('Load Data')
        self.loadbutton.clicked.connect(self.OpenFile)
#Take reference button
        self.refbutton=QtGui.QPushButton('Save Reference')
        self.refbutton.clicked.connect(self.SaveReference)
#Checkboxes

        self.checkbox0=QtGui.QCheckBox('Reference') #View the data feeded by the digitizer
        self.checkbox0.clicked.connect(self.updatePlot)

        self.checkboxStream1=QtGui.QCheckBox('Stream from scanfile') #View the data feeded by the digitizer
        self.checkboxStream1.clicked.connect(self.StreamOnOff)
        
        self.checkbox2=QtGui.QCheckBox('Norm Dscan')
        self.checkbox2.clicked.connect(self.NormalizeDscan)
        self.checkbox3=QtGui.QCheckBox('Norm TOF')
        self.checkbox3.clicked.connect(self.NormalizeTOF)

        self.realtimegraph = pg.GraphicsLayoutWidget()
        self.scangraph = pg.GraphicsLayoutWidget()


# GUI layout
        #self.win.addWidget(QtGui.QLabel('Real time single shot data '),row=0,col=0)
        #self.win.addWidget(QtGui.QLabel('Real time accumulated data'),row=0,col=2)
        #self.win.addWidget(self.realtimegraph,row=1,col=0,colspan=4)
        #self.win.addWidget(QtGui.QLabel('Time of Flight scan'),row=2,col=0)

        self.win.addWidget(self.loadbutton,row=3,col=0)
        self.win.addWidget(self.refbutton,row=4,col=0)
        self.win.addWidget(self.checkbox0,row=5,col=0)
        self.win.addWidget(self.checkboxStream1,row=6,col=0)
        self.win.addWidget(self.checkbox2,row=7,col=0)
        self.win.addWidget(self.checkbox3,row=8,col=0)

        
        self.win.addWidget(self.scangraph,row=2,col=1,rowspan=25,colspan=3)
        self.realtimegraph.setMaximumHeight(200)
        self.win.resize(1250, 1250)
        self.win.show()

# Graph layout

        self.prealtime1=self.realtimegraph.addPlot(row=0,col=0)
        self.prealtime1.setLabel(axis='left',text='Signal (mV) ')
        self.prealtime1.setLabel(axis='bottom',text='Tof (ns)')
        self.prealtime2=self.realtimegraph.addPlot(row=0,col=2)
        self.prealtime2.setLabel(axis='left',text='Signal (mV) ')
        self.prealtime2.setLabel(axis='bottom',text='Tof (ns)')

        self.p1 =self.scangraph.addPlot(row=0,col=0,colspan=2)
        self.p1.setLabel(axis='left',text='Delay (fs)')
        self.p1.setLabel(axis='bottom',text='Tof (ns)')

# Item for displaying image data
        self.img = pg.ImageItem()
        self.p1.addItem(self.img)

# Custom ROI for selecting an image region
        self.roi = pg.ROI([-8, 14], [1000, 100]) # first vector =[x0,y0], second vector =[lx,ly]
        self.roi.addScaleHandle([0.5, 1], [0.5, 0.5])
        self.roi.addScaleHandle([0, 0.5], [0.5, 0.5])
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
        self.scangraph.addItem(self.hist)

# Draggable line for setting isocurve level
        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.hist.vb.addItem(self.isoLine)
        self.hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        self.isoLine.setValue(0.8)
        self.isoLine.setZValue(1000) # bring iso line above contrast controls
        self.isoLine.sigDragged.connect(self.updateIsocurve)

# Another plot area for displaying ROI data
        self.scangraph.nextRow()
        self.p0 = self.scangraph.addPlot(row=1,col=0)
        self.p0.setLabel(axis='left',text='Signal (arb. u)')
        self.p0.setLabel(axis='bottom',text='Delay (fs)')
        #self.p0.setMaximumWidth(250)
        #self.p0.setMaximumHeight(250)
        #self.p0.rotate(90)
        #self.p0.translate(0,-250)
        self.p0.invertX(True)
        self.isoLine0 = pg.InfiniteLine(angle=90, movable=True, pen='g')
        self.p0.vb.addItem(self.isoLine0)
        self.isoLine0.setValue(2.0)
        self.isoLine0.setZValue(1000)
        

        self.scangraph.nextCol()
        self.p2 = self.scangraph.addPlot(row=1,col=1,colspan=1)
        self.p2.setLabel(axis='left',text='Signal (arb. u)')
        self.p2.setLabel(axis='bottom',text='Tof (ns)')
        #self.p2.setMaximumHeight(250)
        

        
        
#Initialize the image
        self.scan = np.random.normal(size=(100, 200))
        self.scan[20:80, 20:80] += 2.
        self.scan = pg.gaussianFilter(self.scan, (3, 3))
        self.scan += np.random.normal(size=(100, 200)) * 0.1
        self.activeimg=self.scan
        
        self.img.setImage(self.activeimg)
        self.img.scale(1,1)
        self.img.translate(0, 0)
        self.hist.setLevels(self.activeimg.min(), self.activeimg.max())
        self.p1.autoRange()
        
# Infos from filedata
        self.pname=''
        self.fname=''
        
# Initialise useful variables
        self.normDscan=[]
        self.normTOF=[]
        self.refDscan=[]
        self.refTOF=[]
        self.refx0=[]
        self.refy0=[]
        
#Timer object for realtime data

        self.timer=QtCore.QTimer()
        self.timer.timeout.connect(self.updatePlot)

    def updatePlot(self):

        dscan = self.roi.getArrayRegion(self.activeimg,self.img)
        x0,y0=self.roi.pos()
        if self.checkbox2.checkState()==2:
            self.normDscan=dscan.sum(axis=0)/max(dscan.sum(axis=0))
            self.p0.plot(np.arange(0,len(dscan.sum(axis=0)))+y0,self.normDscan, clear=True)
            self.p0.setLabel(axis='left',text='Normalized signal')
        else:
            self.p0.plot(np.arange(0,len(dscan.sum(axis=0)))+y0,dscan.sum(axis=0), clear=True)
            self.p0.setLabel(axis='left',text='Signal (arb. u)')
            
        tof = self.activeimg
        if self.checkbox3.checkState()==2:
            self.normTOF=tof.sum(axis=1)/max(tof.sum(axis=1))
            self.p2.plot(self.normTOF, clear=True)
            self.p2.setLabel(axis='left',text='Normalized signal')
        else:
            self.p2.plot(tof.sum(axis=1), clear=True)
            self.p2.setLabel(axis='left',text='Signal (arb. u)')
            
        if self.checkbox0.checkState()==2:
            if np.size(self.refDscan)!=0:
                self.p0.plot(np.arange(0,len(self.refDscan))+self.refy0,self.refDscan, clear=False,pen='r')
            
            if np.size(self.refTOF)!=0:
                self.p2.plot(self.refTOF, clear=False,pen='r')
        
        
    def updateIsocurve(self):
    
        self.iso.setLevel(self.isoLine.value())

    def OpenFile(self):

        PathName = QtGui.QFileDialog.getOpenFileName(directory='/Volumes/qolslc/atto/labdata/2015/20151106_Isopropanol/')
        self.pname=PathName
        struct=sio.loadmat(self.pname)
        self.scan=-np.array(struct['Scan_ChA'].T,dtype=np.float64)
        #self.scan=-np.array(struct['Digiscan']['waveform_B'][0][0],dtype=np.float64)
        #self.scan=np.array(struct['Delayscan']['Ntraw'][0][0],dtype=np.float64)
        self.activeimg=self.scan
        self.img.setImage(self.activeimg)
        
        self.hist.setLevels(self.hist.getLevels)
        
        self.updatePlot
        self.updateIsocurve
        
        print(self.pname)
        
    def SaveReference(self):

        self.refDscan=self.roi.getArrayRegion(self.activeimg,self.img).sum(axis=0)
        self.refx0,self.refy0=self.roi.pos()
        
        self.refTOF=self.activeimg.sum(axis=1)
        self.updatePlot
        if self.checkbox2.checkState()==2:
            self.refDscan=self.normDscan
        if self.checkbox3.checkState()==2:
            self.refTOF=self.normTOF
            
        self.p0.plot(np.arange(0,len(self.refDscan))+self.refy0,self.refDscan,clear=False,pen='r')
        self.p2.plot(self.refTOF,clear=False,pen='r')


    def StreamOnOff(self):

        if self.checkboxStream1.checkState()==2:
            if self.pname != '':
                print 'Stream from file ON'
                self.timer.start(100)
            else:
                print 'No file to stream from... Load a file first.'
        elif self.checkboxStream1.checkState()==0:
            print 'Stream OFF'
            self.timer.stop
            
            
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
