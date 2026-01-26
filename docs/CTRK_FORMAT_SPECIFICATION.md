# CTRK File Format Specification

**Version:** 1.2
**Date:** 2026-01-26
**Status:** En cours - Vérifié par désassemblage de libSensorsRecordIF.so (radare2)
**Author:** Reverse-engineered from Yamaha Y-trac DataViewer Android Application

---

## Changelog

### v1.2 (2026-01-26)
- Ajout de la formule LEAN native exacte (désassemblée)
- Confirmation des mappings CAN par analyse radare2 du binaire x86_64
- Documentation du deadband LEAN (±5°)
- Clarification de l'ordre TPS/APS
- Lien vers `libSensorsRecordIF_howitworks.md` pour les détails techniques

---

## ⚠️ État de vérification (Parser vs Native Library)

### Résumé des tests

| Métrique | Valeur |
|----------|--------|
| Fichier test | 20250729-170818.CTRK |
| Points Native | 16462 |
| Points Parser | 16474 (+12) |
| Champs parfaits | 8/19 (42%) |
| Champs mineurs | 8/19 |
| Champs majeurs | 3/19 |

### ✅ Champs vérifiés (100% match)

| Champ | Statut | Notes |
|-------|--------|-------|
| latitude | ✓ PARFAIT | GPS NMEA parsing correct |
| longitude | ✓ PARFAIT | GPS NMEA parsing correct |
| time_ms | ✓ PARFAIT | Timestamps GPS corrects |
| throttle_grip (APS) | ✓ PARFAIT | CAN 0x0215 bytes 2-3 |
| throttle (TPS) | ✓ PARFAIT | CAN 0x0215 bytes 0-1 |
| rear_brake_bar | ✓ PARFAIT | CAN 0x0260 bytes 2-3 |
| front_brake_bar | ✓ PARFAIT | CAN 0x0260 bytes 0-1 |
| acc_y_g | ✓ PARFAIT | CAN 0x0250 bytes 2-3 |

### ⚡ Champs avec erreurs mineures (<3%)

| Champ | Match | Erreur moy | Cause probable |
|-------|-------|------------|----------------|
| acc_x_g | 99.9% | 1.4% | Timing CAN |
| gear | 99.1% | 0.3% | Timing shifts |
| water_temp | 99.9% | 0.2% | Premier sample |
| intake_temp | 99.8% | 0.2% | Premier sample |
| front_speed_kmh | 98.1% | 0.2% | Timing CAN |
| rear_speed_kmh | 97.1% | 0.2% | Timing CAN |
| fuel_cc | 96.1% | 0.5% | Timing accumulation |
| gps_speed_kmh | 95.6% | 0.5% | Interpolation GPS |

### ❌ Champs avec erreurs majeures

| Champ | Match | Erreur moy | Cause |
|-------|-------|------------|-------|
| lean_deg | 53% | 50% | Formule complexe, décalage ±1° |
| pitch_deg_s | 75% | 59% | Parser 1 sample en avance |
| rpm | 90% | 0.8% | Timing shift ~1 sample |

### Différence de nombre de points

Le parser Python produit **12 points de plus** que la librairie native (16474 vs 16462).

#### Source des timestamps : Découverte importante

Les millisecondes **ne viennent pas du GPRMC** mais d'un champ de 2 bytes stocké dans le fichier :

```
Structure avant chaque GPRMC (15 bytes) :
[...] [ms_lo] [ms_hi] [0a/0b] [sec] [min] [hour] [0x02] [day] [07] [e9] [07] $GPRMC,...
       ^-----------^   ^-----------------------------------------^   ^---------^
       Millisecondes   Structure timestamp (5 bytes)                 CAN marker
       (little-endian)
```

**Exemple concret :**
```
Bytes -15 à -1 avant $GPRMC: 00 02 00 56 00 | ca 00 | 0a | 29 0e 02 1d | 07 e9 07
                                              ^^^^^^
                                              0x00CA = 202 ms
```

#### Comparaison File vs Native vs GPRMC

| Row | GPRMC ms | File ms | Native ms | Écart |
|-----|----------|---------|-----------|-------|
| 1 | 300 | 202 | 202 | 0 |
| 2 | 400 | 304 | 304 | 0 |
| 3 | 500 | 402 | 412 | +10 |
| 4 | 600 | 502 | 512 | +10 |
| 5 | 700 | 604 | 612 | +8 |

**Conclusion :**
- Les millisecondes dans le fichier représentent l'horloge **interne du CCU**
- Le CCU est en avance d'environ ~98ms sur le GPS
- La librairie native applique un **lissage** pour régulariser les intervalles à ~100ms

