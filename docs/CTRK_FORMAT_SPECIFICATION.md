# CTRK File Format Specification

**Version:** 1.2
**Date:** 2026-01-26
**Status:** Draft - Verified via disassembly of libSensorsRecordIF.so (radare2)
**Author:** Reverse-engineered from Yamaha Y-trac DataViewer Android Application

---

## Changelog

### v1.2 (2026-01-26)
- Added native LEAN formula (disassembled from binary)
- Confirmed CAN mappings via radare2 analysis of x86_64 binary
- Documented LEAN deadband behavior (±5°)
- Clarified TPS/APS byte order
- Added reference to `libSensorsRecordIF_howitworks.md` for technical details

### v1.1 (2026-01-25)
- Added CAN message decoding for all telemetry channels
- Documented calibration factors for all sensor types
- Added lap detection via RECORDLINE crossing
- Corrected temperature encoding (single byte, not 16-bit)
- Added fuel accumulator reset behavior at lap boundaries

### v1.0 (2026-01-24)
- Initial specification based on file structure analysis
- Documented header format with magic signature and track coordinates
- Documented GPS NMEA sentence parsing (GPRMC)
- Identified CAN message structure and year marker pattern
- Documented JSON footer metadata format

---

## Abstract

This document specifies the CTRK file format used by the Yamaha Y-trac CCU (Communication Control Unit) data logger system. The CTRK format stores motorcycle telemetry data including GPS position, engine parameters, suspension dynamics, brake inputs, and electronic control system states.

## Table of Contents

