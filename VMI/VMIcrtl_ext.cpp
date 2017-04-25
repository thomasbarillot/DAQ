//////////////////////////////////////////
//                                      //
//      Driving the framegrabber        //
//          from Matlab                 //
//       use boost library 1.55.0       //
//////////////////////////////////////////


//*// FEW INTRODUCTION COMMENTS: //*//

//*//  - THIS SCRIPT IS THE CENTRAL SCRIPT OF THE DATA ACQUISITION: IT DRIVES THE FRAMEGRABBING, 
//*//  THE DATA PROCESSING (WITH CUDA SCRIPT) AND THE LINK TO MATLAB GUI 
//*//  - COMMENTS ON OR DESCRIPTIONS OF THE CODE ARE BETWEEN //*//
//*//  - CPU MEMORY MEANS COMPUTER MEMORY IN OPPOSITION TO GPU MEMORY WHICH IS NOT ACCESSIBLE EXCEPT THROUGH CUDA FRAMEWORK
//

#include <stdio.h>
#include <windows.h>
#include <process.h>	// allow to create a new thread in the mexfile in charge of the acquisition.
#include <limits>
#include <iostream>
#include <time.h>
#include <stdlib.h>
#include <string.h>
#include <fstream> // include i/o streams to file
#include <cmath> // 

#include "C:\Users\Administrator\Documents\PythonRepositories_Tom\DataAcquisition\VMI\VMIacqPrg_v3Feb2016\include\fgrab_struct.h"
#include "C:\Users\Administrator\Documents\PythonRepositories_Tom\DataAcquisition\VMI\VMIacqPrg_v3Feb2016\include\fgrab_prototyp.h"
#include "C:\Users\Administrator\Documents\PythonRepositories_Tom\DataAcquisition\VMI\VMIacqPrg_v3Feb2016\include\fgrab_define.h"
#include "C:\Users\Administrator\Documents\PythonRepositories_Tom\DataAcquisition\VMI\VMIacqPrg_v3Feb2016\include\SisoDisplay.h"
#include "C:\Users\Administrator\Documents\PythonRepositories_Tom\DataAcquisition\VMI\VMIacqPrg_v3Feb2016\include\clser.h"
#include "C:\Users\Administrator\Documents\PythonRepositories_Tom\DataAcquisition\VMI\CUDA_Processing.hpp"

#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\cuda.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\cuda_runtime.h>

#include <C:\local\boost_1_62_0\boost\thread\thread.hpp>        // Allow to create boost thread for the acquisition
#include <C:\local\boost_1_62_0\boost\chrono\chrono.hpp>
#include <C:\local\boost_1_62_0\boost\python.hpp>
#include <C:\local\boost_1_62_0\boost\python\module.hpp>
#include <C:\local\boost_1_62_0\boost\python\def.hpp>
#include <C:\local\boost_1_62_0\boost\python\suite\indexing\vector_indexing_suite.hpp>

#include <ctime>


//#include <omp.h>        // Parallelisation of the code (available for C++ functions and not mexFunction!!!)
//#include "board_and_dll_chooser.h"

//#include "opencv/build/include/opencv2/opencv.hpp"

//#include "matrix.h"
//#include "mexopencv.hpp"

//#include "mex.h"
//#include "class_handle.hpp"

//using namespace boost::interprocess;
//using namespace std;
// The class that interface Matlab and the FrameGrabber

typedef std::vector<int> ImgArray;


/*  Class Declaration */

//extern std::ofstream mexVMIcrtlLog;

class VMIcrtl       // IFG
{
private:
    
    std::string Logfilename;        // Logfile
	std::string Filename;
	
	/*---- Camera and FrameGrabber properties ---*/
    
    double FramePerSec;         //Camera fps
    
    
    int M_WIDTH;             // ROI width (FrameGrabber)
    int M_HEIGHT;            // ROI height (FrameGrabber)
    
    int threshold;
    
    double ROIx;            // x-Offset  (FrameGrabber)
    double ROIy;            // y-Offset  (FrameGrabber)
    
    
    bool IFG_ACQ_IS_ACTIVE;     //FLAG Aquisition status (1=started,0=stopped)
    bool IFG_ACQ_IS_ACTIVE_PREVIEW; // false if accumulation, true if preview
    bool IFG_ACQ_IS_DONE;       //FLAG Acquisition finished.
    bool IFG_DISPLAY_ACTIVE;
//     bool IFG_ACQ_PREVIEW;     // true if we launched the preview
//     bool IFG_ACQ_RECORD;       // true if we launched an acquisition
    
    int ACQSTOP;
    
    int BUFF_SIZE;                  // Number of frames recorded in FG buffer (must be a multiple of the bunch of frame transfered to GPU (ex:5 frames at a time -> buffer size =20 OK))
    int NB_GRABBED_IMAGES;        // Number of grabbed images by the acquisition
//
    int Grabbed_Pictures;   //Number of acquired pictures
    
    
    int trigger_legacy;
    int trigger_mode1;
    int trigger_mode2;
    int trigger_source;
    int exposure_1;
    int exposure_2;
	int flash_polarity;
    int trigger_exsyncon;
    int trigger_exsyncoff;
	int trigger_strobeon;
	int trigger_strobeoff;


    
    Fg_Struct *fg;          // pointer to the object FrameGrabber
    dma_mem *memhdr;        //pointer to the memory space allocated for the framebuffer
    frameindex_t lastPicNr; // Number of the last picture in the buffer
    
    unsigned int *img_ptr;			// Pointer to the image array
    unsigned char *h_BG_Corrptr;
    __constant__ unsigned char *d_BG_Corrptr;
    unsigned char **h_StreamPtr;          // double pointer to array of frames
    //unsigned int *h_StreamAccPtr;          // double pointer to array of frames
    
    unsigned char *d_Frame_GPUptr;       // one memory segment for grabbed frame
    unsigned int  *d_Accumulated_Picture_GPUptr;  // one memory segment for Accumulated picture
    
    // Declare arrays to stock data fron each frame on device.
    // This Memory will be cleared after each Acquisition and data written on file
    
    unsigned int **d_SSDataStream_ptr;
    unsigned int **d_SSIndexStream_ptr;
    
    
    // parameters are stocked in this array for treatement on the GPU
    long *d_FrameParamptr;      // parameter 1 is the threshold, parameter
    long *Frame_Parametersptr;      // same in host memory
    // [0] -> preview (0) or Accumulation (1)
    // [1] -> Number of Frames/Acquisitions(1->1,000,000)
    // [2] -> threshold (0->255)
    // [3] -> number of active pixels.
    // [4] -> Counting mode on(1) or off(0)
    // [5] -> Last image number
    // [6] -> Nb Counts per Frame (in counting mode)
    // [7] -> Single-Shot VMI mode true or false (if true, data will be stored in a giant vector only)
    // [8] -> nb frames at the moment
    // [9] ->
    // [10] -> TriggerMode (0=Free Run, 1=Laser Triggered)
    
