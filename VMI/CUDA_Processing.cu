//////////////////////////////////////////////
//                                          //
//  delocalisation of the data treatement   //
//     on the GPU with CUDA framework       //
//                                          //
//////////////////////////////////////////////

#include "CUDA_Processing.hpp"

/*---------------- GLOBAL VARIABLES TO BE USED ON THE GPU ------------------------------*/




/*----------------------------------------------------------------------------------------*/
/*----------------------------------------------------------------------------------------*/
/*----------------------------- CUDA KERNELS DEFINITIONS ---------------------------------*/
/*----------------------------------------------------------------------------------------*/
/*----------------------------------------------------------------------------------------*/

__global__ void InitParam(long *d_FrameParamPtr)
{
    d_FrameParamPtr[6]=0; // number of counts per frame
    __syncthreads();
}

__global__ void ThresholdingData(unsigned char *src,unsigned int *srcAcc, long *d_FrameParamPtr,unsigned int *SSDataStream,unsigned int *SSIndexStream,unsigned int *BlockCountBuff,int t, unsigned char *d_BGCorr)
{
    int i=threadIdx.x+blockIdx.x*blockDim.x;
    unsigned int BlockThreadoffset;
    unsigned int Blockoffset;
    __shared__ unsigned int BCB;
    BCB=BlockCountBuff[t];

    long SingleShotRecord=d_FrameParamPtr[7];
    int thresh=(int) d_FrameParamPtr[2];
    long counting_mode=d_FrameParamPtr[4];
    
    
    //if(t==0 && d_FrameParamPtr[0]==0 && d_FrameParamPtr[5]%d_FrameParamPtr[1]==0){srcAcc[i]=0;}

    //__syncthreads();

    /*--------------------------------------------------------------------------*/
    /*--------------------------- BG SUBSTRACTION ------------------------------*/
    /*--------------------------------------------------------------------------*/
    
    int u =(int) src[i]-(int) d_BGCorr[i];
    if(u<0){src[i]=0;}
    else{src[i]=(unsigned int) u;} 
    
    __syncthreads();

    /*--------------------------------------------------------------------------*/
    /*--------------------------- THRESHOLDING DATA ----------------------------*/
    /*--------------------------------------------------------------------------*/

    if(src[i]<thresh)
    {
        src[i]=0;
        __syncthreads();
     
    }
    else{src[i]=src[i]-(thresh-1);__syncthreads();}
    
    __syncthreads();
    
    /*--------------------------------------------------------------------------------*/
    /*---------------------------END OF THRESHOLDING DATA ----------------------------*/
    /*--------------------------------------------------------------------------------*/
    
    /*-----------------------------------------------------------------------------*/
    /*---------------------------- CENTROIDING THE DATA ---------------------------*/
    /*-----------------------------------------------------------------------------*/
    
    if(counting_mode==1)
    {
        bool MaxPixl=0;
        int NcountFrame=0;
        //////////////////////////////////////////////////
        // block    -3   -2    1    0    1    2    3    //
        // thread                                       //
        //   -3                    im3                  //
        //   -2               hm2  im2  jm1             //
        //   -1          gm1  hm1  im1  jm1  km1        //
        //    0      f    g    h    i    j    k    l    //
        //    1          gp1  hp1  ip1  jp1  kp1        //
        //    2               hp2  ip2  jp2             //
        //    3                    ip3                  //
        //////////////////////////////////////////////////
        
    
        if (threadIdx.x > 2 || blockIdx.x > 2 || threadIdx.x <(blockDim.x-2) || blockIdx.x < (blockDim.x-2) )
        {
            
               int ip1=(threadIdx.x+1)+blockIdx.x*blockDim.x;
               //int ip2=(threadIdx.x+2)+blockIdx.x*blockDim.x;
               //int ip3=(threadIdx.x+3)+blockIdx.x*blockDim.x;
               int im1=(threadIdx.x-1)+blockIdx.x*blockDim.x;
               //int im2=(threadIdx.x-2)+blockIdx.x*blockDim.x;
               //int im3=(threadIdx.x-3)+blockIdx.x*blockDim.x;
             
               int h=threadIdx.x+(blockIdx.x-1)*blockDim.x;
               int hp1=(threadIdx.x+1)+(blockIdx.x-1)*blockDim.x;
               //int hp2=(threadIdx.x+2)+(blockIdx.x-1)*blockDim.x;
               int hm1=(threadIdx.x-1)+(blockIdx.x-1)*blockDim.x;
               //int hm2=(threadIdx.x-2)+(blockIdx.x-1)*blockDim.x;
             
               int j=threadIdx.x+(blockIdx.x+1)*blockDim.x;
               int jp1=(threadIdx.x+1)+(blockIdx.x+1)*blockDim.x;
               //int jp2=(threadIdx.x+1)+(blockIdx.x+1)*blockDim.x;
               int jm1=(threadIdx.x-1)+(blockIdx.x+1)*blockDim.x;
               //int jm2=(threadIdx.x+1)+(blockIdx.x+1)*blockDim.x;
             
               //int k=threadIdx.x+(blockIdx.x+2)*blockDim.x;
               //int kp1=(threadIdx.x+1)+(blockIdx.x+2)*blockDim.x;
               //int km1=(threadIdx.x-1)+(blockIdx.x+2)*blockDim.x;
             
               //int g=threadIdx.x+(blockIdx.x-2)*blockDim.x;
               //int gp1=(threadIdx.x+1)+(blockIdx.x-2)*blockDim.x;
               //int gm1=(threadIdx.x-1)+(blockIdx.x-2)*blockDim.x;
              
               //int l=threadIdx.x+(blockIdx.x+3)*blockDim.x;
              
               //int f=threadIdx.x+(blockIdx.x-3)*blockDim.x;
              
             /* char C=src[i];*/
                if(src[i]>src[ip1] && src[i]>src[im1] && src[i]>src[j] && src[i]>src[jp1] && src[i]>src[jm1] && src[i]>src[h] && src[i]>src[hp1] && src[i]>src[hm1])
                {
                	MaxPixl=true;
                   // NcountFrame+=1;
                    d_FrameParamPtr[6]+=1;
                }
                else
                {
                    MaxPixl=false;
                }
            
        }
        else
        {
            MaxPixl=false;
        }
        __syncthreads();

        //if(i==1){d_FrameParamPtr[6]=NcountFrame;} // only one thread writes down the number of counts

        if(MaxPixl==true)
        {
            src[i]=1;
        }
        else
        {
            src[i]=0;
        }
         __syncthreads();
    }
    
    /*------------------------------------------------------------------------------------*/
    /*---------------------------- END OF CENTROIDING THE DATA ---------------------------*/
    /*------------------------------------------------------------------------------------*/

    /*------------------------------------------------------------------------------------*/
    /*----------------------------- ACCUMULATE DATA ON FRAME -----------------------------*/
    /*------------------------------------------------------------------------------------*/

    //if(t==0){

        srcAcc[i]=srcAcc[i]+(unsigned int) src[i];
        __syncthreads();
    
    //}
   
    /*------------------------------------------------------------------------------------*/
    /*-------------------------- END OF ACCUMULATE DATA ON FRAME -------------------------*/
    /*------------------------------------------------------------------------------------*/
    
    
    /*------------------------------------------------------------------------------------------------------------------------------------------------------------------*/
    /*------------------------- VECTOR COMPACTION IN THE KERNEL (ref D.M. Hughes & al. Computer Graphics forum, Vol 32, iss 6, p178-188 (2013)) ------------------------*/
    /*------------------------------------------------------------------------------------------------------------------------------------------------------------------*/
    if(SingleShotRecord==1)
    {
    __shared__ unsigned int W[25];          // array of warp offsets (for 800 threads/block -> 25 warps)
    
    
    unsigned int warpindex=i/32;                    // will take only the floor of the value due to the fact that it is defined as int.
    unsigned int threadindexinwarp= i%32;
    unsigned int threadmask=INT_MAX>>(32-threadindexinwarp); // for example: [1111111111]->[0011111111] if arg=2;
    
    unsigned int ballotresult=__ballot(src[i]) & threadmask;
    unsigned int threadoffset=__popc(ballotresult);
    
    if(threadindexinwarp==31)
    {
        if(src[i]==0)
        {
            W[warpindex]=threadoffset;
        }
        else
        {
            W[warpindex]=threadoffset+1;
        }
        __threadfence();
        __syncthreads();
    }
    
    BlockThreadoffset=__syncthreads_count(src[i]);
    
    unsigned int warpoffset=(__popc(__ballot(W[warpindex] & 1)&threadmask)>>warpindex) +(__popc(__ballot(W[warpindex]&2)&threadmask)>>warpindex)+(__popc(__ballot(W[warpindex]&4)&threadmask)>>warpindex)+(__popc(__ballot(W[warpindex]&8)&threadmask)>>warpindex)+(__popc(__ballot(W[warpindex]&16)&threadmask)>>warpindex)+(__popc(__ballot(W[warpindex]&32)&threadmask)>>warpindex);
    
    Blockoffset=atomicAdd(&BCB,BlockThreadoffset);        // Last problem on that line in compilation.
    BlockCountBuff[t]=BCB;
    unsigned int Totaloffset;
    
    Totaloffset=Blockoffset+warpoffset+threadoffset;
    
    if(src[i]>0)
    {
        SSDataStream[Totaloffset]=src[i];
        SSIndexStream[Totaloffset]=i;
    }
    
    __syncthreads();
    }
    /*-----------------------------------------------------------------------------*/
    /*------------------------- END OF VECTOR COMPACTION --------------------------*/
    /*-----------------------------------------------------------------------------*/
      
}

