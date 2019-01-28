#!/usr/bin/env python3
#
# Copyright 2015 Signal Processing Devices Sweden AB. All rights reserved.
#
# Description:    ADQ14 FWDAQ streaming example
# Documentation:
#

import numpy as np
import scipy.signal as signal
import ctypes as ct
import matplotlib.pyplot as plt
import sys
import time
import os

sys.path.insert(1, os.path.dirname(os.path.realpath(__file__))+'/..')
from modules.example_helpers import *

# Down-conversion settings
freq_lo = -30000 # Hz (an input frequency f_in shows up at f_in + freq_lo after the down-conversion)
decimation_factor = 14 # Decimates data rate by a factor of 2^decimation_factor
fftlength = 16384
target_bytes_per_sample = 4 # Set to 2 for 16-bit data, 4 for 32-bit data (this is a trade-off between faster data transfer and lower quantization noise)

stream_time = 60 # Number of seconds to stream. To quit before this time, simply close the plot window.

# Equalizer settings
eqmode = 0 # 0: bypass, 1: real-valued, 2: complex valued
eqcoeffs1 = [0,0,0,0,0,0,0, 1.0, 0,0,0,0,0,0,0]
eqcoeffs2 = [0,0,0,0,0,0,0, 1.0, 0,0,0,0,0,0,0]

# Plot data if set to True
plot_data = True

# Print metadata in headers
print_headers = True

# DMA transfer buffer settings
transfer_buffer_size = 65536
num_transfer_buffers = 8
number_of_records = 1 # Continuous streaming produces a single record header

# DMA flush timeout in seconds
flush_timeout        = 2

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
    sys.exit(1)

# Select ADQ
if n_of_ADQ > 1:
    adq_num = int(input('Select ADQ device 1-{:d}: '.format(n_of_ADQ)))
else:
    adq_num = 1

print_adq_device_revisions(ADQAPI, adq_cu, adq_num)

# Read sample rate and number of channels
tmp = ct.c_double(0)
ADQAPI.ADQ_GetSampleRate(adq_cu, adq_num, 0, ct.byref(tmp))
fs = tmp.value

number_of_channels = ADQAPI.ADQ_GetNofChannels(adq_cu, adq_num)
number_of_iqchannels = int(number_of_channels/2) # Each I/Q channel consists of two data channels

# Setup plot
fsd = fs / (2**decimation_factor)
if number_of_iqchannels == 1:
  fig, ax = plt.subplots(number_of_iqchannels, sharex=True, sharey=True)        
  axarr = [ax]
else:
  fig, axarr = plt.subplots(number_of_iqchannels, sharex=True, sharey=True)        
freq = np.fft.fftfreq(fftlength, d=1/(fsd))
freq = np.fft.fftshift(freq)
freq = freq - freq_lo

print('Decimated sample rate: %.1f Hz' % fsd)

fftline = []

for ch in range(0,number_of_iqchannels):
  (tmp,) = axarr[ch].plot(freq, [0]*fftlength, label='Spectrum')
  fftline.append(tmp)

  if decimation_factor > 0:
    axarr[ch].axvspan(0.7*fsd/2 - freq_lo, fsd/2 - freq_lo, facecolor='0.5', alpha=0.33, label='Aliasing')
    axarr[ch].axvspan(-fsd/2 - freq_lo, -0.7*fsd/2 - freq_lo, facecolor='0.5', alpha=0.33)
    axarr[ch].axvline(-0.7*fsd/2 - freq_lo, color='r', linestyle='--')
    axarr[ch].axvline(0.7*fsd/2 - freq_lo, color='r', linestyle='--')


plt.ylim(-160,0)
plt.xlim(freq[0],freq[-1])
plt.xlabel('Frequency [Hz]')
plt.ylabel('Amplitude [dBFS]')
plt.legend()

fig.canvas.draw()
#fig.canvas.flush_events()
plt.show(block=False)

print('Estimated data rate:', number_of_channels*target_bytes_per_sample*fsd/1e6,'MB/s')

# Set clock source
ADQ_CLOCK_INT_INTREF = 0
ADQAPI.ADQ_SetClockSource(adq_cu, adq_num, ADQ_CLOCK_INT_INTREF)

# Setup test pattern
ADQAPI.ADQ_SetTestPatternMode(adq_cu, adq_num, 0)

# Setup down-conversion
ADQAPI.ADQ_SetSampleDecimation(adq_cu, adq_num, decimation_factor)

for iqchannel in range(1,number_of_iqchannels+1):
  ADQAPI.ADQ_SetMixerFrequency(adq_cu, adq_num, iqchannel, ct.c_double(freq_lo))

if target_bytes_per_sample == 4:
  ADQAPI.ADQ_SetDataFormat(adq_cu, adq_num, 3)
else:
  ADQAPI.ADQ_SetDataFormat(adq_cu, adq_num, 0)