    //string *Filename;
    
    /*---- Output to .txt file (1/2 hour recording <500 Mbytes) ----*/
    
    //ofstream datafilestream;
    
    
    /*---- Declaration of supplementary threads ----*/
    
    // this thread will handle the acquisition leaving matlab free to do something else,
    // manually stop the acquisition by killing it in a second callback to mexfunction;
    
    boost::thread *Fg_Acq_thread;
    //     _                                                            _
    //    / \														   / \
    //   / ! \	the second thread should not communicate with matlab  / ! \
    //  /_____\														 /_____\
    
    /*---- End of declaration of supp threads ----*/
    
public:
    

    
    
    VMIcrtl();      // constructor
    ~VMIcrtl();   // destructor
    
    //ofstream framefile;
    
    /*---- Change of Camera Parameters Methods----*/
    
    bool getStatusIFG(){return IFG_ACQ_IS_DONE;};// return chosen propertie of the class IFG
    void setInitParametersIFG();     // change chosen propertie of the class IFG
	int  GetFrames();
    void GetInfoROI(int&, int&); // Get info about the size and the offset of the ROI.
    void SetAcquisitionParameters(int*);
	void setFilename(const std::string&);
    const char* GetFilename();
    void setThreshold(int);
    void setMedianFilter(int);
    void setNbAcq(int);
    void setCentroiding(int);
    void setTriggerMode(unsigned int);
    void setExposure(int);
    
    /*---- Aquisition Methods ----*/
    
    void StartAcquisition();   //Start the FG acquisition
    void StartAcquisitionPrev(); // Start the FG acquisition preview (no frame saved, just continuous acquisition.)
    void StopAcquisition();  //Stop the FG acquisition
    void GetFrameImagePrev(); // Get Frame for matlab viewer during preview
    void GetFrameImage(); // Get Frame for matlab viewer during acquisition
    //void StackFrames();       // Accumulate Frames to get the final picture
    void StopGrabber();        // Stop FG and release memory
	ImgArray RecallImagePrev();
	ImgArray RecallImage();
	ImgArray RecallBGcorrection();

    void setFlagDisplay();
    void setBGCorrection();
    void GetAcquisitionFlag(unsigned int*);
   
    
    
    
    
    
};

/* Class Functions definitions */

