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
import WetLab_NewportDelayStage as dstage


import time
import os

from ctypes import *
import ctypes as ct

ADQAPI = cdll.LoadLibrary("ADQAPI.dll")
#
ADQAPI.CreateADQControlUnit.restype = c_void_p
#ADQAPI.ADQ14_GetRevision.restype = c_void_p
ADQAPI.ADQControlUnit_FindDevices.argtypes = [c_void_p]

dt=datetime
thislogfilename='%i%s%s_%s%s%s.log' % (dt.today().year,str(dt.today().month).zfill(2),str(dt.today().day).zfill(2), \
                                        str(dt.today().hour).zfill(2), \
                                        str(dt.today().minute).zfill(2), \
                                        str(dt.today().second).zfill(2))



  
    
def SaveDataThread(ch0,ch1,ts,idx,threshold,foldername,SAVESPARSE,ROIB,idxdelay=-1,idxcycle=-1):
        
    try:
        baseline_tmp=np.median(ch0[:,:500],axis=1).astype(np.int64)
        ch0=((ch0.T-baseline_tmp).T)
        ch0[ch0>=threshold]=0
        
        baseline_tmp=np.median(ch1[:,:500],axis=1).astype(np.int64)
        ch1=((ch1.T-baseline_tmp).T)
        
    except:
        print 'error baseline correction'
    #print 'sparsing'
    
    ch1sum=ch1[:,ROIB[0]:ROIB[0]].sum(1)
    
    
    
    
    if SAVESPARSE:
        try:
            dataSparse=sparse.coo_matrix(np.array(ch0))                 
        except:
            print 'error sparsing'
        TS=[ts[t] for t in dataSparse.row]
        datatosave={'specmat_ChA':np.array([TS,dataSparse.col,dataSparse.data]),'specmat_ChB':ch1sum}#,'timestamps':timestamps}
    else:
        datatosave={'specmat_ChA':ch0,'specmat_ChB':0}#,'timestamps':timestamps}
    
    if (idxdelay!=-1) or (idxcycle!=-1):
        path_mat='%s/SSdelay%s_n%s/specfile_%s.mat' % (foldername,str(idxdelay).zfill(3),str(idxcycle).zfill(3),str(idx).zfill(3))
    else:
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



