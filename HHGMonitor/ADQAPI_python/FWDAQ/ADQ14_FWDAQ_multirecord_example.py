#!/usr/bin/env python3
#
# Copyright 2015 Signal Processing Devices Sweden AB. All rights reserved.
#
# Description:    ADQ14 FWDAQ streaming example
# Documentation:
#

import numpy as np
import ctypes as ct
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(1, os.path.dirname(os.path.realpath(__file__))+'/..')
from modules.example_helpers import *

# Record settings
number_of_records  = 4
samples_per_record = 1024
sample_skip = 1;
pretrigger = 0;
triggerdelay = 0;
channel_mask = 0xF;

# Plot data if set to True
plot_data = True

# Print metadata in headers
print_headers = True

# Load ADQAPI
ADQAPI = adqapi_load()

# Create ADQControlUnit
adq_cu = ct.c_void_p(ADQAPI.CreateADQControlUnit())

# Enable error logging from ADQAPI
ADQAPI.ADQControlUnit_EnableErrorTrace(adq_cu, 65536, '.')

# Find ADQ devices
ADQAPI.ADQControlUnit_FindDevices(adq_cu)
n_of_ADQ  = ADQAPI.ADQControlUnit_NofADQ(adq_cu)
n_of_failed_ADQ  = ADQAPI.ADQControlUnit_GetFailedDeviceCount(adq_cu)
if n_of_failed_ADQ > 0:
  print(n_of_failed_ADQ, 'connected devices failed initialization.')
print('Number of ADQ found:  {}'.format(n_of_ADQ))

# Exit if no devices were found
if n_of_ADQ < 1:
    print('No ADQ connected.')
    ADQAPI.DeleteADQControlUnit(adq_cu)
    sys.exit(1)

# Select ADQ
if n_of_ADQ > 1:
    adq_num = int(input('Select ADQ device 1-{:d}: '.format(n_of_ADQ)))
else:
    adq_num = 1

print_adq_device_revisions(ADQAPI, adq_cu, adq_num)

# Set clock source
ADQ_CLOCK_INT_INTREF = 0
ADQAPI.ADQ_SetClockSource(adq_cu, adq_num, ADQ_CLOCK_INT_INTREF)

# Setup test pattern
ADQAPI.ADQ_SetTestPatternMode(adq_cu, adq_num, 0)

# Set trig mode
SW_TRIG = 1
EXT_TRIG_1 = 2
EXT_TRIG_2 = 7
EXT_TRIG_3 = 8
LVL_TRIG = 3
INT_TRIG = 4
LVL_FALLING = 0
LVL_RISING = 1
trig_type = SW_TRIG

success = ADQAPI.ADQ_SetTriggerMode(adq_cu, adq_num, trig_type)
if (success == 0):
    print('ADQ_SetTriggerMode failed.')

if trig_type == LVL_TRIG:
  success = ADQAPI.ADQ_SetLvlTrigLevel(adq_cu, adq_num, 0)
  if (success == 0):
      print('ADQ_SetLvlTrigLevel failed.')
  success = ADQAPI.ADQ_SetLvlTrigEdge(adq_cu, adq_num, LVL_RISING)
  if (success == 0):
      print('ADQ_SetLvlTrigEdge failed.')

# Setup data processing (should be done before multirecord setup)
ADQAPI.ADQ_SetSampleSkip(adq_cu, adq_num, sample_skip)
ADQAPI.ADQ_SetPreTrigSamples(adq_cu, adq_num, pretrigger)
ADQAPI.ADQ_SetTriggerHoldOffSamples(adq_cu, adq_num, triggerdelay);

# Setup multirecord
ADQAPI.ADQ_MultiRecordSetChannelMask(adq_cu, adq_num, channel_mask);
ADQAPI.ADQ_MultiRecordSetup(adq_cu, adq_num, number_of_records, samples_per_record)

# Get number of channels from device
number_of_channels = ADQAPI.ADQ_GetNofChannels(adq_cu, adq_num)


# Arm acquisition
print('Arming device')
ADQAPI.ADQ_DisarmTrigger(adq_cu, adq_num)
ADQAPI.ADQ_ArmTrigger(adq_cu, adq_num)

# Allocate target buffers for intermediate data storage
target_buffers = (ct.POINTER(ct.c_int16*(number_of_records*samples_per_record))*number_of_channels)()
for bufp in target_buffers:
  bufp.contents = (ct.c_int16*(number_of_records*samples_per_record))()

