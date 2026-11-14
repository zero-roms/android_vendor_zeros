/* Stand-ins for Flipper's core/check.h, so lib/infrared builds on a computer.
 * A failed check ends only the current request (irtool_fail), not the run. */
#pragma once
void irtool_fail(void);
#define furi_check(x) do { if(!(x)) irtool_fail(); } while(0)
#define furi_assert(x) furi_check(x)
#define furi_crash(...) irtool_fail()
