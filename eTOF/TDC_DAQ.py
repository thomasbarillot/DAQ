import scipy.io as sio
import scipy.sparse as sparse
import math
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from matplotlib import pyplot as plt


from multiprocessing import Process
from threading import Thread

from datetime import datetime
#import WetLab_NewportDelayStage as dstage


# Communication with the p7889 TDC card through DDE.

import win32ui
import dde

import time
import os

from ctypes import *
import ctypes as ct


dt=datetime
thislogfilename='%i%s%s_%s%s%s.log' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2), \
                                        str(dt.today().second).zfill(2))




def SaveDataWorker(ch0,ch1,ts,idx,threshold,foldername,SAVESPARSE):
        
    try:
        baseline_tmp=np.median(ch0[:,:500],axis=1).astype(np.int64)
        ch0=((ch0.T-baseline_tmp).T)
        ch0[ch0>=threshold]=0
    except:
        print 'error baseline correction'
    #print 'sparsing'
    
    
    if SAVESPARSE:
        try:
            dataSparse=sparse.coo_matrix(np.array(ch0))                 
        except:
            print 'error sparsing'
        TS=[ts[t] for t in dataSparse.row]
        datatosave={'specmat_ChA':np.array([TS,dataSparse.col,dataSparse.data]),'specmat_ChB':0}#,'timestamps':timestamps}
    else:
        datatosave={'specmat_ChA':ch0,'specmat_ChB':0}#,'timestamps':timestamps}
    
    path_mat='%s/SShot/specfile_%s.mat' % (foldername,str(idx).zfill(3))

    sio.savemat(path_mat,datatosave)               
  



class HEADER(ct.Structure):
  _fields_ = [("RecordStatus", ct.c_ubyte),
              ("UserID", ct.c_ubyte),      
              ("Channel", ct.c_ubyte),     
              ("DataFormat", ct.c_ubyte),
              ("SerialNumber", ct.c_uint32),
              ("RecordNumber", ct.c_uint32),
              ("SamplePeriod", ct.c_int32),
              ("Timestamp", ct.c_int64),
              ("RecordStart", ct.c_int64),
              ("RecordLength", ct.c_uint32),
              ("Reserved", ct.c_uint32)]