VMIcrtl::VMIcrtl()
{
    /*---- open a logfile ---*/
    //try 
	//{
		
		//mexVMIcrtlLog<<"Open Logfile run number:\n";
//	}
//    catch (int e)
//	{
//		mexVMIcrtlLog.close();
//    	mexVMIcrtlLog.open("VMIelog.log");
//		mexVMIcrtlLog<<"ERROR: logfile was already opened -> Close, erase and reopen\n";
//	}
	
	Logfilename="TimeStampsLog.log";
    Filename="20000000_0000.dat";
	
    /*---- Clean memory just in case ----*/
    
    FramePerSec=500.0;
    
    /*---- Initialise the FrameGrabber ----*/
    
    M_HEIGHT=400;
    M_WIDTH=400;
    threshold=10;
    // Initialise the FrameGrabber and assign a VisualApplet on board 0 (port A);
    if ((fg=Fg_Init("Acq_FullAreaGray8.dll",0))== NULL)
    {
//        mexVMIcrtlLog<<"ERROR: FG init failed ("<<Fg_getLastErrorDescription(fg)<<": "<<Fg_getLastErrorNumber(fg)<<")\n";
        printf("ERROR: FG init failed (%s)",Fg_getLastErrorDescription(fg));
    }
	
	int FGformatresult = 0;
	unsigned int FGformatvalue = FG_GRAY;
	const enum FgParamTypes FGformatype = FG_PARAM_TYPE_UINT32_T;
	if ((FGformatresult = Fg_setParameterWithType(fg,FG_FORMAT, &FGformatvalue, 0, FGformatype)) < 0) 
	{
//		mexVMIcrtlLog<<"ERROR: FG format ("<<Fg_getLastErrorDescription(fg)<<": "<<Fg_getLastErrorNumber(fg)<<")\n";
	}
	

    Fg_setParameter(fg,FG_WIDTH,&M_WIDTH,0); // Set width of the frame
    Fg_setParameter(fg,FG_HEIGHT,&M_HEIGHT,0); // Set height of the frame
    
    IFG_ACQ_IS_ACTIVE=false;
    IFG_ACQ_IS_ACTIVE_PREVIEW=true;
    IFG_ACQ_IS_DONE=false;
    IFG_DISPLAY_ACTIVE=false;
//     IFG_ACQ_PREVIEW=false;
//     IFG_ACQ_RECORD=false;
    
    NB_GRABBED_IMAGES=1000;
    BUFF_SIZE=3200;
    
    /* Noise removal: Set Median filter as default propertie (3x3 matrix and take 4th value) */
    int resultNF=0;
    int valueNF=FG_OFF;
    const enum FgParamTypes typeNF = FG_PARAM_TYPE_UINT32_T;
	
    if ((resultNF = Fg_setParameterWithType(fg,FG_NOISEFILTER, &valueNF, 0, typeNF)) < 0) 
    {
//        mexVMIcrtlLog<<"ERROR: Could not set Noise filtering (Median filtering 3x3) ("<<Fg_getLastErrorDescription(fg)<<": "<<resultNF<<")\n";
    }
    if ((resultNF = Fg_getParameterWithType(fg,FG_NOISEFILTER, &valueNF, 0, typeNF)) < 0) 
    {
//        mexVMIcrtlLog<<"ERROR: Noise filtering (Median filtering 3x3) not ON ("<<Fg_getLastErrorDescription(fg)<<": "<<resultNF<<")\n";
    }
    else
    {
//        mexVMIcrtlLog<<"INITIALISE Noise filtering (Median filtering 3x3) SUCCESS \n";
    }
    /* Threshold can be applied with the framegrabber:
     *The processing parameters use the lookup table for determination of the correction values.
     *For activation of the processing parameters, set FG_LUT_TYPE of category Lookup Table to LUT_TYPE_PROCESSING .
     *Otherwise, parameter changes will have no effect.
     *int result = 0;
     *double value = 0.0;
     *const enum FgParamTypes type = FG_PARAM_TYPE_DOUBLE;
     *if ((result = Fg_setParameterWithType(FG_PROCESSING_OFFSET, &value, 0, type)) < 0) {
     *   }
    
     * if ((result = Fg_getParameterWithType(FG_PROCESSING_OFFSET, &value, 0, type)) < 0) {
     *   }
     */    
    
    
    /* FG_TURBO_DMA_MODE allows to transfer very fast data  from framegrabber to the mainboard */
     int resultTDMA = 0;
     int valueTDMA = FG_OFF;
     const enum FgParamTypes typeTDMA = FG_PARAM_TYPE_UINT32_T;
     if ((resultTDMA = Fg_setParameterWithType(fg,FG_TURBO_DMA_MODE, &valueTDMA, 0, typeTDMA)) < 0)
     {
        //mexVMIcrtlLog<<"ERROR: Could not set TURBO DMA MODE ("<<Fg_getLastErrorDescription(fg)<<": "<<resultTDMA<<")\n";
      }
     if ((resultTDMA = Fg_getParameterWithType(fg,FG_TURBO_DMA_MODE, &valueTDMA, 0, typeTDMA)) < 0)
     {
         //mexVMIcrtlLog<<"ERROR: TURBO DMA MODE not ON ("<<Fg_getLastErrorDescription(fg)<<": "<<resultTDMA<<")\n";
     }
     else
     {
 //        mexVMIcrtlLog<<"INITIALISE: TURBO DMA MODE SUCCESS ("<<resultTDMA<<")\n";
     }
    
    
    /* Note: The trigger board is a I/O TTL trigger board. it gets input TTL signal up to +5V max*/ 
    
    trigger_mode1=FREE_RUN;   // Default free run mode
    trigger_mode2=ASYNC_TRIGGER;   // External trigger mode
    trigger_legacy = FG_ON;
    trigger_exsyncon = FG_ON;
    trigger_exsyncoff = FG_OFF;
	trigger_strobeon = FG_ON;
	trigger_strobeoff = FG_OFF;

    trigger_source=0;   // Trigger source number on the TTl trigger board
    exposure_1=49900;         //exposure in microseconds for Free Run Mode
    exposure_2=500;         //exposure in microseconds for laser triggered
    flash_polarity=1;  // polarity of trigger out signal (1 is high active)

    const enum FgParamTypes typeTRIG= FG_PARAM_TYPE_UINT32_T;
     
    if(Fg_setParameter(fg,FG_TRIGGER_LEGACY_MODE,&trigger_legacy,0)<0)
    {
 //       mexVMIcrtlLog<<"ERROR: init trigger legacy mode not done: "<<Fg_getLastErrorDescription(fg)<<"\n";
    } 
    
    if(Fg_setParameterWithType(fg,FG_TRIGGERMODE,&trigger_mode2,0,typeTRIG)<0)
    {
 //       mexVMIcrtlLog<<"ERROR: init trigger not done: "<<Fg_getLastErrorDescription(fg)<<"\n";
        int result=0;
        result=Fg_setParameter(fg,FG_TRIGGERMODE,&trigger_mode1,0);
//        mexVMIcrtlLog<<"Init free run? code= "<<result<<"\n";
    }
    else
    {
        int result=0;
        result=Fg_setParameter(fg, FG_TRIGGERINSRC, &trigger_source, 0);
//        mexVMIcrtlLog<<"Init Triggersource? code= "<<result<<"\n";
        result=0;
        result=Fg_setParameter(fg,FG_EXPOSURE,&exposure_2,0);
//        mexVMIcrtlLog<<"Init exposure? code= "<<result<<"\n";
    }
	Fg_setParameter(fg,FG_FLASH_POLARITY,&flash_polarity,0);
	Fg_setFlash(fg,trigger_strobeoff,0);
    
    size_t fbuffsize=M_WIDTH*M_HEIGHT*1.0*500;   //size of picture*pixelsize(bytes)*number of subbuffers (or pictures)
    memhdr=Fg_AllocMemEx(fg,fbuffsize,500); // Allocate memory for the FrameBuffer.
    frameindex_t lastPicNr = 0;
    
    
    
    // Check Status of the camera when the object is built
    
    int RS[10];  // return if the parameter has been read correctly (0 ok, other see SiliconSoftware SDK)
    int statut=10;
    int port=10;
    int format=10;
    //double fps=10.0;
    int trig=10;
    int h=10;
    int w=10;
    int px;
    int tt;
    
    
    RS[0]=Fg_getParameter(fg,FG_CAMSTATUS,&statut,0);
    RS[1]=Fg_getParameter(fg,FG_PORT,&port,0);
    RS[2]=Fg_getParameter(fg,FG_FORMAT,&format,0);
    //RS[3]=Fg_getParameter(fg,FG_FRAMESPERSEC,&fps,0);
    RS[4]=Fg_getParameter(fg,FG_TRIGGERMODE,&trig,0);
    RS[5]=Fg_getParameter(fg,FG_HEIGHT,&h,0);
    RS[6]=Fg_getParameter(fg,FG_WIDTH,&w,0);
    
    RS[7]=Fg_getParameter(fg,FG_PIXELDEPTH,&px,0);
    RS[8]=Fg_getParameter(fg,FG_TIMEOUT,&tt,0);
    
//    mexVMIcrtlLog<<"---------------------------------------\n";
//    mexVMIcrtlLog<<"Camera status and properties:\n";
    if(statut==1)
    {
 //       mexVMIcrtlLog<<"--> Camera Status ON (code:"<<RS[0]<<")\n";
 //       mexVMIcrtlLog<<"--> Camera Port: "<<RS[1]<<"\n";
 //       mexVMIcrtlLog<<"--> Image Format: "<<RS[2]<<"\n";
 //       mexVMIcrtlLog<<"--> Trigger Mode: "<<RS[4]<<"\n";
 //       mexVMIcrtlLog<<"--> Image height: "<<RS[5]<<")\n";
 //       mexVMIcrtlLog<<"--> Image width: "<<RS[6]<<")\n";
    }
//	else{mexVMIcrtlLog<<"ERROR: Camera off or not connected\n";}
    
    /* End of Framegrabber Init */
    
    /* Initialisation of the array to contain the image*/
	
	img_ptr=new unsigned int[M_WIDTH*M_HEIGHT];
    
//     printf("<--->NBP7\n");
    
    /* Initialisation of GPU memory (memory allocation) and host pinned memory */
    
    h_BG_Corrptr=new unsigned char[M_WIDTH*M_HEIGHT];
    memset(h_BG_Corrptr,0,M_WIDTH*M_HEIGHT);
    
    h_StreamPtr=new unsigned char*[5];       //Initialise the array of frames to 5 frames

    d_SSDataStream_ptr=new unsigned int*[5];
    d_SSIndexStream_ptr=new unsigned int*[5];
    
    cudaError_t cudaStatus=InitialiseCUDAMem(h_StreamPtr,d_SSDataStream_ptr,d_SSIndexStream_ptr,d_FrameParamptr,d_Frame_GPUptr, d_Accumulated_Picture_GPUptr, M_WIDTH*M_HEIGHT,d_BG_Corrptr);
    if(cudaStatus == cudaSuccess)
    {
//        mexVMIcrtlLog<<"--> INITIALISE CUDA memory SUCCESS \n";
    }
    else if(cudaStatus == cudaErrorMemoryAllocation)
    {
//        mexVMIcrtlLog<<"ERROR: CUDA memory allocation %s \n",cudaStatus;
    }
    
    //initialise data parameters array on host
    Frame_Parametersptr = new long[11];
    Frame_Parametersptr[0]=0;                       // prev (0) or Acq (1)
    Frame_Parametersptr[1]=1;                       // Frames/Acq
    Frame_Parametersptr[2]=10;                      // threshold
    Frame_Parametersptr[3]=M_HEIGHT*M_WIDTH;        // active px
    Frame_Parametersptr[4]=0;                       // Counting Mode
    Frame_Parametersptr[5]=0;                       // Last image number
    Frame_Parametersptr[6]=1;                       // Nb of count per frame
    Frame_Parametersptr[8]=0;                       // Nb frame acq at the moment
    Frame_Parametersptr[9]=0;                       // BG correction
    Frame_Parametersptr[10]=0;                       // ?
     
    
    ACQSTOP=1;
    
    /* End of shared memory init */
    
    /* Open the stream to the recording file */
    
    //datafilestream.open("datafilestream");
    
    /* End of opening of the stream */
    
    
}

