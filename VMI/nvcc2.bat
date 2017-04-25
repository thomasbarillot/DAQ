nvcc -arch=sm_30 -Xcompiler -fPIC -c -o CUDA_Processing.dll --shared CUDA_Processing.cu -lcudadevrt -lcudart 

