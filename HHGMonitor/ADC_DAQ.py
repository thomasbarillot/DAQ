import scipy.io as sio
import math
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from matplotlib import pyplot as plt

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
        #self.ProgressBar=[]
        
        # Conversion factors
        self.mv_conv=(2**16)/300.0
        self.ns_conv=2
        
        #Acquisition parameters
        self.acqmode=1 # Choose either SINGLE_SHOT(0) or WAVEFORM_AVG(1)
        self.ltofA=2000 # %Record length per shot in ns
        self.ltofB=2000 # %Record length per shot in ns
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
        self.headerbufp_list = 0
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
        
        # Recording options
        
        self.nbuffrecords=2 # Number of buffer records
        self.nrecords=1000 # Number of records per sample
        self.nstreamrecords = 100
        self.nsaverecords=1000
        self.progressrecords=0.0000001
        self.progressflag=0
        self.nsamplesA=self.ltofA*2 #samples per buffer record
        self.nsamplesB=self.ltofB*2 #samples per buffer record
        self.buffer_sizeA = self.nsaverecords*self.nsamplesA
        self.buffer_sizeB = self.nsaverecords*self.nsamplesB
        
        
        self.bytes_per_sample = 2  #2 for 16bits
        
        self.data_chA=np.zeros((self.nsamplesA)).astype(np.int64)
        self.data_chB=np.zeros((self.nsamplesA)).astype(np.int64)
        
        # Trigger options
        self.triggermode=2 # choose: 'CH_A(3)','CH_B(3)' or 'EXTERNAL_TRIGGER (2) or SOFTWARE_TRIGGER (1)'
        self.trigchannel=1 # Choose 'CH_A(1)','CH_B(2)' 
        self.trig_edge = 1 #RISING_EDGE(1) or FALLING EDGE(0)
        self.triglevel_mv =500.0 #Trigger threshold in mV => For a level trigger this must be in the range +/-150mV. For external trigger this must be in the range -500mV to +3300mV.
        self.record_start_shift = 'NONE' #choose 'PRETRIGGER', 'HOLDOFF' OR 'NONE'
        self.pretrigger_ns=0 #only applicable if 'PRETRIGGER' is selected.
        self.holdoff_ns=0 #only applicable if 'HOLDOFF' is selected.
        
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

            
    def setDigitizerParameters(self,ParametersArray):
         self.f.write('set Dig Params\n')
                  
         self.nsamplesA=ParametersArray[0]*2
         self.nrecords=ParametersArray[1] # Number of records per sample

         self.buffer_sizeA = self.nsaverecords*self.nsamplesA
#        
         self.channel=ParametersArray[2]
         self.triggermode=ParametersArray[3]
