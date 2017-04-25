# -*- coding: utf-8 -*-
"""
Created on Sun Apr  3 21:55:26 2016

@author: thomasbarillot
"""

import scipy.io as sio

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import os

import ctype as cp

PiezoStagelib=cp.cdll.LoadLibrary("PI_E750_CP/PI_E750_CP_labviewdll/PI_E750_cp.dll")


class Dstage():
    
    def __init__(self):
        
        PiezoStageLib.PI_E750_cp_setposition(PositionUm);
        PiezoStageLib.PI_E750_cp_setvelocity(stageVelocity);
        PiezoStageLib.PI_E750_cp_getpos();
        PiezoStageLib.PI_E750_cp_close();
        
    def __del__(self):
        
        
    def setPosition(self):
        
    def OpenCommunication(self,comport):
        PiezoStageLib.PI_E750_cp_open(cp.c_float(comport))
        
        
    