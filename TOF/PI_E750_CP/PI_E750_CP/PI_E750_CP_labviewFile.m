function varargout = PI_E750_CP_labviewFile(varargin)
% PI_E750_CP_LABVIEWFILE M-file for PI_E750_CP_labviewFile.fig
%      PI_E750_CP_LABVIEWFILE, by itself, creates a new PI_E750_CP_LABVIEWFILE or raises the existing
%      singleton*.
%
%      H = PI_E750_CP_LABVIEWFILE returns the handle to a new PI_E750_CP_LABVIEWFILE or the handle to
%      the existing singleton*.
%
%      PI_E750_CP_LABVIEWFILE('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in PI_E750_CP_LABVIEWFILE.M with the given input arguments.
%
%      PI_E750_CP_LABVIEWFILE('Property','Value',...) creates a new PI_E750_CP_LABVIEWFILE or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before PI_E750_CP_labviewFile_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to PI_E750_CP_labviewFile_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help PI_E750_CP_labviewFile

% Last Modified by GUIDE v2.5 05-Oct-2009 11:37:20

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @PI_E750_CP_labviewFile_OpeningFcn, ...
                   'gui_OutputFcn',  @PI_E750_CP_labviewFile_OutputFcn, ...
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


% --- Executes just before PI_E750_CP_labviewFile is made visible.
function PI_E750_CP_labviewFile_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to PI_E750_CP_labviewFile (see VARARGIN)

% Choose default command line output for PI_E750_CP_labviewFile
handles.output = hObject;

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes PI_E750_CP_labviewFile wait for user response (see UIRESUME)
% uiwait(handles.figure1);


% --- Outputs from this function are returned to the command line.
function varargout = PI_E750_CP_labviewFile_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;


% --- Executes on button press in go.
function go_Callback(hObject, eventdata, handles)
pos_microns = str2double(get(handles.pos_microns, 'String'));
fid = fopen(get(handles.fileforpos, 'String'), 'w');
fprintf(fid, '%.5f', pos_microns);
fclose(fid);
pause(0.01)

function pos_microns_Callback(hObject, eventdata, handles)
% hObject    handle to pos_microns (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of pos_microns as text
%        str2double(get(hObject,'String')) returns contents of pos_microns as a double


% --- Executes during object creation, after setting all properties.
function pos_microns_CreateFcn(hObject, eventdata, handles)
% hObject    handle to pos_microns (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function fileforpos_Callback(hObject, eventdata, handles)
% handles.fid = fopen(get(handles.fileforpos, 'String'), 'w');
% guidata(hObject, handles)


% --- Executes during object creation, after setting all properties.
function fileforpos_CreateFcn(hObject, eventdata, handles)
% hObject    handle to fileforpos (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in getfile.
function getfile_Callback(hObject, eventdata, handles)



function pos_step_microns_Callback(hObject, eventdata, handles)
% hObject    handle to pos_step_microns (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of pos_step_microns as text
%        str2double(get(hObject,'String')) returns contents of pos_step_microns as a double


% --- Executes during object creation, after setting all properties.
function pos_step_microns_CreateFcn(hObject, eventdata, handles)
% hObject    handle to pos_step_microns (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in step_left.
function step_left_Callback(hObject, eventdata, handles)
pos_microns_is = str2double(get(handles.pos_microns, 'String'));
pos_microns_new = pos_microns_is - str2double(get(handles.pos_step_microns, 'String'));
if pos_microns_new <= 0
    pos_microns_new = 0;
end
set(handles.pos_microns, 'String', sprintf('%.5f', pos_microns_new))
go_Callback(hObject, eventdata, handles);

% --- Executes on button press in step_right.
function step_right_Callback(hObject, eventdata, handles)
pos_microns_is = str2double(get(handles.pos_microns, 'String'));
pos_microns_new = pos_microns_is + str2double(get(handles.pos_step_microns, 'String'));
if pos_microns_new > 12
    pos_microns_new = 12;
end
set(handles.pos_microns, 'String', sprintf('%.5f', pos_microns_new))
go_Callback(hObject, eventdata, handles)




function moveAbsolute(hObject, x)
handles = guidata(hObject);
set(handles.pos_microns, 'String', sprintf('%.5f', x))
eventdata=[];
go_Callback(hObject, eventdata, handles);
