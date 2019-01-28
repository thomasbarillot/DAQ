import ctypes as ct
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

# Setup for individual channels, these are default values
class channel_setup:
  def __init__(self, channel):
    # Set channel
    self.channel = channel
    # Set bit corresponding to channel in mask
    self.coincidence_masking_expression  = 2**channel
  # Default values for all members
  channel                         = 0
  trig_level                      = 0
  reset_hysteresis                = 0
  trigger_arm_hysteresis          = 0
  reset_arm_hysteresis            = 0
  # 1: Rising, 0: Falling
  trigger_polarity                = 1
  reset_polarity                  = 0
  coincidence_window_length       = 1000
  coincidence_masking_expression  = 0
  number_of_records               = 1
  record_variable_length          = 1
  nof_pretrigger_samples          = 0
  nof_moving_average_samples      = 0
  moving_average_delay            = 0
  samples_per_record              = 1024
  # = Record size if record_variable_length is 0
  trailing_edge_window            = samples_per_record

# Common setup for acquisition, these are default values
class acquisition_setup:
  # Collect data from all four channels
  channels_mask = 0b1111

# Define the record header struct
class HEADER(ct.Structure):
  _fields_ = [("RecordStatus", ct.c_ubyte),
              ("UserID", ct.c_ubyte),
              ("Channel", ct.c_ubyte),
              ("DataFormat", ct.c_ubyte),
              ("SerialNumber", ct.c_uint32),
              ("RecordNumber", ct.c_uint32),
              ("SamplePeriod", ct.c_int32),
              ("Timestamp", ct.c_int64),
              ("RecordStart", ct.c_int64),
              ("RecordLength", ct.c_uint32),
              ("MovingAverage", ct.c_int16),
              ("GateCounter", ct.c_uint16)]

# This function loads the ADQAPI library using ctypes
def adqapi_load():
    if os.name == 'nt':
        ADQAPI = ct.cdll.LoadLibrary('ADQAPI.dll')
    else:
        ADQAPI = ct.cdll.LoadLibrary('libadq.so')

    # Manually set return type from some ADQAPI functions
    ADQAPI.CreateADQControlUnit.restype = ct.c_void_p
    ADQAPI.ADQ_GetRevision.restype = ct.c_void_p
    ADQAPI.ADQ_GetPtrStream.restype = ct.POINTER(ct.c_int16)
    ADQAPI.ADQControlUnit_FindDevices.argtypes = [ct.c_void_p]

    # Print ADQAPI revision
    print('ADQAPI loaded, revision {:d}.'.format(ADQAPI.ADQAPI_GetRevision()))

    return ADQAPI

# This function unloads the ADQAPI library using ctypes
def adqapi_unload(ADQAPI):
    if os.name == 'nt':
        # Unload DLL
        ct.windll.kernel32.FreeLibrary(ADQAPI._handle)

# Convenience function when printing status from ADQAPI functions
def adq_status(status):
  if (status==0):
    return 'FAILURE'
  else:
    return 'OK'

# Print revision info for an ADQ device
def print_adq_device_revisions(ADQAPI, adq_cu, adq_num):
    # Get revision info from ADQ
    rev = ADQAPI.ADQ_GetRevision(adq_cu, adq_num)
    revision = ct.cast(rev,ct.POINTER(ct.c_int))
    print('\nConnected to ADQ #{:d}'.format(adq_num))
    # Print revision information
    print('FPGA Revision: {}'.format(revision[0]))
    if (revision[1]):
        print('Local copy')
    else:
        print('SVN Managed')
        if (revision[2]):
            print('Mixed Revision')
        else :
            print('SVN Updated')
            print('')

# This function sets an alternating background color for a matplotlib plot
def alternate_background(ax, start_point, widths, labels=False,
                         color='#dddddd'):

    ax.relim()
    # update ax.viewLim using the new dataLim
    ax.autoscale_view()
    plt.draw()

    # Calculate starting points
    edges = start_point+np.cumsum(np.append([0],widths))
    # Set plot x axis length
    ax.set_xlim(start_point, edges[-1])
    ylim=ax.get_ylim()
    # Draw colored fields for every other width
    for idx in range(1,len(edges)-1,2):
        ax.add_patch(
            patches.Rectangle(
                (edges[idx], ylim[0]), # point(x,y)
                widths[idx], # width
                ylim[1]-ylim[0], # height
                facecolor=color,
                edgecolor='none',
                zorder=-20
                )
            )
    # Optionally draw labels
    if labels==True:
        for idx in range(0,len(edges)-1):
            # Set y-position 1% under top
            ypos=(ylim[1])-0.01*(ylim[1]-ylim[0])
            # Enumerate fields
            plt.text(edges[idx], ypos,
                     'R{}'.format(idx), verticalalignment='top')

def collecting(channel_setup, records_completed):
  state = False

  for ch in range(len(channel_setup)):
    state = state or (records_completed[ch] < channel_setup[ch].number_of_records)

  return state

def print_event_counters(adqapi, adq_cu, adq_num):
  status          = ct.c_uint()
  lt_tevent_ctr   = ct.c_uint()
  lt_revent_ctr   = ct.c_uint()
  ul_tevent_ctr   = ct.c_uint()
  ul_revent_ctr   = ct.c_uint()
  pt_tevent_ctr   = ct.c_uint()
  pt_revent_ctr   = ct.c_uint()
  acq_tevent_ctr  = ct.c_uint()
  acq_revent_ctr  = ct.c_uint()
  acq_revent_pt_ctr  = ct.c_uint()
  status = adqapi.ADQ_PDGetEventCounters(adq_cu, adq_num,
                                         ct.byref(lt_tevent_ctr),
                                         ct.byref(lt_revent_ctr),
                                         ct.byref(ul_tevent_ctr),
                                         ct.byref(ul_revent_ctr),
                                         ct.byref(pt_tevent_ctr),
                                         ct.byref(pt_revent_ctr),
                                         ct.byref(acq_tevent_ctr),
                                         ct.byref(acq_revent_ctr),
                                         ct.byref(acq_revent_pt_ctr))
  print('ADQAPI.ADQ_PDGetEventCounters returned {}'.format(adq_status(status)))
  print('LT tevent ctr:    {}'.format(lt_tevent_ctr.value))
  print('LT revent ctr:    {}'.format(lt_revent_ctr.value))
  print('UL tevent ctr:    {}'.format(ul_tevent_ctr.value))
  print('UL revent ctr:    {}'.format(ul_revent_ctr.value))
  print('PT tevent ctr:    {}'.format(pt_tevent_ctr.value))
  print('PT revent ctr:    {}'.format(pt_revent_ctr.value))
  print('AQ tevent ctr:    {}'.format(acq_tevent_ctr.value))
  print('AQ revent ctr:    {}'.format(acq_revent_ctr.value))
  print('AQ revent pt ctr: {}'.format(acq_revent_pt_ctr.value))
  return
