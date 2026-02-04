# CTRK File Format Specification

**Version:** 2.1
**Date:** 2026-02-04
**Status:** Validated — 47 files tested, 22 channels, 94.9% overall match rate against native library (RPM: 83.0%)
**Source:** Reverse-engineered from Yamaha Y-Trac DataViewer Android Application (v1.3.8), `libSensorsRecordIF.so` disassembly via radare2

---

## Changelog

### v2.1 (2026-02-04)
- Added Section 6.7: Native-Only Behaviors — documented three-band time delta check (10ms secondary threshold at 0xaf1b) and row counter limit (72000 records at 0xaece) from native library
- Enhanced CAN 0x0209 documentation: added disassembly address for gear 7 rejection (`cmp eax, 7; je skip` at 0xe163)
- Enhanced CAN 0x051b documentation: added handler address (0xe102) and storage offset (0x2c8)
- Confirmed all 6 inaccuracies from Review Report Recommendation #6 were already fixed in v2.0: millis wrapping native behavior (5.3), initial state zeros (6.1), LEAN truncation (8.2.5), lap detection comparison (10.4), type-5 payload decode (4.2), CAN padding/GPS sentence wording (4.4/4.5)
- Validated against parser v7 (1048 lines) including `--native` per-lap mode

### v2.0 (2026-01-29)
- **BREAKING:** Complete rewrite. The data section uses structured 14-byte record headers, NOT pattern matching. Previous versions described a fundamentally incorrect parsing approach.
- Documented the full 10-byte timestamp structure: `[millis(2)][sec][min][hour][wday][day][month][year(2)]`
- Documented GetTimeDataEx incremental timestamp PLL algorithm
- Documented millis wrapping edge case (non-atomic hardware timestamp capture)
- Documented emission logic: 100ms interval, zero-order hold, GPS gating
- Documented structured variable-length header entries at offset 0x34
- Documented CAN payload structure: `[canid(2)][pad(2)][DLC(1)][data(DLC)]`
- Documented all 5 record types (CAN, GPS, unused, AIN, Lap marker)
- Documented void GPS handling and sentinel coordinates (9999, 9999)
- Documented fuel delta accumulator with lap-boundary reset
- Added complete hex-level worked examples from real files
- Validated across 45 files (July-October 2025), 422K+ telemetry records

### v1.3 (2026-01-27)
- Decoded CAN timestamp structure (8 bytes, without millis)
- Corrected ABS bit order: R_ABS=bit0, F_ABS=bit1

### v1.0-v1.2 (2026-01-24 to 2026-01-26)
- Initial specification based on pattern matching (superseded by v2.0)

---

## Abstract

This document specifies the CTRK binary file format used by the Yamaha Y-Trac CCU (Communication Control Unit) motorcycle data logger. CTRK files store telemetry data recorded during track sessions, including GPS position, engine parameters, IMU dynamics, brake inputs, and electronic control system states across 21 channels at 10 Hz.

This specification is intended to be sufficient for a developer to implement a fully functional parser from scratch, with no access to the proprietary native library.

## Table of Contents

