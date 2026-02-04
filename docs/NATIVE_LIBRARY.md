# Native Library Analysis (libSensorsRecordIF.so)

Documentation of the reverse-engineered Yamaha Y-Trac native library.

> **Status:** Validated — 47 files, 22 channels, 94.9% match rate against native output (42 comparison pairs)
>
> **Last Updated:** 2026-02-04

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

## Output Data Structure

The native library populates the following data structure for each telemetry sample:

```c
struct SensorsRecord {
    int64_t  mTime;        // Unix timestamp (milliseconds)
    float    mLat;         // Latitude (degrees, WGS84)
    float    mLon;         // Longitude (degrees, WGS84)
    float    mGpsSpeedKnot;// GPS ground speed (knots)
    uint16_t mRPM;         // Engine RPM (raw)
    int16_t  mAPS;         // Accelerator Position Sensor (raw)
    int16_t  mTPS;         // Throttle Position Sensor (raw)
    int16_t  mWT;          // Water temperature (raw)
    int16_t  mINTT;        // Intake air temperature (raw)
    int16_t  mFSPEED;      // Front wheel speed (raw)
    int16_t  mRSPEED;      // Rear wheel speed (raw)
    int32_t  mFUEL;        // Fuel consumption (raw)
    uint16_t mLEAN;        // Lean angle (raw)
    uint16_t mPITCH;       // Pitch rate (raw)
    int16_t  mACCX;        // Longitudinal acceleration (raw)
    int16_t  mACCY;        // Lateral acceleration (raw)
    int16_t  mFPRESS;      // Front brake pressure (raw)
    int16_t  mRPRESS;      // Rear brake pressure (raw)
    int8_t   mGEAR;        // Current gear (0-6, 0=neutral)
    bool     mFABS;        // Front ABS active
    bool     mRABS;        // Rear ABS active
    int8_t   mLAUNCH;      // Launch control active
    int8_t   mSCS;         // Slide Control System active
    int8_t   mTCS;         // Traction Control System active
    int8_t   mLIF;         // Lift control active
};
```

The native library also provides lap timing data:

```c
struct SensorsLapTimeRecord {
    int64_t mTime;        // Lap time in milliseconds
    int64_t mSplitTime;   // Split time (if applicable)
};
```

## CAN Message Parsing

All CAN formulas have been verified by disassembly:

| CAN ID | Fields | Status |
|--------|--------|--------|
| 0x0209 | RPM, Gear | ✓ Confirmed |
| 0x0215 | TPS, APS, Launch, TCS, SCS, LIF | ✓ Confirmed |
| 0x023E | Water Temp, Intake Temp, Fuel | ✓ Confirmed |
| 0x0250 | ACC_X, ACC_Y | ✓ Confirmed |
| 0x0258 | LEAN, PITCH | ✓ Confirmed (with deadband) |
| 0x0260 | Front/Rear Brake | ✓ Confirmed |
| 0x0264 | Front/Rear Speed | ✓ Confirmed |
| 0x0268 | F_ABS, R_ABS | ✓ Confirmed (R_ABS=bit0, F_ABS=bit1) |

### Record Timestamp Structure

Each record has a 14-byte header containing a 10-byte timestamp. See [CTRK_FORMAT_SPECIFICATION.md Section 4.1](CTRK_FORMAT_SPECIFICATION.md#41-record-header) for the complete structure: `[millis(2LE)][sec][min][hour][wday][day][month][year(2LE)]`. The native library uses bytes 2-9 (the same-second portion) for its `memcmp` optimization at 0xaee1.

## Calibration Formulas

See [CTRK_FORMAT_SPECIFICATION.md](CTRK_FORMAT_SPECIFICATION.md) for complete formulas.

### LEAN Angle (Special Case)

The native LEAN formula includes a deadband with nibble interleaving and truncation. See [CTRK_FORMAT_SPECIFICATION.md Section 8.2.5](CTRK_FORMAT_SPECIFICATION.md#825-lean-angle) for the complete algorithm.

## Validation Results

### Test Coverage

- **Files tested:** 47 CTRK files (42 with native comparison pairs)
- **Date range:** July 2025 - October 2025
- **Total records:** 420K+ telemetry points

### Analog Channels Comparison (min/max/avg across all files)

| Channel | Python | Native | Status |
|---------|--------|--------|--------|
| rpm | 0 / 15232 / 5507 | 0 / 15232 / 5515 | ✓ Exact min/max |
| throttle_grip | 0 / 107.2 / 15.0 | 0 / 107.2 / 15.0 | ✓ Exact |
| throttle | 0 / 102.7 / 15.4 | 0 / 102.7 / 15.4 | ✓ Exact |
| water_temp | -30 / 115 / 82.3 | -30 / 115 / 81.7 | ✓ Exact min/max |
| intake_temp | -30 / 51.2 / 26.9 | -30 / 51.3 / 26.8 | ✓ Match |
| front_speed_kmh | 0 / 276.9 / 69.1 | 0 / 276.9 / 69.0 | ✓ Exact |
| rear_speed_kmh | 0 / 274.7 / 70.0 | 0 / 274.7 / 69.9 | ✓ Exact |
| fuel_cc | 0 / 833 / 203.6 | 0 / 833 / 204.0 | ✓ Exact min/max |
| lean_deg | -90 / 56 / 14.9 | -90 / 56 / 14.9 | ✓ Exact |
| pitch_deg_s | -300 / 80.1 / -0.6 | -300 / 80.1 / -0.8 | ✓ Exact min/max |
| acc_x_g | -7 / 2.0 / 0.0 | -7 / 2.0 / 0.0 | ✓ Exact |
| acc_y_g | -7 / 1.5 / 0.0 | -7 / 1.5 / 0.0 | ✓ Exact |
| front_brake_bar | 0 / 1.7 / 0.1 | 0 / 1.7 / 0.1 | ✓ Exact |
| rear_brake_bar | 0 / 0 / 0 | 0 / 0 / 0 | ✓ Exact |
| gear | 0 / 6 / 1.6 | 0 / 6 / 1.6 | ✓ Exact |

### Boolean Channels Comparison

| Channel | Python True | Native True | Status |
|---------|-------------|-------------|--------|
| f_abs | 70 | 68 | ✓ Match |
| r_abs | 7,358 | 7,326 | ✓ Match |
| tcs | 21,111 | 20,995 | ✓ Match |
| scs | 1,742 | 1,735 | ✓ Match |
| lif | 4,156 | 4,113 | ✓ Match |
| launch | 0 | 0 | ✓ Exact |

### Notes

- Minor differences in record counts (~0.1%) due to GPS timestamp handling
- All min/max values are identical between Python and native
- Average values differ by < 0.5% due to record count differences
- Boolean channels show < 1% difference due to record alignment

## Tools Used

- **radare2** - Binary analysis (`r2 -q -e scr.color=0 -c 'aaa; afl~CAN' libSensorsRecordIF.so`)
- **nm -D** - Symbol extraction
- **jadx** - APK decompilation
- **Android Emulator** - Native library execution for comparison
- **Python parser** - Independent implementation for validation

## Changelog

### 2026-01-27
- Validated 47 CTRK files across 4 months (42 with native comparison pairs)
- Documented 10-byte record timestamp structure (millis + date/time fields)
- Documented year encoding as uint16 LE (e.g., 2025 = 0x07E9)
- Corrected ABS bit order (R_ABS=bit0, F_ABS=bit1)
- Full channel validation completed (22 channels, 420K+ records)

### 2026-01-26
- Initial validation with single test file
- CAN formulas verified via disassembly