class ADC_DAQ():

    def __init__(self,f):
        
        self.f=f
        self.buffers_filled=c_uint(0)
        self.foldername=''
        #self.ProgressBar=[]
        
        # Conversion factors
        self.mv_conv=(2**16)/300.0
        self.ns_conv=2
        
        #Acquisition parameters
        self.acqmode=1 # Choose either SINGLE_SHOT(0) or WAVEFORM_AVG(1)
        self.ltofA=3000 # %Record length per shot in ns
        self.ltofB=3000 # %Record length per shot in ns
        self.ROIB=(0,int(self.ltofB*2))
        
        
        self.analogbiasA_mv = 0.0 # Adjustable analog bias (DC offset) in mV. Range is +/-150mV
        self.analogbiasA=np.round(self.analogbiasA_mv*self.mv_conv)
        self.analogbiasB_mv =0.0 # Adjustable analog bias (DC offset) in mV. Range is +/-150mV
        self.analogbiasB=np.round(self.analogbiasB_mv*self.mv_conv)
        self.channel=2
        self.threshold=150
        
        
        #Stream options
        
        self.baserefreshrate = 0.05
        self.buffers_filled = ct.c_uint(0)
        self.target_buffers = 0
        self.target_headers = 0
        self.timestamps_buffers = 0
        self.samples_added=0
        self.headers_added=0
        self.header_status=0
        self.collect_result=0
        
        
        

        #Delay Scan parameters

        self.dscanmode=0
        self.dscanstart=0
        self.dscanstop=80
        self.dscanstep=1
        self.dscanrange=np.arange(self.dscanstart,self.dscanstop,self.dscanstep)
        
        self.idxdelay=0
        self.idxcycle=0
        
        # Recording options
        
        self.nbuffrecords=2 # Number of buffer records
        self.nrecords=1000 # Number of records per sample
        self.nstreamrecords = 100
        self.nsaverecords=10000
        self.progressrecords=0.0000001
        self.progressflag=0
        self.nsamplesA=self.ltofA*2 #samples per buffer record
        self.nsamplesB=self.ltofB*2 #samples per buffer record
        self.buffer_sizeA = self.nsaverecords*self.nsamplesA
        self.buffer_sizeB = self.nsaverecords*self.nsamplesB
        self.SAVESPARSE=False
        self.bytes_per_sample = 2  #2 for 16bits
        self.ROIB=(0,1000)
        
        
        self.data_chA=np.zeros((self.nsamplesA)).astype(np.int64)
        self.data_chB=np.zeros((self.nsamplesA)).astype(np.int64)
        
        # Trigger options
        self.triggermode=2 # choose: 'CH_A(3)','CH_B(3)' or 'EXTERNAL_TRIGGER (2) or SOFTWARE_TRIGGER (1)'
        self.trigchannel=1 # Choose 'CH_A(1)','CH_B(2)' 
        self.trig_edge = 1 #RISING_EDGE(1) or FALLING EDGE(0)
        self.triglevel_mv =500.0 #Trigger threshold in mV => For a level trigger this must be in the range +/-150mV. For external trigger this must be in the range -500mV to +3300mV.
        self.record_start_shift = 'NONE' #choose 'PRETRIGGER', 'HOLDOFF' OR 'NONE'
        self.pretrigger_ns=0 #only applicable if 'PRETRIGGER' is selected.
        
        
        self.holdoff_samples=1 #only applicable if 'HOLDOFF' is selected. Same for both channels
        
        
        self.f.write('nsamplesA: %i, nrecords: %i, buffer size: %i, channel: %i, Triggermode:%i, dscanmode: %i, acqmode: %i\n'\
                 % (self.nsamplesA,self.nrecords,self.buffer_sizeA,self.channel,self.triggermode,self.dscanmode,self.acqmode))
        # Connect with the digitizer
        self.adq_cu = c_void_p(ADQAPI.CreateADQControlUnit())
        
        ADQAPI.ADQControlUnit_FindDevices(self.adq_cu)
        n_of_ADQ = ADQAPI.ADQControlUnit_NofADQ(self.adq_cu)
        err2=ADQAPI.ADQControlUnit_GetLastFailedDeviceError(self.adq_cu)
        n_of_ADQ14 = ADQAPI.ADQControlUnit_NofADQ14(self.adq_cu)
        err3=ADQAPI.ADQControlUnit_GetLastFailedDeviceError(self.adq_cu)
        self.f.write('initialisation values: %i,%i,%i,%i \n' % (n_of_ADQ,n_of_ADQ14,err2,err3))
        try:
            a=ADQAPI.ADQ_GetADQType(self.adq_cu,1)
            print 'card type', a
            rev = ADQAPI.ADQ_GetBoardProductName(self.adq_cu,1)
            revision = ct.cast(rev,ct.POINTER(ct.c_char))
            print 'card number',revision[0],revision[1],revision[2],revision[3],revision[4],revision[5],revision[6],revision[7],revision[8],revision[9],revision[10]
            rev= ADQAPI.ADQ_GetCardOption(self.adq_cu,1)
            revision = ct.cast(rev,ct.POINTER(ct.c_char))
            
            print 'card options',revision[0],revision[1],revision[2],revision[3],revision[4],revision[5],revision[6],revision[7],revision[8],revision[9],revision[10],revision[11],revision[12]
        except:
            print 'error printing card options'
        # Adjustable input range and bias
        
        self.VrangeChA=500.0
        self.VrangeChB=500.0
        
        self.VbiasChA=0.0
        self.VbiasChB=0.0
        
        setVrangeA=ct.c_float(self.VrangeChA)
        setVrangeB=ct.c_float(self.VrangeChB)
        
        setVbiasA=ct.c_float(self.VbiasChA)
        setVbiasB=ct.c_float(self.VbiasChB)
        
        if ADQAPI.ADQ_HasAdjustableInputRange(self.adq_cu, 1):
            success=ADQAPI.ADQ_SetInputRange(self.adq_cu, 1,1,ct.c_float(self.VrangeChA),ct.byref(setVrangeA))
            success=ADQAPI.ADQ_SetInputRange(self.adq_cu, 1,1,ct.c_float(self.VrangeChB),ct.byref(setVrangeB))
            self.f.write('Vrange CHA =%0.2f (mVpp)\n' % setVrangeA.value)
        
        ADQ_CLOCK_INT_INTREF = 0
        ADQAPI.ADQ_SetClockSource(self.adq_cu, 1, ADQ_CLOCK_INT_INTREF)
        
        self.headerbuf_list=[]
        
        if (n_of_ADQ14 != 0):
            self.f.write('found ADQ device \n')
            #ADQAPI.ADQControlUnit_EnableErrorTraceAppend(self.adq_cu,3,'C:/Documents/...')
            self.f.write('enable ADQ log trace \n')
            
            
    def __del__(self):
        success = ADQAPI.DeleteADQControlUnit(self.adq_cu)
        if (success == 0):
            self.f.write('Delete ADQ control failed.\n')
        self.f.close()
        
               
# GUI interaction functions
 
    def setExtTriggerlevel(self,triglvl):
        self.triglevel_mv=triglvl*1000.0
    
    def setSignalThreshold(self,signalthresh):
        self.threshold=signalthresh
        
    def setNRecords(self,nrecords):
        self.nrecords=nrecords
        
    def setNsamples(self,ltof):
        self.ltofA=ltof # %Record length per shot in ns
        self.ltofB=ltof # %Record length per shot in ns
        self.nsamplesA=ltof*2 # %Record length per shot in ns
        self.nsamplesB=ltof*2 # %Record length per shot in ns
        
    def setSaveSparse(self,value):
        if value==2:
            self.SAVESPARSE=True
        elif value==0:
            self.SAVESPARSE=False
        
    def setStreamRecords(self,records):
        self.nstreamrecords=records
        
    def setAcqMode(self,mode):
        self.acqmode=mode
        
    def setHoldOff(self,nholdoff):
        self.holdoff_samples=int(nholdoff*2-((nholdoff*2)%8)) # hold off by chunck of 8 samples

            
    def setDigitizerParameters(self,ParametersArray):
         self.f.write('set Dig Params\n')
                  
         self.nsamplesA=ParametersArray[0]*2
         
         #self.nrecords=ParametersArray[1] # Number of records per sample

         self.buffer_sizeA = self.nsaverecords*self.nsamplesA
#        
         self.channel=ParametersArray[2]
         self.triggermode=ParametersArray[3]
