//////////////////////////////////////////////
//                                          //
//  delocalisation of the data treatement   // 
//     on the GPU with CUDA framework       //
//                                          //
////////////////////////////////////////////// 
//#if defined(_MSC_VER)


#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\cuda.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\cuda_runtime.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\host_vector.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\device_vector.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\reduce.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\count.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\copy.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\execution_policy.h>
#include <C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v6.0\include\thrust\device_ptr.h>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <fstream>

/*-------- CUDA Kernel --------*/

/* Copy data from CPU to GPU */

// Initialise the arrays and streams that are gonna be used by CUDA on the GPU
cudaError_t InitialiseCUDAMem(unsigned char **& h_StreamPtr, unsigned int **& d_SSDataStream_ptr, unsigned int **& d_SSIndexStream_ptr, long *& d_FrameParamPtr, unsigned char *& d_FramePtr, unsigned int *& d_PicturePtr, int Nbytes, unsigned char *& d_BGCorr);
cudaError_t FreeCUDAMem(unsigned char **h_StreamPtr, unsigned int **d_SSDataStream_ptr, unsigned int **d_SSIndexStream_ptr, long *d_FrameParamPtr, unsigned char *d_FramePtr, unsigned int *d_PicturePtr, unsigned char *d_BGCorr);

// Fill the accumulated picture with zeros (Called at the starting onf acquisition either in preview or Acq)
cudaError_t CUDAresetDataArrays(unsigned int *d_PicturePtr);

// Save the background to substract in the GPU memory
cudaError_t CUDAbackgroundFrameToGPU(unsigned char *h_BGCorr, unsigned char *d_BGCorr,  int Nbytes);

// Regroup the processing of the data.
cudaError_t CUDAProcessingData(unsigned char **h_StreamPtr, unsigned int **d_SSDataStream_ptr, unsigned int **d_SSIndexStream_ptr,unsigned int *SharedMem, unsigned char *d_FramePtr, unsigned int *d_PicturePtr, int Nbytes, long *h_FrameParamPtr, long *d_FrameParamPtr, unsigned char *d_BGCorr);

//#endif