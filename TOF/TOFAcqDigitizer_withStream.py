import scipy.io as sio
import math
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from matplotlib import pyplot as plt

from datetime import datetime
from PI_E750_CP_piezostageFunction import PI_E750_CP_piezostageFunction as dstage

import time
import os

from ctypes import *

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



class TOFAcqDigitizer():

    def __init__(self,f):
        
        self.f=f
        self.ProgressBar=[]
        
        # Conversion factors
        self.mv_conv=(2**16)/300.0
        self.ns_conv=2
        
        #Acquisition parameters
        self.acqmode=1 # Choose either SINGLE_SHOT(0) or WAVEFORM_AVG(1)
        self.ltofA=5000 # %Record length per shot in ns
        self.ltofB=100 # %Record length per shot in ns
        self.analogbiasA_mv = 0.0 # Adjustable analog bias (DC offset) in mV. Range is +/-150mV
        self.analogbiasA=np.round(self.analogbiasA_mv*self.mv_conv)
        self.analogbiasB_mv =0.0 # Adjustable analog bias (DC offset) in mV. Range is +/-150mV
        self.analogbiasB=np.round(self.analogbiasB_mv*self.mv_conv)
        self.channel=2

        #Delay Scan parameters

        self.dscanmode=0
        self.dscanstart=0
        self.dscanstop=80
        self.dscanstep=1
        self.dscanrange=np.arange(self.dscanstart,self.dscanstop,self.dscanstep)
        
        # Recording options
        
        self.nbuffrecords=2 # Number of buffer records
        self.nrecords=10000 # Number of records per sample
        self.nsaverecords=1000
        self.nsamplesA=self.ltofA*2 #samples per buffer record
        self.nsamplesB=self.ltofB*2 #samples per buffer record
        self.buffer_sizeA = self.nsaverecords*self.nsamplesA
        self.buffer_sizeB = self.nsaverecords*self.nsamplesB
        self.bytes_per_sample = 2
        
        # Trigger options
        self.triggermode=2 # choose: 'CH_A(3)','CH_B(3)' or 'EXTERNAL_TRIGGER (2)'
        self.trigchannel=1 # Choose 'CH_A(1)','CH_B(2)' 
        self.trig_edge = 1 #RISING_EDGE(1) or FALLING EDGE(0)
        self.triglevel_mv =-0.7 #Trigger threshold in mV => For a level trigger this must be in the range +/-150mV. For external trigger this must be in the range -500mV to +3300mV.
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
        
       
        
        if (n_of_ADQ14 != 0):
            self.f.write('found ADQ device')
            #ADQAPI.ADQControlUnit_EnableErrorTraceAppend(self.adq_cu,3,'C:/Documents/...')
            self.f.write('enable ADQ log trace')
            
            
    def __del__(self):
        success = ADQAPI.DeleteADQControlUnit(self.adq_cu)
        if (success == 0):
            self.f.write('Delete ADQ control failed.\n')
        self.f.close()
