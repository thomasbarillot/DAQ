#  Module fwpd_histogram
import ctypes as ct
import time
from modules.example_helpers import *


def enable_characterization(ADQAPI, adq_cu, adq_num, channel, enable, only_metadata):
    # Enable logic and release reset
    assert (channel < 5 and channel > 0), "Channel must be between 1-4."
    # Lookup base address for histogram setup registers
    base_addr = (channel-1) * (2**(21-2-2)) + 1*(2**(21-2-4))
    # Pull reset (create a negedge)
    ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffffd, 0x00000002, 0)
    ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffffd, 0x00000000, 0)
    # Enable characterization if 'enable' is True
    if enable:
        ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffff9, 0x00000002, 0)
    else:
        ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffff9, 0x00000006, 0)
        
    #  Enable metadata mode if 'only_metadata' is True
    if only_metadata:
        ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffff7, 0x00000008, 0)
    else:
        ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffff7, 0x00000000, 0)
        
    # Strobe register load bit (for enable)
    ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffffe, 0x00000001, 0)
    ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0xfffffffe, 0x00000000, 0)

def _setup(ADQAPI, adq_cu, adq_num, base_addr, scale, offset):
    # Set histogram bin scaling
    ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr, 0x00000000, scale, 0)
    # Set histogram bin offset
    ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr+1, 0x00000000, offset, 0)
    
def _reset(ADQAPI, adq_cu, adq_num, base_addr, hist_size):
    # Write zero to all bins

    if ADQAPI.ADQ_IsUSB3Device(adq_cu, adq_num):
      zero_block = (ct.c_uint32*hist_size)()
      ct.memset(ct.byref(zero_block), 0, hist_size)
      status = ADQAPI.ADQ_WriteBlockUserRegister(adq_cu, adq_num, 2, base_addr, ct.byref(zero_block), hist_size*4, 1)
      print('ADQAPI.ADQ_WriteBlockUserRegister returned {}'.format(adq_status(status)))
    else:
      for idx in range(hist_size):
        ADQAPI.ADQ_WriteUserRegister(adq_cu, adq_num, 2, base_addr+idx,  0x0, 0x0, 0)
    
def _fetch(ADQAPI, adq_cu, adq_num, base_addr, hist_size):
    # Fetch data from histogram memory
    hist = (ct.c_uint32*hist_size)()

    if ADQAPI.ADQ_IsUSB3Device(adq_cu, adq_num):
      ADQAPI.ADQ_ReadBlockUserRegister(adq_cu, adq_num, 2, base_addr, ct.byref(hist), hist_size*4, 1)
    else:
      value = ct.c_uint32()
      for idx in range(hist_size):
        ADQAPI.ADQ_ReadUserRegister(adq_cu, adq_num, 2, base_addr+idx,  ct.byref(value))
        hist[idx] = value.value

    return hist

def _get_mem_base(channel, hist_type):
    # Lookup base address for histogram memory
    assert (channel < 5 and channel > 0), "Channel must be between 1-4."

    if (hist_type == 'tot'):
        return (channel-1) * (2**(21-2-2)) + 2*(2**(21-2-4))
    if (hist_type == 'extr'):
        return (channel-1) * (2**(21-2-2)) + 3*(2**(21-2-4))
    else:
        assert False, "Unknown hist_type {}.".format(hist_type)
        
def _get_setup_base(channel, hist_type):
    # Lookup base address for histogram setup registers
    assert (channel < 5 and channel > 0), "Channel must be between 1-4."

    if (hist_type == 'tot'):
        return (channel-1) * (2**(21-2-2)) + 1*(2**(21-2-4)) + 1
    if (hist_type == 'extr'):
        return (channel-1) * (2**(21-2-2)) + 1*(2**(21-2-4)) + 4
    else:
        assert False, "Unknown hist_type {}.".format(hist_type)

def _get_hist_size(hist_type):
    # Lookup histogram size
    if (hist_type == 'tot'):
        # TOT histogram is 4k+3 bins
        return 1024*16+3
    if (hist_type == 'extr'):
        # TOT histogram is 16k+3 bins
        return 1024*4+3
    else:
        assert False, "Unknown hist_type {}.".format(hist_type)

def setup_tot(ADQAPI, adq_cu, adq_num, channel, scale, offset):
    return _setup(ADQAPI, adq_cu, adq_num, _get_setup_base(channel, 'tot'), scale, offset)

def setup_extr(ADQAPI, adq_cu, adq_num, channel, scale, offset):
    return _setup(ADQAPI, adq_cu, adq_num, _get_setup_base(channel, 'extr'), scale, offset)

def reset_tot(ADQAPI, adq_cu, adq_num, channel):
    return _reset(ADQAPI, adq_cu, adq_num, _get_mem_base(channel, 'tot'), _get_hist_size('tot'))

def reset_extr(ADQAPI, adq_cu, adq_num, channel):
    return _reset(ADQAPI, adq_cu, adq_num, _get_mem_base(channel, 'extr'), _get_hist_size('extr'))

def fetch_tot(ADQAPI, adq_cu, adq_num, channel):
    return _fetch(ADQAPI, adq_cu, adq_num, _get_mem_base(channel, 'tot'),  _get_hist_size('tot'))

def fetch_extr(ADQAPI, adq_cu, adq_num, channel):
    return _fetch(ADQAPI, adq_cu, adq_num, _get_mem_base(channel, 'extr'),  _get_hist_size('extr'))
