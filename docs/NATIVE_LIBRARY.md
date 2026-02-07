# Native Library Analysis (libSensorsRecordIF.so)

Documentation of the reverse-engineered Yamaha Y-Trac native library.

## Overview

The `libSensorsRecordIF.so` library is the core component of the Y-Trac Android application. It parses CTRK/TRG telemetry files recorded by the CCU (Communication Control Unit) motorcycle data logger.

### Library Information

| Property | Value |
|----------|-------|
| Library | libSensorsRecordIF.so |
| Source | Y-Trac Android APK |
| Tested version | 1.3.8 |
| Analysis tool | radare2 |

### Available Architectures

| Architecture | Platform | Notes |
|--------------|----------|-------|
| arm64-v8a | Modern Android devices | Recommended |
| armeabi-v7a | Older 32-bit Android | |
| x86_64 | Emulators | Used for disassembly analysis |
| x86 | Older emulators | |

## JNI Interface

### Main Functions

| Function | Address | Description |
|----------|---------|-------------|
| `GetTotalLap` | — | Returns number of laps in file |
| `GetLapTimeRecordData` | — | Retrieves lap timing data |
| `GetSensorsRecordData` | 0xa970 | Main function to extract telemetry |
| `GetRecordLineData` | — | Gets start/finish line coordinates |
| `SplitLogFile` | — | Splits a log file |
| `DamageRecoveryLogFile` | — | Attempts to recover corrupted files |

### Java Classes (JNI bindings)

- `com.yamaha.jp.dataviewer.SensorsRecordIF` — Native method declarations
- `com.yamaha.jp.dataviewer.SensorsRecord` — Telemetry data structure
- `com.yamaha.jp.dataviewer.SensorsLapTimeRecord` — Lap timing structure
- `com.yamaha.jp.dataviewer.SensorsRecordLine` — Finish line structure
- `com.yamaha.jp.dataviewer.jni.JNISupport` — Library loader

## Data Structures

### SensorsRecord

The native library populates this structure for each telemetry sample:

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

### SensorsLapTimeRecord

```c
struct SensorsLapTimeRecord {
    int64_t mTime;        // Lap time in milliseconds
    int64_t mSplitTime;   // Split time (if applicable)
};
```

## Key Functions (Disassembly)

### GetSensorsRecordData (0xa970)

Main entry point for telemetry extraction. Processes one lap at a time.

**Behavior:**
1. Calls `memset(state, 0, 0x2c8)` at 0xa9fc to initialize CAN state
2. Calls `memset(aux, 0, 0x2e0)` at 0xaa10 to initialize auxiliary state
3. Iterates through records calling `getLogRecord` at 0xf921
4. Dispatches to type-specific handlers

### getLogRecord (0xf921)

Reads a single 14-byte record header from the file.

```c
fread(buf, 14, 1, file);  // Always reads exactly 14 bytes
```

### GetTimeData (0xdf40)

Converts the 10-byte timestamp structure to epoch milliseconds.

**Timestamp structure:**
```
[millis(2LE)][sec][min][hour][wday][day][month][year(2LE)]
```

### GetTimeDataEx (0xde80)

Optimized timestamp computation using incremental updates when records share the same second.

**Logic:**
- Uses `memcmp` at 0xaee1 to compare bytes 2-9 (same-second check)
- If same second: `epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)`
- Otherwise: full recomputation via GetTimeData

### AnalisysCAN (0xdfd0)

Dispatches CAN messages to type-specific decoders.

**CAN payload structure:**
```
[canid(2LE)][pad(2)][DLC(1)][data(DLC)]
```

Note: DLC byte exists but is **never read** — the library assumes fixed sizes per CAN ID.

### AnalisysNMEA (0xe330)

Parses GPS NMEA sentences.

**Behavior:**
- Uses `strncmp` to check for `$GPRMC`
- Validates checksum via XOR
- Extracts lat, lon, speed

## CAN Message Handlers

All handlers verified by disassembly:

| CAN ID | Handler Address | Fields |
|--------|----------------|--------|
| 0x0209 | 0xe14b | RPM, Gear |
| 0x0215 | 0xe170 | TPS, APS, Launch, TCS, SCS, LIF |
| 0x023E | 0xe292 | Water Temp, Intake Temp, Fuel |
| 0x0250 | 0xe0be | ACC_X, ACC_Y |
| 0x0258 | 0xe1bc | LEAN, PITCH |
| 0x0260 | 0xe226 | Front Brake, Rear Brake |
| 0x0264 | 0xe07a | Front Speed, Rear Speed |
| 0x0268 | 0xe2b7 | F_ABS, R_ABS |
| 0x051b | 0xe102 | Stores 8 bytes at offset 0x2c8 (unmapped) |

### Notable Behaviors

#### Gear 7 Rejection (0xe163)

```asm
cmp eax, 7
je skip  ; Reject gear value 7 (transitioning)
```

#### ABS Bit Order (0xe2b7)

```
R_ABS = data[4] & 1      ; bit 0
F_ABS = (data[4] >> 1) & 1  ; bit 1
```

Note: R_ABS is bit 0, F_ABS is bit 1 (counterintuitive order).

#### LEAN Deadband (0xe1bc-0xe32e)

The LEAN calculation includes:
1. Nibble interleaving across bytes 0-3
2. Deviation from center (9000)
3. Deadband: if deviation <= 499, return 9000 (upright)
4. Truncation to nearest 100 (floor, not round)

## Emission Logic

### Time Delta Check (0xaf19)

```asm
cmp rcx, 100  ; Compare delta with 100ms
jge emit      ; Emit if >= 100ms
```

Records are emitted at 100ms intervals (10 Hz).

### Three-Band Classification (0xaf1b)

The native library classifies time deltas into bands:

| Band | Condition | Action |
|------|-----------|--------|
| 0 | delta < 0 | Emit with error code -2 |
| 1 | delta <= 10ms | Skip record entirely |
| 2 | 10ms < delta < 100ms | Process, clear validity flag |
| 3 | delta >= 100ms | Full processing + emit |

### Row Counter Limit (0xaece)

```asm
cmp [rcx], eax
jge error_-3  ; Return -3 if counter >= 72000
```

Maximum 72,000 records per lap (2 hours at 10 Hz).

### GPS Sentinel Values (0xaa39)

```asm
movaps xmm0, [0x2b380]  ; Load 9999.0 sentinel
```

When no GPS fix: lat = 9999.0, lon = 9999.0

### State Initialization (0xa9fc)

```asm
memset(state, 0, 0x2c8)  ; Zero all CAN state
```

Called at the start of each lap, producing physically impossible initial values:
- acc_x, acc_y = -7.0 G
- lean = -90.0°
- pitch = -300.0°/s

## Lap Detection

The native library uses **type-5 Lap marker records** from the CCU hardware for lap boundaries:

1. `fcn.0000a430` scans for type-5 records to count total laps
2. `moveToLapLogRecorOffset` at 0xed50 seeks to lap N's start position
3. Each lap is processed independently with full state reset

## Known Bugs

### Millis Wrapping

When the millisecond counter wraps (999 → 0) within the same second field:
- Native produces negative time delta
- Emits record with error code -2
- Can suppress emission for entire lap (~90 seconds)

**Observed:** File 20250906-161606, lap 6 missing in native output.

## Tools Used

- **radare2** — Binary analysis (`r2 -q -e scr.color=0 -c 'aaa; afl' lib.so`)
- **nm -D** — Symbol extraction
- **jadx** — APK decompilation
- **Android Emulator** — Runtime execution for output comparison