#        
         self.dscanmode=ParametersArray[4]
         self.dscanstart=ParametersArray[5]
         self.dscanstop=ParametersArray[6]
         self.dscanstep=ParametersArray[7]
         
         #self.acqmode=ParametersArray[8]
         
         if (len(ParametersArray[9])!=0):
             self.dscanrange=ParametersArray[9]
         else:
             self.dscanrange=np.arange(self.dscanstart,self.dscanstop,self.dscanstep)
         
            
         if  ParametersArray[10]!=self.VrangeChA:
             self.VrangeChA=ParametersArray[10]
             setVrangeA=ct.c_float(self.VrangeChA)
             if ADQAPI.ADQ_HasAdjustableInputRange(self.adq_cu, 1):
                 try:
                     success=ADQAPI.ADQ_SetInputRange(self.adq_cu, 1,1,ct.c_float(self.VrangeChA),ct.byref(setVrangeA))
                     self.f.write('Vrange CHA =%0.2f (mVpp)\n' % setVrangeA.value)
                 except:
                     self.f.write('error Vrange CHA =%0.2f (mVpp)\n' % setVrangeA.value)
         
             success=ADQAPI.ADQ_GetInputRange(self.adq_cu, 1,1,ct.byref(setVrangeA))
             self.f.write('get Vrange CHA =%0.2f (mVpp)\n' % setVrangeA.value)
         
         
         if not ParametersArray[11]==self.VrangeChB:
             self.VrangeChB=ParametersArray[11]
             setVrangeB=ct.c_float(self.VrangeChB)
             if ADQAPI.ADQ_HasAdjustableInputRange(self.adq_cu, 1):
                 success=ADQAPI.ADQ_SetInputRange(self.adq_cu, 1,1,ct.c_float(self.VrangeChB),ct.byref(setVrangeB))
                 
         if not ParametersArray[12]==self.VbiasChA:
             self.VbiasChA=ParametersArray[12]
             setVbiasA=ct.c_float(self.VbiasChA)
             if ADQAPI.ADQ_HasAdjustableInputRange(self.adq_cu, 1):
                 success=ADQAPI.ADQ_SetInputRange(self.adq_cu, 1,1,ct.c_float(self.VbiasChA),ct.byref(setVbiasChA))
                 
         if not ParametersArray[13]==self.VbiasChB:
             self.VbiasChB=ParametersArray[13]
             setVbiasB=ct.c_float(self.VbiasChB)
             if ADQAPI.ADQ_HasAdjustableInputRange(self.adq_cu, 1):
                 success=ADQAPI.ADQ_SetInputRange(self.adq_cu, 1,1,ct.c_float(self.VbiasChB),ct.byref(setVbiasChB))
                 
         if (ParametersArray[14]!=self.pretrigger_ns and ParametersArray[14]!=0):
             self.pretrigger_ns=ParametersArray[14]
             
         else:
             self.pretrigger_ns=0
           
         self.f.write('nsamplesA: %i, nrecords: %i, buffer size: %i, channel: %i, Triggermode:%i, dscanmode: %i, acqmode: %i\n'\
                 % (self.nsamplesA,self.nrecords,self.buffer_sizeA,self.channel,self.triggermode,self.dscanmode,self.acqmode))

    def StartRecording(self,foldername,idxdelay,idxcycle):
        
        
        self.foldername=foldername
        self.idxdelay=idxdelay
        self.idxcycle=idxcycle
        #StartProgressBar()        
        
        #try:
            #self.ProgressBar=QtGui.QProgressDialog('Acquisition in progress','Abort',0,100)
            #self.ProgressBar.show()
            #self.ProgressBar.setValue(0)
        #except:
            #print 'ERROR starting progress bar dialog box'
        
        #success = ADQAPI.ADQ_SetSampleSkip(self.adq_cu,1,1)
        #if (success == 0):
        #    self.f.write('ADQ_SetSampleSkip failed.\n')
        #self.f.write('bp3\n')
        #success = ADQAPI.ADQ_SetAdjustableBias(self.adq_cu,1,0,self.analogbiasA)
        #if (success == 0):
        #    print('ADQ_SetAdjustableBias failed.')
        #success = ADQAPI.ADQ_SetAdjustableBias(self.adq_cu,1,1,self.analogbiasB)
        #if (success == 0):
        #    print('ADQ_SetAdjustableBias failed.')
        success = ADQAPI.ADQ_SetTriggerMode(self.adq_cu,1, self.triggermode)
        if (success == 0):
            self.f.write('ADQ_SetTriggerMode failed.\n')
        self.f.write('bp4\n')
        #trigth=0.6
        

        
        if self.triggermode==1:
        
            success = ADQAPI.ADQ_SetLvlTrigLevel(self.adq_cu, 1, 0)
            if (success == 0):
                self.f.write('ADQ_SetLvlTrigLevel failed.')    
            success = ADQAPI.ADQ_SetTrigLevelResetValue(self.adq_cu,1, 1000)
            if (success == 0):
                self.f.write('ADQ_SetTrigLevelResetValue failed.')    
            success = ADQAPI.ADQ_SetLvlTrigChannel(self.adq_cu,1, 1)
            if (success == 0):
                self.f.write('ADQ_SetLvlTrigChannel failed.')    
            success = ADQAPI.ADQ_SetLvlTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                self.f.write('ADQ_SetLvlTrigEdge failed.')
        
        if self.triggermode==2:
            success = ADQAPI.ADQ_SetExtTrigThreshold(self.adq_cu,1,1,c_double(self.triglevel_mv/1000.0))
            if (success == 0):
                self.f.write('ADQ_SetExternTrigLevel failed.\n')
            success = ADQAPI.ADQ_SetExternTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                self.f.write('ADQ_SetExternTrigEdge failed.\n')
        
        if self.triggermode==3:
            triglvl=int(round(self.triglevel_mv*self.mv_conv))
            success = ADQAPI.ADQ_SetLvlTrigChannel(self.adq_cu,1, self.trigchannel)
            if (success == 0):
                self.f.write('DParam: ADQ_SetLvlTrigChannel failed.\n')
            success = ADQAPI.ADQ_SetLvlTrigLevel(self.adq_cu,1, triglvl)
            if (success == 0):
                self.f.write('DParam: ADQ_SetLvlTrigLevel failed.\n')
            success = ADQAPI.ADQ_SetLvlTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                self.f.write('DParam: ADQ_SetLvlTrigEdge failed.\n')
                 
                
       
        
        
       
        
        
    def RunRecording(self,idxdelay=0,idxcycle=0,ROIB=(0,1)):
        
        
         ### REINIT THE SIZE OF THE DATA STORAGE FOR CHA AND B
        self.data_chA=np.zeros((self.nsamplesA),dtype=np.int64)
        self.data_chB=np.zeros((1),dtype=np.int64)
        self.progressrecords=0.0000001
        self.progressflag=0
        
        ### DSCAN OFF ###

        if self.dscanmode==0:
            try:
                avgtraceA=np.zeros((self.nsamplesA),dtype=np.int64)
                avgtraceB=np.zeros((1),dtype=np.int64)
            except:
                self.f.write('Initialisation of average scan matrix failed.\n') 
            
            success=ADQAPI.ADQ_MultiRecordSetup(self.adq_cu,1,self.nrecords,self.nsamplesA)
            if (success == 0):
                self.f.write('Recording: ADQ_MultiRecordSetup failed.\n')
            else:
                self.f.write('Recording: ADQ_MultiRecordSetup SUCCESS.\n')
            self.f.write('bp7\n')
            
             ### HOLDOFF SAMPLES ###
            # Same holdoff sample for both channels
