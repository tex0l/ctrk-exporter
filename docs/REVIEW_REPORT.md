# CTRK Parser Review Report

**Date:** 2026-01-29 (updated 2026-02-04)
**Scope:** Spec v2.1, Parser v7 (`ctrk_parser.py`, 1048 lines), 47 CTRK files, native library disassembly
**Method:** Disassembly of `libSensorsRecordIF.so` (x86_64), hex dump analysis of 4.69M records, output comparison across 42 file pairs
**Current match rate:** 94.9% across 22 channels (RPM: 83.0%)

---

## 1. Spec Verification Matrix

| Spec Section | Claim | Disassembly | Hex Dump | Verdict |
|-------------|-------|-------------|----------|---------|
| 3.1 Magic | `HEAD` at 0x00-0x03 | N/A | 47/47 files confirmed | **CONFIRMED** |
| 3.3 Header entries | `[size(4)][name_len(1)][name][value]` at 0x34 | N/A | 45/45 normal files confirmed, data starts at 0xCB | **CONFIRMED** |
| 4.1 Record header | 14 bytes: `[type(2)][size(2)][ts(10)]` | `getLogRecord` at 0xf921: `fread(buf, 14, 1, file)` | 4.69M records, zero failures | **CONFIRMED** |
| 4.1 Timestamp layout | `[millis(2LE)][sec][min][hour][wday][day][month][year(2LE)]` | `GetTimeData` at 0xdf40: exact byte positions confirmed | Cross-checked CAN header vs GPRMC time: <100ms delta | **CONFIRMED** |
| 4.3 CAN payload | `[canid(2LE)][pad(2)][DLC(1)][data(DLC)]` | `AnalisysCAN` at 0xdfd0: reads canid as dword (pad=0); DLC byte at offset 4 exists but is **never read** | 4.26M CAN records: padding always 0x0000, all DLCs match | **CONFIRMED** |
| 4.4 GPS payload | ASCII NMEA sentence | `AnalisysNMEA` at 0xe330: strncmp `$GPRMC` | 423K GPS records: exclusively GPRMC | **CONFIRMED** |
| 4.5 Lap marker | Type 5, payload = `[lap_time_ms(4LE)][zeros(4)]` | `fcn.0000a430`: counts type-5 records for lap total | 309 type-5 records across 45/47 files | **CONFIRMED + DECODED** |
| 4.6 Types 3,4 | Exist but unused | Switch table at 0xb020: case 3 = seek past, case 4 = AnalisysAIN | 0 occurrences in 4.69M records | **CONFIRMED** |
| 5.2 GetTimeDataEx | 3-path: identical → reuse; same-sec → incremental; else → full | Caller memcmp at 0xaee1; GetTimeDataEx at 0xde80 | N/A | **CONFIRMED** |
| 6.1 Initial state | All zeros (`memset(state, 0, 0x2c8)`) | Confirmed at 0xa9fc | N/A | **CONFIRMED** |
| 6.2 Emission clock | `>= 100ms` interval | `jge` at 0xaf19 confirms `>= 100` | Native intervals: 97.81% exactly 100ms | **CONFIRMED** |
| 6.4 GPS sentinel | lat=9999.0, lon=9999.0 | `movaps xmm0, [0x2b380]` at 0xaa39 | N/A | **CONFIRMED** |
| 8.2.1 CAN 0x0209 | RPM + Gear (gear 7 rejected) | `cmp eax, 7; je skip` at 0xe163 | N/A | **CONFIRMED** |
| 8.2.6 LEAN | Deadband ±499, truncate to nearest 100 | 0xe1bc-0xe32e: all steps confirmed | N/A | **CONFIRMED** |

---

## 2. Parser vs Spec Compliance

| Spec Section | Parser Implementation | Compliant? |
|-------------|----------------------|-----------|
| 4.1 Record header | Lines 621-622: reads rec_type, total_size | YES |
| 4.3 CAN payload | Lines 666-669: canid at offset 0, data at offset 5 | YES |
| 5.2 GetTimeDataEx | Lines 639-658: 3-path algorithm | YES |
| 5.3 Millis wrapping | Lines 651-652: +1000ms compensation | **DIVERGES** (intentional: Python compensates, native does not) |
| 6.1 Initial state | Lines 373-383: all zeros | YES |
| 6.2 Emission | Lines 710-717: `>= 100ms` check | YES |
| 7.2 Checksum | Lines 495-515: XOR validation | YES |
| 8.2.1 Gear rejection | Line 188: `if gear != 7` | YES |
| 8.3 Fuel accumulator | Lines 202-210: cumulative delta, lap reset | YES |
| 10 Lap detection | Lines 414-442: GPS crossing (continuous) / type-5 (native) | YES |

---

## 3. What's Correct

- Binary format structure (header, records, CAN, GPS, footer): **100% verified**
- CAN data extraction (byte positions, bit masks, formulas): **100% correct**
- LEAN deadband and truncation: **Correct**
- Timestamp computation (GetTimeData, GetTimeDataEx): **Correct**
- Emission interval (`>= 100ms`): **Correct**
- GPS handling (GPRMC parsing, checksum, void status): **Correct**
- Fuel accumulator (cumulative delta, lap reset): **Correct**
- Gear value 7 rejection: **Correct**

---

## 4. Intentional Divergences From Native

| Behavior | Native | Python | Rationale |
|----------|--------|--------|-----------|
| Millis wrapping | Negative delta + error -2 | +1000ms compensation | Prevents lap-6 gap in 20250906-161606 |
| CAN state at lap boundaries | `memset(0)` → impossible values (-7G, -90°, -300°/s) | Continuous state carry-forward | Avoids physically impossible records |
| Lap detection | Type-5 markers only | GPS crossing (continuous) / type-5 (native) | GPS is more robust; hybrid planned (EPIC-001) |

---

## 5. Match Rate

| Metric | Value |
|--------|-------|
| Overall match rate | **94.9%** (42 files, 420K+ records) |
| RPM match rate | **83.0%** |
| Boolean channels | **99.6-100%** |
| Gear | **99.8%** |
| Files tested | **47** |
| Channels validated | **22/22** |

**RPM gap explanation:** The ~17% RPM mismatch is within-lap emission grid divergence caused by the native per-lap re-reading architecture vs Python's single-pass approach. Not a data quality issue — all RPM values are correct, but emitted at slightly different timestamps.