1. [Introduction](#1-introduction)
2. [File Structure Overview](#2-file-structure-overview)
3. [Header Section](#3-header-section)
4. [Data Section](#4-data-section)
5. [Timestamp Computation](#5-timestamp-computation)
6. [Emission Logic](#6-emission-logic)
7. [GPS NMEA Records](#7-gps-nmea-records)
8. [CAN Bus Messages](#8-can-bus-messages)
9. [Calibration Factors](#9-calibration-factors)
10. [Lap Detection](#10-lap-detection)
11. [Footer Section](#11-footer-section)
12. [Edge Cases](#12-edge-cases)
13. [Output Format](#13-output-format)
14. [References](#14-references)

---

## 1. Introduction

### 1.1 Purpose

The CTRK file format is a proprietary binary format used by the Yamaha Y-Trac motorcycle data logging system to record telemetry during track sessions. This specification documents the format to enable third-party parser implementations.

### 1.2 Scope

This specification covers:
- CTRK file binary structure (`.CTRK` extension)
- Record header format and payload decoding for all record types
- Timestamp computation algorithm (including edge cases)
- CAN bus message decoding for all 21 telemetry channels
- Emission timing logic to produce 10 Hz output
- Calibration formulas for raw-to-engineering-unit conversion
- Lap detection via finish line crossing

### 1.3 Conventions

- All multi-byte integers in record headers and file structures are **little-endian** (LE)
- All multi-byte integers within CAN data payloads are **big-endian** (BE, MSB first)
- Byte offsets are zero-based
- Hex values are prefixed with `0x`
- All timestamps are in UTC

### 1.4 Terminology

| Term | Definition |
|------|------------|
| CCU | Communication Control Unit — the data logger hardware mounted on the motorcycle |
| CAN | Controller Area Network — vehicle bus standard (ISO 11898) |
| NMEA | National Marine Electronics Association — GPS sentence format (NMEA 0183) |
| APS | Accelerator Position Sensor — throttle grip position |
| TPS | Throttle Position Sensor — actual throttle butterfly valve position |
| IMU | Inertial Measurement Unit — lean angle and pitch rate sensor |
| DLC | Data Length Code — number of data bytes in a CAN frame |
| PLL | Phase-Locked Loop — incremental timestamp tracking algorithm |

---

## 2. File Structure Overview

A CTRK file consists of three contiguous sections:

```
Offset     Section         Description
───────────────────────────────────────────────────────────
0x0000     HEADER          Magic + fixed fields + variable-length entries
           │
           ├── 0x0000      Magic signature ("HEAD", 4 bytes)
           ├── 0x0004      Fixed header (48 bytes, partially decoded)
           └── 0x0034      Variable-length entries (RECORDLINE coords, CCU_VERSION)
                           ↓ entries end when entry_size is invalid
───────────────────────────────────────────────────────────
~0x00CB    DATA            Sequential typed records with 14-byte headers
           │
           ├── Record 0    [14-byte header][payload]
           ├── Record 1    [14-byte header][payload]
           ├── ...
           └── Record N    [14-byte header][payload]
                           ↓ ends at null terminator or invalid header
───────────────────────────────────────────────────────────
EOF-370    FOOTER          JSON metadata object (optional, ~370 bytes)
───────────────────────────────────────────────────────────
```

The data section starts immediately after the last valid header entry. Each record in the data section has an explicit type and size — **no pattern matching is required**.

---

## 3. Header Section

### 3.1 Magic Signature

```
Offset  Size  Type    Value
0x0000  4     ASCII   "HEAD" (0x48 0x45 0x41 0x44)
```

A file that does not start with these 4 bytes is not a valid CTRK file.

### 3.2 Fixed Header (0x0004 — 0x0033)

The 48 bytes following the magic contain session metadata. The exact field layout is not fully decoded. Known observations:

- Bytes 0x04-0x0F: typically zero
- The fixed header region is not required for parsing telemetry data

### 3.3 Variable-Length Header Entries (starting at 0x0034)

Starting at offset `0x34`, the header contains a sequence of variable-length entries. Each entry stores a named value (finish line coordinates, CCU version, etc.).

#### Entry Format

```
Offset  Size         Type       Description
0       4            uint32 LE  entry_size (total bytes for this entry, including this field)
4       1            uint8      name_length
5       name_length  ASCII      entry name
5+N     varies       bytes      entry value (entry_size - 5 - name_length bytes)
```

#### Parsing Loop

```
offset = 0x34
while offset < file_length:
    entry_size = read_uint32_le(offset)
    if entry_size < 5 or entry_size > 200:
        break  // end of entries
    name_length = read_uint8(offset + 4)
    if name_length < 1 or name_length > entry_size - 5:
        break  // invalid entry
    name = read_ascii(offset + 5, name_length)
    value = read_bytes(offset + 5 + name_length, entry_size - 5 - name_length)
    offset += entry_size

data_section_start = offset
```

#### Known Entries

| Entry Name | Value Format | Description |
|------------|-------------|-------------|
| `RECORDLINE.P1.LAT` | `(` + 8-byte double LE | Finish line point 1, latitude (degrees) |
| `RECORDLINE.P1.LNG` | `(` + 8-byte double LE | Finish line point 1, longitude (degrees) |
| `RECORDLINE.P2.LAT` | `(` + 8-byte double LE | Finish line point 2, latitude (degrees) |
| `RECORDLINE.P2.LNG` | `(` + 8-byte double LE | Finish line point 2, longitude (degrees) |
| `CCU_VERSION` | 4 unknown bytes + ASCII | CCU firmware version string |

The RECORDLINE value fields begin with byte `0x28` (ASCII `(`), followed by 8 bytes of IEEE 754 double-precision floating point (little-endian).

#### Worked Example

Hex dump of the first header entry from a real file:

```
Offset  Hex                                                          ASCII
0x0034  1f 00 00 00 11 52 45 43 4f 52 44 4c 49 4e 45 2e  .....RECORDLINE.
0x0044  50 31 2e 4c 41 54 28 a1 f2 af e5 95 f9 47 40     P1.LAT(......G@
```

Decoding:
- `1f 00 00 00` → entry_size = 31
- `11` → name_length = 17
- `52 45 43 ... 54` → name = "RECORDLINE.P1.LAT"
- `28 a1 f2 af e5 95 f9 47 40` → value: `(` prefix + double 47.949887

---

## 4. Data Section

The data section begins immediately after the last valid header entry (typically around offset `0xCB`, but varies per file). It consists of a contiguous sequence of binary records, each with a 14-byte header.

### 4.1 Record Header (14 bytes)

Every record begins with this fixed-size header:

```
Offset  Size  Type       Field          Description
0       2     uint16 LE  record_type    Record type identifier
2       2     uint16 LE  total_size     Total record size (header + payload)
4       2     uint16 LE  millis         Millisecond component (0-999)
6       1     uint8      seconds        Seconds (0-59)
7       1     uint8      minutes        Minutes (0-59)
8       1     uint8      hours          Hours (0-23, UTC)
9       1     uint8      weekday        Day of week (1=Monday ... 7=Sunday)
10      1     uint8      day            Day of month (1-31)
11      1     uint8      month          Month (1-12)
12      2     uint16 LE  year           Calendar year (e.g., 0x07E9 = 2025)
```

The payload immediately follows the header and is `total_size - 14` bytes long. The next record starts at `current_offset + total_size`.

#### Worked Example: CAN Record

```
Hex:  01 00 1b 00 6f 03 22 15 0c 02 1d 07 e9 07  [payload...]
      ├───┤ ├───┤ ├───┤ ── ── ── ── ── ── ├───┤
      type  size  ms    s  m  h  wd d  mo year
```

| Field | Hex | Value |
|-------|-----|-------|
| record_type | `01 00` | 1 (CAN) |
| total_size | `1b 00` | 27 bytes |
| millis | `6f 03` | 879 |
| seconds | `22` | 34 |
| minutes | `15` | 21 |
| hours | `0c` | 12 |
| weekday | `02` | Tuesday |
| day | `1d` | 29 |
| month | `07` | July |
| year | `e9 07` | 2025 |

Timestamp: 2025-07-29 12:21:34.879 UTC. Payload: 13 bytes (27 - 14).

#### Worked Example: GPS Record

```
Hex:  02 00 56 00 7b 03 22 15 0c 02 1d 07 e9 07  [payload...]
```

| Field | Hex | Value |
|-------|-----|-------|
| record_type | `02 00` | 2 (GPS/NMEA) |
| total_size | `56 00` | 86 bytes |
| millis | `7b 03` | 891 |
| (rest) | ... | 2025-07-29 12:21:34.891 UTC |

Payload: 72 bytes — an ASCII GPRMC sentence.

### 4.2 Record Types

| Type | Name | Payload Content | Parsing Action |
|------|------|-----------------|----------------|
| 1 | CAN | CAN bus message (see [Section 8](#8-can-bus-messages)) | Update telemetry state |
| 2 | GPS | NMEA sentence (see [Section 7](#7-gps-nmea-records)) | Update GPS position |
| 3 | (unused) | Unknown | Skip (read and discard) |
| 4 | AIN | Analog input (not observed) | Skip (read and discard) |
| 5 | Lap | Lap marker from CCU hardware | Informational (see note) |

**Note on type 5 (Lap):** The CCU emits these records at hardware-detected lap crossings. The parser does not use these for lap detection — it implements its own software-based GPS crossing algorithm (see [Section 10](#10-lap-detection)). The payload is 8 bytes:

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0 | 4 | uint32 LE | Lap elapsed time in milliseconds |
| 4 | 4 | — | Always zero (reserved) |

Verified across 309 type-5 records — decoded values match realistic lap times (60-120 seconds).

### 4.3 End-of-Data Detection

Stop reading records when ANY of these conditions is true:

1. `record_type == 0 AND total_size == 0` — null terminator
2. `total_size < 14` — too small to contain a header
3. `total_size > 500` — unreasonably large
4. `record_type` is not in {1, 2, 3, 4, 5} — unknown type
5. `current_offset + total_size > file_length` — truncated record

### 4.4 Record Type 1: CAN Payload Format

```
Offset  Size   Type       Field      Description
0       2      uint16 LE  can_id     CAN message identifier
2       2      —          (padding)  Unused, always 0x00 0x00
4       1      uint8      dlc        Data Length Code (number of data bytes)
5       dlc    bytes      can_data   CAN frame data
```

Total payload size: `5 + dlc` bytes. Total record size: `14 + 5 + dlc = 19 + dlc` bytes.

#### Worked Example

```
Header:   01 00 1b 00 6f 03 22 15 0c 02 1d 07 e9 07
Payload:  11 05 00 00 08 55 d1 d0 d1 d0 2c 00 28
          ├───┤ ├───┤ ── ├──────────────────────┤
          canid  pad  dlc  can_data (8 bytes)
```

- CAN ID: `11 05` → 0x0511
- Padding: `00 00`
- DLC: 8
- CAN data: `55 d1 d0 d1 d0 2c 00 28`

### 4.5 Record Type 2: GPS Payload Format

The payload is an ASCII string containing an NMEA GPRMC sentence (exclusively — no other sentence types observed across 423,103 GPS records in 47 files), terminated with `\r\n` and/or null bytes. See [Section 7](#7-gps-nmea-records) for parsing details.

#### Worked Example

```
Payload (72 bytes, ASCII):
$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*65\r\n
```

### 4.6 Known CAN Data Length Codes

| CAN ID | DLC | Total Record Size |
|--------|-----|-------------------|
| 0x0209 | 6 | 25 |
| 0x0215 | 8 | 27 |
| 0x0226 | 7 | 26 |
| 0x0227 | 3 | 22 |
| 0x023E | 4 | 23 |
| 0x0250 | 8 | 27 |
| 0x0258 | 8 | 27 |
| 0x0260 | 8 | 27 |
| 0x0264 | 4 | 23 |
| 0x0268 | 6 | 25 |
| 0x0511 | 8 | 27 |
| 0x051b | 8 | 27 |

---

## 5. Timestamp Computation

Each record's 10-byte timestamp must be converted to Unix epoch milliseconds. The native library uses an optimized algorithm called **GetTimeDataEx** that avoids expensive `mktime` calls for records within the same second.

### 5.1 Full Computation (GetTimeData)

When the second changes (or for the very first record), compute the full timestamp:

```
epoch_ms = mktime(year, month, day, hours, minutes, seconds) * 1000 + millis
```

Where `mktime` converts calendar time to Unix epoch seconds (UTC).

### 5.2 Incremental Computation (GetTimeDataEx)

The parser maintains two state variables across ALL record types:
- `prev_ts_bytes`: the raw 10-byte timestamp of the previous record
- `prev_epoch_ms`: the computed epoch_ms of the previous record

For each new record:

```
if prev_ts_bytes is NULL:
    // First record: full computation
    epoch_ms = GetTimeData(ts_bytes)

else if ts_bytes == prev_ts_bytes:
    // Identical timestamp: reuse previous value
    epoch_ms = prev_epoch_ms  // (no update to prev_ variables)

else if ts_bytes[2:10] == prev_ts_bytes[2:10]:
    // Same second, different millis: incremental update
    prev_millis = prev_ts_bytes[0] | (prev_ts_bytes[1] << 8)
    curr_millis = ts_bytes[0] | (ts_bytes[1] << 8)
    epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)

    // Handle millis wrapping (see Section 5.3)
    if curr_millis < prev_millis:
        epoch_ms += 1000

else:
    // Different second: full recomputation
    epoch_ms = GetTimeData(ts_bytes)

// Update state (only when ts_bytes changed)
prev_epoch_ms = epoch_ms
prev_ts_bytes = ts_bytes
```

The "same second" check compares bytes 2 through 9 (sec, min, hour, wday, day, month, year) — all fields except millis.

### 5.3 Millis Wrapping (Hardware Edge Case)

The CCU timestamp capture is **non-atomic**. In rare cases (observed once per ~156,000 records), the millis field wraps from ~999 to ~0 while the seconds field has not yet incremented. Both records show the same second value, but millis decreased.

**Example:**
```
Record N:   millis=999, sec=47  →  epoch = ...107999
Record N+1: millis=8,   sec=47  →  epoch = ...107008  (991ms BACKWARDS!)
```

**Detection:** `curr_millis < prev_millis` within the same second (bytes 2-9 are identical).

**Fix:** Add 1000ms to the computed epoch_ms to compensate for the un-incremented second field. This transforms the backwards jump into a correct forward progression:

```
Record N:   epoch = ...107999
Record N+1: epoch = ...108008  (9ms forward, correct)
```

Without this fix, the emission clock breaks because `current_epoch_ms < last_emitted_ms`, preventing further emissions until the timestamps naturally advance past the stale `last_emitted_ms`.

**Native library behavior:** The native library does NOT compensate for millis wrapping. When wrapping occurs, it produces a negative time delta, emits the record with error code -2, and continues without correction. This can cause the native library to suppress emission for an entire lap (~90 seconds of data), as observed in file 20250906-161606 where native output is missing lap 6. The +1000ms compensation described above is a Python parser improvement that prevents this data loss.

---

## 6. Emission Logic

The parser does **not** output one record per raw CAN/GPS record. Instead, it accumulates CAN state and emits telemetry output records at fixed **100ms intervals** (10 Hz), matching the native library behavior.

### 6.1 Zero-Order Hold

Maintain a state dictionary holding the latest value for each telemetry channel. When a CAN record is processed, update the relevant channels. Values persist until overwritten by a newer CAN record with the same CAN ID.

**Initial state values:**

| Channel | Initial Raw Value | Calibrated Default |
|---------|------------------|--------------------|
| rpm | 0 | 0 RPM |
| gear | 0 | Neutral |
| aps | 0 | 0% |
| tps | 0 | 0% |
| water_temp | 0 | -30.0 C |
| intake_temp | 0 | -30.0 C |
| front_speed | 0 | 0.0 km/h |
| rear_speed | 0 | 0.0 km/h |
| front_brake | 0 | 0.0 bar |
| rear_brake | 0 | 0.0 bar |
| acc_x | 0 | -7.0 G |
| acc_y | 0 | -7.0 G |
| lean | 0 | -90.0 deg |
| pitch | 0 | -300.0 deg/s |
| f_abs | false | inactive |
| r_abs | false | inactive |
| tcs | 0 | inactive |
| scs | 0 | inactive |
| lif | 0 | inactive |
| launch | 0 | inactive |
| fuel | 0 | 0.0 cc |

**Note on initial state:** The native library initializes all CAN state to zero via `memset(state, 0, 0x2c8)` at address 0xa9fc. This produces physically impossible calibrated values for some channels (e.g., -7G acceleration, -90° lean, -300°/s pitch) until real CAN data arrives. This typically affects only the first 1-2 records before CAN messages populate the state buffer. The parser matches this native behavior.

### 6.2 Emission Clock

The emission logic uses two independent time trackers:
- `last_emitted_ms`: the timestamp of the most recently emitted output record
- `current_epoch_ms`: the timestamp of the record currently being processed (from GetTimeDataEx)

**Initialization:** Set `last_emitted_ms` to the `current_epoch_ms` of the **first record** (any type, not just GPS). This aligns the emission clock with the start of data.

**Emission check (after processing each record's payload):**

```
if has_gprmc AND (current_epoch_ms - last_emitted_ms) >= 100:
    emit_record(current_epoch_ms, gps_state, can_state)
    last_emitted_ms = current_epoch_ms
```

### 6.3 GPS Gating

Output records are only emitted **after the first GPRMC sentence** is encountered. This is because GPS coordinates are required for each output record.

- Track a boolean `has_gprmc`, initially false
- Set `has_gprmc = true` upon encountering the first GPRMC sentence with a valid checksum, **regardless of fix status** (even 'V' void status counts)
- On the first GPRMC, **immediately emit one initial record** using `last_emitted_ms` as the timestamp
- Subsequent emissions follow the 100ms interval rule

### 6.4 GPS State

| Variable | Initial Value | Description |
|----------|---------------|-------------|
| latitude | 9999.0 | Sentinel (no fix) |
| longitude | 9999.0 | Sentinel (no fix) |
| speed_knots | 0.0 | GPS ground speed |

The sentinel value (9999.0, 9999.0) matches the native library's behavior when no GPS fix has been acquired.

**Update rules:**
- Only update latitude, longitude, and speed when the GPRMC sentence has status `A` (valid fix)
- GPRMC with status `V` (void): acknowledge it (set `has_gprmc`), but do NOT update position or speed
- Keep emitting with sentinel coordinates until a valid fix is obtained

### 6.5 Processing Order

For each record in the data section:

```
1. Read 14-byte header
2. Compute current_epoch_ms (GetTimeDataEx)
3. Initialize last_emitted_ms if this is the first record
4. Process payload:
   - Type 1 (CAN): update telemetry state
   - Type 2 (GPS): update GPS state; emit initial record if first GPRMC
   - Type 5 (Lap): re-align emission clock (last_emitted_ms = current_epoch_ms)
   - Other types: skip payload
5. Emission check: if has_gprmc AND elapsed >= 100ms, emit and update clock
6. Advance to next record
```

The emission check occurs **after** payload processing so that the emitted state includes the current record's data.

**Type-5 emission clock reset:** The native library calls `GetSensorsRecordData` independently for each lap, zeroing `prev_emitted_epoch_ms` via `memset(0)` at each call. This re-aligns the 100ms emission grid at every lap boundary. The parser matches this behavior by resetting `last_emitted_ms` at type-5 Lap marker records, without resetting CAN state (preserving continuous telemetry across laps).

### 6.6 Final Record

After the parsing loop ends, emit one final record with the last accumulated state. This captures any remaining telemetry accumulated since the last 100ms emission.

### 6.7 Native-Only Behaviors (Not Implemented in Parser)

The following behaviors are present in the native library's emission logic but are **not implemented** in this parser. They are documented here for completeness and as reference for future analysis.

#### 6.7.1 Three-Band Time Delta Check

The native library implements a three-band time delta classification in its main record processing loop. The Python parser only implements band 3 (the 100ms emission interval).

```
delta = current_epoch_ms - last_emitted_ms

Band 0: delta < 0          → emit record with error code -2 (negative time)
Band 1: delta <= 10ms      → skip record entirely (no payload processing)
Band 2: 10ms < delta < 100 → process payload, clear a validity flag
Band 3: delta >= 100ms     → full processing + emit record
```

**Disassembly evidence:** `cmp rcx, 10; jle skip` at 0xaf1b (band 1 threshold). `jge` at 0xaf19 for the 100ms check (band 3).

**Impact:** Negligible. 97.81% of native emissions fall in band 3 (exactly 100ms intervals). Bands 1 and 2 fire in less than 2.2% of records, and band 1 records typically have identical timestamps (delta = 0ms). The "validity flag" semantics in band 2 are not fully understood.

**Decision:** Not implemented. The parser processes all records regardless of time delta. This has no measurable effect on output match rate.

#### 6.7.2 Row Counter Limit (72000)

The native library enforces a maximum of 72,000 emitted records per lap. When the counter reaches this limit, the function returns with error code -3.

**Disassembly evidence:** `cmp [rcx], eax; jge error_-3` at 0xaece.

At 10 Hz emission rate, 72,000 records corresponds to 7,200 seconds (2 hours) of continuous recording per lap. This limit is never reached in normal track sessions (typical laps are 60-120 seconds).

**Decision:** Not enforced in the parser. No test files approach this limit.

---

## 7. GPS NMEA Records

### 7.1 GPRMC Sentence Format

GPS data is stored as standard NMEA 0183 GPRMC sentences:

```
$GPRMC,HHMMSS.sss,S,DDMM.MMMM,N,DDDMM.MMMM,E,SPD,CRS,DDMMYY,,,M*HH
```

| Index | Field | Description | Example |
|-------|-------|-------------|---------|
| 0 | `$GPRMC` | Sentence identifier | `$GPRMC` |
| 1 | Time | UTC time (HHMMSS.sss) | `122135.000` |
| 2 | Status | A=active (valid), V=void | `A` |
| 3 | Latitude | Degrees-minutes (DDMM.MMMM) | `4757.0410` |
| 4 | N/S | Hemisphere | `N` |
| 5 | Longitude | Degrees-minutes (DDDMM.MMMM) | `00012.5240` |
| 6 | E/W | Hemisphere | `E` |
| 7 | Speed | Speed over ground (knots) | `5.14` |
| 8 | Course | Course over ground (degrees) | `334.60` |
| 9 | Date | UTC date (DDMMYY) | `290725` |
| 10-11 | (unused) | Mode/variation | `,` |
| 12 | Checksum | `*` + 2 hex digits | `*65` |

### 7.2 Coordinate Conversion

NMEA coordinates are in degrees-minutes (DDDmm.mmmm) format:

```
decimal_degrees = integer_degrees + (decimal_minutes / 60.0)
```

Apply sign for hemisphere: negative for S (latitude) and W (longitude).

**Example:** `4757.0410,N` → 47 + (57.0410 / 60.0) = **47.950683** degrees North

### 7.3 Checksum Validation

Compute XOR of all ASCII bytes between `$` (exclusive) and `*` (exclusive). Compare with the 2-digit hexadecimal value after `*`.

```
checksum = 0
for each byte between '$' and '*':
    checksum = checksum XOR byte
valid = (checksum == parse_hex(sentence[star_index+1 : star_index+3]))
```

**Reject sentences with invalid checksums.** Do not update GPS state or set `has_gprmc` for rejected sentences.

### 7.4 Void Status Handling

GPRMC sentences with status `V` (void) indicate GPS hardware is active but has no satellite fix. These sentences have empty or invalid coordinate fields.

Parser behavior for void sentences:
- Set `has_gprmc = true` (enables emission)
- Do NOT update latitude, longitude, or speed (retain sentinel/previous values)
- Emit records using current GPS state (which may be sentinel 9999.0, 9999.0)

---

## 8. CAN Bus Messages

### 8.1 Known CAN Message IDs

| CAN ID | Name | DLC | Decoded Fields |
|--------|------|-----|----------------|
| 0x0209 | Engine | 6 | RPM, Gear |
| 0x0215 | Throttle | 8 | TPS, APS, Launch, TCS, SCS, LIF |
| 0x0226 | (unknown) | 7 | Not decoded |
| 0x0227 | (unknown) | 3 | Not decoded |
| 0x023E | Temperature/Fuel | 4 | Water temp, Intake temp, Fuel delta |
| 0x0250 | Acceleration | 8 | ACC_X, ACC_Y |
| 0x0258 | IMU | 8 | LEAN, PITCH |
| 0x0260 | Brake | 8 | Front brake, Rear brake |
| 0x0264 | Wheel Speed | 4 | Front speed, Rear speed |
| 0x0268 | ABS Status | 6 | F_ABS, R_ABS |
| 0x0511 | (unknown) | 8 | Not decoded |
| 0x051b | (unknown) | 8 | Not decoded — handler at 0xe102 stores 8 raw bytes at native struct offset 0x2c8, but data is not mapped to any SensorsRecord field and not included in output |

CAN IDs not in the table above may appear in files and should be silently skipped.

### 8.2 CAN Data Byte Layout

> **Reminder:** All multi-byte values within CAN data are **big-endian** (MSB at lower byte index).

#### 8.2.1 Engine — 0x0209 (DLC=6)

```
Byte  Bits     Field   Type     Description
0     [7:0]    RPM     uint16   Engine RPM (high byte)
1     [7:0]    RPM              Engine RPM (low byte)
2     —        —       —        (unused)
3     —        —       —        (unused)
4     [2:0]    Gear    uint8    Gear position (0=N, 1-6, 7=invalid)
5     —        —       —        (unused)
```

- RPM raw: `(data[0] << 8) | data[1]`
- Gear: `data[4] & 0x07` — value 7 is rejected as invalid (transitioning between gears). Disassembly: `cmp eax, 7; je skip` at 0xe163.

#### 8.2.2 Throttle — 0x0215 (DLC=8)

```
Byte  Bits     Field     Type     Description
0     [7:0]    TPS       uint16   Throttle Position Sensor (high byte)
1     [7:0]    TPS                Throttle Position Sensor (low byte)
2     [7:0]    APS       uint16   Accelerator Position Sensor (high byte)
3     [7:0]    APS                Accelerator Position Sensor (low byte)
4     —        —         —        (unused)
5     —        —         —        (unused)
6     [6:5]    Launch    uint8    Launch control active (non-zero = active)
7     [5]      TCS       bit      Traction Control System active
7     [4]      SCS       bit      Slide Control System active
7     [3]      LIF       bit      Lift Control active
```

- TPS raw: `(data[0] << 8) | data[1]`
- APS raw: `(data[2] << 8) | data[3]`
- Launch: `1 if (data[6] & 0x60) else 0`
- TCS: `(data[7] >> 5) & 1`
- SCS: `(data[7] >> 4) & 1`
- LIF: `(data[7] >> 3) & 1`

#### 8.2.3 Temperature/Fuel — 0x023E (DLC=4)

```
Byte  Bits     Field         Type     Description
0     [7:0]    WaterTemp     uint8    Water temperature (single byte, NOT uint16)
1     [7:0]    IntakeTemp    uint8    Intake air temperature (single byte)
2     [7:0]    FuelDelta     uint16   Fuel consumption delta (high byte)
3     [7:0]    FuelDelta              Fuel consumption delta (low byte)
```

- Water temp raw: `data[0]`
- Intake temp raw: `data[1]`
- Fuel delta: `(data[2] << 8) | data[3]` — this is a **delta** value, NOT absolute. See [Section 8.3](#83-fuel-accumulator).

#### 8.2.4 Acceleration — 0x0250 (DLC=8)

```
Byte  Bits     Field   Type     Description
0     [7:0]    ACC_X   uint16   Longitudinal acceleration (high byte)
1     [7:0]    ACC_X            Longitudinal acceleration (low byte)
2     [7:0]    ACC_Y   uint16   Lateral acceleration (high byte)
3     [7:0]    ACC_Y            Lateral acceleration (low byte)
4-7   —        —       —        (unused)
```

- ACC_X raw: `(data[0] << 8) | data[1]`
- ACC_Y raw: `(data[2] << 8) | data[3]`

#### 8.2.5 IMU — 0x0258 (DLC=8)

```
Byte  Bits     Field   Type     Description
0-3   —        LEAN    packed   Lean angle (packed format, see below)
4     —        —       —        (unused)
5     —        —       —        (unused)
6     [7:0]    PITCH   uint16   Pitch rate (high byte)
7     [7:0]    PITCH            Pitch rate (low byte)
```

- PITCH raw: `(data[6] << 8) | data[7]`
- LEAN decoding requires a special algorithm:

**LEAN Decoding Algorithm:**

The lean angle is encoded in a packed format across bytes 0-3, with a deadband and rounding applied:

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

The output value 9000 represents upright (0 degrees lean). Apply the calibration formula `(raw / 100.0) - 90.0` to convert to degrees.

#### 8.2.6 Brake — 0x0260 (DLC=8)

```
Byte  Bits     Field        Type     Description
0     [7:0]    FrontBrake   uint16   Front brake pressure (high byte)
1     [7:0]    FrontBrake            Front brake pressure (low byte)
2     [7:0]    RearBrake    uint16   Rear brake pressure (high byte)
3     [7:0]    RearBrake             Rear brake pressure (low byte)
4-7   —        —            —        (unused)
```

#### 8.2.7 Wheel Speed — 0x0264 (DLC=4)

```
Byte  Bits     Field        Type     Description
0     [7:0]    FrontSpeed   uint16   Front wheel speed (high byte)
1     [7:0]    FrontSpeed            Front wheel speed (low byte)
2     [7:0]    RearSpeed    uint16   Rear wheel speed (high byte)
3     [7:0]    RearSpeed             Rear wheel speed (low byte)
```

#### 8.2.8 ABS Status — 0x0268 (DLC=6)

```
Byte  Bits     Field   Type  Description
0-3   —        —       —     (unused)
4     [0]      R_ABS   bit   Rear ABS active
4     [1]      F_ABS   bit   Front ABS active
5     —        —       —     (unused)
```

- R_ABS: `data[4] & 1`
- F_ABS: `(data[4] >> 1) & 1`

Note: R_ABS is bit 0, F_ABS is bit 1 (not the other way around).

### 8.3 Fuel Accumulator

CAN ID 0x023E bytes 2-3 contain a fuel consumption **delta** (not an absolute value). The parser must maintain a cumulative fuel accumulator:

```
fuel_accumulator += fuel_delta     // from each 0x023E message
fuel_raw = fuel_accumulator        // stored in telemetry state
```

The fuel accumulator **resets to 0** at each lap boundary (finish line crossing). This gives per-lap fuel consumption.

---

## 9. Calibration Factors

Raw sensor values are converted to engineering units using these formulas. All formulas have been verified against the native library's calibration logic via disassembly.

| Channel | Raw Source | Formula | Output Unit |
|---------|-----------|---------|-------------|
| GPS Speed | speed_knots (from GPRMC) | `raw * 1.852` | km/h |
| RPM | CAN 0x0209 bytes 0-1 | `raw / 2.56` | RPM |
| Throttle Grip (APS) | CAN 0x0215 bytes 2-3 | `((raw / 8.192) * 100.0) / 84.96` | % |
| Throttle (TPS) | CAN 0x0215 bytes 0-1 | `((raw / 8.192) * 100.0) / 84.96` | % |
| Front Wheel Speed | CAN 0x0264 bytes 0-1 | `(raw / 64.0) * 3.6` | km/h |
| Rear Wheel Speed | CAN 0x0264 bytes 2-3 | `(raw / 64.0) * 3.6` | km/h |
| Lean Angle | CAN 0x0258 bytes 0-3 | `(raw / 100.0) - 90.0` | degrees |
| Pitch Rate | CAN 0x0258 bytes 6-7 | `(raw / 100.0) - 300.0` | deg/s |
| Longitudinal Accel | CAN 0x0250 bytes 0-1 | `(raw / 1000.0) - 7.0` | G |
| Lateral Accel | CAN 0x0250 bytes 2-3 | `(raw / 1000.0) - 7.0` | G |
| Front Brake Pressure | CAN 0x0260 bytes 0-1 | `raw / 32.0` | bar |
| Rear Brake Pressure | CAN 0x0260 bytes 2-3 | `raw / 32.0` | bar |
| Water Temperature | CAN 0x023E byte 0 | `(raw / 1.6) - 30.0` | Celsius |
| Intake Temperature | CAN 0x023E byte 1 | `(raw / 1.6) - 30.0` | Celsius |
| Fuel Consumption | CAN 0x023E bytes 2-3 | `raw / 100.0` | cc |
| Gear | CAN 0x0209 byte 4 | direct (0-6) | — |

**Calibration examples:**

| Channel | Raw Value | Formula | Calibrated |
|---------|-----------|---------|------------|
| RPM | 25600 | 25600 / 2.56 | 10000 RPM |
| Lean | 12000 | (12000 / 100) - 90 | 30.0 deg |
| Lean | 9000 | (9000 / 100) - 90 | 0.0 deg (upright) |
| Pitch | 30000 | (30000 / 100) - 300 | 0.0 deg/s |
| Accel | 7000 | (7000 / 1000) - 7 | 0.0 G |
| Water Temp | 176 | (176 / 1.6) - 30 | 80.0 C |

---

## 10. Lap Detection

### 10.1 Finish Line Definition

Two GPS points (P1 and P2) from the header define a line segment representing the start/finish line on the track.

If no RECORDLINE entries are found in the header, lap detection is disabled and all records are assigned to lap 1.

### 10.2 Crossing Detection Algorithm

For each emitted record, check if the motorcycle's trajectory from the previous position to the current position crosses the finish line:

**Step 1: Side-of-line test**

Compute which side of the finish line each point is on using the cross product:

```
side(lat, lon) = (P2.lon - P1.lon) * (lat - P1.lat) - (P2.lat - P1.lat) * (lon - P1.lon)
```

If `side(prev) * side(curr) >= 0`, no crossing occurred.

**Step 2: Parametric intersection**

If the signs differ (potential crossing), verify the intersection falls within the P1-P2 segment:

```
dx1 = P2.lon - P1.lon
dy1 = P2.lat - P1.lat
dx2 = curr_lon - prev_lon
dy2 = curr_lat - prev_lat

denom = dx1 * dy2 - dy1 * dx2
if |denom| < 1e-12: no crossing (parallel lines)

t = ((prev_lon - P1.lon) * dy2 - (prev_lat - P1.lat) * dx2) / denom
crossing = (0 <= t <= 1)
```

### 10.3 Lap Counter

- Start at lap 1
- Each confirmed crossing increments the lap counter
- The first crossing marks the end of lap 1 and the start of lap 2
- Reset the fuel accumulator to 0 at each crossing

### 10.4 Native Library Comparison

The native library uses a different lap detection mechanism: it scans the data section for type-5 Lap marker records (see Section 4.2) and uses them to partition the data into per-lap segments. The two approaches agree in 39 of 42 tested files.

Key differences:
- **Lap detection:** Native uses type-5 hardware markers; Python uses GPS finish-line crossing geometry. The GPS approach is more robust — it detects laps even when type-5 records are missing or corrupt.
- **State at lap boundaries:** Native zeroes all CAN state (`memset(state, 0, 0x2c8)`) when processing each lap independently, producing physically impossible values (e.g., -7G, -90°) in the first 1-2 records of every lap after lap 1. Python carries forward continuous state, producing physically correct values at all times.
- **Disagreements:** In 3 of 42 files, the approaches assign records to different laps due to missing type-5 markers or boundary-edge timing differences.

### 10.5 Initial Position

The crossing algorithm requires a previous position. Initialize `prev_lat` and `prev_lon` to 0.0. Skip the crossing check for the first emitted record (when prev is 0.0, 0.0).

---

## 11. Footer Section

### 11.1 JSON Metadata

The file may end with a JSON object. The JSON starts immediately after the last data record (no gap bytes) and extends to the end of the file.

**Locating the footer:** Scan backwards from EOF for `{"Attribute"` or simply attempt to parse JSON from the last few hundred bytes.

**Example footer (370 bytes):**

```json
{
  "Attribute": [
    {"Key": "FormatVersion", "Value": "1.0"},
    {"Key": "Weather", "Value": "1"},
    {"Key": "Date", "Value": "2025-07-29 15:08:18"},
    {"Key": "Tire", "Value": ""},
    {"Key": "SSID", "Value": "YAMAHA MOTOR CCU D0142A"},
    {"Key": "LapCount", "Value": ""},
    {"Key": "CircuitName", "Value": ""},
    {"Key": "Name", "Value": "20250729-170818"},
    {"Key": "User", "Value": "R122"},
    {"Key": "Temperature", "Value": ""}
  ]
}
```

### 11.2 Metadata Fields

| Key | Description | Example |
|-----|-------------|---------|
| FormatVersion | CTRK format version | "1.0" |
| Weather | Weather condition code | "1" |
| Date | Recording date/time (local) | "2025-07-29 15:08:18" |
| Tire | Tire information (user-entered) | "" |
| SSID | CCU WiFi SSID | "YAMAHA MOTOR CCU D0142A" |
| LapCount | Number of laps (may be empty) | "" |
| CircuitName | Track name (user-entered) | "" |
| Name | Session filename | "20250729-170818" |
| User | Rider identifier | "R122" |
| Temperature | Ambient temperature (user-entered) | "" |

---

## 12. Edge Cases

### 12.1 Short Files / No GPS

Some CTRK files are very short (a few hundred bytes) and contain no GPRMC sentences. These files produce no telemetry output because the `has_gprmc` condition is never met. This is correct behavior.

### 12.2 Default Date (2000-01-01)

Files recorded when the CCU has not synchronized its RTC show a default date of 2000-01-01. The timestamp computation handles this correctly — it produces epoch_ms values in the year 2000 range. Parse these files normally.

### 12.3 Millis Wrapping

See [Section 5.3](#53-millis-wrapping-hardware-edge-case). Observed once per ~7 million raw records (1 in 45 files). Without the compensation, timestamps go backwards and emission breaks for the remainder of the affected section.

### 12.4 Emission Timing vs Native Library

The Python parser's emission clock initialization (`last_emitted_ms = current_epoch_ms` at the first record) produces **identical first emission timestamps** as the native library across all tested files (45/45 files show zero offset).

An earlier version of the parser exhibited a 10-90ms offset that caused a systematic one-CAN-update shift. This was resolved by improvements to timestamp computation (DLC-based CAN advancement, millis wrapping reversal fix). Investigation confirmed the current approach is optimal — all alternative initialization strategies (truncation to 100ms boundary, first-GPRMC gating, GPRMC UTC time, fixed offsets, hybrid approaches) produce worse match rates.

Adding emission clock reset at type-5 Lap marker records (matching the native per-lap `memset(0)` behavior) improved RPM match from ~77% to ~83% and overall from ~94.1% to ~94.9%. The remaining ~17% RPM gap is caused by within-lap emission grid divergence from the native per-lap re-reading architecture. All CAN data extraction (byte positions, formulas, scaling) is correct.

### 12.5 Record Count Differences vs Native Library

The native library has a bug where a millis wrapping event can cause it to suppress emission for an entire lap (~90 seconds of data). The parser described in this specification correctly emits through the wrapping event, producing more records than the native library for affected files. This is the intended behavior — the data is valid and should not be discarded.

---

## 13. Output Format

### 13.1 CSV Columns

```csv
lap,time_ms,latitude,longitude,gps_speed_kmh,rpm,throttle_grip,throttle,water_temp,intake_temp,front_speed_kmh,rear_speed_kmh,fuel_cc,lean_deg,pitch_deg_s,acc_x_g,acc_y_g,front_brake_bar,rear_brake_bar,gear,f_abs,r_abs,tcs,scs,lif,launch
```

### 13.2 Field Definitions

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| lap | int | — | Lap number (1-based, increments at each finish line crossing) |
| time_ms | int64 | ms | Unix timestamp in milliseconds (UTC) |
| latitude | float | degrees | GPS latitude (WGS84, 6 decimal places) |
| longitude | float | degrees | GPS longitude (WGS84, 6 decimal places) |
| gps_speed_kmh | float | km/h | GPS ground speed |
| rpm | int | RPM | Engine RPM |
| throttle_grip | float | % | Accelerator position (APS) |
| throttle | float | % | Throttle valve position (TPS) |
| water_temp | float | Celsius | Coolant temperature |
| intake_temp | float | Celsius | Intake air temperature |
| front_speed_kmh | float | km/h | Front wheel speed |
| rear_speed_kmh | float | km/h | Rear wheel speed |
| fuel_cc | float | cc | Cumulative fuel consumption (resets per lap) |
| lean_deg | float | degrees | Lean angle (0 = upright, positive = right) |
| pitch_deg_s | float | deg/s | Pitch rate |
| acc_x_g | float | G | Longitudinal acceleration |
| acc_y_g | float | G | Lateral acceleration |
| front_brake_bar | float | bar | Front brake hydraulic pressure |
| rear_brake_bar | float | bar | Rear brake hydraulic pressure |
| gear | int | — | Current gear (0=Neutral, 1-6) |
| f_abs | bool | — | Front ABS active |
| r_abs | bool | — | Rear ABS active |
| tcs | int | — | Traction control active |
| scs | int | — | Slide control active |
| lif | int | — | Lift control active |
| launch | int | — | Launch control active |

---

## 14. References

1. [Yamaha Y-Trac Product Page](https://www.yamaha-motor.eu/fr/fr/y-trac/)
2. [NMEA 0183 Standard](https://www.nmea.org/content/STANDARDS/NMEA_0183_Standard)
3. [CAN Bus Specification (ISO 11898)](https://www.iso.org/standard/63648.html)
4. [IEEE 754 Floating Point](https://standards.ieee.org/standard/754-2019.html)
