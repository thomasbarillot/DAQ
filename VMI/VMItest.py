# -*- coding: utf-8 -*-
"""
Created on Sat May  7 11:38:18 2016

@author: thomasbarillot

VMI control
"""
from ctypes import cdll
#slib="VMIcrtl_ext.dll"
#hlib=cdll('VMIcrtl.dll')

import VMIcrtl_ext

test=VMIcrtl_ext.VMIcrtl()
#%%
print test.GetFilename()

#%%

test.setFilename('20161115_1841.dat')
print test.GetFilename()

#%%

test.StartAcquisitionPrev()
#%%
test.StopAcquisition()

#%%
img=test.RecallImagePrev()

#%%
import numpy as np

print np.shape(img)

a=np.array(img)
print a
#%%
from matplotlib import pyplot as plt


#%%
b=np.reshape(a,[400,400])
print b
plt.figure()
plt.pcolor(np.reshape(a,[400,400]))