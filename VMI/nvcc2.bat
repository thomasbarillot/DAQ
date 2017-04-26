nvcc -arch=sm_30 -Xcompiler -fPIC -c -o CUDA_Processing.obj --shared CUDA_Processing.cu -lcudadevrt -lcudart 

