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
import time
import os

sys.path.insert(1, os.path.dirname(os.path.realpath(__file__))+'/..')
from modules.example_helpers import *

# Record settings
number_of_records  = 10
samples_per_record = 512

# Plot data if set to True
plot_data = True

# Print metadata in headers
print_headers = True

# DMA transfer buffer settings
transfer_buffer_size = 65536
num_transfer_buffers = 8

# DMA flush timeout in seconds
flush_timeout        = 0.5

# Load ADQAPI
ADQAPI = adqapi_load()

# Create ADQControlUnit
adq_cu = ct.c_void_p(ADQAPI.CreateADQControlUnit())

# Enable error logging from ADQAPI
ADQAPI.ADQControlUnit_EnableErrorTrace(adq_cu, 3, '.')

# Find ADQ devices
ADQAPI.ADQControlUnit_FindDevices(adq_cu)
n_of_ADQ  = ADQAPI.ADQControlUnit_NofADQ(adq_cu)
print('Number of ADQ found:  {}'.format(n_of_ADQ))

# Exit if no devices were found
if n_of_ADQ < 1:
    print('No ADQ connected.')
    ADQAPI.DeleteADQControlUnit(adq_cu)
    adqapi_unload(ADQAPI)
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

# Maximum number of channels for ADQ14 FWPD is four
max_number_of_channels = ADQAPI.ADQ_GetNofChannels(adq_cu, adq_num)

# Setup test pattern
ADQAPI.ADQ_SetTestPatternMode(adq_cu, adq_num, 4)

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
success = ADQAPI.ADQ_SetLvlTrigLevel(adq_cu, adq_num, 0)
if (success == 0):
    print('ADQ_SetLvlTrigLevel failed.')    
success = ADQAPI.ADQ_SetTrigLevelResetValue(adq_cu, adq_num, 1000)
if (success == 0):
    print('ADQ_SetTrigLevelResetValue failed.')    
success = ADQAPI.ADQ_SetLvlTrigChannel(adq_cu, adq_num, 1)
if (success == 0):
    print('ADQ_SetLvlTrigChannel failed.')    
success = ADQAPI.ADQ_SetLvlTrigEdge(adq_cu, adq_num, LVL_RISING)
if (success == 0):
    print('ADQ_SetLvlTrigEdge failed.')

# Setup acquisition
channels_mask = 0xf
ADQAPI.ADQ_TriggeredStreamingSetup(adq_cu, adq_num, number_of_records, samples_per_record, 0, 0, channels_mask)

ADQAPI.ADQ_SetStreamStatus(adq_cu, adq_num, 1);
# Get number of channels from device
number_of_channels = ADQAPI.ADQ_GetNofChannels(adq_cu, adq_num)

# Setup size of transfer buffers
print('Setting up streaming...')
ADQAPI.ADQ_SetTransferBuffers(adq_cu, adq_num, num_transfer_buffers, transfer_buffer_size)

# Start streaming
print('Collecting data, please wait...')
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)
ADQAPI.ADQ_StartStreaming(adq_cu, adq_num)

# Allocate target buffers for intermediate data storage
target_buffers = (ct.POINTER(ct.c_int16*transfer_buffer_size)*number_of_channels)()
for bufp in target_buffers:
  bufp.contents = (ct.c_int16*transfer_buffer_size)()

# Create some buffers for the full records
data_16bit = [np.array([], dtype=np.int16),
              np.array([], dtype=np.int16),
              np.array([], dtype=np.int16),
              np.array([], dtype=np.int16)]

# Allocate target buffers for headers
headerbuf_list = [(HEADER*number_of_records)() for ch in range(number_of_channels)]
# Create an C array of pointers to header buffers
headerbufp_list = ((ct.POINTER(HEADER*number_of_records))*number_of_channels)()
# Initiate pointers with allocated header buffers
for ch,headerbufp in enumerate(headerbufp_list):
    headerbufp.contents = headerbuf_list[ch]
# Create a second level pointer to each buffer pointer,
# these will only be used to change the bufferp_list pointer values
headerbufvp_list = [ct.cast(ct.pointer(headerbufp_list[ch]), ct.POINTER(ct.c_void_p)) for ch in range(number_of_channels)]

# Allocate length output variable
samples_added = (4*ct.c_uint)()
for ind in range(len(samples_added)):
  samples_added[ind] = 0
  
headers_added = (4*ct.c_uint)()
for ind in range(len(headers_added)):
  headers_added[ind] = 0

header_status = (4*ct.c_uint)()
for ind in range(len(header_status)):
  header_status[ind] = 0

# Generate triggers if software trig is used
if (trig_type == 1):
  for trig in range(number_of_records):
    ADQAPI.ADQ_SWTrig(adq_cu, adq_num)

print('Waiting for data...')
# Collect data until all requested records have been recieved
records_completed = [0, 0, 0, 0]
headers_completed = [0, 0, 0, 0]
records_completed_cnt = 0
ltime = time.time()
buffers_filled = ct.c_uint(0)

