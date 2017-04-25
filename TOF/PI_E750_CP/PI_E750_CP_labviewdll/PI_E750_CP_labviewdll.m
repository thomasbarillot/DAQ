function varargout = PI_E750_CP_labviewdll(varargin)
% PI_E750_CP_LABVIEWDLL M-file for PI_E750_CP_labviewdll.fig
%      PI_E750_CP_LABVIEWDLL, by itself, creates a new PI_E750_CP_LABVIEWDLL or raises the existing
%      singleton*.
%
%      H = PI_E750_CP_LABVIEWDLL returns the handle to a new PI_E750_CP_LABVIEWDLL or the handle to
%      the existing singleton*.
%
%      PI_E750_CP_LABVIEWDLL('CALLBACK',hObject,eventData,handles,...) calls the local
%      function named CALLBACK in PI_E750_CP_LABVIEWDLL.M with the given input arguments.
%
%      PI_E750_CP_LABVIEWDLL('Property','Value',...) creates a new PI_E750_CP_LABVIEWDLL or raises the
%      existing singleton*.  Starting from the left, property value pairs are
%      applied to the GUI before PI_E750_CP_labviewdll_OpeningFcn gets called.  An
%      unrecognized property name or invalid value makes property application
%      stop.  All inputs are passed to PI_E750_CP_labviewdll_OpeningFcn via varargin.
%
%      *See GUI Options on GUIDE's Tools menu.  Choose "GUI allows only one
%      instance to run (singleton)".
%
% See also: GUIDE, GUIDATA, GUIHANDLES

% Edit the above text to modify the response to help PI_E750_CP_labviewdll

% Last Modified by GUIDE v2.5 18-Feb-2013 11:43:25

% Begin initialization code - DO NOT EDIT
gui_Singleton = 1;
gui_State = struct('gui_Name',       mfilename, ...
                   'gui_Singleton',  gui_Singleton, ...
                   'gui_OpeningFcn', @PI_E750_CP_labviewdll_OpeningFcn, ...
                   'gui_OutputFcn',  @PI_E750_CP_labviewdll_OutputFcn, ...
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


% --- Executes just before PI_E750_CP_labviewdll is made visible.
function PI_E750_CP_labviewdll_OpeningFcn(hObject, eventdata, handles, varargin)
% This function has no output args, see OutputFcn.
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)
% varargin   command line arguments to PI_E750_CP_labviewdll (see VARARGIN)

% Choose default command line output for PI_E750_CP_labviewdll
handles.output = hObject;

%% initialise plots
axes(handles.AXposind)
handles.posind = barh(.5,.25,'g');%,1)%,'r');
set(handles.posind,'BarWidth',1)
set(gca,'XLim',[0 1],'YLim',[0 1])
set(gca,'Color',[1 0 0])
set(gca,'Xticklabel','','YTicklabel','')

% Update handles structure
guidata(hObject, handles);

% UIWAIT makes PI_E750_CP_labviewdll wait for user response (see UIRESUME)
% uiwait(handles.figure1);


%% own functions:

function moveAbsolute(hObject, x)
handles = guidata(hObject);
set(handles.position, 'String', sprintf('%.6f', x))
eventdata=[];
position_Callback(hObject, eventdata, handles);

%% end of own functions!


% --- Outputs from this function are returned to the command line.
function varargout = PI_E750_CP_labviewdll_OutputFcn(hObject, eventdata, handles) 
% varargout  cell array for returning output args (see VARARGOUT);
% hObject    handle to figure
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Get default command line output from handles structure
varargout{1} = handles.output;


% --- Executes on button press in open.
function open_Callback(hObject, eventdata, handles)
if get(handles.open, 'Value')
    disp('opening stage...')
    [notfound,warnings]=loadlibrary('PI_E750_cp.dll', 'PI_E750_cp.h', 'alias', 'PI');
    pause(0.25)
    comport = str2double(get(handles.comport,'String'));
    calllib('PI', 'PI_E750_cp_open', comport)
    pause(0.25)
    velocity_Callback(hObject, eventdata, handles);
    pause(0.05)
    getpos_Callback(hObject, eventdata, handles);
    pause(0.05)
    set(handles.open, 'BackgroundColor', [1,0,0], 'String', 'close connection to stage')
else
    disp('closing stage...')
    unloadlibrary('PI')
    set(handles.open, 'BackgroundColor', [0,1,0], 'String', 'open connection to stage')

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



function velocity_Callback(hObject, eventdata, handles)
calllib('PI', 'PI_E750_cp_setvelocity', str2double(get(handles.velocity, 'String')))