VMIcrtl::~VMIcrtl()
{
	delete img_ptr;
    
	//try 
	//{
		//mexVMIcrtlLog.close();
	//}
	//catch (int e)
	//{
	//	printf(" Stream to logfile already closed");
	//}
	
}

void VMIcrtl::SetAcquisitionParameters(int* Ptr1)
{
    // printf("nb grabbed=%i",Ptr1[0]);
    NB_GRABBED_IMAGES=Ptr1[0];
}

void VMIcrtl::StartAcquisition()
{
    /* Start the acquisition, has to be parametrized to grab image at a certain time (wait 2s before start grabbing to synchronize the trigger) */
    
    bool *pAcq=new bool[2];
    int acqstart=1;
    IFG_ACQ_IS_ACTIVE=true;
    IFG_ACQ_IS_ACTIVE_PREVIEW=false;
    pAcq[0]=IFG_ACQ_IS_ACTIVE;
    pAcq[1]=IFG_ACQ_IS_ACTIVE_PREVIEW;
    Frame_Parametersptr[0]=1;
    Frame_Parametersptr[8]=0;
    
    try
    {
        cudaError_t cudaStatus;
        cudaStatus=CUDAresetDataArrays(d_Accumulated_Picture_GPUptr); // fill Accumulated array with zeros on GPU before launching the acquisition
    
        cudaStatus=CUDAbackgroundFrameToGPU(h_BG_Corrptr,d_BG_Corrptr,400*400);// Copy the BG data in the GPU before launching acquistion (save a memory transfer)
    
        if(cudaStatus == cudaSuccess)
        {
//            mexVMIcrtlLog<<"--> INITIALISE Accumulated frame SUCCESS \n";
        }
        else if(cudaStatus == cudaErrorMemoryAllocation)
        {
//            mexVMIcrtlLog<<"ERROR: initialise Accumulated frame \n";
        }
    
        acqstart=Fg_AcquireEx(fg,0,GRAB_INFINITE,ACQ_BLOCK,memhdr);
//        mexVMIcrtlLog<<"Aquisition started?:"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
    }
    catch (int e)
    {
//        mexVMIcrtlLog<<"Error in starting acquisition"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
    }
        
    /* Grab the frames */
    IFG_ACQ_IS_DONE=false;
    ACQSTOP=1;
    try
    {
        Fg_Acq_thread=new boost::thread(boost::bind(&VMIcrtl::GetFrameImage,this)); // initiate the thread with the grabbing function
        
        delete [] pAcq;
        //if(IFG_ACQ_IS_DONE==true){printf("Acquisition DONE\n");Interf_FrameGrabber::StopAcquisition();} // properly stop the thread
    }
    catch (int e)
    {
        
//        mexVMIcrtlLog.close();
    
        delete [] pAcq;
    }
    
    
}

void VMIcrtl::StartAcquisitionPrev()
{
    // if(Fg_Acq_thread!=NULL){delete Fg_Acq_thread;}
    
//	mexVMIcrtlLog<<"*** START ACQUISITION PREVIEW ***\n";
	
    bool *pAcq=new bool[2];
    int acqstart=1;
    IFG_ACQ_IS_ACTIVE=true;
    IFG_ACQ_IS_ACTIVE_PREVIEW=true;
    pAcq[0]=IFG_ACQ_IS_ACTIVE;
    pAcq[1]=IFG_ACQ_IS_ACTIVE_PREVIEW;
    Frame_Parametersptr[0]=0;
    Frame_Parametersptr[8]=0;
    
    cudaError_t cudaStatus;
    cudaStatus=CUDAresetDataArrays(d_Accumulated_Picture_GPUptr); // fill Accumulated array with zeros on GPU before launching the acquisition
    
    cudaStatus=CUDAbackgroundFrameToGPU(h_BG_Corrptr,d_BG_Corrptr,400*400); // Copy the BG data in the GPU before launching acquistion (save a memory transfer)
    
//    if(cudaStatus == cudaSuccess)
//    {
//        mexVMIcrtlLog<<"--> INITIALISE Accumulated frame SUCCESS \n";
//    }
//    else if(cudaStatus == cudaErrorMemoryAllocation)
//    {
//        mexVMIcrtlLog,"ERROR: in initialise Accumulated frame \n";
//    }
    
    /* Start the acquisition, has to be parametrized to grab image at a certain time (wait 2s before start grabbing to synchronize the trigger) */
//    mexVMIcrtlLog<<"Aquisition not started:"<<acqstart<<" (1=OK) \n";
    acqstart=Fg_AcquireEx(fg,0,GRAB_INFINITE,ACQ_STANDARD,memhdr);
//    mexVMIcrtlLog<<"Aquisition started?:"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
    //mexVMIcrtlLog<<"Aquisition started?:"<<acqstart<<" (0=OK) \n";
    
//    mexVMIcrtlLog<<"Frames per seconds:"<<FramePerSec<<"\n";
    
    
    /* Grab the frames in a separate thread*/
    try
    {
        ACQSTOP=1;
        Fg_Acq_thread=new boost::thread(boost::bind(&VMIcrtl::GetFrameImagePrev,this)); // initiate the thread with the grabbing function
        delete [] pAcq;
    }
    catch (int e)
    {
        
//        mexVMIcrtlLog.close();
    
        delete [] pAcq;
    }
    
    
    
}

/* This function transfers grabbed frames for display */

