# -*- coding: utf-8 -*-
"""
Created on Thu Apr 07 08:37:00 2016

@author: atto
"""
import numpy as np
import scipy.io as sio
from glob import glob
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("path", help="Data folder path",type=str)
parser.add_argument("ch",help="Channel A or B",nargs=1,default='A', type=str)
parser.add_argument("n",help="number of array entries, default value: 1000",default=1000, type=int)
parser.add_argument("b",help="Boundaries: min max, default values: [0,10000]",nargs=2,default=[0,10000], type=int)
#parser.add_argument("--ch",help="Channel A or B",default=-1, type=int)

args = parser.parse_args()


def TOFSpectrumCrop(iargs):
    
    filename=glob('%s/specfile_%s_*.mat' % (iargs.path,iargs.ch[0]))
    wfname='spectra_%s' % iargs.ch[0]
    
    
    for i,fname in enumerate(filename):
        
        MStruct=sio.loadmat(fname)
        newfname='specfile_%s_%i.mat' % (iargs.ch[0],i)
        Mtmp=np.array(MStruct[wfname],dtype=np.int32)
        
        M=Mtmp[:,iargs.b[0]:iargs.b[1]]
        
        sio.savemat('%s/Cropped_%s' % (iargs.path,newfname),{'Digiscan':{wfname:M}})
        p=(float(i)/len(filename))*100.0 
        pprint='%0.2f percent of files treated' % p
        print pprint
        
        
print 'start treating TOFs ...'
TOFSpectrumCrop(args)
print 'TOFs cropping done.'