# Create some buffers for the full records
data_numpy = [np.zeros(number_of_records*samples_per_record, dtype=np.int16),
              np.zeros(number_of_records*samples_per_record, dtype=np.int16),
              np.zeros(number_of_records*samples_per_record, dtype=np.int16),
              np.zeros(number_of_records*samples_per_record, dtype=np.int16)]

# Allocate target buffers for headers
header_list = (HEADER*number_of_records)()
target_headers = ct.POINTER(HEADER*number_of_records)()
target_headers.contents = header_list
target_headers_vp = ct.cast(ct.pointer(target_headers), ct.POINTER(ct.c_void_p))

# Generate triggers if software trig is used
if (trig_type == 1):
  for trig in range(number_of_records):
    ADQAPI.ADQ_SWTrig(adq_cu, adq_num)

print('Waiting for data...')
# Collect data until all requested records have been recieved
records_completed = 0
records_available = 0;

# Read out data until records_completed for ch A is number_of_records
while (records_completed < number_of_records):
  records_available = ADQAPI.ADQ_GetAcquiredRecords(adq_cu, adq_num)
  new_records = records_available - records_completed

  if new_records > 0:      
    # Fetch data and headers into target buffers
    status = ADQAPI.ADQ_GetDataWHTS(adq_cu, adq_num,
                                         target_buffers,
                                         target_headers,
                                         None,
                                         number_of_records*samples_per_record,
                                         2,
                                         records_completed,
                                         new_records,
                                         channel_mask,
                                         0,
                                         samples_per_record,
                                         0x00)

    if status == 0:
      print('GetDataWH failed!')
      ADQAPI.DeleteADQControlUnit(adq_cu)
      sys.exit()

    for ch in range(0,number_of_channels):
      data_buf = np.frombuffer(target_buffers[ch].contents, dtype=np.int16, count=(samples_per_record*new_records))
      for rec in range(0,new_records):
        for s in range(0,samples_per_record):
          data_numpy[ch][(records_completed+rec)*samples_per_record + s] = data_buf[rec*samples_per_record + s]

    records_completed += new_records
    target_headers_vp.contents.value += new_records*ct.sizeof(HEADER)

    print('Records read out:',records_completed)

# Close multirecord
ADQAPI.ADQ_MultiRecordClose(adq_cu, adq_num)

# Print recieved headers
if print_headers:
  for header in header_list:
    print('RecordStatus:  {}'.format(header.RecordStatus)) 
    print('UserID:        {}'.format(header.UserID))      
    print('SerialNumber:  {}'.format(header.SerialNumber))
    print('Channel:       {}'.format(header.Channel)) 
    print('DataFormat:    {}'.format(header.DataFormat))   
    print('RecordNumber:  {}'.format(header.RecordNumber))
    print('Timestamp:     {} ns'.format(header.Timestamp * 0.125))   
    print('RecordStart:   {} ns'.format(header.RecordStart / header.SamplePeriod)) 
    print('SamplePeriod:  {} ns'.format(header.SamplePeriod * 0.125))
    print('RecordLength:  {} ns'.format(header.RecordLength * (header.SamplePeriod* 0.125)))
    print('------------------')  


#plt.figure(1)
#plt.clf()
# Plot data
#plt.plot(data_numpy[0], '.-')
# Show plot
#plt.show()  

# Plot data
if plot_data:
  for ch in range(number_of_channels):
    if number_of_records > 0:        
      widths = np.array([], dtype=np.uint32)
      record_end_offset = 0
      # Extract record lengths from headers
      for rec in range(number_of_records):
        header = header_list[rec]    
        widths = np.append(widths, header.RecordLength) 

      # Get new figure
      plt.figure(ch)
      plt.clf()
      # Plot data
      plt.plot(data_numpy[ch].T, '.-')
      # Set window title
      plt.gcf().canvas.set_window_title('Channel {}'.format(ch))
      # Set grid mode
      plt.grid(which='Major')
      # Mark records in plot
      alternate_background(plt.gca(), 0, widths, labels=True)  
      # Show plot
      plt.show()      
      
# Delete ADQControlunit
ADQAPI.DeleteADQControlUnit(adq_cu)

print('Done.')
