from ctypes import *
ADQAPI = cdll.LoadLibrary("ADQAPI.dll")

ADQAPI.CreateADQControlUnit.restype = c_void_p
ADQAPI.SDR14_GetRevision.restype = c_void_p
ADQAPI.ADQControlUnit_FindDevices.argtypes = [c_void_p]

print 'SDR14 Python example'

# Creating control unit
adq_cu = c_void_p(ADQAPI.CreateADQControlUnit())

# Finding devices
ADQAPI.ADQControlUnit_FindDevices(adq_cu)

# Print number of SDR14 found
n_of_SDR14  = ADQAPI.ADQControlUnit_NofSDR14(adq_cu)
print 'Number of SDR14 found:  ', n_of_SDR14

if (n_of_SDR14 != 0):
    rev = ADQAPI.SDR14_GetRevision(adq_cu,1)
    revision = cast(rev,POINTER(c_int))
    print '\nConnected to SDR14 #1'
    # Print revision information
    print 'FPGA Revision: ', revision[0]
    if (revision[1]):
        print 'Local copy'
    else :
        print 'SVN Managed'
    if (revision[2]):
        print 'Mixed Revision'
    else :
            print 'SVN Updated'
    print ''
    
    # Setup board
    SW_TRIG=1
    ADQAPI.SDR14_SetTriggerMode(adq_cu,1, SW_TRIG)
    number_of_records=2
    samples_per_record=6000
    ADQAPI.SDR14_MultiRecordSetup(adq_cu,1,number_of_records,samples_per_record)

    print 'Automatically triggering your device to collect data'
    ADQAPI.SDR14_DisarmTrigger(adq_cu,1)
    ADQAPI.SDR14_ArmTrigger(adq_cu,1)
    ADQAPI.SDR14_SWTrig(adq_cu,1)
    trig=0
    while (trig == 0) :
        trig = ADQAPI.SDR14_GetTrigged(adq_cu,1)
        ADQAPI.SDR14_SWTrig(adq_cu,1)

    # Get data
    outfile_a = open("dataA.out", "w");
    outfile_b = open("dataB.out", "w");

    d_ptr_a = ADQAPI.SDR14_GetPtrData(adq_cu,1,1)
    data_ptr_a = cast(d_ptr_a,POINTER(c_short))
    d_ptr_b = ADQAPI.SDR14_GetPtrData(adq_cu,1,2)
    data_ptr_b = cast(d_ptr_b,POINTER(c_short))

    print 'Collecting data, please wait...'
    n_records_collect = number_of_records

    for i in range(0,n_records_collect) :
        samples_to_collect = samples_per_record;
        while samples_to_collect > 0 :
            collect_result = ADQAPI.SDR14_CollectRecord(adq_cu,1, i)
            samples_in_buffer = min(ADQAPI.SDR14_GetSamplesPerPage(adq_cu,1), samples_to_collect)
            if (collect_result) :
                for channel in range(0,2) :
                    for j in range(0,samples_in_buffer) :                        
                        if(channel == 0) :
                            outfile_a.write('%d\n' % data_ptr_a[j])
                        else :
                            outfile_b.write('%d\n' % data_ptr_b[j])
                samples_to_collect -= samples_in_buffer;
            else :
                print 'Collect next data page failed!'
                samples_to_collect = 0
                i = n_records_collect

    # Only disarm trigger after data is collected
    ADQAPI.SDR14_DisarmTrigger(adq_cu,1)

    print 'Samples stored in data.out.'

    outfile_a.close
    outfile_b.close
    
    print 'Delete control unit...'
    ADQAPI.DeleteADQControlUnit(adq_cu);

    
else :
    print 'No SDR14 found'
    
print 'Done'