# GUI interaction functions
            
    def setDigitizerParameters(self,ParametersArray):
         self.f.write('set Dig Params0\n')
                  
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
         
         self.f.write('nsamplesA: %i, nrecords: %i, buffer size: %i, channel: %i, Triggermode:%i, dscanmode: %i, acqmode: %i\n'\
                 % (self.nsamplesA,self.nrecords,self.buffer_sizeA,self.channel,self.triggermode,self.dscanmode,self.acqmode))

    def StartRecording(self,foldername):
        
        #StartProgressBar()        
        
        try:
            self.ProgressBar=QtGui.QProgressDialog('Acquisition in progress','Abort',0,100)
            self.ProgressBar.show()
            self.ProgressBar.setValue(0)
        except:
            print 'ERROR starting progress bar dialog box'
        
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
        
        if self.triggermode==2:
            success = ADQAPI.ADQ_SetExtTrigThreshold(self.adq_cu,1,1,c_double(0.5))
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
                    
        ### DSCAN OFF ###

        if self.dscanmode==0:
            if self.acqmode==1:
                try:
                    avgtraceA=np.zeros((self.nsamplesA),dtype=np.int64)
                    avgtraceB=np.zeros((self.nsamplesA),dtype=np.int64)
                except:
                    self.f.write('Initialisation of average trace failed.\n') 
            
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
                        try:
                            
                            ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                            data_16bit_ch0 = np.frombuffer(target_buffers[0].contents,dtype=np.int16)
                            data_16bit_ch0[data_16bit_ch0>=-200]=0
                            data_16bit_ch1 = np.frombuffer(target_buffers[1].contents,dtype=np.int16)
                            avgtraceA+=np.reshape(data_16bit_ch0,(self.nsaverecords,self.nsamplesA)).sum(0)
                            avgtraceB+=np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA)).sum(0)
                            
                        except:
                            self.f.write('failed recording average trace\n')
                        i+=1
                        saveend+=self.nsaverecords

                    self.ProgressBar.setValue(np.round(100*aquiredrecord/np.float(self.nrecords)))                    
                    
                data={'wf_ChA':avgtraceA,'wf_ChB':avgtraceB}
    
                path_mat='%s/WaveformAvg.mat' % (foldername)
                try:
                    sio.savemat(path_mat,data)
                    #path_npz='%s/WaveformAvg.npz' % (foldername,i)
                    #np.savez(path_npz,**data)
                except:
                    self.f.write('failed saving average trace\n')
                    
            else:
                
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
                        
                            ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,target_headers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                            data_16bit_ch0 = np.frombuffer(target_buffers[0].contents,dtype=np.int16)
                            data_16bit_ch1 = np.frombuffer(target_buffers[1].contents,dtype=np.int16)
                            #timestamps=np.frombuffer(target_headers.Timestamp,dtype=np.int64)
                            data={'specmat_ChA':data_16bit_ch0,'specmat_ChB':data_16bit_ch1}#,'timestamps':timestamps}

                            path_mat='%s/specfile_%s.mat' % (foldername,str(i).zfill(3))
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

                    self.ProgressBar.setValue(np.round(100*aquiredrecord/np.float(self.nrecords))) 
                        
                        
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
                dstage('//155.198.197.13/CEP_remotecontrol/',delayval)
                if self.acqmode==0:
                    if not os.path.exists('%s/SSdelay%s' % (foldername,str(j).zfill(2))):
                        os.makedirs('%s/SSdelay%s' % (foldername,str(j).zfill(2)))
                
                #if self.acqmode==1:
                try:
                    avgtraceA=np.zeros((self.nsamplesA),dtype=np.int64)
                    avgtraceB=np.zeros((self.nsamplesA),dtype=np.int64)
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
                            try:
                                ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffers,self.buffer_sizeA,self.bytes_per_sample,savestart,NumberOfRecords,ChannelsMask,StartSample,self.nsamplesA,0x00)
                            
                                data_16bit_ch0 = np.frombuffer(target_buffers[0].contents,dtype=np.int16)
                                data_16bit_ch0[data_16bit_ch0>=-150]=0
                                data_16bit_ch1 = np.frombuffer(target_buffers[1].contents,dtype=np.int16)
                                avgtraceA+=np.reshape(data_16bit_ch0,(self.nsaverecords,self.nsamplesA)).sum(0)
                                avgtraceB+=np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA)).sum(0)
                            except:
                                self.f.write('failed recording average trace\n')
                            i+=1
                            saveend+=self.nsaverecords
                            
                    try:
                        avgscanA[j,:]=avgtraceA
                        avgscanB[j,:]=avgtraceB
                    except:
                        self.f.write('failed building average scan\n')
                else:
                    
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
                                tmp=data_16bit_ch0
                                tmp[tmp>=-150]=0
                                avgtraceA+=np.reshape(tmp,(self.nsaverecords,self.nsamplesA)).sum(0)
                                avgtraceB+=np.reshape(data_16bit_ch1,(self.nsaverecords,self.nsamplesA)).sum(0)
                                
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
                        avgscanA[j,:]=avgtraceA
                        avgscanB[j,:]=avgtraceB
                    except:
                        self.f.write('failed building average scan\n')
                            
                self.ProgressBar.setValue(np.round(100*j/np.float(len(self.dscanrange))))
                                   
                
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
        self.ProgressBar.hide()
##
    def StopRecording(self):
#        
        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
