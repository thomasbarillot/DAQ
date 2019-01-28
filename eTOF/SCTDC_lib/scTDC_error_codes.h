#pragma once

//error codes
const int SC_TDC_ERR_DEFAULT                                = -1;
const int SC_TDC_ERR_INIFILE                                = -2;
const int SC_TDC_ERR_TDCOPEN                                = -3;
const int SC_TDC_ERR_NOMEM                                  = -4;
const int SC_TDC_ERR_SERIAL                                 = -5;
const int SC_TDC_ERR_TDCOPEN2                               = -6;
const int SC_TDC_ERR_PARAMETER                              = -7;
const int SC_TDC_ERR_SMALLBUFFER                            = -8;
const int SC_TDC_ERR_BADCONFI                               = -9;
const int SC_TDC_ERR_NOTINIT                                = -10;
const int SC_TDC_ERR_NOTRDY                                 = -11;
const int SC_TDC_ERR_DEVCLS_LD                              = -12;
const int SC_TDC_ERR_DEVCLS_VER                             = -13;
const int SC_TDC_ERR_DEVCLS_INIT                            = -14;
const int SC_TDC_ERR_FPGA_INIT                              = -15;
const int SC_TDC_ERR_ALRDYINIT                              = -16;
const int SC_TDC_ERR_TIMEOUT                                = -17;
const int SC_TDC_ERR_NOSIMFILE                              = -18;
const int SC_TDC_ERR_GPX_RST                                = -21;
const int SC_TDC_ERR_GPX_PLL_NLOCK                          = -22;
const int SC_TDC_ERR_USB_COMM                               = -30;
const int SC_TDC_ERR_BIN_SET                                = -41;
const int SC_TDC_ERR_ROI_SET                                = -42;
const int SC_TDC_ERR_FMT_SET                                = -43;
const int SC_TDC_ERR_FMT_UNSUPPORT                          = -44;
const int SC_TDC_ERR_ROI_BAD                                = -45;
const int SC_TDC_ERR_ROI_TOOBIG                             = -46;
const int SC_TDC_ERR_BUFSIZE                                = -47;
const int SC_TDC_ERR_GPX_FMT_UNSUPPORT                      = -48;
const int SC_TDC_ERR_GPX_FMT_SET                            = -49;
const int SC_TDC_ERR_FMT_NDEF                               = -50;
const int SC_TDC_ERR_FIFO_ADDR_SET                          = -60;
const int SC_TDC_ERR_MODE_SET                               = -61;
const int SC_TDC_ERR_START_FAIL                             = -62;
const int SC_TDC_ERR_TIMER_SET                              = -63;
const int SC_TDC_ERR_TIMER_EX_SET                           = -64;
const int SC_TDC_ERR_STRT_FREQ_DIV_SET                      = -65;
const int SC_TDC_ERR_TWI_NO_MODULE                          = -70;
const int SC_TDC_ERR_TWI_FAIL                               = -71;
const int SC_TDC_ERR_TWI_NACK                               = -72;
const int SC_TDC_ERR_POT_NO                                 = -73;
const int SC_TDC_ERR_POT_SET                                = -74;
const int SC_TDC_ERR_FLIM_PARM_SET                          = -80;
const int SC_TDC_ERR_SYSTEM                                 = -81;
const int SC_TDC_ERR_NOT_IMPL                               = -9000;

//used only for callback
const int SC_TDC_INFO_MEAS_COMPLETE                         = 1;
const int SC_TDC_INFO_USER_INTERRUPT                        = 2;
const int SC_TDC_INFO_BUFFER_FULL                           = 3;