void VMIcrtl::GetFrameImagePrev()
{
     /*LARGE_INTEGER clockFrequency;
     LARGE_INTEGER start;
     LARGE_INTEGER end;
     QueryPerformanceFrequency(&clockFrequency);*/
    std::ofstream mexVMIcrtlLog;
	mexVMIcrtlLog.open(Logfilename);

    cudaError_t cudaStatus;
	unsigned int timestamp;

    int count=0;
    frameindex_t PreviousImageNumber=0;
    
    //*// LOOP INFINITE UNTIL ACQUISITION IS STOPPED //*//
    Fg_setFlash(fg,trigger_strobeon,0);
    while(IFG_ACQ_IS_ACTIVE==true) 
    {
		cudaEvent_t start, stop;
		cudaEventCreate(&start);
		cudaEventCreate(&stop);
		cudaEventRecord(start);

        if(IFG_ACQ_IS_ACTIVE==false){break;}//Fg_Acq_thread->Interruption_point();}
		
		frameindex_t ImNum = Fg_getImage(fg, SEL_ACT_IMAGE,10,0, 10);
		frameindex_t ImNum2 = Fg_getStatus(fg, NUMBER_OF_GRABBED_IMAGES,1,0);
		frameindex_t LastImageNumber=Fg_getLastPicNumberEx(fg,0,memhdr);
		
        //*// PROCESS THE FRAMES RECORDED, SEPARAING CASES WITH LESS THAN 5 FRAMES (MAXIMUM PARALLEL PROCESSING SET WITH CUDA) //*//
        if(Frame_Parametersptr[1]<5)                                        
        {
			
            if((PreviousImageNumber+(Frame_Parametersptr[1]-1))<LastImageNumber)
            {
                Frame_Parametersptr[5]=LastImageNumber;
                for(int j=0;j<Frame_Parametersptr[1];j++)
                {
                //*// PICK FRAME FROM CAMERA TO CPU MEMORY //*//
					try
					{		
						timestamp=Fg_getImageEx(fg,SEL_NUMBER,LastImageNumber,0,0,memhdr);
                        Fg_getParameterEx(fg,FG_TIMESTAMP,&timestamp,0,memhdr,LastImageNumber);
                        mexVMIcrtlLog<<timestamp<<"\n";
						//mexVMIcrtlLog<<"Bufnum"<<timestamp<<" frame number"<<LastImageNumber<<"\n";
						memmove(h_StreamPtr[j],(unsigned char*)Fg_getImagePtrEx(fg,LastImageNumber,0,memhdr),M_WIDTH*M_HEIGHT);
						
						
					}
					catch (int e)
					{
//						mexVMIcrtlLog<<"ERROR grab image:"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
					}
                }
                //*// PARALLEL TREATEMENT OF EACH FRAME //*//
				try
				{
	
					cudaStatus=CUDAProcessingData(h_StreamPtr,d_SSDataStream_ptr,d_SSIndexStream_ptr,img_ptr,d_Frame_GPUptr,d_Accumulated_Picture_GPUptr,M_WIDTH*M_HEIGHT,Frame_Parametersptr,d_FrameParamptr,d_BG_Corrptr);
					count+=Frame_Parametersptr[1];
                    if (cudaStatus != cudaSuccess){throw cudaGetErrorString(cudaStatus);}

                }
				catch (const char* cudaerror)
				{
//					mexVMIcrtlLog<<"ERROR: Cuda failed: "<<cudaerror<<"\n";
				}
            }
        }
        else if((PreviousImageNumber+4)<LastImageNumber)
        {

            Frame_Parametersptr[5]=LastImageNumber; //*// SAVE NUMBER OF LAST FRAME GRABBED //*//
            
            //QueryPerformanceCounter(&start);
            
            for(int i=0;i<5;i++)
            {
            //*// PICK FRAME FROM CAMERA TO CPU MEMORY //*//
				try
				{	
					
					timestamp=LastImageNumber-i;
					Fg_getParameterEx(fg,FG_TIMESTAMP,&timestamp,0,memhdr,LastImageNumber-i);
					mexVMIcrtlLog<<timestamp<<"\n";
					memmove(h_StreamPtr[i],(unsigned char*)Fg_getImagePtrEx(fg,LastImageNumber-i,0,memhdr),M_WIDTH*M_HEIGHT);
						
				}
				catch (int e)
				{
//						mexVMIcrtlLog<<"ERROR grab image:"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
				}
            }
        
            //*// PARALLEL TREATEMENT OF EACH FRAME //*//
			try
			{

				cudaStatus=CUDAProcessingData(h_StreamPtr,d_SSDataStream_ptr,d_SSIndexStream_ptr,img_ptr,d_Frame_GPUptr,d_Accumulated_Picture_GPUptr,M_WIDTH*M_HEIGHT,Frame_Parametersptr,d_FrameParamptr,d_BG_Corrptr);
                if (cudaStatus != cudaSuccess){throw cudaGetErrorString(cudaStatus);}				

			}
			catch (const char* cudaerror)
			{
//				mexVMIcrtlLog<<"ERROR: Cuda failed: "<<cudaerror<<"\n";
			}
            
			
            
            count +=5;
            Frame_Parametersptr[8]=(long) count;
            PreviousImageNumber=LastImageNumber;
            
			
            //if(LastImageNumber==BUFF_SIZE){PreviousImageNumber=0;}
           
		  
		   //QueryPerformanceCounter(&end);
           //double ProcTime= ((double)((end.QuadPart - start.QuadPart) * 1000000 /clockFrequency.QuadPart)) ;
           //mexVMIcrtlLog<<"processus time average ="<<ProcTime<<" microseconds\n";
        }
        
        //*// RESET THE ACCUMULATED IMAGE (ONLY IN PREVIEW) //*//
        if(count>=Frame_Parametersptr[1])
        {
            cudaStatus=CUDAresetDataArrays(d_Accumulated_Picture_GPUptr);
            count=0;
        } 
	
		cudaEventRecord(stop);
		cudaEventSynchronize(stop);
		float milliseconds = 0;
		cudaEventElapsedTime(&milliseconds, start, stop);

		//mexVMIcrtlLog<<"Elapsed time"<<milliseconds<<"\n";
		//mexVMIcrtlLog<<"Effective Bandwidth (GB/s): "<<1.6e5*1*5/(1e-3*milliseconds)/1e9<<"\n";
		
    }
    Fg_setFlash(fg,trigger_strobeoff,0);
    mexVMIcrtlLog.close();
}

/* This function write electron impacts positions in a file */

