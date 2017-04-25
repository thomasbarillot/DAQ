#include "extcode.h"
#pragma pack(push)
#pragma pack(1)

#ifdef __cplusplus
extern "C" {
#endif

void __cdecl PI_E750_cp_setposition(float PositionUm);
void __cdecl PI_E750_cp_setvelocity(float stageVelocity);
float __cdecl PI_E750_cp_getpos(void);
void __cdecl PI_E750_cp_close(void);
void __cdecl PI_E750_cp_open(float COM_Port);

long __cdecl LVDLLStatus(char *errStr, int errStrLen, void *module);

#ifdef __cplusplus
} // extern "C"
#endif

#pragma pack(pop)

