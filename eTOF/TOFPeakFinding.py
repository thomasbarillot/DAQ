# -*- coding: utf-8 -*-
"""
Created on Wed Mar 23 14:46:24 2016

@author: tbarillot
"""

import numpy as np
import scipy.io as sio

from FuncDetectPeaks import detect_peaks

def TOFPeakfinding(filename,mindist,minheight):
    
    
    SStmparray=sio.loadmat('%s' % (filename))
    SSarray=SStmparray['spectra_A']

    SSarray[SSarray>-1]=-1
    SSarray=-(SSarray+1)

    peakarray=[]
    
    for i in range(0,SSarray.shape[0]):

        peaks=detect_peaks(SSarray[i,6500:8000],mindist,minheight)
        
        peakarray=np.append(peakarray,len(peaks))
        
        
    return peakarray