#        

    def StartStream(self):
        
        success = ADQAPI.ADQ_SetSampleSkip(self.adq_cu,1,0) 
        if (success == 0):
           print 'ADQ_SetSampleSkip failed.'
        
        success = ADQAPI.ADQ_SetTriggerMode(self.adq_cu,1, self.triggermode)
        if (success == 0):
            print 'ADQ_SetTriggerMode failed.'
        
        
        if self.triggermode==2:
            success = ADQAPI.ADQ_SetExtTrigThreshold(self.adq_cu,1,1,c_double(0.5))
            if (success == 0):
                print 'ADQ_SetExternTrigLevel failed.'
            success = ADQAPI.ADQ_SetExternTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                print 'ADQ_SetExternTrigEdge failed.'
        
        if self.triggermode==3:
            triglvl=int(round(self.triglevel_mv*self.mv_conv))
            success = ADQAPI.ADQ_SetLvlTrigChannel(self.adq_cu,1, self.trigchannel)
            if (success == 0):
                print 'DParam: ADQ_SetLvlTrigChannel failed.'
            success = ADQAPI.ADQ_SetLvlTrigLevel(self.adq_cu,1, triglvl)
            if (success == 0):
                print 'DParam: ADQ_SetLvlTrigLevel failed.'
            success = ADQAPI.ADQ_SetLvlTrigEdge(self.adq_cu,1, self.trig_edge)
            if (success == 0):
                print 'DParam: ADQ_SetLvlTrigEdge failed.'
        
        
       
            
    def UpdateStream(self):
        
        success=ADQAPI.ADQ_MultiRecordSetup(self.adq_cu,1,2,self.nsamplesA)
        if (success == 0):
            print 'Recording: ADQ_MultiRecordSetup failed'
        else:
            print 'Recording: ADQ_MultiRecordSetup SUCCESS'        
        
        success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        if (success == 0):
            print 'Recording: ADQ_DisarmTrigger failed.'
        success=ADQAPI.ADQ_ArmTrigger(self.adq_cu,1)
        if (success == 0):
            print 'Recording: ADQ_ArmTrigger failed'
            
        #ChannelsMask = 0xF  
        #ADQAPI.ADQ_TriggeredStreamingSetup(self.adq_cu,1,10,self.nsamplesA,0,0,ChannelsMask)

        #ADQAPI.ADQ_SetStreamStatus(self.adq_cu,1, 1);
        # Get number of channels from device
        #number_of_channels = ADQAPI.ADQ_GetNofChannels(self.adq_cu,1)

        # Setup size of transfer buffers
        #print('Setting up streaming...')
        #ADQAPI.ADQ_SetTransferBuffers(self.adq_cu,1,8, 65536)

        # Start streaming
        #print('Collecting data, please wait...')
        #ADQAPI.ADQ_StopStreaming(self.adq_cu,1)
        #ADQAPI.ADQ_StartStreaming(self.adq_cu,1)
    #def UpdateStream(self):
        print 'teststream'
        
        
        ChannelsMask = 0xF  
        StartSample = 0
        
        #data_16bit_ch0=np.array([],dtype=np.int16)
        #data_16bit_ch1=np.array([],dtype=np.int16)
        target_buffersStream=(POINTER(c_int16*self.nsamplesA)*2)()
        for bufp in target_buffersStream:
            bufp.contents = (c_int16*self.nsamplesA)()
        
        time.sleep(0.01)
        try:
            success=ADQAPI.ADQ_GetData(self.adq_cu,1,target_buffersStream,self.buffer_sizeA,self.bytes_per_sample,0,1,ChannelsMask,StartSample,self.nsamplesA,0x00)
            acquiredrecord=ADQAPI.ADQ_GetAcquiredRecords(self.adq_cu,1)
            if acquiredrecord>1:
                if success==0:
                    data_16bit_ch0 = np.zeros((self.nsamplesA),dtype=np.int16)
                    data_16bit_ch1 = np.zeros((self.nsamplesA),dtype=np.int16)
                else:
                    data_16bit_ch0 = np.frombuffer(target_buffersStream[0].contents,dtype=np.int16)
                    data_16bit_ch1 = np.frombuffer(target_buffersStream[1].contents,dtype=np.int16)
            else:
                data_16bit_ch0 = np.zeros((self.nsamplesA),dtype=np.int16)
                data_16bit_ch1 = np.zeros((self.nsamplesA),dtype=np.int16)
        except:
            
            data_16bit_ch0 = np.zeros((self.nsamplesA),dtype=np.int16)
            data_16bit_ch1 = np.zeros((self.nsamplesA),dtype=np.int16)
            print 'error reading buffer'
            
        if len(data_16bit_ch0)==0 or len(data_16bit_ch1)==0:
            data_16bit_ch0 = np.zeros((self.nsamplesA),dtype=np.int16)
            data_16bit_ch1 = np.zeros((self.nsamplesA),dtype=np.int16)
            
        ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
            
        del target_buffersStream
        return data_16bit_ch0,data_16bit_ch1
        
    def StopStream(self):
        print 'teststream'
        
        success=ADQAPI.ADQ_DisarmTrigger(self.adq_cu,1)
        ADQAPI.ADQ_MultiRecordClose(self.adq_cu,1);
        if (success == 0):
           print 'Recording: ADQ_DisarmTrigger failed.'
        #success=ADQAPI.ADQ_StopStreaming(self.adq_cu,1)
        #if (success == 0):
        #    print 'Recording: ADQ_DisarmTrigger failed.'
#   #

#f=open(thislogfilename,'w')
#TAQD=TOFAcqDigitizer(f)
#TAQD.StartRecording('D:/labdata/2016/20160410_Isopropanol')
#f.close()
