#
# (C)opyright 2015 Signal Processing Devices Sweden AB
#
# This script showcases in Python
# - How to connect to ADQ devices in Python
# - Upload of waveforms to the SDR14
# - Using a playlist on the SDR14
# - How to setup an acquisition of data
# - How to read data by GetData API in Python
# - How to plot data in Python
#
# Note: The example is intended to use the SDR14 device connected in loopback mode (i.e. connect DAC output to ADC input)

import numpy as np
import ctypes as ct
import matplotlib.pyplot as plt


def set_playlist( adq_cu, adq_num, dac_id, tcstr ):
    
    tc = {}

    if (tcstr == 'basic1'):
        ns = 2 # Number of items
        tc["ns"] = ns
        #                                          1      2      3      4       5      6      7      8       9
        tc["index"] =      (ct.c_uint32 * ns)(     1,     2)
        tc["segment"] =    (ct.c_uint32 * ns)(     1,     2)
        tc["next"] =       (ct.c_uint32 * ns)(     2,     1)
        tc["wrap"] =       (ct.c_uint32 * ns)(     4,     3)
        tc["ulsign"] =     (ct.c_uint32 * ns)(     0,     0)
        tc["trigtype"] =   (ct.c_uint32 * ns)(     1,     1)    
        tc["triglength"] = (ct.c_uint32 * ns)(    50,    50)
        tc["trigpolarity"]=(ct.c_uint32 * ns)(     0,     0)
        tc["trigsample"]=  (ct.c_uint32 * ns)(     1,     1)
        tc["writemask"]=   (ct.c_uint32 * ns)(    15,    15)
        
    
    # Transfer playlist to device
    ADQAPI.ADQ_AWGWritePlaylist( adq_cu, adq_num, dac_id, tc['ns'], ct.byref(tc['index']), ct.byref(tc['writemask']), ct.byref(tc['segment']), ct.byref(tc['wrap']), ct.byref(tc['next']), ct.byref(tc['trigtype']), ct.byref(tc['triglength']), ct.byref(tc['trigpolarity']), ct.byref(tc['trigsample']), ct.byref(tc['ulsign']) )

    # Select the Playlist mode 
    ADQAPI.ADQ_AWGPlaylistMode( adq_cu, adq_num, dac_id, 1)

    return tc

def lessen_to_14bits( databuf ):

    for x in range(0,4096):
        databuf[x] = databuf[x] & 0x3FFF;

    return databuf

def define_and_upload_segments( adq_cu, adq_num, dac_id ):
    # Setup target buffers for upload of data
    number_of_data_segments = 3
    data_length = 4096
    data_buffers=(ct.POINTER(ct.c_int16*data_length)*number_of_data_segments)()
    
    databuf = np.zeros((number_of_data_segments,data_length))

    for bufp in data_buffers:
        bufp.contents = (ct.c_int16*data_length)()
 
    # Re-arrange data in numpy arrays
    databuf = np.frombuffer(data_buffers[0].contents,dtype=np.int16)
    
    #Create sawtooth    
    for x in range(0, 1024):
        databuf[x] = x
        databuf[x+1024] = 1024 - x
        databuf[x+2048] = -x
        databuf[x+2048+1024] = -1024 + x
    databuf = lessen_to_14bits(databuf)
        
    databuf = np.frombuffer(data_buffers[1].contents,dtype=np.int16)
    #Create positive pulse    
    for x in range(0, 128):
        databuf[x] = 1024+x
        databuf[x+128] = 1300+x
        databuf[x+256] = 1300+128-x
    for x in range(384, 4096):
        databuf[x] = 0
    databuf = lessen_to_14bits(databuf)

    #Create negative pulse (one level)   
    databuf = np.frombuffer(data_buffers[2].contents,dtype=np.int16) 
    for x in range(0, 256):
        databuf[x] = -512
    for x in range(256, 4096):
        databuf[x] = 0
    databuf = lessen_to_14bits(databuf)
             

    length_np = (ct.c_uint32 * number_of_data_segments)(data_length, data_length, data_length)
    segId_np = (ct.c_uint32 * number_of_data_segments)(1, 2, 3)
    NofLaps_np = (ct.c_uint32 * number_of_data_segments)(3, 3, 3)
            
    for idx,bufp in enumerate(data_buffers):
        ADQAPI.ADQ_AWGSegmentMalloc( adq_cu, adq_num, dac_id, idx+1, length_np[idx], 0)
    
    ADQAPI.ADQ_AWGWriteSegments( adq_cu, adq_num, dac_id, number_of_data_segments, ct.byref(segId_np), ct.byref(NofLaps_np), ct.byref(length_np), data_buffers )

    # Note: In playlist mode, all used segments must be in the enabled range, otherwise plaqyback will stop
    ADQAPI.ADQ_AWGEnableSegments( adq_cu, adq_num, dac_id, number_of_data_segments )
    return

# For Python under Linux (uncomment in Linux)
#ADQAPI = ct.cdll.LoadLibrary("libadq.so")
# For Python under Windows
ADQAPI = ct.cdll.LoadLibrary("ADQAPI.dll")
ADQAPI.ADQAPI_GetRevision()


# Manually set return type from some ADQAPI functions
ADQAPI.CreateADQControlUnit.restype = ct.c_void_p
ADQAPI.ADQ_GetRevision.restype = ct.c_void_p
ADQAPI.ADQ_GetPtrStream.restype = ct.POINTER(ct.c_int16)
ADQAPI.ADQControlUnit_FindDevices.argtypes = [ct.c_void_p]