#            success=ADQAPI.ADQ_SetTriggerHoldOffSamples(self.holdoff_samples)
#            if success==0:
#                self.f.write('DParam: ADQ_SetTriggerHoldOffSamples failed.\n')
        
            
            acquiredrecord=0
            savestart= 0
            NumberOfRecords = self.nsaverecords
            ChannelsMask = 0xF
            StartSample = 0
            saveend=self.nsaverecords
            
            success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
            if (success == 0):
                 self.f.write('Recording: ADQ_DisarmTrigger failed.\n')
            success=ADQAPI.ADQ_ArmTrigger(self.adq_cu,1)
            if (success == 0):
                 self.f.write('Recording: ADQ_ArmTrigger failed.\n')
            
            i=0
            
            if self.acqmode==1:
                while (acquiredrecord<self.nrecords):
                    
                    acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
                    
                    max_number_of_channels = 2
                    target_buffers=(POINTER(c_int16*self.nsamplesA*self.nsaverecords)*max_number_of_channels)()
                    for bufp in target_buffers:
                        bufp.contents = (c_int16*self.nsamplesA*self.nsaverecords)()
                    
                    #self.f.write('bp10; nofacq: %i\n' % acquiredrecord)
                    if (acquiredrecord>=saveend):
                        
                        savestart=saveend-self.nsaverecords
                        #4try:
                            
                        ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                            
                        data_16bit_ch0 = np.reshape(np.frombuffer(target_buffers[0].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                        baselineCh0=np.median(data_16bit_ch0[:,:500],axis=1).astype(np.int64)
                        data_16bit_ch0=((data_16bit_ch0.T-baselineCh0).T)
                        data_16bit_ch0[data_16bit_ch0>=self.threshold]=0
                            
                        data_16bit_ch1 = np.frombuffer(target_buffers[1].contents,dtype=np.int16)
                            
                        self.data_chA+=data_16bit_ch0.sum(0)
                        self.data_chB+=(np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA))[:,ROIB[0]:ROIB[1]].sum(1)).sum()
                    
                        #except:
                        #    self.f.write('failed recording average trace\n')
                        i+=1
                        saveend+=self.nsaverecords
                    
                    self.progressrecords=acquiredrecord/np.float(self.nrecords)
                    #self.ProgressBar.setValue(np.round(100*acquiredrecord/np.float(self.nrecords)))                    
                
                dataavg={'Scan_ChA':self.data_chA, \
                                           'Scan_ChB':self.data_chB}
                
    
                path_mat='%s/ScanAvg.mat' % (self.foldername)
                try:
                    sio.savemat(path_mat,dataavg)

                except:
                    self.f.write('failed saving average trace\n')
                    
                
                    
            else:
                
                if not os.path.exists('%s/SShot' % (self.foldername)):
                    os.makedirs('%s/SShot' % (self.foldername))
                    
                print 'record %i shots'%self.nrecords
                savedrecords=0 #number of records already saved
                
                while (acquiredrecord<self.nrecords):# and (savedrecords<acquiredrecord)):
                    
                    acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
                    
                    max_number_of_channels = 2
                    #target_headers=(POINTER(c_int64*self.nsaverecords))()
                    #for headp in target_headers:
                    #    headp.contents= (c_int64*self.nsaverecords)()
                    target_buffers=(POINTER(c_int16*self.nsamplesA*self.nsaverecords)*max_number_of_channels)()
                    for bufp in target_buffers:
                        bufp.contents = (c_int16*self.nsamplesA*self.nsaverecords)()
                    header_list = (HEADER*self.nsaverecords)()
                    target_headers= ct.POINTER(HEADER*self.nsaverecords)()
                    target_headers.contents = header_list
                    target_header_vp = ct.cast(ct.pointer(target_headers), ct.POINTER(ct.c_void_p))
                    #self.f.write('bp10; nofacq: %i\n' % acquiredrecord)
                    if (acquiredrecord>=saveend):
                        
                        savestart=saveend-self.nsaverecords
                        #print 'loop on data'
                        try:
                            
                             #ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                            
                            ADQAPI.ADQ_GetDataWHTS(self.adq_cu,1,
                                                   target_buffers,
                                                   target_headers,
                                                   None,
                                                   self.buffer_sizeA,
                                                   self.bytes_per_sample,
                                                   savestart,
                                                   NumberOfRecords,
                                                   ChannelsMask,
                                                   StartSample,
                                                   self.nsamplesA,
                                                   0x00)
                            
                            data_16bit_ch0 = np.reshape(np.frombuffer(target_buffers[0].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                            data_16bit_ch1 = np.reshape(np.frombuffer(target_buffers[1].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                            TS=np.array([target_headers[0][t].Timestamp*0.125*1e-3 for t in range(self.nsaverecords)])
                            
                            try:
                                
                                proc0=Thread(target=SaveDataThread,args=(data_16bit_ch0[:self.nsaverecords/4,:],data_16bit_ch1[:self.nsaverecords/4,:],TS[:self.nsaverecords/4],i+0,self.threshold,foldername,self.SAVESPARSE,ROIB))
                                proc1=Thread(target=SaveDataThread,args=(data_16bit_ch0[self.nsaverecords/4:2*self.nsaverecords/4,:],data_16bit_ch1[self.nsaverecords/4:2*self.nsaverecords/4,:],TS[self.nsaverecords/4:2*self.nsaverecords/4],i+1,self.threshold,foldername,self.SAVESPARSE,ROIB))
                                proc2=Thread(target=SaveDataThread,args=(data_16bit_ch0[2*self.nsaverecords/4:3*self.nsaverecords/4,:],data_16bit_ch1[2*self.nsaverecords/4:3*self.nsaverecords/4,:],TS[2*self.nsaverecords/4:3*self.nsaverecords/4],i+2,self.threshold,foldername,self.SAVESPARSE,ROIB))
                                proc3=Thread(target=SaveDataThread,args=(data_16bit_ch0[3*self.nsaverecords/4:self.nsaverecords,:],data_16bit_ch1[3*self.nsaverecords/4:self.nsaverecords,:],TS[3*self.nsaverecords/4:self.nsaverecords],i+3,self.threshold,foldername,self.SAVESPARSE,ROIB))
                                    
                            except:
                                print 'error creating process'
                            try:
                                proc0.start()
                                proc1.start()
                                proc2.start()
                                proc3.start()
                                
                                proc0.join()
                                proc1.join()
                                proc2.join()
                                proc3.join()
                                
                            except:
                                print 'error running process'  
                            
                            
                            self.data_chA+=data_16bit_ch0.sum(0)
                            self.data_chB+=(np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA))[:,ROIB[0]:ROIB[1]].sum(1)).sum()
                    
                           
                        except:
                                self.f.write('failed recording singleshot trace\n')
                        i+=4
                        saveend+=self.nsaverecords
                        savedrecords+=self.nsaverecords

                    self.progressrecords=acquiredrecord/np.float(self.nrecords)
                    #self.ProgressBar.setValue(np.round(100*acquiredrecord/np.float(self.nrecords))) 
                
                dataavg={'Scan_ChA':self.data_chA, \
                                           'Scan_ChB':self.data_chB}

                path_mat='%s/ScanAvg.mat' % (self.foldername)
                try:
                    sio.savemat(path_mat,dataavg)

                except:
                    self.f.write('failed saving average trace\n')

### DSCAN ON ###
        elif self.dscanmode==1:
            
            #if self.acqmode==1:
            try:
                avgscanA=np.zeros((len(self.dscanrange),self.nsamplesA),dtype=np.int64)
                avgscanB=np.zeros((len(self.dscanrange)),dtype=np.int64)
            except:
                self.f.write('Initialisation of average scan matrix failed.\n')
            
        
            # Change the delay on the delaystage (humongium computer)
            #dstage('//155.198.197.13/CEP_remotecontrol/',delayval)

            if self.acqmode==0:
                if not os.path.exists('%s/SSdelay%s_n%s' % (foldername,str(idxdelay).zfill(3),str(idxcycle).zfill(3))):
                    os.makedirs('%s/SSdelay%s_n%s' % (foldername,str(idxdelay).zfill(3),str(idxcycle).zfill(3)))

            #if self.acqmode==1:
            try:
                self.data_chA=np.zeros((self.nsamplesA),dtype=np.int64)
                self.data_chB=np.zeros((self.nsamplesA),dtype=np.int64)
            except:
                self.f.write('Initialisation of average trace failed.\n') 
            # Wait for 1 second that the stage has moved
            time.sleep(1.0)
            
            success=ADQAPI.ADQ_MultiRecordSetup(self.adq_cu,1,self.nrecords,self.nsamplesA)
            if (success == 0):
                self.f.write('Recording: ADQ_MultiRecordSetup failed.\n')
            else:
                self.f.write('Recording: ADQ_MultiRecordSetup SUCCESS.\n')
            self.f.write('bp7\n')
            
            acquiredrecord=0
            savestart= 0
            NumberOfRecords = self.nsaverecords
            ChannelsMask = 0xF
            StartSample = 0
            saveend=self.nsaverecords
            
            success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
            if (success == 0):
                 self.f.write('Recording: ADQ_DisarmTrigger failed.\n')
            success=ADQAPI.ADQ_ArmTrigger(self.adq_cu,1)
            if (success == 0):
                 self.f.write('Recording: ADQ_ArmTrigger failed.\n')
            
            i=0
            
            if self.acqmode==1:  #Average trace case
                while (acquiredrecord<self.nrecords):
                    
                    acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
                    
                    max_number_of_channels = 2
                    target_buffers=(POINTER(c_int16*self.nsamplesA*self.nsaverecords)*max_number_of_channels)()
                    for bufp in target_buffers:
                        bufp.contents = (c_int16*self.nsamplesA*self.nsaverecords)()
                    
                    #self.f.write('bp10; nofacq: %i\n' % acquiredrecord)
                    if (acquiredrecord>=saveend):
                        
                        savestart=saveend-self.nsaverecords
                        try:
                            ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                        
                            data_16bit_ch0 = np.reshape(np.frombuffer(target_buffers[0].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                            baselineCh0=np.median(data_16bit_ch0[:,:500],axis=1).astype(np.int64)
                            data_16bit_ch0=((data_16bit_ch0.T-baselineCh0).T)
                            data_16bit_ch0[data_16bit_ch0>=self.threshold]=0
                            
                            data_16bit_ch1 = np.reshape(np.frombuffer(target_buffers[1].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                            #baselineCh1=np.median(data_16bit_ch1[:,:500],axis=1)
                            #data_16bit_ch1=((data_16bit_ch1.T-baselineCh1).T)
                            #data_16bit_ch1[data_16bit_ch1>=self.threshold]=0
                            
                            self.data_chA+=(data_16bit_ch0).sum(0)
                            self.data_chB+=(data_16bit_ch1).sum(0)
                            
                        except:
                            self.f.write('failed recording average trace\n')
                            
                        i+=1
                        saveend+=self.nsaverecords
                        
                    self.progressrecords=(acquiredrecord/np.float(self.nrecords))*(j/len(self.dscanrange))
                        
                try:
                    avgscanA[idxdelay,:]=self.data_chA
                    avgscanB[idxdelay]=self.data_chB[:,ROIB[0]:ROIB[1]].sum(1)
                except:
                    self.f.write('failed building average scan\n')
                    
               
                
            else:  #Single Shot trace case (With Averaging)
                
                while (acquiredrecord<self.nrecords):
                    
                    acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
                    
                    max_number_of_channels = 2
                    
                    #target_headers=(POINTER(c_int64*self.nsaverecords))()
                    #for headp in target_headers:
                    #    headp.contents= (c_int64*self.nsaverecords)()
                    target_buffers=(POINTER(c_int16*self.nsamplesA*self.nsaverecords)*max_number_of_channels)()
                    for bufp in target_buffers:
                        bufp.contents = (c_int16*self.nsamplesA*self.nsaverecords)()
                        
                    header_list = (HEADER*self.nsaverecords)()
                    target_headers= ct.POINTER(HEADER*self.nsaverecords)()
                    target_headers.contents = header_list
                    target_header_vp = ct.cast(ct.pointer(target_headers), ct.POINTER(ct.c_void_p))
                    
                    #self.f.write('bp10; nofacq: %i\n' % acquiredrecord)
                    if (acquiredrecord>=saveend):
                        
                        savestart=saveend-self.nsaverecords
                    #print 'loop on data'
                        try:
                        
                         #ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                        
                            ADQAPI.ADQ_GetDataWHTS(self.adq_cu,1,
                                               target_buffers,
                                               target_headers,
                                               None,
                                               self.buffer_sizeA,
                                               self.bytes_per_sample,
                                               savestart,
                                               NumberOfRecords,
                                               ChannelsMask,
                                               StartSample,
                                               self.nsamplesA,
                                               0x00)
                            
                            data_16bit_ch0 = np.reshape(np.frombuffer(target_buffers[0].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                            data_16bit_ch1 = np.reshape(np.frombuffer(target_buffers[1].contents,dtype=np.int16),(self.nsaverecords,self.nsamplesA))
                            TS=np.array([target_headers[0][t].Timestamp*0.125*1e-3 for t in range(self.nsaverecords)])
                        
                            try:
                            
                                proc0=Thread(target=SaveDataThread,args=(data_16bit_ch0[:self.nsaverecords/4,:],data_16bit_ch1[:self.nsaverecords/4,:],TS[:self.nsaverecords/4],i+0,self.threshold,foldername,self.SAVESPARSE,ROIB,j))
                                proc1=Thread(target=SaveDataThread,args=(data_16bit_ch0[self.nsaverecords/4:2*self.nsaverecords/4,:],data_16bit_ch1[self.nsaverecords/4:2*self.nsaverecords/4,:],TS[self.nsaverecords/4:2*self.nsaverecords/4],i+1,self.threshold,foldername,self.SAVESPARSE,ROIB,j))
                                proc2=Thread(target=SaveDataThread,args=(data_16bit_ch0[2*self.nsaverecords/4:3*self.nsaverecords/4,:],data_16bit_ch1[2*self.nsaverecords/4:3*self.nsaverecords/4,:],TS[2*self.nsaverecords/4:3*self.nsaverecords/4],i+2,self.threshold,foldername,self.SAVESPARSE,ROIB,j))
                                proc3=Thread(target=SaveDataThread,args=(data_16bit_ch0[3*self.nsaverecords/4:self.nsaverecords,:],data_16bit_ch1[3*self.nsaverecords/4:self.nsaverecords,:],TS[3*self.nsaverecords/4:self.nsaverecords],i+3,self.threshold,foldername,self.SAVESPARSE,ROIB,j))
                                
                            except:
                                print 'error creating process'
                            try:
                                proc0.start()
                                proc1.start()
                                proc2.start()
                                proc3.start()
                                
                                proc0.join()
                                proc1.join()
                                proc2.join()
                                proc3.join()
                                
                            except:
                                print 'error running process'  
                                
                            self.data_chA+=data_16bit_ch0.sum(0)
                            self.data_chB+=(np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA))[:,self.ROIB[0]:self.ROIB[1]].sum(1)).sum()
                
                            
                            
                        except:
                            self.f.write('failed recording singleshot trace\n')
                                
                    i+=4
                    saveend+=self.nsaverecords
                    savedrecords+=self.nsaverecords
                    
                try:
                    avgscanA[self.idxdelay,:]=self.data_chA
                    avgscanA[self.idxdelay]=(self.data_chB[:,ROIB[0]:ROIB[1]].sum(1)).sum()
                except:
                    self.f.write('failed building average scan\n')
                    
                self.progressrecords=(acquiredrecord/np.float(self.nrecords))*(self.idxdelay/len(self.dscanrange))
                    
                
            #self.ProgressBar.setValue(np.round(100*j/np.float(len(self.dscanrange))))
                               
            
            #if self.acqmode==1:
            dataavg={'Scan_ChA':avgscanA, \
                                       'Scan_ChB':avgscanA,\
                                       'Delay':self.dscanrange}
    
            path_mat='%s/ScanAvg.mat' % (self.foldername)
            try:
                sio.savemat(path_mat,dataavg)
                    #path_npz='%s/ScanAvg.npz' % (foldername,i)
                    #np.savez(path_npz,**data)
            except:
                self.f.write('failed saving avg trace\n')
                
            return avgscanA,avgscanB,self.progressrecords
            
        success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        if (success == 0):
            self.f.write('Recording: ADQ_DisarmTrigger failed.\n')
        success=ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
        if (success == 0):
            self.f.write('Recording: ADQ_MultiRecordClose failed.\n')
            
        self.f.write('Acquisition finished at %s:%s:%s' % (str(dt.today().hour).zfill(2), \
                                                           str(dt.today().minute).zfill(2), \
                                                           str(dt.today().second).zfill(2)))
            
        self.progressflag=1
        #self.StopRecording
        
        
        
        if self.dscanmode==0:
            return((self.data_chA,self.data_chB,0))
        else:
            return (avgscanA,avgscanB,self.idxdelay)
        
##
    def StopRecording(self):
#        
        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);


    def StartStream(self):
        
        #self.nstreamrecords = 200
        max_number_of_channels = 2
        
        ## Initiate the data and header buffer
        
        
        #success = ADQAPI.ADQ_SetSampleSkip(self.adq_cu,1,0) 
        #if (success == 0):
        #    self.f.write('ADQ_SetSampleSkip failed.\n')
        
        success = ADQAPI.ADQ_SetTriggerMode(self.adq_cu,1, self.triggermode)
        if (success == 0):
           self.f.write('ADQ_SetTriggerMode failed.\n')
        
        if self.triggermode==1:
            success = ADQAPI.ADQ_SetLvlTrigLevel(self.adq_cu, 1, 0)
            if (success == 0):
                self.f.write('ADQ_SetLvlTrigLevel failed.\n')    
            success = ADQAPI.ADQ_SetTrigLevelResetValue(self.adq_cu, 1, 1000)
            if (success == 0):
                self.f.write('ADQ_SetTrigLevelResetValue failed.\n')    
            success = ADQAPI.ADQ_SetLvlTrigChannel(self.adq_cu, 1, 1)
            if (success == 0):
                self.f.write('ADQ_SetLvlTrigChannel failed.\n')    
            success = ADQAPI.ADQ_SetLvlTrigEdge(self.adq_cu, 1, self.trig_edge)
            if (success == 0):
                self.f.write('ADQ_SetLvlTrigEdge failed.\n')
        
        if self.triggermode==2:
            success = ADQAPI.ADQ_SetExtTrigThreshold(self.adq_cu,1,1,c_double(self.triglevel_mv/1000.0))
            if (success == 0):
                print 'ADQ_SetExternTrigLevel failed.\n'
            success = ADQAPI.ADQ_SetExternTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                print 'ADQ_SetExternTrigEdge failed.\n'
        
        if self.triggermode==3:
            triglvl=int(round(self.triglevel_mv*self.mv_conv))
            success = ADQAPI.ADQ_SetLvlTrigChannel(self.adq_cu,1, self.trigchannel)
            if (success == 0):
                print 'DParam: ADQ_SetLvlTrigChannel failed.\n'
            success = ADQAPI.ADQ_SetLvlTrigLevel(self.adq_cu,1, triglvl)
            if (success == 0):
                print 'DParam: ADQ_SetLvlTrigLevel failed.\n'
            success = ADQAPI.ADQ_SetLvlTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                print 'DParam: ADQ_SetLvlTrigEdge failed.\n'
                
        
        
        
        ## Prepare buffers
        self.target_buffers=(POINTER(c_int16*self.nsamplesA*self.nstreamrecords)*max_number_of_channels)()
        for bufp in self.target_buffers:
            bufp.contents = (c_int16*self.nsamplesA*self.nstreamrecords)()
        
        
    def RunStream(self):
        
        
        success=ADQAPI.ADQ_MultiRecordSetup(self.adq_cu,1,self.nstreamrecords,self.nsamplesA)
        if (success == 0):
            self.f.write('Recording: ADQ_Setup failed.\n')
            
        ## HOLD OFF
#        success=ADQAPI.ADQ_SetTriggerHoldOffSamples(ct.c_uint(self.holdoff_samples))
#        if success==0:
#            self.f.write('DParam: ADQ_SetTriggerHoldOffSamples failed.\n')
        
        success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        if (success == 0):
            self.f.write('Recording: ADQ_DisarmTrigger failed.\n')
        success=ADQAPI.ADQ_ArmTrigger(self.adq_cu,1)
        if (success == 0):
            self.f.write('Recording: ADQ_ArmTrigger failed.\n')
            
        header_list = (HEADER*self.nstreamrecords)()
        target_headers= ct.POINTER(HEADER*self.nstreamrecords)()
        target_headers.contents = header_list
        target_header_vp = ct.cast(ct.pointer(target_headers), ct.POINTER(ct.c_void_p))
        
        time.sleep(self.baserefreshrate)
#        self.buffers_filled.value = 0
#        collect_results = 1
        ChannelsMask = 0xf
        StartSample=0
        
        
        acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
        while (acquiredrecord<self.nstreamrecords):
            time.sleep(0.01)
            acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
        
        
        success=ADQAPI.ADQ_GetDataWHTS(self.adq_cu,1,
                                   self.target_buffers,
                                   target_headers,
                                   None,
                                   self.nsamplesA*self.nstreamrecords,
                                   self.bytes_per_sample,
                                   0,
                                   self.nstreamrecords,
                                   ChannelsMask,
                                   StartSample,
                                   self.nsamplesA,
                                   0x00)
        

        #print status
        if (success == 0):
            print('Data grab failed\n')
           
        data_16bit_ch0 = np.frombuffer(self.target_buffers[0].contents,dtype=np.int16).reshape(self.nstreamrecords,self.nsamplesA).copy()#[:self.nsamplesA]
        data_16bit_ch1 = np.frombuffer(self.target_buffers[1].contents,dtype=np.int16).reshape(self.nstreamrecords,self.nsamplesA).copy()#[:self.nsamplesA]
        
        data_16bit_ch0[data_16bit_ch0>self.threshold]=0
        data_16bit_ch1[data_16bit_ch1>self.threshold]=0
        
        Tstamps=[]
        
        for i in range(self.nstreamrecords):
            Tstamps.append(target_headers[0][i].Timestamp*0.125*1e-3)
        
        Tavg=np.array(Tstamps).mean()
        
        #baselineCh0 = np.median(data_16bit_ch0[:500]).astype(np.int16)
        #baselineCh1 = np.median(data_16bit_ch1[:500]).astype(np.int16)
        
#        header=[]
#        for i in range(self.nstreamrecords):
#            header.append(self.headerbuf_list[0][i].Timestamp*0.125*1e-3)


        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
        
        
        #print data_16bit_ch0.shape
        
        return data_16bit_ch0.mean(0),data_16bit_ch1.mean(0),Tavg
    
    
    
#        ChannelsMask = 0xF  
#        StartSample = 0
#        
#        target_buffersStream=(POINTER(c_int16*self.nsamplesA*Navg)*2)()
#        for bufp in target_buffersStream:
#            bufp.contents = (c_int16*self.nsamplesA*Navg)()
#        
#        #if Navg<=1000:
#        time.sleep(self.baserefreshrate)
#        #else:
#        #time.sleep(self.baserefreshrate*(np.floor(Navg/1000)+1))
#            
#        source_bufferStream=Navg*self.nsamplesA   
#        try:
#            self.data_chA=np.zeros((self.nsamplesA),dtype=np.int64)
#            self.data_chB=np.zeros((self.nsamplesA),dtype=np.int64)
#        except:
#            self.f.write('Initialisation of average trace failed.\n')
#        
#        try:
#            
#            success=ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffersStream,source_bufferStream,self.bytes_per_sample,0,Navg,ChannelsMask,StartSample,self.nsamplesA,0x00)
#            
#            data_16bit_ch0 = np.reshape(np.frombuffer(target_buffersStream[0].contents,dtype=np.int16),(Navg,self.nsamplesA))
#            data_16bit_ch1 = np.reshape(np.frombuffer(target_buffersStream[1].contents,dtype=np.int16),(Navg,self.nsamplesA))
#
#            if Navg==1:
#                baselineCh0=np.median(data_16bit_ch0[:,:500],axis=1).astype(np.int64)
#                data_16bit_ch0=(data_16bit_ch0-baselineCh0)
#                data_16bit_ch0[data_16bit_ch0>=self.threshold]=0
#                self.data_chA=(data_16bit_ch0).sum(0)
#                
#                baselineCh1=np.median(data_16bit_ch1[:,:500],axis=1).astype(np.int64)
#                data_16bit_ch1=(data_16bit_ch1-baselineCh1)
#                data_16bit_ch1[data_16bit_ch1>=self.threshold]=0
#                self.data_chB=(data_16bit_ch1).sum(0)
#            else:
#                baselineCh0=np.median(data_16bit_ch0[:,:500],axis=1).astype(np.int64)
#                data_16bit_ch0=((data_16bit_ch0.T-baselineCh0).T)
#                data_16bit_ch0[data_16bit_ch0>=self.threshold]=0
#                self.data_chA=(data_16bit_ch0).sum(0)/np.float(Navg)
#            
#                baselineCh1=np.median(data_16bit_ch1[:,:500],axis=1).astype(np.int64)
#                data_16bit_ch1=((data_16bit_ch1.T-baselineCh1).T)
#                data_16bit_ch1[data_16bit_ch1>=self.threshold]=0
#                self.data_chB=(data_16bit_ch1).sum(0)/np.float(Navg)
#            
#            if success==0:
#                    self.data_chA = np.zeros((self.nsamplesA),dtype=np.int64)
#                    self.data_chB = np.zeros((self.nsamplesA),dtype=np.int64)
#
#        except:
#            self.data_chA = np.zeros((self.nsamplesA),dtype=np.int64)
#            self.data_chB = np.zeros((self.nsamplesA),dtype=np.int64)
#            self.f.write('error reading buffer\n')
#            
#        if len(self.data_chA)==0 or len(self.data_chB)==0:
#            self.data_chA = np.zeros((self.nsamplesA),dtype=np.int64)
#            self.data_chB = np.zeros((self.nsamplesA),dtype=np.int64)
#
#            
        
#        
    def StopStream(self):
 
        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
       