__global__ void ResetDataArrays(unsigned int *srcAcc)
{
     int i=threadIdx.x+blockIdx.x*blockDim.x;
     srcAcc[i]=0;
     __syncthreads();
}


/*\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-/-\-*/


/*----------------------------------------------------------------------------------------*/
/*---------------------------- END OF CUDA KERNELS DEFINITIONS ---------------------------*/
/*----------------------------------------------------------------------------------------*/
/*------------------------------------ DEFINITION OF -------------------------------------*/
/*----------------------------------------------------------------------------------------*/
/*-------------------------------- C++ WRAPPING FUNCTIONS --------------------------------*/
/*----------------------------------------------------------------------------------------*/


cudaError_t InitialiseCUDAMem(unsigned char **& h_StreamPtr, unsigned int **& d_SSDataStream_ptr, unsigned int **& d_SSIndexStream_ptr, long *& d_FrameParamPtr, unsigned char *& d_FramePtr, unsigned int *& d_PicturePtr, int Nbytes, unsigned char *& d_BGCorr)
{
    cudaError_t cudaStatus;
    
    /* Pinned Host memory allocation */

    for(int i=0;i<5;i++)
    {
    cudaStatus=cudaMallocHost((void**)&h_StreamPtr[i],Nbytes);
    }

    //cudaMallocHost((void**)&h_StreamAccPtr,Nbytes*4);
    
    /* Single shot data array allocation */
    /*(for a maximum of 50 millions points which represents 5millions frames at 10 evt/frame (2h45min acq)) */
    
    for(int i=0;i<5;i++)
    {
    cudaMalloc((void**) &d_SSDataStream_ptr[i],40000000);
    cudaMalloc((void**) &d_SSIndexStream_ptr[i],40000000);
    }
    
    /* memory allocation for frame on GPU */
    
    cudaMalloc((void**) &d_FrameParamPtr,11*8);
    cudaMalloc((void**) &d_FramePtr,Nbytes);
    cudaMalloc((void**) &d_PicturePtr,Nbytes*4);

    cudaMalloc((void**) &d_BGCorr,Nbytes);
    
    return cudaStatus;
}

