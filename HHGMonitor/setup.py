# -*- coding: utf-8 -*-
"""
Created on Mon Jul 10 13:45:40 2017

@author: Thomas Barillot

Setup file for standalone python acq program

"""
from distutils.core import setup
import py2exe

setup(console=['TOFAcqDigitizerGUI_withStream.py'])