void VMIcrtl::GetFrameImage()
{
    LARGE_INTEGER start1, end1, start2, end2, clockFrequency;
	
    QueryPerformanceFrequency(&clockFrequency);

    cudaError_t cudaStatus;
    
    unsigned int timestamp;
    
    int count=0;
    frameindex_t PreviousImageNumber=0;
    
    //*// LOOP WHILE THE TOTAL AMOUNT OF FRAMES CHOSEN IS NOT REACHED //*//
    Fg_setFlash(fg,trigger_strobeon,0);
    while(count<Frame_Parametersptr[1]) 
    { 
        if(IFG_ACQ_IS_ACTIVE==false){break;}//Fg_Acq_thread->Interruption_point();}
        frameindex_t ImNum = Fg_getImage(fg, SEL_ACT_IMAGE,10,0, 10);
        frameindex_t ImNum2 = Fg_getStatus(fg, NUMBER_OF_GRABBED_IMAGES,1,0);
        frameindex_t LastImageNumber=Fg_getLastPicNumberEx(fg,0,memhdr);
       
        //*// PROCESS THE FRAMES RECORDED, SEPARATING CASES WITH LESS THAN 5 FRAMES (MAXIMUM PARALLEL PROCESSING SET WITH CUDA) //*//  
        if(Frame_Parametersptr[1]<5)
        {
			//flush the stream to GPU
			/*for(int j=0;j<5;j++)
			{
				h_StreamPtr[j]=NULL;
			}*/
            if((PreviousImageNumber+(Frame_Parametersptr[1]-1))<LastImageNumber)
            {
                Frame_Parametersptr[5]=LastImageNumber;
                for(int j=0;j<Frame_Parametersptr[1];j++)
                {
                //*// PICK FRAME FROM CAMERA TO CPU MEMORY with timestamp //*//
                timestamp=Fg_getImageEx(fg,SEL_NUMBER,LastImageNumber,0,0,memhdr);
                Fg_getParameterEx(fg,FG_TIMESTAMP,&timestamp,0,memhdr,LastImageNumber);
                TimeStampsLog<<timestamp<<"\n";
                memmove(h_StreamPtr[j],(unsigned char*)Fg_getImagePtrEx(fg,LastImageNumber,0,memhdr),M_WIDTH*M_HEIGHT);
				}
                //*// PARALLEL TREATEMENT OF EACH FRAME //*//
                cudaStatus=CUDAProcessingData(h_StreamPtr,d_SSDataStream_ptr,d_SSIndexStream_ptr,img_ptr,d_Frame_GPUptr,d_Accumulated_Picture_GPUptr,M_WIDTH*M_HEIGHT,Frame_Parametersptr,d_FrameParamptr,d_BG_Corrptr);
                count+=Frame_Parametersptr[1];
                
			}
        }
        else if((PreviousImageNumber+4)<LastImageNumber)
        {
       
            Frame_Parametersptr[5]=LastImageNumber; //*// SAVE NUMBER OF LAST FRAME GRABBED //*//
            
            //QueryPerformanceCounter(&start1);
			//QueryPerformanceCounter(&start2);
          
            // Send the frame from framegrabber to GPU for threshold processing.
            
            for(int i=0;i<5;i++)
            {
            //*// PICK FRAME FROM CAMERA TO CPU MEMORY with timestamp//*//
            timestamp=LastImageNumber-i;
            Fg_getParameterEx(fg,FG_TIMESTAMP,&timestamp,0,memhdr,LastImageNumber-i);
            TimeStampsLog<<timestamp<<"\n";
            memmove(h_StreamPtr[i],(unsigned char*)Fg_getImagePtrEx(fg,LastImageNumber-i,0,memhdr),M_WIDTH*M_HEIGHT);
            }
            
            //*// PARALLEL TREATEMENT OF EACH FRAME //*//
            cudaStatus=CUDAProcessingData(h_StreamPtr,d_SSDataStream_ptr,d_SSIndexStream_ptr,img_ptr,d_Frame_GPUptr,d_Accumulated_Picture_GPUptr,M_WIDTH*M_HEIGHT,Frame_Parametersptr,d_FrameParamptr,d_BG_Corrptr);
          
            count +=5;
            Frame_Parametersptr[8]=(long) count;
            PreviousImageNumber=LastImageNumber;
			
			//QueryPerformanceCounter(&end1);
			
            
			//QueryPerformanceCounter(&end2);
            //double ProcTime1= ((double)((end1.QuadPart - start1.QuadPart) * 1000000 /clockFrequency.QuadPart));
			//double ProcTime2= ((double)((end2.QuadPart - start2.QuadPart) * 1000000 /clockFrequency.QuadPart));
			//mexVMIcrtlLog<<"5 frames Process time ="<<ProcTime1<<" microseconds\n";
//            mexVMIcrtlLog<<"5 frames Process time and display ="<<ProcTime2<<" microseconds\n";
			
			
        }
		
		Fg_setStatus(fg, FG_UNBLOCK_ALL,1,0);
        
    }
    Fg_setFlash(fg,trigger_strobeoff,0); /* stop the trigger to the digitizer */
//	mexVMIcrtlLog<<"END OF Acquisition: "<<count<<" images recorded and processed \n";
 
    IFG_ACQ_IS_DONE=true; 
//    mexVMIcrtlLog<<"Acquisition DONE\n";
    VMIcrtl::StopAcquisition(); //*// STOP THE CPU THREAD PROPERLY //*//

    //*// SAVE IMAGE IN FILE NAMED IN MATLAB GUI //*//
    FILE *pFile;
	const char * str = Filename.c_str();
    pFile=fopen(str,"w+");
    for(int j=0;j<M_WIDTH*M_HEIGHT;j++)
    {
    fprintf(pFile,"%i\n",img_ptr[j]);    
    }
    fclose(pFile);
}

void VMIcrtl::StopAcquisition()
{
    if(ACQSTOP==1)
    {  
        bool *pAcq=&IFG_ACQ_IS_ACTIVE;
        IFG_ACQ_IS_ACTIVE=false;
    
//        mexVMIcrtlLog<<"Aquisition not stopped?:"<<ACQSTOP<<" (1=OK) \n";
        Fg_setFlash(fg,trigger_strobeoff,0);
        ACQSTOP=Fg_stopAcquireEx(fg,0,memhdr,STOP_ASYNC);
    
//        mexVMIcrtlLog<<"Aquisition stopped?:"<<ACQSTOP<<" (0=OK) \n";
        
        delete Fg_Acq_thread;
    
    }
}


void VMIcrtl::StopGrabber()
{
    Fg_FreeMemEx(fg,memhdr);    // Free the ressources allowed to the frame grabber.
    Fg_FreeGrabber(fg);
    
    
    cudaError_t cudaStatus=FreeCUDAMem(h_StreamPtr,d_SSDataStream_ptr,d_SSIndexStream_ptr,d_FrameParamptr,d_Frame_GPUptr,d_Accumulated_Picture_GPUptr,d_BG_Corrptr);
    if(cudaStatus == cudaSuccess)
    {
//        mexVMIcrtlLog<<"--> RELEASE Cuda Memory SUCCESS \n";
    }
    else if(cudaStatus == cudaErrorInvalidDevicePointer)
    {
//        mexVMIcrtlLog<<"ERROR: cudaErrorInvalidDevicePointer \n";
    }
    else if(cudaStatus == cudaErrorInitializationError)
    {
//        mexVMIcrtlLog<<"ERROR: cudaErrorInitializationError \n";
    }
    
//     for(int i=0;i<5;i++)
//     {
//         delete h_StreamPtr[i];
//         delete d_SSDataStream_ptr[i];
//         delete d_SSIndexStream_ptr[i];
//     }
    delete h_BG_Corrptr;
    delete [] h_StreamPtr;
    delete [] d_SSDataStream_ptr;
    delete [] d_SSIndexStream_ptr;
    
    
    
    delete [] Frame_Parametersptr;
    
//    mexVMIcrtlLog.close();
    
    
    
   
}
/* Methods to recall image in the viewer */

