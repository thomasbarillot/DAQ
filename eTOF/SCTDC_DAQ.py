# -*- coding: utf-8 -*-
"""
Éditeur de Spyder

Ceci est un script temporaire.
"""

from ctypes import *
from ctypes.wintypes import *

import win32file
import win32pipe
from pywin32_testutil import str2bytes

import numpy as np
import struct

import time

global lpszPipename 
lpszPipename = u'\\\\.\\pipe\\scTDCserver'


class SCTDC_DAQ():
    
    def __init__(self):
        
        self.pipename = u'\\\\.\\pipe\\scTDCserver'
        self.hpipe=[]
        
        
    def __del__(self):
        
        #↨try:
        #    win32pipe.DisconnectNamedPipe(self.hpipe)
        #except:
        #    print 'error Disconnecting pipe handle'
        try:
            win32file.CloseHandle(self.hpipe)
        except:
            print 'error Releasing pipe handle'
            
    def DisconnectSCTDC(self):
        try:
            win32file.CloseHandle(self.hpipe)
        except:
            print 'error Releasing pipe handle'
        

    def ConnectSCTDC(self):
    
        self.hpipe=win32file.CreateFile(self.pipename,
                                   win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                   0,
                                   None,
                                   win32file.OPEN_EXISTING,
                                   0,
                                   None)
        
        if (self.hpipe == win32file.INVALID_HANDLE_VALUE):
            
            print "Create File failed" 
            return -1
        

    def SCTDCStart(self,acqtime):
        
        BUFFSIZE=1024*1024
        target_buffer=POINTER(c_char*BUFFSIZE)()
        target_buffer.contents=(c_char*BUFFSIZE)()
        
        read_buffer=POINTER(c_char*BUFFSIZE)()
        read_buffer.contents=(c_char*BUFFSIZE)()
        
        mybuffer=win32file.AllocateReadBuffer(1024*1024)
        
        win32pipe.SetNamedPipeHandleState(self.hpipe,win32pipe.PIPE_READMODE_MESSAGE, None, None)
        success=win32pipe.TransactNamedPipe(self.hpipe,
                                            str2bytes("START %i"%(acqtime)),
                                            mybuffer,
                                            None)
    
        #↨win32pipe.DisconnectNamedPipe(self.hpipe)
        #win32file.CloseHandle(self.hpipe)
        
        return success

    def SCTDCRead(self,ROI):
        
        
        mybuffer=win32file.AllocateReadBuffer(1024*1024)
        
        data_pumped = []
        data_unpumped = []
        
        ROIlow=ROI[0]
        ROIhigh=ROI[1]
        
        #self.ConnectSCTDC()
        
        win32pipe.SetNamedPipeHandleState(self.hpipe,win32pipe.PIPE_READMODE_MESSAGE, None, None)
        result = win32pipe.TransactNamedPipe(self.hpipe,
                                            str2bytes("READ"),
                                            mybuffer,
                                            None)
        start=time.time()
        databytes = np.reshape(np.array([result[1][i] for i in range(len(result[1]))]),(-1,4))
        dataint = np.array([struct.unpack('I',databytes[i,:])[0] for i in range(databytes.shape[0])])
        #dataint = np.array([struct.unpack('I',databytes[i,:])[0] & 0x07FFFFFF for i in range(databytes.shape[0])])
        
            
        for d in dataint:
            
            val = d & 0x07FFFFFF
            if ((val >= ROIlow) and (val <= ROIhigh)):
                if (((d & 0x08000000) >> 27 ) == 1 ):
                    data_pumped.append(val)
                else:
                    data_unpumped.append(val)
        
        stop=time.time()-start
        print stop
        
        return data_unpumped, data_pumped
