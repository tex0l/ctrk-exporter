# Native Library Analysis (libSensorsRecordIF.so)

Documentation of the reverse-engineered Yamaha Y-Trac native library.

## Overview

The `libSensorsRecordIF.so` library is the core component of the Y-Trac Android application. It parses CTRK/CCT/TRG telemetry files recorded by the CCU (Communication Control Unit) motorcycle data logger. The Android app calls into this library via JNI to extract per-lap telemetry records.

### Library Information

| Property | Value |
|----------|-------|
| Library | libSensorsRecordIF.so |
| Source | Y-Trac Android APK (package: `com.yamaha.jp.dataviewer`) |
| Tested version | 1.3.8 |
| Analysis tools | radare2, nm -D, jadx |

### Available Architectures

| Architecture | Platform | Notes |
|--------------|----------|-------|
| arm64-v8a | Modern Android devices | Recommended for Apple Silicon emulators |
| armeabi-v7a | Older 32-bit Android | |
| x86_64 | Emulators (Intel/AMD) | Used for disassembly analysis |
| x86 | Older emulators | |

### File Type Support

The library handles two file formats identified by extension:

| Format Code | Extension | Constant |
|-------------|-----------|----------|
| 0 | `.CTRK` / `.CCT` | `FILE_TYPE_CCT` |
| 1 | `.TRG` | `FILE_TYPE_TRG` |

---

## JNI Interface

### Java/Kotlin Classes (JNI Bindings)

| Class | Description |
|-------|-------------|
| `com.yamaha.jp.dataviewer.SensorsRecordIF` | Native method declarations (singleton) |
| `com.yamaha.jp.dataviewer.SensorsRecord` | Telemetry data structure (filled by native via JNI reflection) |
| `com.yamaha.jp.dataviewer.SensorsLapTimeRecord` | Lap timing structure |
| `com.yamaha.jp.dataviewer.SensorsRecordLine` | Finish line coordinates structure |
| `com.yamaha.jp.dataviewer.SensorsLapRecord` | Container for one lap's samples |
| `com.yamaha.jp.dataviewer.LoggerFile` | Top-level session container |
| `com.yamaha.jp.dataviewer.LoggerFile.AINInfo` | Auxiliary analog input metadata |
| `com.yamaha.jp.dataviewer.jni.JNISupport` | Library loader and initialization |

### JNI Functions

All addresses are from the x86_64 build unless noted otherwise.

| Function | Address | Scope | Description |
|----------|---------|-------|-------------|
| `Initialize` | -- | static (JNISupport) | One-time library initialization; called on load |
| `GetTotalLap` | -- | static | Returns number of laps in file (counts type-5 markers) |
| `GetLapTimeRecordData` | -- | static | Retrieves lap timing data (fills `SensorsLapTimeRecord[]`) |
| `GetRecordLineData` | -- | static | Gets start/finish line coordinates (fills `SensorsRecordLine[]`) |
| `GetSensorsRecordData` | 0xa970 | instance | Main function: extracts telemetry for one lap |
| `GetSensorsDistanceRecordData` | -- | instance | Distance-based resampling mode (alternative to time-based) |
| `SplitLogFile` | -- | instance | Splits a multi-session log file |
| `DamageRecoveryLogFile` | -- | static | Checks for / recovers corrupted files |
| `TimeStampRecoveryLogFile` | -- | static | Recovers files with timestamp errors |
| `GetEncryptSecretKey` | -- | instance | Returns encryption secret key (string) |

### GetSensorsRecordData Signature

This is the primary telemetry extraction function. Its full JNI signature:

```java
int GetSensorsRecordData(
    String fileName,       // Path to CTRK/TRG file
    int fileType,          // 0=CCT/CTRK, 1=TRG
    int lapIndex,          // 0-based lap index
    SensorsRecord[] output,// Pre-allocated array (filled by native)
    int maxRecords,        // Maximum records to return (typically 72000)
    int[] actualCount,     // Output: actual number of records written [1]
    AINInfo ainInfo         // Output: auxiliary input metadata
)
```

**Return codes:**