cudaError_t FreeCUDAMem(unsigned char **h_StreamPtr, unsigned int **d_SSDataStream_ptr, unsigned int **d_SSIndexStream_ptr, long *d_FrameParamPtr, unsigned char *d_FramePtr, unsigned int *d_PicturePtr, unsigned char *d_BGCorr)
{
    cudaError_t cudaStatus;
    
    for(int i=0;i<5;i++)
    {
        cudaFreeHost(h_StreamPtr[i]);
        cudaFree(d_SSDataStream_ptr[i]);
        cudaFree(d_SSIndexStream_ptr[i]);
    }

    cudaStatus=cudaFree(d_FrameParamPtr);
    cudaFree(d_FramePtr); // Free the GPU ressources.
    cudaFree(d_PicturePtr);
    cudaFree(d_BGCorr);
    
    return cudaStatus;
}

cudaError_t CUDAresetDataArrays(unsigned int *d_PicturePtr)
{
    cudaError_t cudaStatus;
    dim3 grid(400,1);
    dim3 threads(400,1);

    ResetDataArrays<<<grid,threads>>>(d_PicturePtr);
    cudaStatus=cudaDeviceSynchronize();
    
    return cudaStatus;
        
}

cudaError_t CUDAbackgroundFrameToGPU(unsigned char *h_BGCorr, unsigned char *d_BGCorr, int Nbytes)
{   
    cudaError_t cudaStatus;
    cudaStatus=cudaMemcpy(d_BGCorr,h_BGCorr,Nbytes,cudaMemcpyHostToDevice);
    cudaDeviceSynchronize();
    return cudaStatus;
}

