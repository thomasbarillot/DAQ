%%
clear

%%
[notfound,warnings]=loadlibrary('PI_E750_cp.dll', 'PI_E750_cp.h', 'alias', 'PI')
libfunctionsview('PI')

%% open stage
%v = libpointer('voidPtr')
comport=1;
calllib('PI', 'PI_E750_cp_open', comport)

%%  set velocity:
velocity = 150;
calllib('PI', 'PI_E750_cp_setvelocity', velocity)

%% positoning:
position= 10;
calllib('PI', 'PI_E750_cp_setposition', position)
pause(0.1)
pos = calllib('PI', 'PI_E750_cp_getpos')

%%
unloadlibrary('PI')