#        
         self.dscanmode=ParametersArray[4]
         self.dscanstart=ParametersArray[5]
         self.dscanstop=ParametersArray[6]
         self.dscanstep=ParametersArray[7]
         
         self.acqmode=ParametersArray[8]
         
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
         if (ParametersArray[15]!=self.holdoff_ns and ParametersArray[15]!=0):
             self.holdoff_ns=ParametersArray[15]
             self.f.write('Hold off val:%i\n'%self.holdoff_ns)
         else:
             self.holdoff_ns=0
           
         self.f.write('nsamplesA: %i, nrecords: %i, buffer size: %i, channel: %i, Triggermode:%i, dscanmode: %i, acqmode: %i\n'\
                 % (self.nsamplesA,self.nrecords,self.buffer_sizeA,self.channel,self.triggermode,self.dscanmode,self.acqmode))

    def StartRecording(self,foldername):
        
        #StartProgressBar()        
        
        #try:
            #self.ProgressBar=QtGui.QProgressDialog('Acquisition in progress','Abort',0,100)
            #self.ProgressBar.show()
            #self.ProgressBar.setValue(0)
        #except:
            #print 'ERROR starting progress bar dialog box'
        
        success = ADQAPI.ADQ_SetSampleSkip(self.adq_cu,1,1)
        if (success == 0):
            self.f.write('ADQ_SetSampleSkip failed.\n')
        self.f.write('bp3\n')
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
                 
                
        ### HOLDOFF SAMPLES ###
        
        #HOLDOFFSAMPLE=int(self.holdoff_ns*2)
        #success=ADQAPI.ADQ_SetTriggerHoldOffSamples(ct.c_uint(self.holdoff_ns*2))
        #if success==0:
        #    self.f.write('DParam: ADQ_SetTriggerHoldOffSamples failed.\n')
        
        ### REINIT THE SIZE OF THE DATA STORAGE FOR CHA AND B
        self.data_chA=np.zeros((self.nsamplesA),dtype=np.int64)
        self.data_chB=np.zeros((self.nsamplesA),dtype=np.int64)
        self.progressrecords=0.0000001
        self.progressflag=0
        
        ### DSCAN OFF ###

        if self.dscanmode==0:
            try:
                avgtraceA=np.zeros((self.nsamplesA),dtype=np.int64)
                avgtraceB=np.zeros((self.nsamplesA),dtype=np.int64)
            except:
                self.f.write('Initialisation of average scan matrix failed.\n') 
            
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
                        self.data_chB+=np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA)).sum(0)
                    
                        #except:
                        #    self.f.write('failed recording average trace\n')
                        i+=1
                        saveend+=self.nsaverecords
                    
                    self.progressrecords=acquiredrecord/np.float(self.nrecords)
                    #self.ProgressBar.setValue(np.round(100*acquiredrecord/np.float(self.nrecords)))                    
                
                dataavg={'Scan_ChA':self.data_chA, \
                                           'Scan_ChB':self.data_chB}
                
    
                path_mat='%s/ScanAvg.mat' % (foldername)
                try:
                    sio.savemat(path_mat,dataavg)

                except:
                    self.f.write('failed saving average trace\n')
                    
            else:
                
                if not os.path.exists('%s/SShot' % (foldername)):
                    os.makedirs('%s/SShot' % (foldername))
                
                while (acquiredrecord<self.nrecords):
                    
                    acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
                    
                    max_number_of_channels = 2
                    #target_headers=(POINTER(c_int64*self.nsaverecords))()
                    #for headp in target_headers:
                    #    headp.contents= (c_int64*self.nsaverecords)()
                    target_buffers=(POINTER(c_int16*self.nsamplesA*self.nsaverecords)*max_number_of_channels)()
                    for bufp in target_buffers:
                        bufp.contents = (c_int16*self.nsamplesA*self.nsaverecords)()

                    #self.f.write('bp10; nofacq: %i\n' % acquiredrecord)
                    if (acquiredrecord>=saveend):
                        
                        savestart=saveend-self.nsaverecords
                        try:
                        
                            ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                            data_16bit_ch0 = np.frombuffer(target_buffers[0].contents,dtype=np.int16)
                            data_16bit_ch1 = np.frombuffer(target_buffers[1].contents,dtype=np.int16)
                            
                            tmp=np.copy(data_16bit_ch0)
                            tmp=np.reshape(tmp,(self.nsaverecords,self.nsamplesA))
                            baseline_tmp=np.median(tmp[:,:500],axis=1).astype(np.int64)
                            tmp=((tmp.T-baseline_tmp).T)
                            tmp[tmp>=self.threshold]=0
                            self.data_chA+=tmp.sum(0)
                            self.data_chB+=np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA)).sum(0)
                            
                            
                            data={'specmat_ChA':data_16bit_ch0,'specmat_ChB':data_16bit_ch1}#,'timestamps':timestamps}
                            

                            path_mat='%s/SShot/specfile_%s.mat' % (foldername,str(i).zfill(3))
                            #path_npz='%s/specfile_%i.npz' % (foldername,i)
                            try:
                                sio.savemat(path_mat,data)
                                #np.savez(path_npz,**data)
                            except:
                                self.f.write('failed saving singleshot trace\n')
                        except:
                                self.f.write('failed recording singleshot trace\n')
                        i+=1
                        saveend+=self.nsaverecords

                    self.progressrecords=acquiredrecord/np.float(self.nrecords)
                    #self.ProgressBar.setValue(np.round(100*acquiredrecord/np.float(self.nrecords))) 
                
                dataavg={'Scan_ChA':self.data_chA, \
                                           'Scan_ChB':self.data_chB}

                path_mat='%s/ScanAvg.mat' % (foldername)
                try:
                    sio.savemat(path_mat,dataavg)

                except:
                    self.f.write('failed saving average trace\n')
                        
            success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
            if (success == 0):
                 self.f.write('Recording: ADQ_DisarmTrigger failed.\n')
            success=ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
            if (success == 0):
                 self.f.write('Recording: ADQ_MultiRecordClose failed.\n')
                 
            self.f.write('Acquisition finished at %s:%s:%s' % (str(dt.today().hour).zfill(2), \
                                                               str(dt.today().minute).zfill(2), \
                                                               str(dt.today().second).zfill(2)))
            
