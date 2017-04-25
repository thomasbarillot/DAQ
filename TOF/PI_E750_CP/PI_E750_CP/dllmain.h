#ifndef _DLLMAIN_H
#define _DLLMAIN_H
//////////////////////////////////////////////////////////////////////////////////////////////
/* this header is appropriate for VC++ 5.0 enviroment */
//////////////////////////////////////////////////////////////////////////////////////////////
#define FUNC_DECL __declspec(dllimport)
#define PAR_TYP	float

#ifdef __cplusplus
extern "C" {
#endif

//////////////////////////////////////////////////////////////////////////////////////////////
/* DLL exported function interface */
//////////////////////////////////////////////////////////////////////////////////////////////

// ALPHA API *********************************************************************************


// functions for direct access to basic controller commands/actions
BOOL FUNC_DECL SetPosition( PAR_TYP fNewPosition );
BOOL FUNC_DECL TellPosition( PAR_TYP *pfPosition );

BOOL FUNC_DECL SetVoltage( PAR_TYP fNewVoltage );
BOOL FUNC_DECL TellVoltage( PAR_TYP *pfVoltage );

BOOL FUNC_DECL SetVelocity( PAR_TYP fNewVel );
BOOL FUNC_DECL TellVelocity( PAR_TYP *pfVel );


BOOL FUNC_DECL GetTravelRanges( PAR_TYP *fMinTravel, PAR_TYP *fMaxTravel  );
BOOL FUNC_DECL SetPolynomTerms( PAR_TYP *fPoly );
BOOL FUNC_DECL TellPolynomTerms( PAR_TYP *fPoly );

BOOL FUNC_DECL SetSensorLPF(PAR_TYP fValue);
BOOL FUNC_DECL GetSensorLPF(PAR_TYP* fValue);



// functions for direct access to filter controller commands/actions
BOOL FUNC_DECL SetConvolveParam( int impNR, PAR_TYP impTime,  PAR_TYP impAmp );
BOOL FUNC_DECL SetConvolveImpulsNr( int impNR);

BOOL FUNC_DECL TellConvolveParam( PAR_TYP *pfParam );
BOOL FUNC_DECL SetDigPterm( PAR_TYP fDigP );
BOOL FUNC_DECL SetDigIterm( PAR_TYP fDigI );
BOOL FUNC_DECL TellDigParam( PAR_TYP *fDigP );
BOOL FUNC_DECL SetNotch( PAR_TYP fNotchF, PAR_TYP fNotchC );
BOOL FUNC_DECL TellNotchParam( PAR_TYP *pfNotch );
// functions for direct access to vector controller commands/actions

// functions for direct access to analo-input controller commands/actions
BOOL FUNC_DECL TellAnalogParam( PAR_TYP *pfParam );
//
BOOL FUNC_DECL SetAnalogMin( PAR_TYP fVoltOff );
BOOL FUNC_DECL SetAnalogMax( PAR_TYP fVoltOff );
//

// Step Response
BOOL FUNC_DECL SetSR_Rate(PAR_TYP sr_Rate);
BOOL FUNC_DECL SetSR_Length(PAR_TYP len);
BOOL FUNC_DECL SetSR_StepHeight(PAR_TYP sr_height, BOOL isServo);

BOOL FUNC_DECL TellSR_Param(PAR_TYP *pValues);
BOOL FUNC_DECL Execute_SR(PAR_TYP *values);

//Optical link settings
BOOL FUNC_DECL OL_SetStrobe(PAR_TYP strb );
BOOL FUNC_DECL OL_SetTrigger(PAR_TYP trigg );
BOOL FUNC_DECL OL_SetPosErr(PAR_TYP pErr );
BOOL FUNC_DECL OL_SetRepTime(PAR_TYP rTime );
BOOL FUNC_DECL OL_SetResolution(PAR_TYP lsb );

BOOL FUNC_DECL OL_TellParam( PAR_TYP *OL_Param );

//FirmWare Information
BOOL FUNC_DECL FW_Version( PAR_TYP *pVersion );
//READ UNIT ID
BOOL FUNC_DECL ReadUnitID();
////////////////////////////////////////////////////////////////////////////////////////
//////// INPUT SHAPING LICENZE
BOOL FUNC_DECL SetLicenze(long L_1, long L_2);
BOOL FUNC_DECL CheckLicenze(int *pR);
//
BOOL FUNC_DECL SetServo( BOOL bOnOff );
BOOL FUNC_DECL ResetBoard(BOOL HardSoft);
BOOL FUNC_DECL StatusByte( long *pnStatus );
BOOL FUNC_DECL SetAnalog( BOOL bOnOff );
BOOL FUNC_DECL SetConvolveFlag( BOOL bOnOff );
BOOL FUNC_DECL ResetErrorFlag();
//
BOOL FUNC_DECL Dll_FreeInterface();

BOOL FUNC_DECL rs232_connect(int COM_NR, int br);
BOOL FUNC_DECL is_connected();

void FUNC_DECL Dll_ErrStatus( int *pnDllErr );


// class internal errors i.e. DLL internal errors
const int ERR_NONE         = 0;
const int NOT_CONNECTED    = -1;	// DLL interface function was called althougth there is no connection to F-206
const int CONNECTION_FAILED= -2;	// The connection of the DLL to the alpha system can not be established
const int OBJECT_CN_FAILED = -3;	// DLL can not create required internal object, memory problems
const int PARAM_RANGE_ERR  = -4;	// parameter of DLL interface function is out of range
const int UNKNOWN_INTERFACE= -5;	// Interface ID is not known
const int IMP_DLL_LINK     = -6;	// Implementation DLL can not be linked 
const int COM_PORT_ACCESS  = -7;    // COM-port can not be accessed by DLL

const int UNEXPECTED_ERROR = -19;	// the DLL is in a non expected state
const int UNKNOWN_ERROR    = -20;	// the DLL execution failed but no error can be detected

// errors related to communication and alpha handlin
const int BYSINC_COM      = -8;		// Durimg sending or receiving a communication error occured
const int ALPHA_IDENT     = -9;		// An ALPHA controller could not be identified as connected device

// parsing errors
const int PARSER_ERR      = -10;	// General parser error

#define ERR_WRITE	-11
#define ERR_READ	-12
#define TRY_OUT		-13
#define NO_INPUT	-14
#define BCC_ERR		-15
#define SYNC_ERR	-16


#ifdef __cplusplus
}
#endif 

#endif //  _DLLMAIN_H