# Read out data until records_completed for ch A is number_of_records
while (number_of_records > records_completed[0]):
  buffers_filled.value = 0
  collect_result = 1
  poll_time_diff_prev = time.time()
  # Wait for next data buffer
  while ((buffers_filled.value == 0) and (collect_result)):
    collect_result = ADQAPI.ADQ_GetTransferBufferStatus(adq_cu, adq_num,
                                                        ct.byref(buffers_filled))
    poll_time_diff = time.time()

    if ((poll_time_diff - poll_time_diff_prev) > flush_timeout):
      # Force flush
      print('No data for {}s, flushing the DMA buffer.'.format(flush_timeout))
      status = ADQAPI.ADQ_FlushDMA(adq_cu, adq_num);
      print('ADQAPI.ADQ_FlushDMA returned {}'.format(adq_status(status)))
      poll_time_diff_prev = time.time()


  # Fetch data and headers into target buffers
  status = ADQAPI.ADQ_GetDataStreaming(adq_cu, adq_num,
                                       target_buffers,
                                       headerbufp_list,
                                       channels_mask,
                                       ct.byref(samples_added),
                                       ct.byref(headers_added),
                                       ct.byref(header_status))
  if status == 0:
    print('GetDataStreaming failed!')
    sys.exit()

  for ch in range(number_of_channels):
    if (headers_added[ch] > 0):
      # The last call to GetDataStreaming has generated header data
      if  (header_status[ch]):
        headers_done = headers_added[ch]
      else:
        # One incomplete header
        headers_done = headers_added[ch]-1
      # Update counter counting completed records
      headers_completed[ch] += headers_done
      
      # Update the number of completed records if at least one header has completed
      if (headers_done > 0):
        records_completed[ch] = headerbuf_list[ch][headers_completed[ch]-1].RecordNumber + 1

      # Update header pointer so that it points to the current header
      headerbufvp_list[ch].contents.value += headers_done*ct.sizeof(headerbuf_list[ch]._type_)
      if headers_done > 0 and (np.sum(records_completed)-records_completed_cnt) > 1000:
          dtime = time.time()-ltime
          if (dtime > 0):
              print('{:d} {:.2f} MB/s'.format(np.sum(records_completed),
                    ((samples_per_record
                      *2
                      *(np.sum(records_completed)-records_completed_cnt))
                      /(dtime))/(1024*1024)))
          sys.stdout.flush()
          records_completed_cnt = np.sum(records_completed)
          ltime = time.time()

    if (samples_added[ch] > 0 and plot_data):
      # Copy channel data to continuous buffer
      data_buf          = np.frombuffer(target_buffers[ch].contents, dtype=np.int16, count=samples_added[ch])
      data_16bit[ch]    = np.append(data_16bit[ch], data_buf)

    print(records_completed[0])

# Stop streaming
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)

# Print recieved headers
if print_headers:
  for ch in range(max_number_of_channels):
    if number_of_records > 0:       
      print('------------------')
      print('Headers channel {}'.format(ch))
      print('------------------')
      for rec in range(number_of_records):
        header = headerbuf_list[ch][rec]
        print('RecordStatus:  {}'.format(header.RecordStatus)) 
        print('UserID:        {}'.format(header.UserID))      
        print('SerialNumber:  {}'.format(header.SerialNumber))
        print('Channel:       {}'.format(header.Channel)) 
        print('DataFormat:    {}'.format(header.DataFormat))   
        print('RecordNumber:  {}'.format(header.RecordNumber))
        print('Timestamp:     {} ns'.format(header.Timestamp / header.SamplePeriod))   
        print('RecordStart:   {} ns'.format(header.RecordStart / header.SamplePeriod)) 
        print('SamplePeriod:  {} ns'.format(header.SamplePeriod * 0.125))
        print('RecordLength:  {} ns'.format(header.RecordLength * (header.SamplePeriod* 0.125)))
        print('------------------')

# Plot data
if plot_data:
  for ch in range(max_number_of_channels):
    if number_of_records > 0:        
      widths = np.array([], dtype=np.uint32)
      record_end_offset = 0
      # Extract record lengths from headers
      for rec in range(number_of_records):
        header = headerbuf_list[ch][rec]    
        widths = np.append(widths, header.RecordLength) 

      # Get new figure
      plt.figure(ch)
      plt.clf()
      # Plot data
      plt.plot(data_16bit[ch].T, '.-')
      # Set window title
      plt.gcf().canvas.set_window_title('Channel {}'.format(ch))
      # Set grid mode
      plt.grid(which='Major')
      # Mark records in plot
      alternate_background(plt.gca(), 0, widths, labels=True)  
      # Show plot
      plt.show()      
      
# Delete ADQ device handle
ADQAPI.ADQControlUnit_DeleteADQ(adq_cu, adq_num)
# Delete ADQControlunit
ADQAPI.DeleteADQControlUnit(adq_cu)

print('Done.')