### DSCAN ON ###
        elif self.dscanmode==1:
            
            #if self.acqmode==1:
            try:
                avgscanA=np.zeros((len(self.dscanrange),self.nsamplesA),dtype=np.int64)
                avgscanB=np.zeros((len(self.dscanrange),self.nsamplesA),dtype=np.int64)
            except:
                self.f.write('Initialisation of average scan matrix failed.\n')
            
            for j,delayval in enumerate(self.dscanrange):
                
                # Change the delay on the delaystage (humongium computer)
                #dstage('//155.198.197.13/CEP_remotecontrol/',delayval)
                if self.acqmode==0:
                    if not os.path.exists('%s/SSdelay%s' % (foldername,str(j).zfill(2))):
                        os.makedirs('%s/SSdelay%s' % (foldername,str(j).zfill(2)))
                
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
                        avgscanA[j,:]=self.data_chA
                        avgscanB[j,:]=self.data_chB
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
                        
                        #self.f.write('bp10; nofacq: %i\n' % acquiredrecord)
                        if (acquiredrecord>=saveend):
                            
                            savestart=saveend-self.nsaverecords
                            try:
                                ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                                data_16bit_ch0 = np.frombuffer(target_buffers[0].contents,dtype=np.int16)
                                data_16bit_ch1 = np.frombuffer(target_buffers[1].contents,dtype=np.int16)
                                
                                tmp=np.copy(data_16bit_ch0)
                                tmp=np.reshape(tmp,(self.nsaverecords,self.nsamplesA))
                                baseline_tmp=np.median(tmp[:,:500],axis=1).astype(np.int64)
                                tmp=((tmp.T-baseline_tmp).T)
                                tmp[tmp>=self.threshold]=0
                                self.data_chA+=tmp.sum(0)
                                self.data_chB+=np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA)).sum(0)
                                
                                #timestamps=np.frombuffer(target_headers.Timestamp,dtype=np.int64)
                                data={'specmat_ChA':data_16bit_ch0,'specmat_ChB':data_16bit_ch1}#'timestamps':timestamps}
                                
                                path_mat='%s/SSdelay%s/specfile_%s.mat' % (foldername,str(j).zfill(2),str(i).zfill(3))
                                #path_npz='%s/SSdelay%i/specfile_%i.npz' % (foldername,j,i)
                                try:
                                    sio.savemat(path_mat,data)
                                    #np.savez(path_npz,**data)
                                except:
                                    self.f.write('failed saving singleshot trace\n')
                            except:
                                self.f.write('failed recording singleshot trace\n')
                            i+=1
                            saveend+=self.nsaverecords
                        
                    try:
                        avgscanA[j,:]=self.data_chA
                        avgscanB[j,:]=self.data_chB
                    except:
                        self.f.write('failed building average scan\n')
                        
                    self.progressrecords=(acquiredrecord/np.float(self.nrecords))*(j/len(self.dscanrange))
                            
                #self.ProgressBar.setValue(np.round(100*j/np.float(len(self.dscanrange))))
                                   
                
                #if self.acqmode==1:
                dataavg={'Scan_ChA':avgscanA, \
                                           'Scan_ChB':avgscanB,\
                                           'Delay':self.dscanrange}
        
                path_mat='%s/ScanAvg.mat' % (foldername)
                try:
                    sio.savemat(path_mat,dataavg)
                        #path_npz='%s/ScanAvg.npz' % (foldername,i)
                        #np.savez(path_npz,**data)
                except:
                    self.f.write('failed saving avg trace\n')
                
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
        self.StopRecording
##
    def StopRecording(self):
#        
        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