cudaError_t CUDAProcessingData(unsigned char **h_StreamPtr, unsigned int **d_SSDataStream_ptr, unsigned int **d_SSIndexStream_ptr,unsigned int *SharedMem, unsigned char *d_FramePtr,  unsigned int *d_PicturePtr, int Nbytes, long *h_FrameParamPtr, long *d_FrameParamPtr, unsigned char *d_BGCorr)
{
    cudaError_t cudaStatus;
    
    /*---- Cuda streams to optimize data transfer and kernel treatement (5 streams for now) ----*/
    
    cudaStream_t *stream=new cudaStream_t[5];
    
    for(int i=0;i<5;i++)
    {
        cudaStreamCreate(&stream[i]);
    }

    /*---- Buffers for frame Compaction ----*/
    
    unsigned int *d_BlockCountBuff;
    cudaMalloc((void**) &d_BlockCountBuff,5*4);
    //__device__ unsigned int d_BlockCountBuff[5];
    
    
    
    /*---- Parameters copy from GUI ----*/
    
    cudaMemcpy(d_FrameParamPtr,h_FrameParamPtr,11*8,cudaMemcpyHostToDevice);  // copy parameters to treat the data
    
    dim3 grid(160,1);
    dim3 threads(1000,1);
    
    unsigned int* d_FrameIndexPtr;
    cudaMalloc((void**) &d_FrameIndexPtr,Nbytes*4);

    cudaEvent_t* event=new cudaEvent_t[10];

    for(int i=0;i<10;i++)
    {
    cudaEventCreate(&event[i]);
	}

    /*---- Core of the processing: data transfer then kernel execution ----*/

    if(h_FrameParamPtr[1]<5)
    {
        for(int t=0;t<h_FrameParamPtr[1];t++) // Create Asynchronous data transfer and kernel
        {
            if(t==0)
            {
                cudaMemcpyAsync(d_FramePtr,h_StreamPtr[t],Nbytes,cudaMemcpyHostToDevice,stream[t]);       // Copy the frame to the GPU
                //cudaThreadSynchronize();
                cudaEventRecord(event[0],stream[0]);

                InitParam<<<1,1,0,stream[0]>>>(d_FrameParamPtr);
                ThresholdingData<<<grid,threads,0,stream[t]>>>(d_FramePtr,d_PicturePtr,d_FrameParamPtr,d_SSDataStream_ptr[t],d_SSIndexStream_ptr[t],d_BlockCountBuff,t,d_BGCorr);     // Call thresholding data with number of blocks
                //cudaThreadSynchronize();
                cudaEventRecord(event[h_FrameParamPtr[1]],stream[0]);
            }
            else
            {
                cudaStreamWaitEvent(stream[t],event[t-1],0);
                cudaMemcpyAsync(d_FramePtr,h_StreamPtr[t],Nbytes,cudaMemcpyHostToDevice,stream[t]);       // Copy the frame to the GPU
                //cudaThreadSynchronize();
                cudaEventRecord(event[t],stream[t]);

                cudaStreamWaitEvent(stream[t],event[t+1],0);
                InitParam<<<1,1,0,stream[t]>>>(d_FrameParamPtr);
                ThresholdingData<<<grid,threads,0,stream[t]>>>(d_FramePtr,d_PicturePtr,d_FrameParamPtr,d_SSDataStream_ptr[t],d_SSIndexStream_ptr[t],d_BlockCountBuff,t,d_BGCorr);     // Call thresholding data with number of blocks
                //cudaThreadSynchronize();
                cudaEventRecord(event[t+h_FrameParamPtr[1]],stream[t]);
            }
            cudaStreamSynchronize(stream[t]);
        }
        //cudaDeviceSynchronize();
    }
    else
    {
        for(int t=0;t<5;t++) // Create Asynchronous data transfer and kernel
        {
            if(t==0)
            {
                cudaMemcpyAsync(d_FramePtr,h_StreamPtr[t],Nbytes,cudaMemcpyHostToDevice,stream[t]);       // Copy the frame to the GPU
                //cudaThreadSynchronize();
                cudaEventRecord(event[0],stream[0]);
        
                InitParam<<<1,1,0,stream[0]>>>(d_FrameParamPtr);
                ThresholdingData<<<grid,threads,0,stream[t]>>>(d_FramePtr,d_PicturePtr,d_FrameParamPtr,d_SSDataStream_ptr[t],d_SSIndexStream_ptr[t],d_BlockCountBuff,t,d_BGCorr);     // Call thresholding data with number of blocks
                //cudaThreadSynchronize();
                cudaEventRecord(event[5],stream[0]);
            }
            else
            {
                cudaStreamWaitEvent(stream[t],event[t-1],0);
                cudaMemcpyAsync(d_FramePtr,h_StreamPtr[t],Nbytes,cudaMemcpyHostToDevice,stream[t]);       // Copy the frame to the GPU
                //cudaThreadSynchronize();
                cudaEventRecord(event[t],stream[t]);

                cudaStreamWaitEvent(stream[t],event[t+1],0);
                InitParam<<<1,1,0,stream[t]>>>(d_FrameParamPtr);
                ThresholdingData<<<grid,threads,0,stream[t]>>>(d_FramePtr,d_PicturePtr,d_FrameParamPtr,d_SSDataStream_ptr[t],d_SSIndexStream_ptr[t],d_BlockCountBuff,t,d_BGCorr);     // Call thresholding data with number of blocks
                //cudaThreadSynchronize();
                cudaEventRecord(event[t+5],stream[t]);
            }
            cudaStreamSynchronize(stream[t]);
        }
        //cudaDeviceSynchronize();
    }
    if(h_FrameParamPtr[0]==0) // Send the updated accumulated frame at the end of the number of counts when it is a preview.
    {
        cudaStatus=cudaMemcpy(SharedMem,d_PicturePtr,Nbytes*4,cudaMemcpyDeviceToHost);
    }
    else if(h_FrameParamPtr[0] == 1) // Send the updated accumulated frame in real time when it is acquisition mode.
    {
        cudaStatus=cudaMemcpy(SharedMem,d_PicturePtr,Nbytes*4,cudaMemcpyDeviceToHost);    
    }

    cudaMemcpy(h_FrameParamPtr,d_FrameParamPtr,11*8,cudaMemcpyDeviceToHost);

    cudaDeviceSynchronize();
    
    /*---- Cleaning ----*/
    
     for(int i=0;i<5;i++)
    {
        cudaStreamDestroy(stream[i]);
    }
    
    delete [] stream;
	
    for(int i=0;i<10;i++)
    {
        cudaEventDestroy(event[i]);
	}

	delete [] event;
    
    cudaFree(d_FrameIndexPtr);
    cudaFree(d_BlockCountBuff);
    return cudaStatus;
    
}
