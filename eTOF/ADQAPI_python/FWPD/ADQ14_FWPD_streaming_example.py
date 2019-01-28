#!/usr/bin/env python3
#
# Copyright 2015 Signal Processing Devices Sweden AB. All rights reserved.
#
# Description:    ADQ14 FWPD streaming example
# Documentation:
#

import numpy as np
import ctypes as ct
import matplotlib.pyplot as plt
import sys
import time
import os
from modules.example_helpers import *
import modules.fwpd_histogram as hist

# Plot data if set to True
plot_data = True

# Print metadata in headers
print_headers = True

# Histogram settings
plot_hist = False
hist_extr_scale  = 64
hist_extr_offset = 2**15
hist_extr_norm    = True
hist_tot_scale   = 1024
hist_tot_offset  = 0
hist_tot_norm    = True

# Bypass calibrated gain & offset values if True
calibrated_go = False

# Enable internal trigger output
int_trig_output = False

# Enable reset of the device timestamp on external trigger edge
ext_trig_timestamp_reset = False

# Enable trigger blocking
trigger_blocking = False

# Setup pulse characterization (ONLY FWPD-PC devices)
setup_pulse_characterization = False

transfer_buffer_size = 512*1024
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

# Setup test pattern
ADQAPI.ADQ_SetTestPatternMode(adq_cu, adq_num, 4)

# Maximum number of channels for ADQ14 FWPD is four
max_number_of_channels = ADQAPI.ADQ_GetNofChannels(adq_cu, adq_num)

# Create common settings, use default values
acqs = acquisition_setup()
# Collect data from all four channels
acqs.channels_mask = 0b1111

# Create settings for channels 1-4
cs_all = [channel_setup(channel) for channel in range(1, max_number_of_channels+1)]
# Setup individual channels
# Channel 1
cs_all[0].trigger_level                   = 1000
cs_all[0].reset_hysteresis                = 500
cs_all[0].trigger_arm_hysteresis          = 500
cs_all[0].reset_arm_hysteresis            = 0
cs_all[0].trigger_polarity                = 1
cs_all[0].reset_polarity                  = 0
cs_all[0].coincidence_masking_expression  = 0b0001
cs_all[0].number_of_records               = 5
cs_all[0].record_variable_length          = 0
cs_all[0].nof_pretrigger_samples          = 128
cs_all[0].nof_moving_average_samples      = 0
cs_all[0].moving_average_delay            = 0
cs_all[0].samples_per_record              = 8000
cs_all[0].trailing_edge_window            = cs_all[0].samples_per_record

if (max_number_of_channels > 1):
  # Channel 2
  cs_all[1].trigger_level                   = 500
  cs_all[1].reset_hysteresis                = 500
  cs_all[1].trigger_arm_hysteresis          = 500
  cs_all[1].reset_arm_hysteresis            = 500
  cs_all[1].trigger_polarity                = 1
  cs_all[1].reset_polarity                  = 0
  cs_all[1].coincidence_masking_expression  = 0b0010
  cs_all[1].number_of_records               = 0
  cs_all[1].record_variable_length          = 0
  cs_all[1].nof_pretrigger_samples          = 0
  cs_all[1].nof_moving_average_samples      = 0
  cs_all[1].moving_average_delay            = 0
  cs_all[1].samples_per_record              = 1000
  cs_all[1].trailing_edge_window            = cs_all[1].samples_per_record

if (max_number_of_channels > 2):
  # Channel 3
  cs_all[2].trigger_level                   = 100
  cs_all[2].reset_hysteresis                = 500
  cs_all[2].trigger_arm_hysteresis          = 500
  cs_all[2].reset_arm_hysteresis            = 500
  cs_all[2].trigger_polarity                = 1
  cs_all[2].reset_polarity                  = 0
  cs_all[2].coincidence_masking_expression  = 0b0100
  cs_all[2].number_of_records               = 0
  cs_all[2].record_variable_length          = 0
  cs_all[2].nof_pretrigger_samples          = 0
  cs_all[2].nof_moving_average_samples      = 0
  cs_all[2].moving_average_delay            = 0
  cs_all[2].samples_per_record              = 1000
  cs_all[2].trailing_edge_window            = cs_all[2].samples_per_record

  # Channel 4
  cs_all[3].trigger_level                   = 100
  cs_all[3].reset_hysteresis                = 500
  cs_all[3].trigger_arm_hysteresis          = 500
  cs_all[3].reset_arm_hysteresis            = 500
  cs_all[3].trigger_polarity                = 1
  cs_all[3].reset_polarity                  = 0
  cs_all[3].coincidence_masking_expression  = 0b1000
  cs_all[3].number_of_records               = 0
  cs_all[3].record_variable_length          = 0
  cs_all[3].nof_pretrigger_samples          = 0
  cs_all[3].nof_moving_average_samples      = 0
  cs_all[3].moving_average_delay            = 0
  cs_all[3].samples_per_record              = 1000
  cs_all[3].trailing_edge_window            = cs_all[3].samples_per_record