#        

    def StartStream(self):
        
        self.nstreamrecords = 100
        max_number_of_channels = 2
        
        ## Initiate the data and header buffer
        
        
        success = ADQAPI.ADQ_SetSampleSkip(self.adq_cu,1,0) 
        if (success == 0):
            self.f.write('ADQ_SetSampleSkip failed.\n')
        
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
                
                
                
        ADQAPI.ADQ_TriggeredStreamingSetup(self.adq_cu,1,self.nstreamrecords,self.nsamplesA,0,0,0xf)
        
        ADQAPI.ADQ_SetTransferBuffers(self.adq_cu,1,8,131072*8)
        
        self.target_buffers=(POINTER(c_int16*self.nsamplesA*self.nstreamrecords)*max_number_of_channels)()
        for bufp in self.target_buffers:
            bufp.contents = (c_int16*self.nsamplesA*self.nstreamrecords)()
        
        self.headerbuf_list = [(HEADER*self.nstreamrecords)() for ch in range(max_number_of_channels)]
        # Create an C array of pointers to header buffers
        self.headerbufp_list = ((ct.POINTER(HEADER*self.nstreamrecords))*max_number_of_channels)()
        # Initiate pointers with allocated header buffers
        for ch,headerbufp in enumerate(self.headerbufp_list):
            headerbufp.contents = self.headerbuf_list[ch]
            
        # Allocate length output variable
        self.samples_added = (4*ct.c_uint)()
        for ind in range(len(self.samples_added)):
            self.samples_added[ind] = 0
  
        self.headers_added = (4*ct.c_uint)()
        for ind in range(len(self.headers_added)):
            self.headers_added[ind] = 0

        self.header_status = (4*ct.c_uint)()
        for ind in range(len(self.header_status)):
            self.header_status[ind] = 0
                
        
        #print 'Start Streaming.\n'
        ADQAPI.ADQ_StopStreaming(self.adq_cu,1)
        if (success == 0):
            print('Stop Streaming failed\n')
        success=ADQAPI.ADQ_StartStreaming(self.adq_cu,1)
        if (success == 0):
            print('Start Streaming failed\n')
        
        
    def RunStream(self):
        
        
        
        self.buffers_filled.value = 0
        collect_results = 1
        ChannelsMask = 0xf  
        
        #if ADQAPI.ADQ_GetStreamOverflow()==1:
        poll_time_diff_prev = time.time()
        while ((self.buffers_filled.value==0) and (collect_results)):
            collect_results = ADQAPI.ADQ_GetTransferBufferStatus(self.adq_cu,1,ct.byref(self.buffers_filled))
            poll_time_diff=time.time()-poll_time_diff_prev
            
            if poll_time_diff>0.05:
                
                ADQAPI.ADQ_FlushDMA(self.adq_cu,1)
                poll_time_diff_prev=time.time()
        
        status = ADQAPI.ADQ_GetDataStreaming(self.adq_cu,1,\
                                             self.target_buffers,\
                                             self.headerbufp_list,\
                                             0xf,\
                                             ct.byref(self.samples_added),\
                                             ct.byref(self.headers_added),\
                                             ct.byref(self.header_status))
        #print status
        if (status == 0):
            print('Data grab failed\n')
           
        data_16bit_ch0 = np.frombuffer(self.target_buffers[0].contents,dtype=np.int16).reshape(self.nstreamrecords,self.nsamplesA).copy()#[:self.nsamplesA]
        data_16bit_ch1 = np.frombuffer(self.target_buffers[1].contents,dtype=np.int16).reshape(self.nstreamrecords,self.nsamplesA).copy()#[:self.nsamplesA]
        
        baselineCh0 = np.median(data_16bit_ch0[:500]).astype(np.int16)
        baselineCh1 = np.median(data_16bit_ch1[:500]).astype(np.int16)
        
        header=[]
        for i in range(self.nstreamrecords):
            header.append(self.headerbuf_list[0][i].Timestamp*0.125*1e-3)
   
        return data_16bit_ch0.mean(0),data_16bit_ch1.mean(0),header
    
    
    
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
#        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
#        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
#        
    def StopStream(self):
 
        ADQAPI.ADQ_StopStreaming(self.adq_cu,1)
        success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
       