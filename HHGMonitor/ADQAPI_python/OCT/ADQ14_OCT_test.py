#!/usr/bin/env python3
#
# Copyright 2015 Signal Processing Devices Sweden AB. All rights reserved.
#
# Description:    ADQ14 OCT test script
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
# Setting stream_number_of_records to 2^32-1 means we want infinite number of records
stream_number_of_records  = 2**32-1
samples_per_record = 500
OCTCount = 100

# separate parameter for how many we collect in this script before plotting
number_of_records  = min([stream_number_of_records, 50])

pretrig = 0; #offset collected samples to before trigger point
holdoff = 0; #offset collected samples to after trigger point

# Plot data if set to True
plot_data = True

# DMA transfer buffer settings
transfer_buffer_size = 1024
num_transfer_buffers = 8

# DMA flush timeout in seconds
flush_timeout        = 0.5

# Target buffers in software (Must be 4)
num_sw_buffers = 4;

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

print('Reseting device ')  
ADQAPI.ADQ_ResetDevice(adq_cu, adq_num, 16)
# Delete ADQ device handle
ADQAPI.ADQControlUnit_DeleteADQ(adq_cu, adq_num)


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

# Set OCT parameters
#trig_type = 1 #software trigger
trig_type = 7 #oct trigger

#ADQAPI.ADQ_OCTDebug(adq_cu, adq_num, 0x5e72f039, 1, 0) #use debug data instead of analog inputs
ADQAPI.ADQ_OCTSetTriggerCount(adq_cu, adq_num, OCTCount) #set OCT frame count
ADQAPI.ADQ_SetTriggerMode(adq_cu, adq_num, 1) #first set software trigger to clear OCT counters
ADQAPI.ADQ_SetTriggerMode(adq_cu, adq_num, trig_type) #set triggering mode

# Setup acquisition
# Use 0 in the last two arguments since they are currently unsupported, we use separate calls afterwards to set pretrig and holdoff.
ADQAPI.ADQ_TriggeredStreamingSetup(adq_cu, adq_num,
                                   stream_number_of_records,
                                   samples_per_record,
                                   0, 0);
ADQAPI.ADQ_SetPreTrigSamples(adq_cu, adq_num, pretrig);
ADQAPI.ADQ_SetTriggerHoldOffSamples(adq_cu, adq_num, holdoff);

# Setup streaming mode
ADQAPI.ADQ_SetStreamStatus(adq_cu, adq_num, 2)

# Get number of channels from device
number_of_channels = ADQAPI.ADQ_GetNofChannels(adq_cu, adq_num)

# Setup size of transfer buffers
print('Setting up streaming...')
ADQAPI.ADQ_SetTransferBuffers(adq_cu, adq_num, num_transfer_buffers, transfer_buffer_size)
ADQAPI.ADQ_PDSetupStreaming(adq_cu, adq_num, 0xf)

# Start streaming
print('Collecting data, please wait...')
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)
ADQAPI.ADQ_StartStreaming(adq_cu, adq_num)

# Allocate target buffers for intermediate data storage
target_buffers = (ct.POINTER(ct.c_int16*transfer_buffer_size)*num_sw_buffers)()
for bufp in target_buffers:
  bufp.contents = (ct.c_int16*transfer_buffer_size)()

# Create some buffers for the full records
data_16bit = [np.array([], dtype=np.int16),
              np.array([], dtype=np.int16),
              np.array([], dtype=np.int16),
              np.array([], dtype=np.int16)]

# Allocate target buffers for headers
headerbuf_list = [(HEADER*number_of_records)() for ch in range(num_sw_buffers)]
# Create an C array of pointers to header buffers
headerbufp_list = ((ct.POINTER(HEADER*number_of_records))*num_sw_buffers)()
# Initiate pointers with allocated header buffers
for ch,headerbufp in enumerate(headerbufp_list):
    headerbufp.contents = headerbuf_list[ch]
# Create a second level pointer to each buffer pointer,
# these will only be used to change the bufferp_list pointer values
headerbufvp_list = [ct.cast(ct.pointer(headerbufp_list[ch]), ct.POINTER(ct.c_void_p)) for ch in range(num_sw_buffers)]

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
  for trig in range(number_of_records*2): #twice as needed to handle that ADQ14OCT currently misses some software triggers
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
                                       0xf,
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
      print('Adding {} samples.'.format(samples_added[ch]))
      
  print('Records completed: {}'.format(records_completed[0]))

# Stop streaming
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)

# Plot data
if plot_data:
  if number_of_records > 0:        
    widths = np.array([], dtype=np.uint32)
    record_end_offset = 0
    # Extract record lengths from headers
    for rec in range(number_of_records):
      header = headerbuf_list[0][rec]    
      widths = np.append(widths, header.RecordLength) 

    # Get new figure
    plt.figure(0)
    plt.clf()
    # Plot data
    plt.plot(data_16bit[0].T, '.-')
    # Set window title
    plt.gcf().canvas.set_window_title('Channel {}'.format(0))
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