###

# Setup internal trigger output
if int_trig_output:
  trigger_period = 200*2
  status = ADQAPI.ADQ_SetInternalTriggerPeriod(adq_cu, adq_num, trigger_period)
  print('ADQAPI.ADQ_SetInternalTriggerPeriod returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_SetConfigurationTrig(adq_cu, adq_num, 0x5, 75, 0)
  print('ADQAPI.ADQ_SetConfigurationTrig returned {}'.format(adq_status(status)))

# Setup timestamp reset via external trigger
if ext_trig_timestamp_reset:
  timestamp_reset_edge = 1 # 0: Falling, 1: Rising
  timestamp_reset_mode = 0 # 0: First edge 1: Every edge
  status = ADQAPI.ADQ_SetTriggerEdge(adq_cu, adq_num, 2, timestamp_reset_edge)
  print('ADQAPI.ADQ_SetExternTrigEdge returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_SetupTimestampSync(adq_cu, adq_num, timestamp_reset_mode, 2)
  print('ADQAPI.ADQ_SetupTimestampSync returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_DisarmTimestampSync(adq_cu, adq_num)
  print('ADQAPI.ADQ_DisarmTimestampSync returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_ArmTimestampSync(adq_cu, adq_num)
  print('ADQAPI.ADQ_ArmTimestampSync returned {}'.format(adq_status(status)))

# Setup trigger blocking
if trigger_blocking:
  trigger_blocking_mode = 0 # 0: ONCE, 1: WINDOW, 2: GATE
  trigger_blocking_source = 2 # 2: External trigger, 9: Sync input
  trigger_blocking_window_length = 131072*2;

  status = ADQAPI.ADQ_SetupTriggerBlocking(adq_cu, adq_num, trigger_blocking_mode, trigger_blocking_source, trigger_blocking_window_length)
  print('ADQAPI.ADQ_SetupTriggerBlocking returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_DisarmTriggerBlocking(adq_cu, adq_num)
  print('ADQAPI.ADQ_DisarmTriggerBlocking returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_ArmTriggerBlocking(adq_cu, adq_num)
  print('ADQAPI.ADQ_ArmTriggerBlocking returned {}'.format(adq_status(status)))

if not calibrated_go:
  print('Bypassing gain & offset calibration.')
  for ch in range(1,max_number_of_channels+1):
    status = ADQAPI.ADQ_SetGainAndOffset(adq_cu, adq_num,
                                         128+ch,
                                         1024,
                                         0)
    print('ADQ_SetGainAndOffset returned {}'.format(adq_status(status)))

# Setup acquisition
for ts in cs_all:
  print('Setting up channel {}'.format(ts.channel))
  status = ADQAPI.ADQ_PDSetupLevelTrig(adq_cu, adq_num,
                                       ts.channel,
                                       ts.trigger_level,
                                       ts.reset_hysteresis,
                                       ts.trigger_arm_hysteresis,
                                       ts.reset_arm_hysteresis,
                                       ts.trigger_polarity,
                                       ts.reset_polarity)
  print('ADQAPI.ADQ_PDSetupLevelTrig returned {}'.format(adq_status(status)))

  status = ADQAPI.ADQ_PDSetupTiming(adq_cu, adq_num,
                                    ts.channel,
                                    ts.nof_pretrigger_samples,
                                    ts.nof_moving_average_samples,
                                    ts.moving_average_delay,
                                    ts.trailing_edge_window,
                                    ts.number_of_records,
                                    ts.record_variable_length)
  print('ADQAPI.ADQ_PDSetupTiming returned {}'.format(adq_status(status)))

# Setup trigger coincidence windows
for ts in cs_all:
  status = ADQAPI.ADQ_PDSetupTriggerCoincidence(adq_cu, adq_num,
                                                ts.channel,
                                                ts.coincidence_window_length,
                                                ts.coincidence_masking_expression)
  print('ADQAPI.ADQ_PDSetupTriggerCoincidence returned {}'.format(adq_status(status)))

# Bypass moving average
status = ADQAPI.ADQ_PDSetupMovingAverageBypass(adq_cu, adq_num, 0, 0)
print('ADQAPI.ADQ_PDSetupMovingAverageBypass returned {}'.format(adq_status(status)))

if setup_pulse_characterization:
  for ch in range(1,max_number_of_channels+1):
    # Enable characterization
    hist.enable_characterization(ADQAPI, adq_cu, adq_num, ch, True, False)
    hist.setup_extr(ADQAPI, adq_cu, adq_num, ch, hist_extr_scale, hist_extr_offset)
    hist.reset_extr(ADQAPI, adq_cu, adq_num, ch)
    hist.setup_tot(ADQAPI, adq_cu, adq_num, ch, hist_tot_scale, hist_tot_offset)
    hist.reset_tot(ADQAPI, adq_cu, adq_num, ch)

# Enable level trig
status = ADQAPI.ADQ_PDEnableLevelTrig(adq_cu, adq_num, 1)
print('ADQAPI.ADQ_PDEnableLevelTrig returned {}'.format(adq_status(status)))

# Enable trigger coincidence
status = ADQAPI.ADQ_PDEnableTriggerCoincidence(adq_cu, adq_num, 1)
print('ADQAPI.ADQ_PDEnableTriggerCoincidence returned {}'.format(adq_status(status)))

# Setup size of transfer buffers
print('Setting up streaming...')
ADQAPI.ADQ_SetTransferBuffers(adq_cu, adq_num, num_transfer_buffers, transfer_buffer_size)
ADQAPI.ADQ_PDSetupStreaming(adq_cu, adq_num, acqs.channels_mask)

# Start streaming
print('Collecting data, please wait...')
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)
ADQAPI.ADQ_StartStreaming(adq_cu, adq_num)

# Allocate target buffers for intermediate data storage
target_buffers = (ct.POINTER(ct.c_int16*transfer_buffer_size)*max_number_of_channels)()
for bufp in target_buffers:
  bufp.contents = (ct.c_int16*transfer_buffer_size)()

# Create some buffers for the full records
data_16bit = [np.array([], dtype=np.int16),
              np.array([], dtype=np.int16),
              np.array([], dtype=np.int16),
              np.array([], dtype=np.int16)]

max_number_of_records = max([cs_all[i].number_of_records for i in range(max_number_of_channels)]) + 2000

for ts in cs_all:
  max_number_of_records = max(max_number_of_records, ts.number_of_records)

# Allocate target buffers for headers
headerbuf_list = [(HEADER*max_number_of_records)() for ch in range(max_number_of_channels)]
# Create an C array of pointers to header buffers
headerbufp_list = ((ct.POINTER(HEADER*max_number_of_records))*max_number_of_channels)()
# Initiate pointers with allocated header buffers
for ch,headerbufp in enumerate(headerbufp_list):
    headerbufp.contents = headerbuf_list[ch]
# Create a second level pointer to each buffer pointer,
# these will only be used to change the bufferp_list pointer values
headerbufvp_list = [ct.cast(ct.pointer(headerbufp_list[ch]), ct.POINTER(ct.c_void_p)) for ch in range(max_number_of_channels)]

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

print('Waiting for data...')

# Collect data until all requested records have been recieved
records_completed = [0, 0, 0, 0]
headers_completed = [0, 0, 0, 0]
records_completed_cnt = 0
ltime = time.time()
buffers_filled = ct.c_uint(0)

while (collecting(cs_all, records_completed)):
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
      success = ADQAPI.ADQ_FlushDMA(adq_cu, adq_num);
      print('ADQAPI.ADQ_FlushDMA returned {}'.format(adq_status(status)))
      poll_time_diff_prev = time.time()

  # Fetch data and headers into target buffers
  status = ADQAPI.ADQ_GetDataStreaming(adq_cu, adq_num,
                                       target_buffers,
                                       headerbufp_list,
                                       acqs.channels_mask,
                                       ct.byref(samples_added),
                                       ct.byref(headers_added),
                                       ct.byref(header_status))
  if status == 0:
    print('GetDataStreaming failed!')
    sys.exit()

  for ch in range(max_number_of_channels):
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
                    ((cs_all[ch].samples_per_record
                      *2
                      *(np.sum(records_completed)-records_completed_cnt))
                      /(dtime))/(1024*1024)))
          sys.stdout.flush()
          records_completed_cnt = np.sum(records_completed)
          ltime = time.time()

    if (samples_added[ch] > 0 and plot_data):
      # Copy channel data to continuous buffer
      data_buf          = np.frombuffer(target_buffers[ch].contents, dtype=np.int16, count=samples_added[ch])
      # data_16bit[ch]    = data_buf
      data_16bit[ch]    = np.append(data_16bit[ch], data_buf)

# Disable trigger
ADQAPI.ADQ_PDEnableLevelTrig(adq_cu, adq_num, 0)

# Stop streaming
ADQAPI.ADQ_StopStreaming(adq_cu, adq_num)

if ext_trig_timestamp_reset:
  status = ADQAPI.ADQ_DisarmTimestampSync(adq_cu, adq_num)
  print('ADQAPI.ADQ_DisarmTimestampSync returned {}'.format(adq_status(status)))

if trigger_blocking:
  gate_count = ADQAPI.ADQ_GetTriggerBlockingGateCount(adq_cu, adq_num)
  print('Gate count: {}'.format(gate_count))

  status = ADQAPI.ADQ_DisarmTriggerBlocking(adq_cu, adq_num)
  print('ADQAPI.ADQ_DisarmTriggerBlocking returned {}'.format(adq_status(status)))

# Print recieved headers
if print_headers:
  for ch in range(max_number_of_channels):
    if cs_all[ch].number_of_records > 0:
      print('------------------')
      print('Headers channel {}'.format(ch))
      print('------------------')
      for rec in range(cs_all[ch].number_of_records):
        header = headerbuf_list[ch][rec]
        print('RecordStatus:  {}'.format(header.RecordStatus))
        print('UserID:        {}'.format(header.UserID))
        print('SerialNumber:  {}'.format(header.SerialNumber))
        print('Channel:       {}'.format(header.Channel))
        print('DataFormat:    {}'.format(header.DataFormat))
        print('RecordNumber:  {}'.format(header.RecordNumber))
        print('Timestamp:     {} ns'.format(header.Timestamp * 0.125))
        print('RecordStart:   {} ns'.format(header.RecordStart * 0.125))
        print('SamplePeriod:  {} ns'.format(header.SamplePeriod * 0.125))
        print('RecordLength:  {} ns'.format(header.RecordLength * (header.SamplePeriod* 0.125)))
        print('MovingAverage: {}'.format(header.MovingAverage))
        print('GateCounter:   {}'.format(header.GateCounter))
        print('------------------')

# Plot data
if plot_data:
  for ch in range(max_number_of_channels):
    if cs_all[ch].number_of_records > 0:
      widths = np.array([], dtype=np.uint32)
      record_end_offset = 0
      # Extract record lengths from headers
      for rec in range(cs_all[ch].number_of_records):
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

if plot_hist:
  for ch in range(max_number_of_channels):
    if cs_all[ch].number_of_records > 0:
      # Fetch histograms
      histogram_tot = hist.fetch_tot(ADQAPI, adq_cu, adq_num, ch+1)
      histogram_tot_np = np.frombuffer(histogram_tot, dtype=np.uint32)
      histogram_extr = hist.fetch_extr(ADQAPI, adq_cu, adq_num, ch+1)
      histogram_extr_np = np.frombuffer(histogram_extr, dtype=np.uint32)
      # Plot TOT values
      plt.figure(max_number_of_channels+(2*ch))
      nof_tot_pulses = histogram_tot_np[-1]
      nof_tot_of_pulses = histogram_tot_np[-2]
      nof_tot_uf_pulses = histogram_tot_np[-3]
      if hist_tot_norm:
          histogram_tot_np = histogram_tot_np[0:-3]/nof_tot_pulses
      x_tot = ((np.arange(len(histogram_tot_np))*1024)/hist_tot_scale)-hist_tot_offset
      plt.vlines(x_tot, np.zeros(len(histogram_tot_np)),histogram_tot_np,'r')
      plt.title('TOT ({:.0f} pulses, {} under, {} over)'.format(nof_tot_pulses, nof_tot_uf_pulses, nof_tot_of_pulses))
      # Plot extreme values
      plt.figure(max_number_of_channels+(2*ch)+1)
      nof_extr_pulses = histogram_extr_np[-1]
      nof_extr_of_pulses = histogram_extr_np[-2]
      nof_extr_uf_pulses = histogram_extr_np[-3]
      if hist_extr_norm:
          histogram_extr_np = histogram_extr_np[0:-3]/nof_extr_pulses
      x_extr = ((np.arange(len(histogram_extr_np))*1024)/hist_extr_scale)-hist_extr_offset
      plt.vlines(x_extr, np.zeros(len(histogram_tot_np)), histogram_extr_np,'g')
      plt.title('Extreme values ({:.0f} pulses, {} under, {} over)'.format(nof_extr_pulses, nof_extr_uf_pulses, nof_extr_of_pulses))

#ADQAPI.ADQ_Blink(adq_cu, adq_num)
ADQAPI.ADQControlUnit_DeleteADQ(adq_cu, adq_num)
# Delete ADQControlunit
ADQAPI.DeleteADQControlUnit(adq_cu)
# Unload ADQAPI
#adqapi_unload(ADQAPI)

print('Done.')