| Code | Constant | Description |
|------|----------|-------------|
| 0 | `RET_NORMAL` | Success |
| -1 | `RET_ERROR` | General error |
| -2 | `RET_TIMESTAMP_ERROR` | Negative time delta detected |
| -3 | `RET_READSIZE_OVER` | Record counter exceeded 72,000 limit |
| -4 | `RET_EMPTY` | No data to return |
| -201 | `RET_LAPSPLIT_FAILED` | Lap splitting failed |
| 64 | `RET_DAMAGE_RECOVERY` | File is damaged (recoverable) |
| 128 | `RET_TIME_STAMP_RECOVERY` | Timestamp recovery applied |

### Per-Lap Calling Convention

The Android app calls `GetSensorsRecordData` once per lap in a loop:

```kotlin
for (lapIdx in 0 until lapTotal) {
    val samples = Array(72000) { SensorsRecord() }
    val sampleCount = intArrayOf(0)
    val auxChannels = LoggerFile.AINInfo()
    parser.getSensorsRecordData(path, formatCode, lapIdx, samples, 72000, sampleCount, auxChannels)
    // Write sampleCount[0] records to CSV
}
```

Each call processes one lap independently with full state reset (see [State Initialization](#state-initialization-0xa9fc)).

### Coordinate Validation Utility

```kotlin
fun IsEffectiveLonLat(coord: Float): Boolean = coord < 1000.0f
```

Coordinates >= 1000.0 are treated as sentinel/invalid (default is 9999.0).

---

## Data Structures

### SensorsRecord

The native library populates this structure for each telemetry sample via JNI field reflection. Field names must match exactly for JNI to work.

```c
// Native C struct (reconstructed from JNI bindings)
struct SensorsRecord {
    // Timing and position
    int64_t  mTime;         // Unix timestamp (milliseconds)
    float    mLat;          // Latitude (degrees, WGS84; 9999.0 = no fix)
    float    mLon;          // Longitude (degrees, WGS84; 9999.0 = no fix)
    float    mGpsSpeedKnot; // GPS ground speed (knots)

    // Powertrain
    uint16_t mRPM;          // Engine RPM (raw, Kotlin type: Char)
    int16_t  mAPS;          // Accelerator Position Sensor (raw)
    int16_t  mTPS;          // Throttle Position Sensor (raw)
    int8_t   mGEAR;         // Current gear (0-6, 0=neutral)

    // Thermal
    int16_t  mWT;           // Water temperature (raw)
    int16_t  mINTT;         // Intake air temperature (raw)

    // Velocity
    int16_t  mFSPEED;       // Front wheel speed (raw)
    int16_t  mRSPEED;       // Rear wheel speed (raw)

    // Brakes
    int16_t  mFPRESS;       // Front brake pressure (raw)
    int16_t  mRPRESS;       // Rear brake pressure (raw)

    // IMU / Dynamics
    uint16_t mLEAN;         // Lean angle (raw, Kotlin type: Char)
    uint16_t mPITCH;        // Pitch rate (raw, Kotlin type: Char)
    int16_t  mACCX;         // Longitudinal acceleration (raw)
    int16_t  mACCY;         // Lateral acceleration (raw)

    // Consumption
    int32_t  mFUEL;         // Fuel consumption (raw, cumulative)

    // Electronic systems
    bool     mFABS;         // Front ABS active
    bool     mRABS;         // Rear ABS active
    int8_t   mLAUNCH;       // Launch control active
    int8_t   mSCS;          // Slide Control System active
    int8_t   mTCS;          // Traction Control System active
    int8_t   mLIF;          // Lift control active

    // Auxiliary analog inputs
    char*    mAIN1;         // AIN channel 1 value (string, Kotlin: String)
    char*    mAIN2;         // AIN channel 2 value (string, Kotlin: String)

    // Raw CAN bus frames (stored but not decoded into named channels)
    int64_t  mCAN0511;      // Raw 8-byte payload from CAN 0x0511
    int64_t  mCAN051B;      // Raw 8-byte payload from CAN 0x051B
    int64_t  mCAN0226;      // Raw 8-byte payload from CAN 0x0226
    int64_t  mCAN0227;      // Raw 8-byte payload from CAN 0x0227
};
```

**Notes on Kotlin/JVM types:**

- `mRPM`, `mLEAN`, `mPITCH` are `Char` in Kotlin (unsigned 16-bit). Access the numeric value via `.code`.
- `mFABS`, `mRABS` are `Boolean`. All other electronic system flags are `Byte`.
- `mCAN0511`, `mCAN051B`, `mCAN0226`, `mCAN0227` are `Long` (64-bit), storing the raw 8 CAN data bytes packed into a single integer.

### SensorsLapTimeRecord

```c
struct SensorsLapTimeRecord {
    int64_t mTime;      // Lap time in milliseconds
    int8_t  mRank;      // Lap ranking (e.g., best=1)
    int8_t  mNo;        // Lap number
};
```

**Note:** An earlier version of this document listed `mSplitTime` as a field. The actual Kotlin binding shows `mRank` and `mNo` instead. There is no split-time field.

### SensorsRecordLine

Represents the start/finish line as two GPS points.

```c
struct SensorsRecordLine {
    double mStartLat;   // Finish line point 1, latitude (degrees)
    double mStartLon;   // Finish line point 1, longitude (degrees)
    double mEndLat;     // Finish line point 2, latitude (degrees)
    double mEndLon;     // Finish line point 2, longitude (degrees)
};
```

### LoggerFile.AINInfo

Metadata about auxiliary analog input channels.

```c
struct AINInfo {
    bool  mAIN1Valid;    // Whether AIN channel 1 is present
    bool  mAIN2Valid;    // Whether AIN channel 2 is present
    int8_t mAIN1Format; // Format code for AIN channel 1
    int8_t mAIN2Format; // Format code for AIN channel 2
};
```

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `RECORD_SIZE_MAX` | 72000 | Maximum records per lap (2 hours at 10 Hz) |
| `LAT_DEFAULT` | 9999.0f | GPS latitude sentinel (no fix) |
| `LON_DEFAULT` | 9999.0f | GPS longitude sentinel (no fix) |
| `FILE_TYPE_CCT` | 0 | CTRK/CCT file format |
| `FILE_TYPE_TRG` | 1 | TRG file format |
| `LAP_ALL` | 0 | Retrieve all laps at once (if supported) |

---

## Key Functions (Disassembly)

All addresses below are from the **x86_64** build of the library.

### GetSensorsRecordData (0xa970)

Main entry point for telemetry extraction. Processes **one lap** per call.

**Behavior:**

1. Calls `memset(state, 0, 0x2c8)` at 0xa9fc to initialize CAN state (712 bytes)
2. Calls `memset(aux, 0, 0x2e0)` at 0xaa10 to initialize auxiliary state (736 bytes)
3. Initializes GPS sentinels: lat = 9999.0, lon = 9999.0 at 0xaa39
4. Seeks to the target lap's starting position via `moveToLapLogRecorOffset` (0xed50)
5. Iterates through records calling `getLogRecord` at 0xf921
6. Dispatches to type-specific handlers based on record type
7. Applies emission logic to output records at 100ms intervals
8. Returns status code and actual record count via output parameters

### getLogRecord (0xf921)

Reads a single record from the file.

```c
fread(buf, 14, 1, file);  // Always reads exactly 14 bytes (record header)
```

The 14-byte header contains: record_type (2 LE), total_size (2 LE), and 10-byte timestamp.

### GetTimeData (0xdf40)

Converts the 10-byte timestamp structure to epoch milliseconds (full computation).

**Timestamp structure (10 bytes):**
```
Offset  Size  Field
0       2     millis (uint16 LE, 0-999)
2       1     seconds (0-59)
3       1     minutes (0-59)
4       1     hours (0-23, UTC)
5       1     weekday (1=Monday ... 7=Sunday)
6       1     day (1-31)
7       1     month (1-12)
8       2     year (uint16 LE, e.g. 2025)
```

Converts calendar fields to Unix epoch seconds via `mktime`, then adds millis.

### GetTimeDataEx (0xde80)

Optimized timestamp computation using incremental updates when consecutive records share the same second. This is a performance optimization that avoids calling `mktime` for every record.

**Algorithm:**

```
1. If prev_ts_bytes is NULL (first record):
   → Full computation via GetTimeData

2. If ts_bytes == prev_ts_bytes (all 10 bytes identical):
   → Reuse prev_epoch_ms (fast path, no computation needed)

3. If ts_bytes[2:10] == prev_ts_bytes[2:10] (same second, different millis):
   → memcmp at 0xaee1 compares bytes 2-9
   → Incremental: epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)

4. Otherwise (different second):
   → Full recomputation via GetTimeData
```

The same-second check (step 3) compares bytes 2 through 9 (sec, min, hour, wday, day, month, year) -- all fields except millis.

**Millis wrapping:** If `curr_millis < prev_millis` within the same second (hardware non-atomic capture), the native library does NOT add 1000ms. This produces a negative delta, which triggers the error -2 return code (see [Known Bugs](#known-bugs)).

### AnalisysCAN (0xdfd0)

Dispatches CAN messages to type-specific decoders based on CAN ID.

**CAN payload structure (within record payload):**
```
Offset  Size  Field
0       2     can_id (uint16 LE)
2       2     padding (always 0x0000)
4       1     DLC (Data Length Code)
5       DLC   can_data (CAN frame payload)
```

**Note:** The DLC byte exists in the payload but is **never read by the native library** -- it assumes fixed sizes per CAN ID based on a hardcoded dispatch table.

### AnalisysNMEA (0xe330)

Parses GPS NMEA sentences from type-2 records.

**Behavior:**

1. Uses `strncmp` to check for `$GPRMC` prefix
2. Validates checksum via XOR of all bytes between `$` and `*`
3. Checks status field (field 2): `A` = valid fix, `V` = void
4. If status `A`: extracts latitude, longitude, and speed from sentence fields
5. If status `V`: acknowledges GPS presence (enables emission) but does NOT update position or speed
6. Converts NMEA DDDmm.mmmm format to decimal degrees
7. Updates mLat, mLon, mGpsSpeedKnot in the output record

---

## CAN Message Handlers

All handlers verified by radare2 disassembly of the x86_64 build.

### Handler Dispatch Table

| CAN ID | Handler Address | DLC | Fields | Mapped to SensorsRecord |
|--------|----------------|-----|--------|------------------------|
| 0x0209 | 0xe14b | 6 | RPM, Gear | mRPM, mGEAR |
| 0x0215 | 0xe170 | 8 | TPS, APS, Launch, TCS, SCS, LIF | mTPS, mAPS, mLAUNCH, mTCS, mSCS, mLIF |
| 0x0226 | -- | 7 | (unknown purpose) | mCAN0226 (raw 8 bytes as int64) |
| 0x0227 | -- | 3 | (unknown purpose) | mCAN0227 (raw 8 bytes as int64) |
| 0x023E | 0xe292 | 4 | Water Temp, Intake Temp, Fuel delta | mWT, mINTT, mFUEL |
| 0x0250 | 0xe0be | 8 | ACC_X, ACC_Y | mACCX, mACCY |
| 0x0258 | 0xe1bc | 8 | LEAN, PITCH | mLEAN, mPITCH |
| 0x0260 | 0xe226 | 8 | Front Brake, Rear Brake | mFPRESS, mRPRESS |
| 0x0264 | 0xe07a | 4 | Front Speed, Rear Speed | mFSPEED, mRSPEED |
| 0x0268 | 0xe2b7 | 6 | F_ABS, R_ABS | mFABS, mRABS |
| 0x0511 | 0xe102 | 8 | (unknown purpose) | mCAN0511 (raw 8 bytes as int64) |
| 0x051b | 0xe102 | 8 | (stores at state offset 0x2c8) | mCAN051B (raw 8 bytes as int64) |

**Note on unknown CAN IDs:** CAN IDs 0x0226, 0x0227, 0x0511, and 0x051b are present in CTRK files and handled by the native library, but the library does not decode them into named telemetry channels. Instead, it stores the raw CAN data bytes into the corresponding `mCAN*` fields of `SensorsRecord`, making them available for future use or external analysis.

### Handler Details

#### CAN 0x0209 -- Engine (DLC=6)

**Address:** 0xe14b

```
Byte  Field    Type      Description
0-1   RPM      uint16 BE Engine RPM
2-3   --       --        (unused)
4     Gear     uint8     data[4] & 0x07 (lower 3 bits)
5     --       --        (unused)
```

##### Gear 7 Rejection (0xe163)

```asm
cmp eax, 7
je skip  ; Reject gear value 7 (transitioning between gears)
```

Gear value 7 indicates a gear transition in progress and is discarded. The previous gear value is retained.

#### CAN 0x0215 -- Throttle and Electronic Controls (DLC=8)

**Address:** 0xe170

```
Byte  Field    Type      Description
0-1   TPS      uint16 BE Throttle Position Sensor
2-3   APS      uint16 BE Accelerator Position Sensor
4-5   --       --        (unused)
6     Launch   uint8     (data[6] & 0x60): non-zero = active
7     Controls uint8     bit 5 = TCS, bit 4 = SCS, bit 3 = LIF
```

Extraction:
- TPS raw: `(data[0] << 8) | data[1]`
- APS raw: `(data[2] << 8) | data[3]`
- Launch: `1 if (data[6] & 0x60) else 0`
- TCS: `(data[7] >> 5) & 1`
- SCS: `(data[7] >> 4) & 1`
- LIF: `(data[7] >> 3) & 1`

#### CAN 0x023E -- Temperature and Fuel (DLC=4)

**Address:** 0xe292

```
Byte  Field       Type      Description
0     WaterTemp   uint8     Single byte (NOT uint16)
1     IntakeTemp  uint8     Single byte (NOT uint16)
2-3   FuelDelta   uint16 BE Fuel consumption delta (accumulated)
```

**Fuel accumulator:** The fuel value is a delta, not an absolute. The native library maintains an internal accumulator:

```
fuel_accumulator += (data[2] << 8) | data[3]
mFUEL = fuel_accumulator
```

The accumulator resets to 0 when `GetSensorsRecordData` is called (per-lap reset via `memset`).

#### CAN 0x0250 -- Acceleration (DLC=8)

**Address:** 0xe0be

```
Byte  Field  Type      Description
0-1   ACC_X  uint16 BE Longitudinal acceleration
2-3   ACC_Y  uint16 BE Lateral acceleration
4-7   --     --        (unused)
```

#### CAN 0x0258 -- IMU: Lean and Pitch (DLC=8)

**Address:** 0xe1bc (LEAN decoding spans 0xe1bc-0xe32e)

```
Byte  Field  Type      Description
0-3   LEAN   packed    Lean angle (packed nibble format, see below)
4-5   --     --        (unused)
6-7   PITCH  uint16 BE Pitch rate
```

##### LEAN Decoding Algorithm (0xe1bc-0xe32e)

The lean angle uses a non-trivial packed format with deadband and truncation:

```python
def decode_lean(data):
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    # Step 1: Extract two packed values from interleaved nibbles
    val1_part = (b0 << 4) | (b2 & 0x0F)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0F) << 4) | (b3 >> 4)

    # Step 2: Sum (16-bit)
    sum_val = (val1 + val2) & 0xFFFF

    # Step 3: Compute deviation from upright (9000 = 0 degrees)
    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Step 4: Apply deadband (approximately +/-5 degrees)
    if deviation <= 499:
        return 9000  # Upright

    # Step 5: Truncate to nearest 100 (floor/integer division, NOT rounding)
    deviation_rounded = deviation - (deviation % 100)
    return (9000 + deviation_rounded) & 0xFFFF
```

**Key properties:**
1. Output value 9000 means upright (0 degrees lean after calibration)
2. Deadband of 499 raw units (~5 degrees) around center
3. Truncation to nearest 100 uses floor (integer division), not rounding
4. The native output loses lean direction -- always produces values >= 9000
5. The Python parser extends this with a signed variant (`lean_signed`) that preserves direction

#### CAN 0x0260 -- Brake Pressure (DLC=8)

**Address:** 0xe226

```
Byte  Field       Type      Description
0-1   FrontBrake  uint16 BE Front brake hydraulic pressure
2-3   RearBrake   uint16 BE Rear brake hydraulic pressure
4-7   --          --        (unused)
```

#### CAN 0x0264 -- Wheel Speed (DLC=4)

**Address:** 0xe07a

```
Byte  Field       Type      Description
0-1   FrontSpeed  uint16 BE Front wheel speed
2-3   RearSpeed   uint16 BE Rear wheel speed
```

#### CAN 0x0268 -- ABS Status (DLC=6)

**Address:** 0xe2b7

```
Byte  Field   Type  Description
0-3   --      --    (unused)
4     ABS     uint8 bit 0 = R_ABS, bit 1 = F_ABS
5     --      --    (unused)
```

##### ABS Bit Order (0xe2b7)

```
R_ABS = data[4] & 1        ; bit 0
F_ABS = (data[4] >> 1) & 1 ; bit 1
```

**Note:** R_ABS is bit 0 and F_ABS is bit 1 (counterintuitive order -- one might expect front first).

#### CAN 0x0511 and 0x051b -- Unknown (DLC=8)

**Addresses:** 0xe102 (0x051b); 0x0511 handler address not independently confirmed.

These CAN IDs are present in files but not decoded into named telemetry channels. The native library stores the raw 8-byte payloads:

- 0x051b: stores 8 bytes at state offset 0x2c8, mapped to `mCAN051B`
- 0x0511: mapped to `mCAN0511`
- 0x0226: mapped to `mCAN0226`
- 0x0227: mapped to `mCAN0227`

All four are exposed as `Long` (int64) fields in the `SensorsRecord` Java class but are not decoded into physical quantities.

---

## Calibration Formulas

The native library outputs **raw** sensor values in `SensorsRecord`. Calibration to engineering units is performed in the Java/Kotlin layer (specifically in `SensorsRecord.formatCalibrated()` and the Y-Trac app's `SeriesDispInfo` class).

All calibration formulas are documented in `CTRK_FORMAT_SPECIFICATION.md` Section 9 and in `CLAUDE.md`. A quick reference:

| Channel | Formula | Unit |
|---------|---------|------|
| RPM | `mRPM.code / 2.56` | RPM |
| TPS/APS | `((raw / 8.192) * 100.0) / 84.96` | % |
| Front/Rear Speed | `(raw / 64.0) * 3.6` | km/h |
| Lean | `(mLEAN.code / 100.0) - 90.0` | degrees |
| Pitch | `(mPITCH.code / 100.0) - 300.0` | deg/s |
| ACC_X / ACC_Y | `(raw / 1000.0) - 7.0` | G |
| Front/Rear Brake | `raw / 32.0` | bar |
| Water/Intake Temp | `(raw / 1.6) - 30.0` | Celsius |
| Fuel | `mFUEL / 100.0` | cc |
| GPS Speed | `mGpsSpeedKnot * 1.852` | km/h |
| Gear | direct (0-6) | -- |

These formulas are confirmed both by disassembly and by the Kotlin `formatCalibrated()` method in the Android app.

---

## Emission Logic

The native library does not output one record per raw CAN/GPS record. Instead, it accumulates CAN state and emits output records at 100ms intervals (10 Hz).

### Time Delta Check (0xaf19)

```asm
cmp rcx, 100  ; Compare delta with 100ms
jge emit      ; Emit if >= 100ms since last emission
```

### Three-Band Time Delta Classification (0xaf1b)

The native library classifies time deltas between consecutive records into bands:

| Band | Condition | Action |
|------|-----------|--------|
| 0 | delta < 0 | Emit with error code -2 (`RET_TIMESTAMP_ERROR`) |
| 1 | delta <= 10ms | Skip record entirely (duplicate/noise suppression) |
| 2 | 10ms < delta < 100ms | Process CAN/GPS data, update state, but do NOT emit |
| 3 | delta >= 100ms | Full processing + emit output record |

**Band 0** occurs when the timestamp goes backwards (e.g., millis wrapping). The native library emits a record with the error code but may suppress further emission for the remainder of the lap.

**Band 1** suppresses near-duplicate records that arrive within 10ms (likely retransmissions or measurement noise).

**Band 2** processes the data (updates CAN state) but waits for the 100ms emission interval.

**Band 3** is the normal emission path.

### Row Counter Limit (0xaece)

```asm
cmp [rcx], eax
jge error_-3  ; Return RET_READSIZE_OVER (-3) if counter >= 72000
```

Maximum 72,000 records per lap (2 hours at 10 Hz). This matches `RECORD_SIZE_MAX`.

### GPS Gating

Output records are only emitted **after the first GPRMC sentence** is encountered. This is because GPS coordinates are required for each output record. The `has_gprmc` flag is set when ANY GPRMC sentence is seen (including void/status-V sentences).

### GPS Sentinel Values (0xaa39)

```asm
movaps xmm0, [0x2b380]  ; Load 9999.0 sentinel
```

When no GPS fix is available: `mLat = 9999.0f`, `mLon = 9999.0f`.

### Processing Order

For each record in the data section:

1. Read 14-byte header via `getLogRecord`
2. Compute `current_epoch_ms` via `GetTimeDataEx`
3. Initialize `last_emitted_ms` if this is the first record
4. Process payload:
   - Type 1 (CAN): dispatch to `AnalisysCAN`, update state
   - Type 2 (GPS): dispatch to `AnalisysNMEA`, update GPS state; emit initial record if first GPRMC
   - Type 5 (Lap): re-align emission clock (`last_emitted_ms = current_epoch_ms`)
   - Other types (3, 4): skip payload
5. Check time delta classification (three-band)
6. If Band 3 (delta >= 100ms): emit record, update emission clock
7. Advance to next record

### Final Record

After the parsing loop ends, one final record is emitted with the last accumulated state. This ensures no data is silently dropped at the end of a lap.

---

## State Initialization (0xa9fc)

```asm
memset(state, 0, 0x2c8)  ; Zero all CAN state (712 bytes)
memset(aux, 0, 0x2e0)    ; Zero auxiliary state (736 bytes)
```

Called at the start of **each lap** (each `GetSensorsRecordData` call), producing physically impossible initial values for the first few records of each lap:

| Channel | Initial Raw | Calibrated | Physical Reality |
|---------|------------|------------|------------------|
| acc_x | 0 | -7.0 G | Impossible (> 5G would be a crash) |
| acc_y | 0 | -7.0 G | Impossible |
| lean | 0 | -90.0 degrees | Impossible (bike on its side) |
| pitch | 0 | -300.0 deg/s | Impossible |
| water_temp | 0 | -30.0 C | Below freezing |
| intake_temp | 0 | -30.0 C | Below freezing |
| rpm | 0 | 0 | Plausible only if engine is off |
| all others | 0/false | 0/false | -- |

The Python parser in continuous mode carries state forward across laps to avoid these impossible initial values. In `--native` mode, it replicates this behavior for match rate comparison.

---

## Lap Detection

The native library uses **type-5 Lap marker records** from the CCU hardware for lap boundaries. It does NOT perform GPS-based finish-line crossing detection internally.

### Lap Counting

1. `GetTotalLap` (called first) scans the entire file for type-5 records
2. Internally, `fcn.0000a430` iterates through all records counting type-5 markers
3. Returns `count + 1` (N markers = N+1 laps: out-lap, lap 1, lap 2, ..., in-lap)

### Lap Seeking

1. `moveToLapLogRecorOffset` at 0xed50 seeks to lap N's start position
2. For lap 0: starts at data section beginning
3. For lap N (N>0): skips past the Nth type-5 record
4. Each lap is processed independently with full state reset (memset)

### Type-5 Record Payload

```
Offset  Size  Type       Description
0       4     uint32 LE  Lap elapsed time (milliseconds)
4       4     --         Always zero (reserved)
```

### Python Parser Differences

The Python parser implements **two modes**:

1. **Continuous mode (default):** Single-pass processing. Uses GPS finish-line crossing for lap detection (from RECORDLINE header entries). More robust when type-5 markers are missing.

2. **Native mode (`--native`):** Per-lap processing matching native behavior. Scans for type-5 markers, processes each lap range independently with full state reset. Used for validation against native output.

---

## Known Bugs

### Millis Wrapping

The CCU timestamp capture is non-atomic. In rare cases (~1 per 156,000 records), the millis field wraps from ~999 to ~0 while the seconds field has not yet incremented.

**Example:**
```
Record N:   millis=999, sec=47  →  epoch = ...107999
Record N+1: millis=8,   sec=47  →  epoch = ...107008  (991ms BACKWARDS)
```

**Native behavior:**
- `GetTimeDataEx` computes `curr_millis + (prev_epoch_ms - prev_millis)` = 8 + (...107999 - 999) = ...107008
- The resulting negative time delta triggers Band 0 classification
- Emits record with return code -2 (`RET_TIMESTAMP_ERROR`)
- Can suppress emission for the remainder of the lap in some cases

**Observed impact:** File `20250906-161606`, lap 6 is entirely missing in native output because a single millis wrapping event at the start of the lap caused all subsequent records to be suppressed.

**Python parser fix:** When `curr_millis < prev_millis` within the same second, add 1000ms to compensate for the un-incremented second field. This prevents data loss.

### State Reset Artifacts

Due to `memset(0)` at the start of each lap, the first few records of every lap (except lap 1 if CAN data arrives before GPS) contain physically impossible values (-7G, -90 degrees lean, etc.). These are not bugs per se but an architectural limitation of per-lap processing.

---

## Native-Only Behaviors Not Replicated in Python Parser

The following native library features are NOT implemented in the Python parser:

| Feature | Native | Python | Notes |
|---------|--------|--------|-------|
| Distance-based resampling | `GetSensorsDistanceRecordData` | Not implemented | Emits records at fixed distance intervals instead of time intervals |
| Damage recovery | `DamageRecoveryLogFile` | Not implemented | Attempts to repair corrupted files |
| Timestamp recovery | `TimeStampRecoveryLogFile` | Not implemented | Repairs timestamp errors in files |
| File splitting | `SplitLogFile` | Not implemented | Splits multi-session log files |
| Encryption key | `GetEncryptSecretKey` | Not implemented | Returns encryption secret key |
| AIN channels | mAIN1, mAIN2 | Not implemented | Auxiliary analog inputs (not observed in test data) |
| Raw CAN storage | mCAN0511, mCAN051B, mCAN0226, mCAN0227 | Not implemented | Raw CAN frame storage for undecoded IDs |
| TRG format support | fileType=1 | Not implemented | Only CTRK/CCT files are supported |
| Band 1 suppression | Skips records with delta <= 10ms | Not implemented | Python processes all records regardless of delta |

---

## Validation Status

The Python parser has been validated against native library output across:

| Metric | Value |
|--------|-------|
| Files tested | 47 |
| Comparison pairs | 42 |
| Total aligned records | 420,000+ |
| Channels validated | 22 |
| Overall match rate | 94.9% |
| RPM match rate | 83.0% |
| Boolean channels | 99.6-100% |
| With `--native` mode | 95.6% |

The remaining ~5% gap is primarily due to emission grid phase divergence between per-lap (native) and single-pass (Python) processing. All CAN data extraction formulas (byte positions, bit masks, calibration) are confirmed correct.

See `docs/COMPARISON.md` for the full validation report including per-channel match rates and analysis of differences.

---

## Tools Used

- **radare2** -- Binary analysis (`r2 -q -e scr.color=0 -c 'aaa; afl' lib.so`)
- **nm -D** -- Symbol extraction from ELF shared objects
- **jadx** -- APK decompilation (Java/Kotlin source recovery)
- **Android Emulator** -- Runtime execution for output comparison
- **Python struct** -- Hex dump analysis and binary format validation
