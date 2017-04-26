// ============================================================================
// === Smarties includes and constant definitions
// ===
// === (c) 2009-2010 Silicon Software GmbH
// ============================================================================

#ifndef __FGRAB_SMARTIES_H__
#define __FGRAB_SMARTIES_H__

// ### INCLUDES

#include "fgrab_struct.h"
#include "fgrab_prototyp.h"
#include "fgrab_define.h"
//#include "fgrab_blob.h"

// ### PARAMETER IDS

#define FG_OUTPUT_SELECT 100000
#define FG_RATE_SUPPRESS 100001
#define FG_SOFTWARETRIGGER_IS_BUSY 110075
#define FG_DEBOUNCING 110062
#define FG_LUT_TYPE 110017
#define FG_LUT_PARAM_CUSTOM_FILE 110019
#define FG_LUT_PARAM_PROCESSING_OFFSET 110023
#define FG_LUT_PARAM_PROCESSING_GAIN 110024
#define FG_LUT_PARAM_PROCESSING_GAMMA 110025
#define FG_LUT_PARAM_PROCESSING_INVERT 110026
#define FG_LUT_SAVE_FILE 110021
#define FG_NOISEFILTER 110016
#define FG_BINARIZATION_THRESHOLD_FROM 110069
#define FG_BINARIZATION_THRESHOLD_TO 110070
#define FG_MORPH_RADIUS_1 110012
#define FG_MORPH_OPERATION_1 110014
#define FG_MORPH_RADIUS_2 110013
#define FG_MORPH_OPERATION_2 110015
//#define FG_BLOB_BB_XPOS_MIN 110001
//#define FG_BLOB_BB_XPOS_MAX 110002
//#define FG_BLOB_BB_YPOS_MIN 110003
//#define FG_BLOB_BB_YPOS_MAX 110004
//#define FG_BLOB_BB_WIDTH_MIN 110007
//#define FG_BLOB_BB_WIDTH_MAX 110008
//#define FG_BLOB_BB_HEIGHT_MIN 110009
//#define FG_BLOB_BB_HEIGHT_MAX 110010
//#define FG_BLOB_AREA_MIN 110005
//#define FG_BLOB_AREA_MAX 110006
//#define FG_BLOB_ERROR_STATUS 110011
//#define FG_BLOB_ERROR_CLEAR_ACTION 110073
#define FG_FILLLEVEL 110086
#define FG_OVERFLOW 110087
#define FG_LINETRIGGERDEBOUNCING 110063
#define FG_SHAFTENCODERMODE 110065
#define FG_IMGTRIGGER_IS_BUSY 110066
#define FG_IMGTRIGGERDEBOUNCING 110064
#define FG_SC_SUBSENSORCOUNT 110118
#define FG_SC_SENSORLENGTH 110119
#define FG_SC_TAPCOUNT 110120
#define FG_SC_ROTATEDSENSOR 110121
#define FG_SC_READOUTDIRECTION 110122
#define FG_SC_PIXELORDER 110123
#define FG_SC_UPDATESCHEME 110124
#define FG_BINARIZATION_MODE 110078
#define FG_BINARIZATION_NEIGHBOURHOOD 110079
#define FG_BINARIZATION_OFFSET 110080
#define FG_BINARIZATION_PATTERNMODE 110081
#define FG_BINARIZATION_THRESHOLD_MIN 110082
#define FG_BINARIZATION_THRESHOLD_MAX 110083
#define FG_BINARIZATION_THRESHOLD 110084
#define FG_LINESHADING_HIGHSPEED 110117
#define FG_IMAGEHEIGHT 110061

// ### SYMBOLIC ENUMERATION VALUES

#define OUTPUT_GRAY 0
#define OUTPUT_BINARY 1
#define FG_APPLY 1
#define IS_BUSY 1
#define IS_NOT_BUSY 0
#define FG_ONE 1
#define FG_ZERO 0
#define FG_ZERO 0
#define FG_ONE 1
#define LUT_TYPE_IDENTITY 1
#define LUT_TYPE_INVERT 2
#define LUT_TYPE_PROCESSING 3
#define LUT_TYPE_CUSTOM 0
#define MORPH_RADIUS_10 0
#define MORPH_RADIUS_15 1
#define MORPH_RADIUS_20 2
#define MORPH_RADIUS_25 3
#define MORPH_RADIUS_30 4
#define MORPH_RADIUS_35 5
#define MORPH_OP_NOP 0
#define MORPH_OP_DILATE 1
#define MORPH_OP_ERODE 2
#define MORPH_OP_OPEN 3
#define MORPH_OP_CLOSE 4
//#define BLOB_STATUS_NO_ERROR 0
//#define BLOB_STATUS_ERROR 1
#define FILTER_X1 1
#define FILTER_X2 2
#define FILTER_X4 3
#define FG_FALSE 0
#define FG_TRUE 1
#define BINARIZATION_THRESHOLD 0
#define BINARIZATION_ADAPTIVE 1
#define KERNEL8X8 0
#define KERNEL16X16 1
#define KERNEL32X32 2
#define BRIGHT_PATTERN 1
#define DARK_PATTERN 0
#define KERNEL64X64 3
#define MONO8 0
#define MONO8_SIGNED 1
#define MONO10 2
#define MONO10_PACKED 3
#define MONO12 4
#define MONO12_PACKED 5
#define MONO16 6
#define OUTPUT_BLOB 2
#define OUTPUT_GRAY_AND_BLOB 3
#define OUTPUT_BINARY_AND_BLOB 4

#endif