1. [Introduction](#1-introduction)
2. [File Structure Overview](#2-file-structure-overview)
3. [Header Section](#3-header-section)
4. [Data Section](#4-data-section)
5. [Footer Section](#5-footer-section)
6. [Timestamp Format](#6-timestamp-format)
7. [GPS NMEA Records](#7-gps-nmea-records)
8. [CAN Bus Message Format](#8-can-bus-message-format)
9. [Calibration Factors](#9-calibration-factors)
10. [Lap Detection](#10-lap-detection)
11. [Sample Output Format](#11-sample-output-format)
12. [References](#12-references)

---

## 1. Introduction

### 1.1 Purpose

The CTRK file format is a proprietary binary format used by the Yamaha Y-trac motorcycle data logging system to record telemetry during track sessions. This specification documents the format structure to enable interoperability with third-party analysis tools.

### 1.2 Scope

This specification covers:
- CTRK file structure (`.CTRK` extension)
- Data record formats
- Calibration factors for raw sensor values

### 1.3 Terminology

| Term | Definition |
|------|------------|
| CCU | Communication Control Unit - the data logger hardware |
| CAN | Controller Area Network - vehicle bus standard |
| NMEA | National Marine Electronics Association - GPS sentence format |
| APS | Accelerator Position Sensor (throttle grip) |
| TPS | Throttle Position Sensor (actual throttle) |
| IMU | Inertial Measurement Unit |

---

## 2. File Structure Overview

A CTRK file is a continuous binary stream without explicit section delimiters. Sections are identified by pattern matching:

```
+------------------+
|    HEADER        |  Identified by "HEAD" magic and "RECORDLINE." patterns
+------------------+
|                  |
|    DATA          |  Identified by "$GPRMC" and "07 E9 07" patterns
|                  |
+------------------+
|    FOOTER        |  JSON object at end of file (optional)
+------------------+
```

There are no length fields or explicit markers separating these sections. Parsers must scan for known byte patterns to locate data.

---

## 3. Header Section

The header section has no fixed size. It is identified by the presence of specific ASCII patterns embedded in the binary data.

### 3.1 Magic Signature

The file begins with a 4-byte ASCII magic signature:

```
Offset  Size  Description
0x0000  4     "HEAD" (0x48 0x45 0x41 0x44)
```

### 3.2 Track Line Coordinates

Track start/finish line coordinates are stored as ASCII key-value pairs followed by binary double-precision floats. The parser locates these by searching for the ASCII patterns:

```
Pattern                              Followed by
"RECORDLINE.P1.LAT("                 8 bytes double (little-endian)
"RECORDLINE.P1.LNG("                 8 bytes double (little-endian)
"RECORDLINE.P2.LAT("                 8 bytes double (little-endian)
"RECORDLINE.P2.LNG("                 8 bytes double (little-endian)
```

**Example values (from sample file):**
- Start Latitude: 47.949887
- Start Longitude: 0.207159
- End Latitude: 47.949876
- End Longitude: 0.207953

These coordinates define a virtual line used for lap timing detection. The patterns are typically found within the first 500 bytes of the file.

---

## 4. Data Section

The data section contains interleaved records of two types, identified by pattern matching:

### 4.1 GPS Records

GPS data is identified by the ASCII pattern `$GPRMC` (NMEA sentence start). Each GPS record is preceded by a timestamp structure (see Section 7).

### 4.2 CAN Records

CAN bus data is identified by the byte sequence `07 E9 07` where:
- `07 E9` = year 2025 encoded as little-endian (0xE907 = 2025)
- `07` = CAN data sub-type marker

### 4.3 Interleaving

GPS and CAN records are interleaved at approximately 10 Hz (100ms intervals). Multiple CAN messages typically appear between consecutive GPS records. The parser scans the file sequentially, associating CAN values with the next GPS timestamp.

---

## 5. Footer Section

### 5.1 JSON Metadata

The file ends with a JSON object at the very end of the file (0 bytes from EOF). Some binary bytes of unknown purpose appear between the last data record and the JSON.

**Footer from sample file (370 bytes):**

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

### 5.2 Metadata Fields

| Key | Value in sample | Description |
|-----|-----------------|-------------|
| FormatVersion | "1.0" | File format version |
| Weather | "1" | Weather condition code |
| Date | "2025-07-29 15:08:18" | Recording start date/time |
| Tire | "" | Tire information |
| SSID | "YAMAHA MOTOR CCU D0142A" | CCU WiFi network name |
| LapCount | "" | Lap count |
| CircuitName | "" | Track/circuit name |
| Name | "20250729-170818" | Session name |
| User | "R122" | User/rider identifier |
| Temperature | "" | Ambient temperature |

---

## 6. Timestamp Format

Each GPS record is preceded by a timestamp structure containing milliseconds from the CCU internal clock:

```
Field       Type      Description
time_ms     uint16    Milliseconds (little-endian, 2 bytes before GPRMC)
```

The full Unix timestamp is reconstructed by combining:
- Date and time from the GPRMC sentence (seconds precision)
- Milliseconds from the file structure (2 bytes before each GPRMC)

**Example:** `1753792870202` = July 29, 2025 at 17:01:10.202 UTC

---

## 7. GPS NMEA Records

### 7.1 GPRMC Sentence Format

GPS data is stored as standard NMEA 0183 GPRMC sentences:

```
$GPRMC,HHMMSS.sss,A,DDMM.MMMM,N,DDDMM.MMMM,E,SSS.SS,CCC.CC,DDMMYY,,,A*HH
```

| Field | Description | Example |
|-------|-------------|---------|
| HHMMSS.sss | UTC time | 170110.200 |
| A/V | Status (A=valid, V=void) | A |
| DDMM.MMMM | Latitude | 4757.1013 |
| N/S | North/South | N |
| DDDMM.MMMM | Longitude | 01212.4293 |
| E/W | East/West | E |
| SSS.SS | Speed (knots) | 54.32 |
| CCC.CC | Course (degrees) | 123.45 |
| DDMMYY | Date | 290725 |
| *HH | Checksum | *4A |

### 7.2 Coordinate Conversion

NMEA coordinates are in degrees-minutes format. Convert to decimal degrees:

```
decimal_degrees = degrees + (minutes / 60.0)
```

Example: `4757.1013,N` = 47 degrees + (57.1013 / 60) = **47.951688** degrees N

---

## 8. CAN Bus Message Format

### 8.1 CAN Record Structure

CAN bus telemetry is encoded with a year marker and message identifier:

```
Offset  Size  Description
-5      5     Timestamp bytes (sec, min, hour, day, month)
0       2     Year marker: 0x07 0xE9 (2025)
2       1     Sub-type: 0x07 (CAN data)
3       2     CAN ID (little-endian)
5       2     Flags
7       8     CAN data payload
```

### 8.2 CAN Message IDs

| CAN ID | Name | Description |
|--------|------|-------------|
| 0x0209 | Engine | RPM, Gear position |
| 0x0215 | Throttle | APS, TPS, TCS, SCS, LIF, Launch |
| 0x0226 | Raw CAN 1 | Unknown |
| 0x0227 | Temperature | Unknown (replaced by 0x023E?) |
| 0x023E | Temperature 2 | Water temp, Intake temp, Fuel delta |
| 0x0250 | Motion | ACC_X, ACC_Y |
| 0x0257 | ABS 1 | Unknown |
| 0x0258 | IMU | LEAN, PITCH |
| 0x0260 | Brake | Front/Rear brake pressure |
| 0x0264 | Speed | Front/Rear wheel speed |
| 0x0267 | ABS 2 | Unknown |
| 0x0268 | ABS Status | ABS activation F/R |
| 0x0511 | Raw CAN 2 | Unknown |
| 0x051B | Raw CAN 3 | Unknown |

### 8.3 CAN Message Decoding

> **Note:** Bytes are numbered 0-7. All multi-byte values are big-endian unless otherwise specified.

#### 8.3.1 Engine (0x0209)

```
Byte    Description
0-1     RPM (uint16)
4       Gear (bits 0-2, value 7 = neutral)
```

#### 8.3.2 Throttle (0x0215)

```
Byte    Description
0-1     TPS (uint16)
2-3     APS (uint16)
6       Launch (bits 5-6)
7       TCS (bit 5), SCS (bit 4), LIF (bit 3)
```

#### 8.3.3 Temperature (0x023E)

```
Byte    Description
0       Water temperature (uint8)
1       Intake temperature (uint8)
2-3     Fuel delta (uint16, cumulative)
```

Update frequency: ~1 Hz (1 message per 10 GPS samples).

#### 8.3.4 Acceleration (0x0250)

```
Byte    Description
0-1     ACC_X (uint16)
2-3     ACC_Y (uint16)
```

#### 8.3.5 IMU (0x0258)

```
Byte    Description
0-3     LEAN (packed format, see below)
6-7     PITCH (uint16)
```

**LEAN decoding:**

```python
def decode_lean(data: bytes) -> int:
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
    sum_val = (val1 + val2) & 0xFFFF

    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    if deviation <= 499:  # Deadband: ±5°
        return 9000

    deviation_rounded = deviation - (deviation % 100)
    return (9000 + deviation_rounded) & 0xFFFF
```

#### 8.3.6 Speed (0x0264)

```
Byte    Description
0-1     Front wheel speed (uint16)
2-3     Rear wheel speed (uint16)
```

#### 8.3.7 Brake (0x0260)

```
Byte    Description
0-1     Front brake pressure (uint16)
2-3     Rear brake pressure (uint16)
```

#### 8.3.8 ABS Status (0x0268)

```
Byte    Description
4       F_ABS (bit 0), R_ABS (bit 1)
```

---

## 9. Calibration Factors

Raw sensor values must be converted to engineering units using these calibration factors:

### 9.1 Calibration Table

| Parameter | Formula | Unit | Notes |
|-----------|---------|------|-------|
| GPS Speed | `raw_knots * 1.852` | km/h | |
| Engine RPM | `raw / 2.56` | RPM | |
| Wheel Speed | `(raw / 64.0) * 3.6` | km/h | |
| Throttle (APS/TPS) | `((raw / 8.192) * 100) / 84.96` | % | |
| Brake Pressure | `raw / 32.0` | bar | |
| Lean Angle | `(raw / 100.0) - 90.0` | degrees | Requires ±5° deadband |
| Pitch Rate | `(raw / 100.0) - 300.0` | deg/s | |
| Acceleration | `(raw / 1000.0) - 7.0` | G | |
| Temperature | `(raw / 1.6) - 30.0` | Celsius | Single byte, not 16-bit |
| Fuel | `raw / 100.0` | cc | Cumulative (delta summed) |

### 9.2 Raw Value Examples

From sample file (second record):

| Parameter | Raw Value | Calibrated | Unit |
|-----------|-----------|------------|------|
| RPM | 8291 | 3238 | RPM |
| APS | 154 | 22.1 | % |
| TPS | 73 | 10.5 | % |
| Front Speed | 162 | 9.11 | km/h |
| Rear Speed | 156 | 8.78 | km/h |
| Lean | 9000 | 0.0 | deg |
| Pitch | 29904 | -0.96 | deg/s |
| Acc X | 7260 | 0.26 | G |
| Acc Y | 7017 | 0.017 | G |
| Front Brake | 4 | 0.125 | bar |

---

## 10. Lap Detection

### 10.1 Track Line Crossing

Laps are detected when the motorcycle crosses the virtual start/finish line defined by coordinates P1 and P2 in the header.

### 10.2 Lap Time Record Structure

```c
struct SensorsLapTimeRecord {
    int64_t mTime;        // Lap time in milliseconds
    int64_t mSplitTime;   // Split time (if applicable)
};
```

### 10.3 Sample Lap Times

From sample file (9 laps):

| Lap | Time (mm:ss.mmm) | Duration (ms) |
|-----|------------------|---------------|
| 1 | 2:16.174 | 136174 |
| 2 | 1:52.800 | 112800 |
| 3 | 1:51.276 | 111276 |
| 4 | 1:51.271 | 111271 |
| 5 | 1:57.921 | 117921 |
| 6 | 1:53.980 | 113980 |
| 7 | 1:53.769 | 113769 |
| 8 | 2:18.707 | 138707 |
| 9 | 11:31.479 | 691479 |

---

## 11. Sample Output Format

### 11.1 CSV Export Format

The CSV export format includes all telemetry channels with calibrated values and descriptive column names:

```csv
lap,time_ms,latitude,longitude,gps_speed_kmh,rpm,throttle_grip,throttle,water_temp,intake_temp,front_speed_kmh,rear_speed_kmh,fuel_cc,lean_deg,pitch_deg_s,acc_x_g,acc_y_g,front_brake_bar,rear_brake_bar,gear,f_abs,r_abs,tcs,scs,lif,launch
```

### 11.2 Field Definitions

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| lap | int | - | Lap number (1-based) |
| time_ms | int64 | ms | Unix timestamp (milliseconds) |
| latitude | float | ° | GPS latitude (degrees) |
| longitude | float | ° | GPS longitude (degrees) |
| gps_speed_kmh | float | km/h | GPS ground speed |
| rpm | int | RPM | Engine RPM (calibrated) |
| throttle_grip | float | % | Accelerator position (APS, calibrated) |
| throttle | float | % | Throttle valve position (TPS, calibrated) |
| water_temp | float | °C | Water temperature (calibrated) |
| intake_temp | float | °C | Intake air temperature (calibrated) |
| front_speed_kmh | float | km/h | Front wheel speed (calibrated) |
| rear_speed_kmh | float | km/h | Rear wheel speed (calibrated) |
| fuel_cc | float | cc | Cumulative fuel consumption (calibrated) |
| lean_deg | float | ° | Lean angle (calibrated) |
| pitch_deg_s | float | °/s | Pitch rate (calibrated) |
| acc_x_g | float | G | Lateral acceleration (calibrated) |
| acc_y_g | float | G | Longitudinal acceleration (calibrated) |
| front_brake_bar | float | bar | Front brake pressure (calibrated) |
| rear_brake_bar | float | bar | Rear brake pressure (calibrated) |
| gear | int | - | Current gear (0=N, 1-6) |
| f_abs | bool | - | Front ABS active |
| r_abs | bool | - | Rear ABS active |
| tcs | int | - | Traction control active |
| scs | int | - | Slide control active |
| lif | int | - | Lift control active |
| launch | int | - | Launch control active |

---

## 12. References

1. [Yamaha Y-Trac Product Page](https://www.yamaha-motor.eu/fr/fr/y-trac/)
2. [NMEA 0183 Standard](https://www.nmea.org/content/STANDARDS/NMEA_0183_Standard)
3. [CAN Bus Specification (ISO 11898)](https://www.iso.org/standard/63648.html)