ImgArray VMIcrtl::RecallImage()
{
	int size = M_WIDTH*M_HEIGHT;
	ImgArray pArray;
	for(int i=0; i<size; ++i)
	{
		pArray.push_back(img_ptr[i]);
	}
	return pArray;
}

ImgArray VMIcrtl::RecallImagePrev()
{
	int size = M_WIDTH*M_HEIGHT;
	ImgArray pArray;
	for(int i=0; i<size; ++i)
	{
		pArray.push_back((int) img_ptr[i]);
	}
	return pArray;
}

ImgArray VMIcrtl::RecallBGcorrection()
{
	int size = M_WIDTH*M_HEIGHT;
	ImgArray pArray;
	for(int i=0; i<size; ++i)
	{
		pArray.push_back((int) h_BG_Corrptr[i]);
	}
	return pArray;
}



/* Methods to get infos */

int VMIcrtl::GetFrames()
{
	return (int) Frame_Parametersptr[8];
}

void VMIcrtl::GetInfoROI(int& MsizeW, int& MsizeH)
{
    MsizeW=M_WIDTH;
    MsizeH=M_HEIGHT;
}
void VMIcrtl::setInitParametersIFG()
{
    
}

void VMIcrtl::setFilename(const std::string &FN)
{
	Filename=FN.c_str();
}

const char* VMIcrtl::GetFilename()
{
	const char * str = Filename.c_str();
	return str;
}

void VMIcrtl::setThreshold(int th)
{
    try
    {
    Frame_Parametersptr[2]=th;
//    mexVMIcrtlLog<<"DEBUG: Threshold set to "<<(long) Frame_Parametersptr[2]<<"\n";
    }
    catch (int e)
    {
//    mexVMIcrtlLog<<"ERROR: memory access violation (set Threshold)\n";
    }

}

void VMIcrtl::setMedianFilter(int MedianFilterStatus)
{
	int NFstatus=MedianFilterStatus;
    
    if(NFstatus==1)
    {
        int resultNF=0;
		unsigned int valueNF=FG_ON;
		const enum FgParamTypes type = FG_PARAM_TYPE_UINT32_T;
        
        if ((resultNF = Fg_setParameterWithType(fg,FG_NOISEFILTER, &valueNF, 0, type)) < 0)
        {
//            mexVMIcrtlLog<<"ERROR: Could not set Noise filtering (Median filtering 3x3) ("<<resultNF<<")\n";
        }
        if ((resultNF = Fg_getParameterWithType(fg,FG_NOISEFILTER, &valueNF, 0, type)) < 0)
        {
//            mexVMIcrtlLog<<"ERROR: Noise filtering (Median filtering 3x3) not ON ("<<resultNF<<")\n";
        }
        else
        {
//            mexVMIcrtlLog<<"Median filter ON\n";
        }
    }
    else
    {
        int resultNF=0;
		unsigned int valueNF=FG_OFF;
		const enum FgParamTypes type = FG_PARAM_TYPE_UINT32_T;
		
        if ((resultNF = Fg_setParameterWithType(fg,FG_NOISEFILTER, &valueNF, 0, type)) < 0)
        {
//            mexVMIcrtlLog<<"ERROR: Could not set Noise filtering (Median filtering 3x3) ("<<resultNF<<")\n";
        }
        if ((resultNF = Fg_getParameterWithType(fg,FG_NOISEFILTER, &valueNF, 0, type)) < 0)
        {
//            mexVMIcrtlLog<<"ERROR: Noise filtering (Median filtering 3x3) not ON ("<<resultNF<<")\n";
        }
        else
        {
//            mexVMIcrtlLog<<"Median filter OFF\n";
        }
    }
}

void VMIcrtl::setNbAcq(int N)
{
    try
    {
        Frame_Parametersptr[1]=N;
//        mexVMIcrtlLog<<"DEBUG: Set Number of frames per Acq "<<(long) Frame_Parametersptr[1]<<"\n";
    }
    catch (int e)
    {
//        mexVMIcrtlLog<<"ERROR: memory access violation (set Nb Acq)\n";
    }
    
}

void VMIcrtl::setCentroiding(int C)
{
    try
    {
        Frame_Parametersptr[4]=C;
//        mexVMIcrtlLog<<"DEBUG: Set Centroiding ON"<<(long) Frame_Parametersptr[1]<<"\n";
    }
    catch (int e)
    {
//        mexVMIcrtlLog<<"ERROR: memory access violation (set Centroiding)\n";
    }
}

void VMIcrtl::setTriggerMode(unsigned int TM)
{
    //Frame_Parametersptr[10]=TM[0];
//    mexVMIcrtlLog<<"Try to switch Free run to triggered or triggered to Free run\n";
    
//    mexVMIcrtlLog<<"DEBUG: Return value from the GUI"<<TM[0]<<"\n";
//    mexVMIcrtlLog<<"DEBUG: Stored value in Frame_Parametersptr"<<Frame_Parametersptr[10]<<"\n";
    
    int trigger_mode_ExtTrig=ASYNC_TRIGGER;
    int trigger_mode_FreeRun=FREE_RUN;
//    mexVMIcrtlLog<<"DEBUG: Value of Async trigger:"<<ASYNC_TRIGGER<<"\n";
//    mexVMIcrtlLog<<"DEBUG: Value of Free Run:"<<FREE_RUN<<"\n";
    const unsigned int CP=0;
//    mexVMIcrtlLog<<"DEBUG: Value of camport:"<<CP<<"\n";
    

    const enum FgParamTypes type = FG_PARAM_TYPE_INT32_T;
    
    if(TM==1)
    {
        
        if(Fg_setParameter(fg,FG_TRIGGERMODE,&trigger_mode_ExtTrig,0)<0)
        {
//            mexVMIcrtlLog<<"ERROR: Trigger mode not set,"<<Fg_getLastErrorDescription(fg)<<", error number:"<<Fg_getLastErrorNumber(fg)<<"\n";
            Fg_setParameter(fg,FG_TRIGGERMODE,&trigger_mode_FreeRun,0);
			Fg_setFlash(fg,trigger_strobeoff,0);
			
        }
        else
        {
            Fg_setParameter(fg,FG_EXSYNCON,&trigger_exsyncon,0);
            Fg_setParameter(fg,FG_EXPOSURE,&exposure_2,0);
            Fg_setParameter(fg,FG_TRIGGERINSRC,&trigger_source,0);
			
//			mexVMIcrtlLog<<"Trigger mode ACTIVE\n";
        }
    }
    else
    {
        int result=0;
        Fg_setParameter(fg,FG_EXSYNCON,&trigger_exsyncoff,0);
        result=Fg_setParameter(fg,FG_TRIGGERMODE,&trigger_mode_FreeRun,0);
		Fg_setFlash(fg,trigger_strobeoff,0);
//        mexVMIcrtlLog<<"Free run mode ACTIVE, code:"<<result<<"\n";
    }       
}


