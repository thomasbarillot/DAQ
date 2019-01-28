# -*- coding: utf-8 -*-
"""
Created on Mon Apr 04 11:17:15 2016

@author: atto

Piezostage remote control (ie writingdelay into file read by humongium)

"""
import sys

# The CLR module provide functions for interacting with the underlying
# .NET runtime
import visa
import time

# Add reference to assembly and import names from namespace

import system 



class DelayStage():
    
    def __init__(self):
        
        self.rm=visa.ResourceManager()
        self.controller=self.rm.open_resource('GPIB0::1::INSTR', read_termination='\r')
        self.controller.timeout = 1000
        self.stagenum=1
    
    def __del__(self):
        self.controller.clear()
        self.controller.close()
        self.rm.close()
    
    def MoveAbs(self,target):
#    
        cmd = str(self.stagenum)+'PA'+str(target)+';'+str(self.stagenum)+'WS\r'
        status=self.controller.write(unicode(cmd,"utf-8"))
        time.sleep(0.5)
        return status
        
    def MoveRel(self,step,pol):
        
        if pol==1:
            cmd = str(self.stagenum)+'PR+'+str(step)+';'+str(self.stagenum)+'WS\r'
        elif pol==-1:
            cmd = str(self.stagenum)+'PR-'+str(step)+';'+str(self.stagenum)+'WS\r'            
        status=self.controller.write(unicode(cmd,"utf-8"))
        time.sleep(0.5)
        return status
        
#    def QueryMotion(self):
#        
#        return bool(self.controller.query_ascii_values('MD?'))