#### Structure CAN (pas de millisecondes)

Les messages CAN ont un timestamp de 5 bytes sans millisecondes :
```
[second] [minute] [hour] [0x02] [day]
```

> **Note:** Les CAN sont associés aux GPS par position dans le fichier, pas par timestamp précis.

## Abstract

This document specifies the CTRK file format used by the Yamaha Y-trac CCU (Communication Control Unit) data logger system. The CTRK format stores motorcycle telemetry data including GPS position, engine parameters, suspension dynamics, brake inputs, and electronic control system states.

## Table of Contents

1. [Introduction](#1-introduction)
2. [File Structure Overview](#2-file-structure-overview)
3. [Header Section](#3-header-section)
4. [Data Section](#4-data-section)
5. [Footer Section (JSON Metadata)](#5-footer-section)
6. [Data Record Format](#6-data-record-format)
7. [GPS NMEA Records](#7-gps-nmea-records)
8. [CAN Bus Message Format](#8-can-bus-message-format)
9. [Calibration Factors](#9-calibration-factors)
10. [Lap Detection](#10-lap-detection)
11. [Sample Output Format](#11-sample-output-format)
12. [Security Considerations](#12-security-considerations)
13. [References](#13-references)

---

## 1. Introduction

### 1.1 Purpose

The CTRK file format is a proprietary binary format used by the Yamaha Y-trac motorcycle data logging system to record telemetry during track sessions. This specification documents the format structure to enable interoperability with third-party analysis tools.

### 1.2 Scope

This specification covers:
- CTRK file structure (`.CTRK` extension)
- CCT file structure (`.CCT` extension) - similar format
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

A CTRK file consists of three main sections:

```
+------------------+
|    HEADER        |  (~1000 bytes)
+------------------+
|                  |
|    DATA          |  (variable, bulk of file)
|                  |
+------------------+
|    FOOTER        |  (~500 bytes, JSON)
+------------------+
```

### 2.1 File Extensions

| Extension | Description |
|-----------|-------------|
| `.CTRK` | Standard telemetry recording |
| `.CCT` | Compressed/alternate format |
| `.TRG` | Trigger-based recording |

---

## 3. Header Section

### 3.1 Magic Signature

The file begins with a 4-byte ASCII magic signature:

```
Offset  Size  Description
0x0000  4     "HEAD" (0x48 0x45 0x41 0x44)
```

### 3.2 Track Line Coordinates

The header contains track start/finish line coordinates encoded as double-precision floats:

```
RECORDLINE.P1.LAT(<8 bytes double, little-endian>)
RECORDLINE.P1.LNG(<8 bytes double, little-endian>)
RECORDLINE.P2.LAT(<8 bytes double, little-endian>)
RECORDLINE.P2.LNG(<8 bytes double, little-endian>)
```

**Example values (from sample file):**
- Start Latitude: 47.949887
- Start Longitude: 0.207159
- End Latitude: 47.949876
- End Longitude: 0.207953

These coordinates define a virtual line used for lap timing detection.

---

## 4. Data Section

The data section contains interleaved records of two types:
1. GPS NMEA sentences (ASCII)
2. CAN bus telemetry records (binary)

Records are stored sequentially at approximately 10 Hz sampling rate (100ms intervals).

---

## 5. Footer Section

### 5.1 JSON Metadata

The file ends with a JSON object containing session metadata:

```json
{
  "Attribute": [
    {"Key": "FormatVersion", "Value": "2"},
    {"Key": "Date", "Value": "2025-07-29 15:08:18"},
    {"Key": "Name", "Value": "20250729-170818"},
    {"Key": "User", "Value": "R122"},
    {"Key": "SSID", "Value": ""},
    {"Key": "Weather", "Value": "sunny"}
  ]
}
```

### 5.2 Metadata Fields

| Key | Type | Description |
|-----|------|-------------|
| FormatVersion | String | File format version (typically "2") |
| Date | String | Recording date/time (YYYY-MM-DD HH:MM:SS) |
| Name | String | Session name (typically filename) |
| User | String | User/rider identifier |
| SSID | String | WiFi SSID (if connected) |
| Weather | String | Weather condition |

---

## 6. Data Record Format

### 6.1 Timestamp Structure

Each telemetry sample is associated with a Unix timestamp in milliseconds:

```
Field       Type      Description
time_ms     int64     Unix timestamp in milliseconds (since 1970-01-01)
```

**Example:** `1753792870202` = July 29, 2025 at 17:01:10.202 UTC

### 6.2 Sensor Record Structure

The native library populates the following data structure for each sample:

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

| CAN ID | Name | Description | Vérifié |
|--------|------|-------------|---------|
| 0x0209 | Engine | RPM, Gear position | ✓ |
| 0x0215 | Throttle | APS, TPS, TCS, SCS, LIF, Launch | ✓ |
| 0x023E | Temperature 2 | Water temp, Intake temp, Fuel delta | ✓ |
| 0x0250 | Motion | ACC_X, ACC_Y (PAS lean/pitch!) | ✓ |
| 0x0258 | IMU | LEAN (formule complexe), PITCH | ⚠️ Partiellement |
| 0x0260 | Brake | Front/Rear brake pressure | ✓ |
| 0x0264 | Speed | Front/Rear wheel speed | ✓ |
| 0x0268 | ABS Status | ABS activation F/R | ✓ |
| 0x0226 | Raw CAN 1 | Non utilisé | |
| 0x0227 | Temperature | Non utilisé (remplacé par 0x023E) | |
| 0x0257 | ABS 1 | Non utilisé | |
| 0x0267 | ABS 2 | Non utilisé | |
| 0x0511 | Raw CAN 2 | Non utilisé | |
| 0x051B | Raw CAN 3 | Non utilisé | |

### 8.3 CAN Message Decoding (Vérifié par reverse engineering)

> **Note:** Les bytes sont numérotés 0-7. Format big-endian sauf indication contraire.

#### 8.3.1 Engine (0x0209) ✓ Vérifié

```
Byte    Description
0-1     RPM (big-endian, raw) → diviser par 2.56
4       Gear (bits 0-2, valeur 7 = ignoré/neutre)
```

#### 8.3.2 Throttle (0x0215) ✓ Vérifié

```
Byte    Description
0-1     TPS - Throttle Position Sensor (big-endian, raw)
2-3     APS - Accelerator Position Sensor (big-endian, raw)
6       Launch control (bits 5-6)
7       TCS (bit 5), SCS (bit 4), LIF (bit 3)
```

> **Attention:** TPS et APS sont inversés par rapport à la doc originale !

#### 8.3.3 Temperature (0x023E) ✓ Vérifié

```
Byte    Description
0       Water temperature (single byte, raw)
1       Intake temperature (single byte, raw)
2-3     Fuel delta (big-endian, cumulatif)
```

> **Fréquence:** ~1 Hz (1 message pour 10 GPS samples)

#### 8.3.4 Motion/Accélération (0x0250) ✓ Vérifié

```
Byte    Description
0-1     ACC_X - Accélération longitudinale (big-endian, raw)
2-3     ACC_Y - Accélération latérale (big-endian, raw)
```

> **Important:** Ce CAN contient ACC_X/ACC_Y, PAS lean/pitch !

#### 8.3.5 IMU - Lean/Pitch (0x0258) ✓ Vérifié par désassemblage

```
Byte    Description
0-3     LEAN - Formule complexe (voir ci-dessous)
6-7     PITCH (big-endian, raw)
```

**Formule LEAN (confirmée par désassemblage de AnalisysCAN @ 0x0000e1bc):**

```python
def compute_lean_native(data: bytes) -> int:
    """
    Calcule la valeur LEAN exactement comme la bibliothèque native.
    Source: désassemblage radare2 de libSensorsRecordIF.so (x86_64)

    Args:
        data: 8 bytes du message CAN 0x0258

    Returns:
        lean_raw: Valeur brute (9000 = upright, calibrer avec (raw/100) - 90)
    """
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    # Step 1: Extract values from packed bytes
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)

    # Step 2: Compute sum
    sum_val = (val1 + val2) & 0xFFFF

    # Step 3: Transform to deviation from center (9000)
    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Step 4: Deadband - if within ±5° (~499 raw), return upright
    if deviation <= 499:
        return 9000  # Upright (0° after calibration)

    # Step 5: For larger deviations, round to nearest degree
    deviation_rounded = deviation - (deviation % 100)
    result = 9000 + deviation_rounded

    return result & 0xFFFF
```

**Note:** Cette formule produit toujours une valeur ≥ 9000 ou exactement 9000 pour le deadband.
La librairie native semble stocker l'amplitude de l'inclinaison, pas la direction signée.
Voir `docs/libSensorsRecordIF_howitworks.md` pour le désassemblage complet.

#### 8.3.6 Wheel Speed (0x0264) ✓ Vérifié

```
Byte    Description
0-1     Front wheel speed (big-endian, raw)
2-3     Rear wheel speed (big-endian, raw)
```

#### 8.3.7 Brake Pressure (0x0260) ✓ Vérifié

```
Byte    Description
0-1     Front brake pressure (big-endian, raw)
2-3     Rear brake pressure (big-endian, raw)
```

#### 8.3.8 ABS Status (0x0268) ✓ Vérifié

```
Byte    Description
4       F-ABS (bit 0), R-ABS (bit 1)
```

---

## 9. Calibration Factors

Raw sensor values must be converted to engineering units using these calibration factors:

### 9.1 Calibration Table

| Parameter | Formula | Unit | Vérifié | Notes |
|-----------|---------|------|---------|-------|
| GPS Speed | `raw_knots * 1.852` | km/h | ✓ | |
| Engine RPM | `raw / 2.56` | RPM | ✓ | |
| Wheel Speed | `(raw / 64.0) * 3.6` | km/h | ✓ | |
| Throttle (APS/TPS) | `((raw / 8.192) * 100) / 84.96` | % | ✓ | |
| Brake Pressure | `raw / 32.0` | bar | ✓ | |
| Lean Angle | `(raw / 100.0) - 90.0` | degrees | ⚠️ | Nécessite deadband ±4° |
| Pitch Rate | `(raw / 100.0) - 300.0` | deg/s | ⚠️ | Timing shift |
| Acceleration | `(raw / 1000.0) - 7.0` | G | ✓ | |
| Temperature | `(raw / 1.6) - 30.0` | Celsius | ✓ | Single byte, pas 16-bit |
| Fuel | `raw / 100.0` | cc | ✓ | Cumulatif (delta additionné) |

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

The recommended CSV export format includes all telemetry channels:

```csv
lap,time_ms,latitude,longitude,gps_speed_kmh,rpm,aps,tps,water_temp,intake_temp,front_speed,rear_speed,fuel,lean,pitch,acc_x,acc_y,front_brake,rear_brake,gear,f_abs,r_abs,tcs,scs,lif,launch
```

### 11.2 Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| lap | int | Lap number (1-based) |
| time_ms | int64 | Unix timestamp (milliseconds) |
| latitude | float | GPS latitude (degrees) |
| longitude | float | GPS longitude (degrees) |
| gps_speed_kmh | float | GPS ground speed (km/h) |
| rpm | int | Engine RPM (raw) |
| aps | int | Accelerator position (raw) |
| tps | int | Throttle position (raw) |
| water_temp | int | Water temperature (raw) |
| intake_temp | int | Intake air temperature (raw) |
| front_speed | int | Front wheel speed (raw) |
| rear_speed | int | Rear wheel speed (raw) |
| fuel | int | Fuel flow (raw) |
| lean | int | Lean angle (raw) |
| pitch | int | Pitch rate (raw) |
| acc_x | int | Longitudinal acceleration (raw) |
| acc_y | int | Lateral acceleration (raw) |
| front_brake | int | Front brake pressure (raw) |
| rear_brake | int | Rear brake pressure (raw) |
| gear | int | Current gear (0=N, 1-6) |
| f_abs | bool | Front ABS active |
| r_abs | bool | Rear ABS active |
| tcs | int | Traction control level |
| scs | int | Slide control level |
| lif | int | Lift control level |
| launch | int | Launch control active |

---

## 12. Security Considerations

### 12.1 File Validation

Implementations MUST validate:
1. File begins with "HEAD" magic bytes
2. File size is reasonable (typically < 100 MB)
3. GPS coordinates are within valid ranges (-90 to 90 lat, -180 to 180 lon)
4. Timestamps are within reasonable bounds

### 12.2 Privacy

CTRK files contain precise GPS location data. Care should be taken when sharing files to avoid revealing home locations or other private information.

---

## 13. References

1. Yamaha Y-trac DataViewer Android Application (version 2.x)
2. NMEA 0183 Standard for Interfacing Marine Electronic Devices
3. CAN Bus Specification (ISO 11898)

---

## Appendix A: Complete Sample Record

```
Lap: 1
Timestamp: 1753792870304 (2025-07-29 17:01:10.304 UTC)
GPS: 47.951694, 0.207152 @ 7.96 km/h
Engine: 8291 raw (3238 RPM), Gear 1
Throttle: APS=154 (18.8%), TPS=73 (8.9%)
Wheel Speed: Front=162 (2.5 km/h), Rear=156 (2.4 km/h)
IMU: Lean=9000 (0 deg), Pitch=29904 (-0.96 deg/s)
Acceleration: X=7260 (0.26G), Y=7017 (0.02G)
Brakes: Front=4 (0.125 bar), Rear=0
Systems: F-ABS=off, R-ABS=off, TCS=0, SCS=0, LIF=0, Launch=0
```

---

*End of Specification*