class TDC_DAQ():

    def __init__(self):
        
        self.foldername='' # Path to the file
        self.fname='' #Full filename including the path
        #self.ProgressBar=[]
        
        # Conversion factors
        self.mv_conv=(2**16)/300.0
        self.ns_conv=2
        
        #Acquisition parameters
        self.acqmode=3 # Choose either SINGLE_SHOT(0) or WAVEFORM_AVG(1)
        self.ltof=3000 # %Record length per shot in ns
        self.analogbias_mv = 0.0 # Adjustable analog bias (DC offset) in mV. Range is +/-150mV
        self.analogbias=np.round(self.analogbias_mv*self.mv_conv)
        self.channel=1
        self.threshold=150
        
        
        #Stream options
        
        self.baserefreshrate = 0.05
        self.samples_added=0

        #Delay Scan parameters

        self.dscanmode=0
        self.dscanstart=0
        self.dscanstop=80
        self.dscanstep=1
        self.dscanrange=np.arange(self.dscanstart,self.dscanstop,self.dscanstep)
        
        # Recording options
        
        self.nrecords=1000 # Number of records (sweeps) per sample
        self.nsamples=self.ltof*2 #samples per buffer record
        
        
        self.bytes_per_sample = 2  #2 for 16bits
        
        self.data_ch=np.zeros((self.nsamples)).astype(np.int64)
        
        # Trigger options
        self.triggermode=2 # choose: 'CH_A(3)','CH_B(3)' or 'EXTERNAL_TRIGGER (2) or SOFTWARE_TRIGGER (1)'
        self.trigchannel=1 # Choose 'CH_A(1)','CH_B(2)' 
        self.trig_edge = 1 #RISING_EDGE(1) or FALLING EDGE(0)
        self.triglevel_mv =500.0 #Trigger threshold in mV => For a level trigger this must be in the range +/-150mV. For external trigger this must be in the range -500mV to +3300mV.
        self.record_start_shift = 'NONE' #choose 'PRETRIGGER', 'HOLDOFF' OR 'NONE'
        self.pretrigger_ns=0 #only applicable if 'PRETRIGGER' is selected.
        self.holdoff_ns=0 #only applicable if 'HOLDOFF' is selected.
        
        #self.f.write('nsamplesA: %i, nrecords: %i, buffer size: %i, channel: %i, Triggermode:%i, dscanmode: %i, acqmode: %i\n'\
        #         % (self.nsamples,self.nrecords,self.buffer_size,self.channel,self.triggermode,self.dscanmode,self.acqmode))
        
        # Connect with the TDC card p7889
        self.server=[]
        self.tchat=[]
        #self.tchat.Exec("RUN TDCCMD.CTL")
        
        
        # Adjustable input range and bias
        
        self.Vrange=500.0
        self.Vbias=0.0
        
        setVrange=ct.c_float(self.Vrange)
        setVbias=ct.c_float(self.Vbias)
        
        
        # Configuration of data acquisition on p7889
        cfg=open('p7889_initconfig.cfg','w')
        cfg.write('digio=0\n')
        cfg.write('digval=0\n')
        cfg.write('range=%i\n'%self.nsamples)
        cfg.write('fstchan=93.75\n')
        cfg.write('holdafter=0\n')
        cfg.write('sweepmode=3a0\n')
        cfg.write('swpreset=%i\n'%self.nrecords)
        cfg.write('prena=4\n')
        cfg.write('syncout=300\n')
        cfg.write('cftfak=2580100\n')
        cfg.write('cycles=2\n')
        cfg.write('sequences=1\n')
        cfg.write('dac0=6700\n')
        cfg.write('dac1=7d80\n')
        cfg.write('bitshift=0\n')
        cfg.write('rtpreset=1000.000\n')
        cfg.write('evtpreset=0\n')
        cfg.write('autoinc=0\n')
        cfg.write('datname=%s\n'%(self.foldername))
        cfg.write('savedata=3\n')
        cfg.write('fmt=%s\n'%('csv'))
        cfg.write('smoothpts=1\n')
        cfg.write('roimin=4000\n')
        cfg.write('roimax=4200\n')
        cfg.write('caluse=1\n')
        cfg.close()
        
        
            
    def __del__(self):
        
        self.tchat.close()
        self.f.close()
        
               
# GUI interaction functions
 
    def setFoldername(self,foldername):
        self.foldername=foldername
        
    def setFilename(self,fname):
        self.fname=self.foldername+fname
    
    def setExtTriggerlevel(self,triglvl):
        self.triglevel_mv=triglvl*1000.0
    
    def setSignalThreshold(self,signalthresh):
        self.threshold=signalthresh
        
    def setNRecords(self,nrecords):
        self.nrecords=nrecords
        
    def setNsamples(self,ltof):
        self.ltof=ltof # %Record length per shot in ns
        self.nsamples=ltof*10 # %Record length per shot in ns
            
    def setStreamRecords(self,records):
        self.nstreamrecords=records
        
    def setAcqMode(self,mode):
        self.acqmode=mode
        
    def setDscanMode(self,mode):
        self.dscanmode=mode
    
    def setTDCParameters(self):

        # Configuration of scans parameters
        #self.f.write('set Dig Params\n')
        #self.nsamples=ParametersArray[0]*2
        
        #self.buffer_size = self.nsaverecords*self.nsamplesA
#        
        #self.channel=ParametersArray[2]
        #self.triggermode=ParametersArray[3]