void VMIcrtl::setExposure(int E)
{
    Fg_setParameter(fg,FG_EXSYNCON, &trigger_exsyncoff,0);
    int exposure = E;
//    mexVMIcrtlLog<<"Exposure value attempt "<<exposure<<" microseconds\n";
    if(Fg_setParameter(fg,FG_EXPOSURE, &exposure,0) == FG_OK)
    {
//        mexVMIcrtlLog<<"Exposure set to "<<exposure<<" microseconds\n";
    }
    else
    {
//        mexVMIcrtlLog<<"Exposure not set, default to "<<exposure_2<<" microseconds\n";
        if(Fg_setParameter(fg,FG_EXPOSURE,&exposure_2,0)<0)
        {
//            mexVMIcrtlLog<<"Exposure could not be set to default \n";
        }
    }
    Fg_setParameter(fg,FG_EXSYNCON, &trigger_exsyncon,0);

}

void VMIcrtl::setFlagDisplay()
{
    bool *FD=&IFG_DISPLAY_ACTIVE;
    IFG_DISPLAY_ACTIVE=true;
    
}

void VMIcrtl::setBGCorrection()
{
    /* Start the acquisition, has to be parametrized to grab image at a certain time (wait 2s before start grabbing to synchronize the trigger) */
//    mexVMIcrtlLog<<"BG Referencing started\n";
	 
    int acqstart=1;
    int acqstop=1;
    int count=0;
     
    double* BGtemp= new double[M_WIDTH*M_HEIGHT];
    memset(h_BG_Corrptr,0,M_WIDTH*M_HEIGHT);
     
    Fg_AcquireEx(fg,0,50,ACQ_STANDARD,memhdr);
    frameindex_t LastImageNumber=Fg_getLastPicNumberEx(fg,0,memhdr);
//    mexVMIcrtlLog<<"DEBUG: last image number at acquisition start "<<(int) LastImageNumber<<"\n";
//    mexVMIcrtlLog<<"BGCorrACQ Started ?"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
    //boost::this_thread::sleep(boost::posix_time::seconds(1));
    LastImageNumber=Fg_getLastPicNumberEx(fg,0,memhdr);
//    mexVMIcrtlLog<<"DEBUG: last image number after the 1 second thread pause "<<(int) LastImageNumber<<"\n";
    //*// ACQUIRE THE BACKGROUND WHICH IS AN AVERAGE OF THE BACKGROUND OVER 50 FRAMES, HELPS TO GET SMOOTH IMAGES WITHOUT "GRAIN" //*//
    while(LastImageNumber<50) 
    {
        memmove(h_BG_Corrptr,(unsigned char*)Fg_getImagePtrEx(fg,1,0,memhdr),M_WIDTH*M_HEIGHT);
        count+=1;
        for(int i=0;i<M_WIDTH*M_HEIGHT;i++)
        {
            BGtemp[i]+=(double) h_BG_Corrptr[i];
        }
        //mexVMIcrtlLog<<"DEBUG: Loop on the images grabbed, count = "<<count<<"\n";
		
		if(count>1000){break;}
    }
    for(int i=0;i<M_WIDTH*M_HEIGHT;i++)
    {
        BGtemp[i]=BGtemp[i]/count;
        h_BG_Corrptr[i]=(unsigned char) BGtemp[i];
    }
    
    Fg_stopAcquireEx(fg,0,memhdr,STOP_ASYNC);
    
//	mexVMIcrtlLog<<"BGCorrACQ Stopped ?"<<Fg_getLastErrorDescription(fg)<<" "<<Fg_getLastErrorNumber(fg)<<"\n";
    boost::this_thread::sleep(boost::posix_time::seconds(1));
	
}

void VMIcrtl::GetAcquisitionFlag(unsigned int* Flagptr)
{
    
    if(ACQSTOP==1){Flagptr[0]=0;}
    else{Flagptr[0]=1;}
   
}

using namespace boost::python;

/*--------- Python wrapper for interfacing with GUI ---------*/
BOOST_PYTHON_MODULE(VMIcrtl_ext)
{
	class_<ImgArray>("ImgArray")
		.def(vector_indexing_suite<ImgArray>())
		;

    class_<VMIcrtl>("VMIcrtl")
        .def("getStatusIFG", &VMIcrtl::getStatusIFG)
        .def("setInitParametersIFG", &VMIcrtl::setInitParametersIFG)
        .def("GetInfoROI", &VMIcrtl::GetInfoROI)
        .def("SetAcquisitionParameters", &VMIcrtl::SetAcquisitionParameters)
		.def("setFilename", &VMIcrtl::setFilename)
        .def("GetFilename", &VMIcrtl::GetFilename)
		.def("GetFrames", &VMIcrtl::GetFrames)
        .def("setThreshold", &VMIcrtl::setThreshold)
        .def("setMedianFilter", &VMIcrtl::setMedianFilter)
        .def("setNbAcq", &VMIcrtl::setNbAcq)
        .def("setCentroiding", &VMIcrtl::setCentroiding)
        .def("setTriggerMode", &VMIcrtl::setTriggerMode)
        .def("setExposure", &VMIcrtl::setExposure)
        
        .def("StartAcquisition", &VMIcrtl::StartAcquisition)
        .def("StartAcquisitionPrev", &VMIcrtl::StartAcquisitionPrev)
        .def("StopAcquisition", &VMIcrtl::StopAcquisition)
        .def("GetFrameImagePrev", &VMIcrtl::GetFrameImagePrev)
        .def("GetFrameImage", &VMIcrtl::GetFrameImage)
        //.def("StackFrames", &VMIcrtl::StackFrames)
        .def("StopGrabber", &VMIcrtl::StopGrabber)
		.def("RecallImagePrev", &VMIcrtl::RecallImagePrev)
		.def("RecallImage", &VMIcrtl::RecallImage)
		.def("RecallBGcorrection", &VMIcrtl::RecallBGcorrection)
        .def("setFlagDisplay", &VMIcrtl::setFlagDisplay)
        .def("setBGCorrection", &VMIcrtl::setBGCorrection)
        .def("GetAcquisitionFlag", &VMIcrtl::GetAcquisitionFlag)
        ;
}