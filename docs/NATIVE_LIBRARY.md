# Native Library Analysis (libSensorsRecordIF.so)

Documentation of the reverse-engineered Yamaha Y-Trac native library.

> **Status:** Validated - CAN formulas verified against native output (99.7% match)

## Overview

The `libSensorsRecordIF.so` library is the core component of the Y-Trac Android application. It parses CTRK/TRG telemetry files recorded by the CCU (Communication Control Unit) motorcycle data logger.

### Architectures

| Architecture | Platform | Notes |
|--------------|----------|-------|
| arm64-v8a | Modern Android devices | Recommended |
| armeabi-v7a | Older 32-bit Android | |
| x86_64 | Emulators | Used for analysis |
| x86 | Older emulators | |

## JNI Interface

### Main Functions

| Function | Description |
|----------|-------------|
| `GetTotalLap(fileName)` | Returns number of laps in file |
| `GetLapTimeRecordData(...)` | Retrieves lap timing data |
| `GetSensorsRecordData(...)` | Main function to extract telemetry |
| `GetRecordLineData(...)` | Gets start/finish line coordinates |
| `SplitLogFile(...)` | Splits a log file |
| `DamageRecoveryLogFile(...)` | Attempts to recover corrupted files |

### Java Classes (JNI bindings)

- `com.yamaha.jp.dataviewer.SensorsRecordIF` - Native method declarations
- `com.yamaha.jp.dataviewer.SensorsRecord` - Telemetry data structure
- `com.yamaha.jp.dataviewer.SensorsLapTimeRecord` - Lap timing structure
- `com.yamaha.jp.dataviewer.SensorsRecordLine` - Finish line structure
- `com.yamaha.jp.dataviewer.jni.JNISupport` - Library loader

## CAN Message Parsing

All CAN formulas have been verified by disassembly:

| CAN ID | Fields | Status |
|--------|--------|--------|
| 0x0209 | RPM, Gear | Confirmed |
| 0x0215 | TPS, APS, Launch, TCS, SCS, LIF | Confirmed |
| 0x023E | Water Temp, Intake Temp, Fuel | Confirmed |
| 0x0250 | ACC_X, ACC_Y | Confirmed |
| 0x0258 | LEAN, PITCH | Confirmed (with deadband) |
| 0x0260 | Front/Rear Brake | Confirmed |
| 0x0264 | Front/Rear Speed | Confirmed |
| 0x0268 | F_ABS, R_ABS | Confirmed |

## Calibration Formulas

See [CTRK_FORMAT_SPECIFICATION.md](CTRK_FORMAT_SPECIFICATION.md) for complete formulas.

### LEAN Angle (Special Case)

The native LEAN formula includes a deadband:

```python
def compute_lean_native(data: bytes) -> int:
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
    sum_val = (val1 + val2) & 0xFFFF

    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Deadband: ±5° (499 units) returns upright (9000)
    if deviation <= 499:
        return 9000

    deviation_rounded = deviation - (deviation % 100)
    return (9000 + deviation_rounded) & 0xFFFF
```

## Validation Results

| Metric | Python Parser | Native | Difference |
|--------|---------------|--------|------------|
| Total points | 16475 | 16462 | +13 (0.08%) |
| RPM match | 100% | 100% | Exact |
| LEAN upright | 9165 | 9156 | ~0.1% |
| Timestamp intervals | 100% @ 100ms | 97.8% | Parser more regular |

The 13 extra points are due to undocumented GPS filtering in the native library.

## Tools Used

- **radare2** - Binary analysis (`r2 -q -e scr.color=0 -c 'aaa; afl~CAN' libSensorsRecordIF.so`)
- **nm -D** - Symbol extraction
- **jadx** - APK decompilation