# Create ADQControlUnit
adq_cu = ct.c_void_p(ADQAPI.CreateADQControlUnit())
ADQAPI.ADQControlUnit_EnableErrorTrace(adq_cu, 3, '.')
adq_num = 1
dac_id = 1
bypass_analog = 1


# Convenience function
def adq_status(status):
    if (status==0):
        return 'FAILURE'
    else:
        return 'OK'  

# Find ADQ devices
ADQAPI.ADQControlUnit_FindDevices(adq_cu)
n_of_ADQ  = ADQAPI.ADQControlUnit_NofADQ(adq_cu)
print('Number of ADQ found:  {}'.format(n_of_ADQ))

if n_of_ADQ > 0:
    # Get revision info from ADQ
    rev = ADQAPI.ADQ_GetRevision(adq_cu, adq_num)
    revision = ct.cast(rev,ct.POINTER(ct.c_int))
    print('\nConnected to ADQ #1')
    # Print revision information
    print('FPGA Revision: {}'.format(revision[0]))
    if (revision[1]):
        print('Local copy')
    else :
        print('SVN Managed')
        if (revision[2]):
            print('Mixed Revision')
        else :
            print('SVN Updated')
            print('')


    # Choose whether to bypass_analog
    ADQAPI.ADQ_WriteRegister(adq_cu, adq_num, 10240, 0, 2*bypass_analog);
    
    # Upload data to SDR14
    define_and_upload_segments(adq_cu, adq_num, dac_id)
    set_playlist(adq_cu, adq_num, dac_id, 'basic1')
        
    ADQAPI.ADQ_AWGAutoRearm(adq_cu, adq_num, dac_id, 1)
    ADQAPI.ADQ_AWGContinuous(adq_cu, adq_num, dac_id, 0)
    ADQAPI.ADQ_AWGSetTriggerEnable(adq_cu, adq_num, 31)
    ADQAPI.ADQ_AWGArm(adq_cu, adq_num, dac_id)
    #ADQAPI.ADQ_AWGTrig(adq_cu, adq_num, dac_id)
    
    # Set clock source
    ADQ_CLOCK_INT_INTREF = 0
    ADQAPI.ADQ_SetClockSource(adq_cu, adq_num, ADQ_CLOCK_INT_INTREF);

    # Set trig mode
    SW_TRIG = 1
    EXT_TRIG_1 = 2
    EXT_TRIG_2 = 7
    EXT_TRIG_3 = 8
    LVL_TRIG = 3
    INT_TRIG = 4
    LVL_FALLING = 0
    LVL_RISING = 1
    trigger = SW_TRIG
    success = ADQAPI.ADQ_SetTriggerMode(adq_cu, adq_num, trigger)
    if (success == 0):
        print('ADQ_SetTriggerMode failed.')
        
    number_of_records = 1
    samples_per_record = 65536
        
    # Start acquisition
    ADQAPI.ADQ_MultiRecordSetup(adq_cu, adq_num,
                                number_of_records,
                                samples_per_record)
    ADQAPI.ADQ_DisarmTrigger(adq_cu, adq_num)
    ADQAPI.ADQ_ArmTrigger(adq_cu, adq_num)
    
    while(ADQAPI.ADQ_GetAcquiredAll(adq_cu,adq_num) == 0):
        if (trigger == SW_TRIG):
            ADQAPI.ADQ_SWTrig(adq_cu, adq_num)
        print('Waiting for trigger')

    # Setup target buffers for data
    max_number_of_channels = 2
    target_buffers=(ct.POINTER(ct.c_int16*samples_per_record*number_of_records)*max_number_of_channels)()
    for bufp in target_buffers:
        bufp.contents = (ct.c_int16*samples_per_record*number_of_records)()

    # Get data from ADQ
    ADQ_TRANSFER_MODE_NORMAL = 0
    ADQ_CHANNELS_MASK = 0x3
    status = ADQAPI.ADQ_GetData(adq_cu, adq_num, target_buffers,
                                samples_per_record*number_of_records, 2,
                                0, number_of_records, ADQ_CHANNELS_MASK,
                                0, samples_per_record, ADQ_TRANSFER_MODE_NORMAL);
    print('ADQ_GetData returned {}'.format(adq_status(status)))

    # Re-arrange data in numpy arrays
    data_16bit_ch0 = np.frombuffer(target_buffers[0].contents[0],dtype=np.int16)
    data_16bit_ch1 = np.frombuffer(target_buffers[1].contents[0],dtype=np.int16)

    # Plot data
    if True:
        plt.figure(1)
        plt.clf()
        plt.plot(data_16bit_ch0, '.-')
        plt.plot(data_16bit_ch1, '.--')
        plt.show()

    # Only disarm trigger after data is collected
    ADQAPI.ADQ_DisarmTrigger(adq_cu, adq_num)
    ADQAPI.ADQ_MultiRecordClose(adq_cu, adq_num);

    # Delete ADQControlunit
    ADQAPI.DeleteADQControlUnit(adq_cu);

    print('Done')

else:
    print('No ADQ connected.')

# This can be used to completely unload the DLL in Windows
#ct.windll.kernel32.FreeLibrary(ADQAPI._handle)


