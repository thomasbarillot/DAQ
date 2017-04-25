function varargout = PI_E750_CP(varargin)
% PI_E750_CP M-file for PI_E750_CP.fig
%      PI_E750_CP, by itself, creates a new PI_E750_CP or raises the existing
%      singleton*.
%
%      H = PI_E750_CP returns the handle to a new PI_E750_CP or the handle to
%      the existing singleton*.
%
%      PI_E750_CP('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in PI_E750_CP.M with the given input arguments.
%
%      PI_E750_CP('Property','Value',...) creates a new PI_E750_CP or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before PI_E750_CP_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to PI_E750_CP_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help PI_E750_CP

% Last Modified by GUIDE v2.5 29-Sep-2009 15:37:48

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @PI_E750_CP_OpeningFcn, ...
                   'gui_OutputFcn',  @PI_E750_CP_OutputFcn, ...
                   'gui_LayoutFcn',  [] , ...
                   'gui_Callback',   []);
if nargin && ischar(varargin{1})
    gui_State.gui_Callback = str2func(varargin{1});
end

if nargout
    [varargout{1:nargout}] = gui_mainfcn(gui_State, varargin{:});
else
    gui_mainfcn(gui_State, varargin{:});
end
% End initialization code - DO NOT EDIT


% --- Executes just before PI_E750_CP is made visible.
function PI_E750_CP_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to PI_E750_CP (see VARARGIN)

% Choose default command line output for PI_E750_CP
handles.output = hObject;
handles.serial_port.Status='closed';

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes PI_E750_CP wait for user response (see UIRESUME)
% uiwait(handles.figure1);


% --- Outputs from this function are returned to the command line.
function varargout = PI_E750_CP_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;


% --- Executes on button press in open_serial.
function open_serial_Callback(hObject, eventdata, handles)
if strcmp(handles.serial_port.Status, 'closed')
    handles.serial_port = serial(get(handles.comport,'String'),...
        'BaudRate',115200,...
        'DataBits', 8, ...
        'Parity', 'none', 'StopBits', 1, 'FlowControl', 'hardware');
    fopen(handles.serial_port);
    set(handles.open_serial, 'String', 'Close serial');
    guidata(hObject,handles)
else
    fclose(handles.serial_port);
    set(handles.open_serial, 'String', 'Open serial');
end


function comport_Callback(hObject, eventdata, handles)
% hObject    handle to comport (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of comport as text
%        str2double(get(hObject,'String')) returns contents of comport as a double


% --- Executes during object creation, after setting all properties.
function comport_CreateFcn(hObject, eventdata, handles)
% hObject    handle to comport (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in resetserial.
function resetserial_Callback(hObject, eventdata, handles)
disp('--- running instrreset ---')
instrreset
pause(0.1)


% --- Executes on button press in openDLL.
function openDLL_Callback(hObject, eventdata, handles)
if get(handles.openDLL, 'Value')
    set(handles.openDLL, 'String', 'close DLL')
    [notfound,warnings] = loadlibrary('alphapi.dll', 'dllmain.h');
    pause(1)
    ok = calllib('fdi', 'PSL_FDI_Open', '.')
else
    set(handles.openDLL, 'String', 'open DLL')
    unloadlibrary('alphapi');
end


