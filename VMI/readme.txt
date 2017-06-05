VMI acquisition folder


VMIViewer.py:
26-03-16
Replaces the matlab VMI display for the VMi acquisition program. It uses the VMITraceProcessing class to call the basic preprocess routines like rotate or plot in polar coordinates


RECOMPILE CUDA CODE:

Launch the following command

"nvcc -arch=sm_30 -Xcompiler -fPIC -c -o CUDA_Processing.obj CUDA_Processing.cu -lcudadevrt -lcudart"


RECOMPILE C++ CODE: