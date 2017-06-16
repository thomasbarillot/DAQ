# -*- coding: utf-8 -*-
"""
Created on Sat Apr  2 11:34:25 2016

@author: thomasbarillot
"""

##### CLIENT FILE

from psana import *
import numpy as np
import scipy.io
#import mpidata
import random
from xtcav.ShotToShotCharacterization import *
import pypsalg
import os

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()



def ArrInit(self):
        # Magnetic bottle array 3D: time,amplitude;index of event; length of MB wf
        #self.mbArr = np.zeros((2,self.args.nsave,self.mblen/ \
        #                       self.args.binsize),dtype=np.float32)
        # Gas detector array (6 ebeam EL3 values)
        self.gmdArr   = np.zeros((self.args.nsave,6))
        # Acq parameters: offset and fullscale for both channels low gain: 2, high gain 1
        self.envArr   = np.zeros((1,5))
        self.delayArr = np.zeros(1)
        #
        self.ebeamArr = np.zeros((self.args.nsave,21))
        # Time stamp array
        self.TimeSt = np.zeros((self.args.nsave,))

        #hits for peak finding
        self.hits  = [[np.nan]*self.args.nsave,[np.nan]*self.args.nsave]

        #self.mbArr[:,:,:]   = np.nan
        self.gmdArr[:]      = np.nan
        self.ebeamArr[:,:]  = np.nan
        self.envArr[:,:]    = np.nan
        self.TimeSt[:]      = np.nan
        self.delayArr[:] = np.nan
        self.nsave          = 0
        
#### Save function for matfile and npzfile ####

def save(self):
        if self.args.save == True:
            runnumber = int(self.args.exprun[17:])
            filename = 'amoj1516_r' + str(runnumber).zfill(4) + '_' + \
                        str(rank).zfill(3) + '_' + str(self.filenum).zfill(3)

            directory_n=self.args.path+self.args.npzdir + \
                        self.args.binlabel + '/run' + \
                        str(runnumber).zfill(4) + '/'
            directory_m=self.args.path+self.args.matdir + \
                        self.args.binlabel +  '/run' + \
                        str(runnumber).zfill(4) + '/'
            if rank!=1:
                comm.Barrier()
            if not os.path.exists(directory_n):
                os.makedirs(directory_n)
            if not os.path.exists(directory_m):
                os.makedirs(directory_m)
    datanpz={'EBeamParameters':self.ebeamArr, \
                                       #'MBchannel1':self.mbArr[0,:self.nsave,:].astype(np.float16), \
                                       #'MBchannel2':self.mbArr[1,:self.nsave,:].astype(np.float16), \
                                       #'MBChan2':self.mbArr[1], \
                                       'GasDetector':self.gmdArr[0:self.nsave,:], \
                                       'EnvVar':self.envArr[0:self.nsave,:], \
                                       'T':self.T, \
                                       'TimeStamp':self.TimeSt, \
                                       'Delay':self.delayArr[0], \
                                       'HitsChan1':self.hits[0][0:self.nsave], \
                                       'HitsChan2':self.hits[1][0:self.nsave], \
                                       'Elmode':self.args.Elmode}
            scipy.io.savemat(directory_m+filename+'.mat',datamat)

            np.savez(directory_n+filename,**datanpz)
            
            
### MPI RUNFILE
            
            #from master import runmaster
from clientnew import runclient

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
#assert size>1, 'At least 2 MPI ranks required'
#numClients = size-1

# Allow to parse command line arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("exprun", help="psana experiment/run string (e.g. exp=amoj1516:run=43)")
parser.add_argument("-n","--noe",help="number of events, all events=0",default=-1, type=int)

args = parser.parse_args()

