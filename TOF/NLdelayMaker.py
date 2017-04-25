# -*- coding: utf-8 -*-
"""
Created on Fri May 13 14:36:48 2016

@author: atto
"""

import numpy as np

Delay=np.zeros((10))
print Delay.shape

np.savetxt('SingleDelaylist.txt',Delay)