% --- Executes during object creation, after setting all properties.
function velocity_CreateFcn(hObject, eventdata, handles)
% hObject    handle to velocity (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end



function position_Callback(hObject, eventdata, handles)
setpos = str2double(get(handles.position, 'String'));
calllib('PI', 'PI_E750_cp_setposition', setpos)
if get(handles.poschecker, 'Value')
    set(handles.moving_indicator, 'String', 'moving', 'BackgroundColor', [1,0,0])
    err = str2double(get(handles.pos_err, 'String'));
    ispos = str2double(get(handles.position_indicator, 'String'));
    while abs(setpos-ispos) > err
        getpos_Callback(hObject, eventdata, handles)
        ispos = str2double(get(handles.position_indicator, 'String'));
        pause(0.05)
    end
    set(handles.moving_indicator, 'String', 'ok', 'BackgroundColor', [0,1,0])
else
    getpos_Callback(hObject, eventdata, handles)
end
% --- Executes during object creation, after setting all properties.
function position_CreateFcn(hObject, eventdata, handles)
% hObject    handle to position (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in step_minus.
function step_minus_Callback(hObject, eventdata, handles)
pos = str2double(get(handles.position, 'String'));
step= str2double(get(handles.step, 'String'));
newpos = pos - step;
set(handles.position, 'String', sprintf('%.6f', newpos))
position_Callback(hObject, eventdata, handles)

% --- Executes on button press in step_plus.
function step_plus_Callback(hObject, eventdata, handles)
pos = str2double(get(handles.position, 'String'));
step= str2double(get(handles.step, 'String'));
newpos = pos + step;
set(handles.position, 'String', sprintf('%.6f', newpos))
position_Callback(hObject, eventdata, handles)



function step_Callback(hObject, eventdata, handles)
% hObject    handle to step (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of step as text
%        str2double(get(hObject,'String')) returns contents of step as a double


% --- Executes during object creation, after setting all properties.
function step_CreateFcn(hObject, eventdata, handles)
% hObject    handle to step (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on selection change in units.
function units_Callback(hObject, eventdata, handles)
% hObject    handle to units (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: contents = get(hObject,'String') returns units contents as cell array
%        contents{get(hObject,'Value')} returns selected item from units


% --- Executes during object creation, after setting all properties.
function units_CreateFcn(hObject, eventdata, handles)
% hObject    handle to units (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: popupmenu controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in getpos.
function getpos_Callback(hObject, eventdata, handles)
pos = calllib('PI', 'PI_E750_cp_getpos');
set(handles.position_indicator, 'String', sprintf('%.4f', pos))
set(handles.posind,'ydata', pos./38);
drawnow

% --- Executes on button press in checkpos_online.
function checkpos_online_Callback(hObject, eventdata, handles)
% hObject    handle to checkpos_online (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of checkpos_online


% --- Executes on button press in poschecker.
function poschecker_Callback(hObject, eventdata, handles)
% hObject    handle to poschecker (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hint: get(hObject,'Value') returns toggle state of poschecker



function pos_err_Callback(hObject, eventdata, handles)
% hObject    handle to pos_err (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of pos_err as text
%        str2double(get(hObject,'String')) returns contents of pos_err as a double


% --- Executes during object creation, after setting all properties.
function pos_err_CreateFcn(hObject, eventdata, handles)
% hObject    handle to pos_err (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in moving_indicator.
function moving_indicator_Callback(hObject, eventdata, handles)
% hObject    handle to moving_indicator (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)



function posn_Callback(hObject, eventdata, handles)
% hObject    handle to posn (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    structure with handles and user data (see GUIDATA)

% Hints: get(hObject,'String') returns contents of posn as text
%        str2double(get(hObject,'String')) returns contents of posn as a double


% --- Executes during object creation, after setting all properties.
function posn_CreateFcn(hObject, eventdata, handles)
% hObject    handle to posn (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end


% --- Executes on button press in getposnplot.
function getposnplot_Callback(hObject, eventdata, handles)
N = str2double(get(handles.posn, 'String'));
posn = zeros(N,1);
set(handles.position, 'String', get(handles.posnew, 'String'))
position_Callback(hObject, eventdata, handles)
t0 = clock;
for n=1:N
    getpos_Callback(hObject, eventdata, handles);
    posn(n) = str2double(get(handles.position_indicator, 'String'));
    time(n) = etime(clock, t0);
end

figure_docked('postest');clf
plot(time, posn)
title(sprintf('%i positions, mean = %.6f microns, rms = %.2f nm', ...
    N, mean(posn), std(posn)*1e3))
xlabel('time (sec)')
ylabel('position (microns)')


function posnew_Callback(hObject, eventdata, handles)



% --- Executes during object creation, after setting all properties.
function posnew_CreateFcn(hObject, eventdata, handles)
% hObject    handle to posnew (see GCBO)
% eventdata  reserved - to be defined in a future version of MATLAB
% handles    empty - handles not created until after all CreateFcns called

% Hint: edit controls usually have a white background on Windows.
%       See ISPC and COMPUTER.
if ispc && isequal(get(hObject,'BackgroundColor'), get(0,'defaultUicontrolBackgroundColor'))
    set(hObject,'BackgroundColor','white');
end