# Setup equalizer
eqcoeff1arr = (ct.c_float * len(eqcoeffs1))(*eqcoeffs1)
eqcoeff2arr = (ct.c_float * len(eqcoeffs2))(*eqcoeffs2)
for iqchannel in range(1,number_of_iqchannels+1):
  ADQAPI.ADQ_SetEqualizerSDR(adq_cu, adq_num, iqchannel, eqcoeff1arr, eqcoeff2arr, eqmode)


# Synchronize decimation and mixers between channels
ADQAPI.ADQ_ForceResynchronizationSDR(adq_cu, adq_num)

# Set trigger mode
SW_TRIG = 1
EXT_TRIG_1 = 2
trig_type = SW_TRIG
success = ADQAPI.ADQ_SetTriggerMode(adq_cu, adq_num, trig_type)

# Setup acquisition
channels_mask = 0xf # Collect all channels
ADQAPI.ADQ_ContinuousStreamingSetup(adq_cu, adq_num, channels_mask)

# Setup size of transfer buffers
ADQAPI.ADQ_SetTransferBuffers(adq_cu, adq_num, num_transfer_buffers, transfer_buffer_size)

# Allocate target buffers for intermediate data storage
if target_bytes_per_sample == 4:
  target_buffers = (ct.POINTER(ct.c_int32*int(transfer_buffer_size/target_bytes_per_sample))*number_of_channels)()
  for bufp in target_buffers:
    bufp.contents = (ct.c_int32*transfer_buffer_size)()
else:
  target_buffers = (ct.POINTER(ct.c_int16*int(transfer_buffer_size/target_bytes_per_sample))*number_of_channels)()
  for bufp in target_buffers:
    bufp.contents = (ct.c_int16*transfer_buffer_size)()


# Create some buffers for the full records
data_numpy = [np.array([], dtype=np.int16),
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

# Start streaming
print('Starting stream')
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)
ADQAPI.ADQ_StartStreaming(adq_cu, adq_num)

if (trig_type == 1):
  ADQAPI.ADQ_SWTrig(adq_cu, adq_num) # Send a software trigger if software trigger mode is selected

print('Waiting for data...')
# Collect data until all requested records have been recieved
ltime = time.time()
buffers_filled = ct.c_uint(0)

overflow = 0
# Read out data until records_completed for ch A is number_of_records
while time.time() - ltime < stream_time and overflow == 0:
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
    ADQAPI.DeleteADQControlUnit(adq_cu)
    sys.exit()

  # Continuous streaming sends a single record header showing where the inital trigger occurred
  if (headers_added[0] > 0):
    header = headerbuf_list[0][0]
    print('\n-------------------')
    print('   Record header   ') 
    print('UserID:        {}'.format(header.UserID))      
    print('SerialNumber:  {}'.format(header.SerialNumber))
    print('DataFormat:    {}'.format(header.DataFormat))   
    print('Timestamp:     {} ns'.format(header.Timestamp * 0.125))   
    print('RecordStart:   {} ns'.format(header.RecordStart * 0.125)) 
    print('SamplePeriod:  {} ns'.format(header.SamplePeriod * 0.125))
    print('-------------------\n')

  for ch in range(number_of_channels):
    if (samples_added[ch] > 0 and plot_data):
      # If we retrieved any samples, copy channel data to buffer
      if target_bytes_per_sample == 4:
        data_buf = np.frombuffer(target_buffers[ch].contents, dtype=np.int32, count=samples_added[ch])
      else:
        data_buf = np.frombuffer(target_buffers[ch].contents, dtype=np.int16, count=samples_added[ch])
      data_numpy[ch]    = np.append(data_numpy[ch], data_buf)

  # If we have enough data to update the FFT plot, do it
  for ch in range(0,number_of_iqchannels):
    if len(data_numpy[2*ch]) >= fftlength and len(data_numpy[2*ch+1]) >= fftlength:

      # Calculate FFT from complex-valued data
      iqdata = np.zeros(fftlength, complex)
      iqdata.real = data_numpy[2*ch + 0][0:fftlength]
      iqdata.imag = data_numpy[2*ch + 1][0:fftlength]

      data_numpy[2*ch + 0] = data_numpy[2*ch + 0][fftlength:]
      data_numpy[2*ch + 1] = data_numpy[2*ch + 1][fftlength:]

      iqdata = np.multiply(iqdata,signal.flattop(fftlength))
      iqfft = 20*np.log10(np.abs(np.fft.fft(iqdata))/iqdata.size/2**(target_bytes_per_sample*8-2))
      iqfft = np.fft.fftshift(iqfft)

      # Update plot
      try:
        fftline[ch].set_ydata(iqfft)
        fig.canvas.draw()
        fig.canvas.flush_events()
      except:
        ADQAPI.DeleteADQControlUnit(adq_cu)
        sys.exit()
  
  if(ADQAPI.ADQ_GetStreamOverflow(adq_cu,adq_num)):
    print('Overflow detected, shutting down')
    overflow = 1

# Stop streaming
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)    
      
# Delete ADQ device handle
ADQAPI.ADQControlUnit_DeleteADQ(adq_cu, adq_num)
# Delete ADQControlunit
ADQAPI.DeleteADQControlUnit(adq_cu)

print('Done.')
