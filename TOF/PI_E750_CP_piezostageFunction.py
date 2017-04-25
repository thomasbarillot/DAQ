# -*- coding: utf-8 -*-
"""
Created on Mon Apr 04 11:17:15 2016

@author: atto

Piezostage remote control (ie writingdelay into file read by humongium)

"""
import scipy.io as sio

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import os

from glob import glob

import ctypes as cp

def PI_E750_CP_piezostageFunction(remotefpath,delay_fs):
    
    # folder of interest //155.198.197.13/CEP_remotecontrol/
    if delay_fs>80:
        delay_fs=80
    elif delay_fs<0:
        delay_fs=0
        
    delay_um=(delay_fs*299792458*1e-15*1e6)/2.0
    
    for filename in glob('%s/delayrequest_*' % remotefpath):
        os.remove(filename)
        
    f=open('%s/delayrequest_%.5f' % (remotefpath,delay_um),'w')
    f.write('\n')
    f.close()
    
    