#        
        #self.dscanmode=ParametersArray[4]
        #self.dscanstart=ParametersArray[5]
        #self.dscanstop=ParametersArray[6]
        #self.dscanstep=ParametersArray[7]
         
        #if (len(ParametersArray[9])!=0):
        #    self.dscanrange=ParametersArray[9]
        #else:
        #    self.dscanrange=np.arange(self.dscanstart,self.dscanstop,self.dscanstep)
        
        # Write the parameters in the command file to be sent to the card
        cmd=open('C:\P7889\TDCCMD.CTL','w')
        cmd.write('fstchan=9.375000e+01\n')
        cmd.write('sweepmode=2a0\n')
        cmd.write('prena=4\n')
        cmd.write('swpreset=%i\n'%(self.nrecords))
        cmd.write('range=%i\n'%(self.nsamples))
        cmd.write('roimin=2000\n')
        cmd.write('roimax=3000\n')
        cmd.write('savedata=%i\n'%(self.acqmode))
        cmd.write('datname=%s\n'%(self.fname))
        #cmd.write('autoinc=%i\n'%(self.dscanmode))
        cmd.write('fmt=csv\n')
        cmd.write('start\n')
        cmd.close()
        
    def StartRecording(self):
        
        
#            savestart= 0
#            ChannelsMask = 0xF
#            StartSample = 0
            
        #if self.dscanmode == 0:
        #self.setFilename('Spectrum')
        #else:
        #    self.setFilename('Spectrum_D%s'%(str(increment).zfill(4)))
            
        #self.setTDCParameters()
        
        
        
        self.server=dde.CreateServer()
        self.server.Create('DAQ_GUI')
        self.tchat=dde.CreateConversation(self.server)
        self.tchat.ConnectTo("P7889","7889")
        self.tchat.Exec("RUN TDCCMD.CTL")
        self.server.Destroy()
            
            #self.f.write('Acquisition finished at %s:%s:%s' % (str(dt.today().hour).zfill(2), \
            #                                                   str(dt.today().minute).zfill(2), \
            #                                                   str(dt.today().second).zfill(2)))
### DSCAN ON ###
#        elif self.dscanmode==1:
#            
#            for j,delayval in enumerate(self.dscanrange):
#                
#               self.setFilename('Spectrum_D%s'%(str(j).zfill(4)))
#               self.setTDCParameters()
#               #self.tchat.ConnectTo("P7889","7889")
#               self.tchat.Exec("RUN TDCCMD.CTL")
#               
#               while os.path.isfile(self.fname)==False:
#                   time.sleep(0.2)
                    
            #self.f.write('Acquisition finished at %s:%s:%s' % (str(dt.today().hour).zfill(2), \
            #                                                   str(dt.today().minute).zfill(2), \
            #                                                   str(dt.today().second).zfill(2)))
        #self.progressflag=1
        #self.StopRecording
##
    def StopRecording(self):
        
        #self.server.Shutdown()
        try:
            self.server=dde.CreateServer()
            self.server.Create('DAQ_GUI')
            self.tchat=dde.CreateConversation(self.server)
            self.tchat.ConnectTo("P7889","7889")
            self.tchat.Exec("halt")
            self.server.Destroy()
        except:
            return 0
            
    def StartStream(self):
        
        
        self.setFilename('PE_tmp_file')
        self.setTDCParameters()
        self.server=dde.CreateServer()
        self.server.Create('DAQ_GUI')
        self.tchat=dde.CreateConversation(self.server)
        self.tchat.ConnectTo("P7889","7889")
        self.tchat.Exec("RUN TDCCMD.CTL")
        self.server.Destroy()
        
        
    def PollRange(self):
        
        self.server=dde.CreateServer()
        self.server.Create('DAQ_GUI')
        self.tchat=dde.CreateConversation(self.server)
        self.tchat.ConnectTo("P7889","7889")
        datarange=self.tchat.Request("RANGE")
        self.server.Destroy()
        
        return int(datarange)
        
    def RunStream(self):
        
        self.server=dde.CreateServer()
        self.server.Create('DAQ_GUI')
        self.tchat=dde.CreateConversation(self.server)
        self.tchat.ConnectTo("P7889","7889")
        datastr=self.tchat.Request("DATA")
        self.server.Destroy()
        
        data=map(int,datastr.splitlines())
        
        return data
    
    def StopStream(self):
        
        try:
            self.server=dde.CreateServer()
            self.server.Create('DAQ_GUI')
            self.tchat=dde.CreateConversation(self.server)
            self.tchat.ConnectTo("P7889","7889")
            self.tchat.Exec("halt")
            self.server.Destroy()
        except:
            return 0
       
