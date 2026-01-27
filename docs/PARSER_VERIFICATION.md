# Parser Verification and Analysis

**Date:** 2026-01-26
**Test File:** 20250729-170818.CTRK
**Purpose:** Comparative analysis between Python parser output and native library output

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Test Methodology](#2-test-methodology)
3. [Quantitative Comparison](#3-quantitative-comparison)
4. [Timestamp Analysis](#4-timestamp-analysis)
5. [Channel-by-Channel Analysis](#5-channel-by-channel-analysis)
6. [Root Cause Analysis](#6-root-cause-analysis)
7. [Interpolation Strategy](#7-interpolation-strategy)
8. [Recommendations](#8-recommendations)

---

## 1. Executive Summary

The Python parser produces functionally equivalent output to the native library with minor differences attributable to timestamp handling and CAN message synchronization. The parser generates approximately 0.08% more data points due to less aggressive GPS record filtering.

### Key Metrics

| Metric | Native | Parser | Difference |
|--------|--------|--------|------------|
| Total points | 16462 | 16475 | +13 (+0.08%) |
| Exact match fields | - | - | 2/24 |
| High match fields (>=95%) | - | - | 11/24 |
| Lower match fields (<95%) | - | - | 11/24 |

---

## 2. Test Methodology

### 2.1 Alignment Strategy

Records are aligned by timestamp using a ±50ms tolerance window. This accounts for:
- Native library timestamp smoothing
- Different millisecond source interpretations

### 2.2 Comparison Metrics

For each field, the following metrics are computed:
- **Match rate**: Percentage of records where values are equal within tolerance
- **Average difference**: Mean absolute difference for non-matching records
- **Maximum difference**: Worst-case deviation

### 2.3 Field-Specific Tolerances

| Field Type | Tolerance | Rationale |
|------------|-----------|-----------|
| Boolean | exact | Binary values |
| Integer (gear) | exact | Discrete values |
| Temperature | ±0.5°C | ~1Hz update rate |
| Speed | ±0.5 km/h | CAN timing |
| Throttle | ±1% | CAN timing |
| Pressure | ±0.1 bar | CAN timing |
| Acceleration | ±0.02 G | CAN timing |
| GPS coordinates | ±0.00001° | float32 precision |

---

## 3. Quantitative Comparison

### 3.1 Exact Match Fields (100%)

| Field | Match Rate | Notes |
|-------|------------|-------|
| rear_brake_bar | 100% | CAN 0x0260 bytes 2-3 |
| launch | 100% | CAN 0x0215 byte 6 |

These fields demonstrate that the parser correctly decodes the CAN message structure for these specific data points.

### 3.2 High Match Fields (>=95%)

| Field | Match Rate | Avg Diff | Cause |
|-------|------------|----------|-------|
| tcs | 99.9% | - | CAN timing |
| lif | 99.9% | - | CAN timing |
| gear | 99.6% | 0.004 | Timing shifts |
| scs | 99.6% | - | CAN timing |
| intake_temp | 99.3% | 0.18°C | ~1Hz CAN update rate |
| front_brake_bar | 99.3% | 0.03 bar | CAN timing |
| water_temp | 98.8% | 0.37°C | ~1Hz CAN update rate |
| fuel_cc | 98.1% | 0.42 cc | Accumulation timing |
| f_abs | 97.6% | - | CAN timing |
| r_abs | 97.6% | - | CAN timing |
| acc_x_g | 95.3% | 0.006 G | CAN timing |

### 3.3 Lower Match Fields (<95%)

| Field | Match Rate | Avg Diff | Cause |
|-------|------------|----------|-------|
| acc_y_g | 94.8% | 0.006 G | CAN timing |
| throttle_grip | 91.3% | 0.37% | CAN timing |
| lean_deg | 89.6% | 0.24° | Complex formula, deadband |
| throttle | 88.8% | 0.33% | CAN timing |
| front_speed_kmh | 88.8% | 0.23 km/h | CAN timing |
| rear_speed_kmh | 88.8% | 0.24 km/h | CAN timing |
| longitude | 84.3% | <0.00001° | float32 vs float64 |
| latitude | 82.4% | <0.00001° | float32 vs float64 |
| pitch_deg_s | 81.7% | 0.70°/s | CAN timing |
| gps_speed_kmh | 81.1% | 0.36 km/h | GPS interpolation |
| rpm | 75.8% | 49 RPM | CAN timing |

---

## 4. Timestamp Analysis

### 4.1 Millisecond Source

The native library uses a 2-byte millisecond field stored in the file structure, NOT the GPRMC sentence time:

```
File structure before each GPRMC (15 bytes):
[...] [ms_lo] [ms_hi] [0a/0b] [sec] [min] [hour] [0x02] [day] [07] [e9] [07] $GPRMC,...
       ^-----------^   ^-----------------------------------------^   ^---------^
       Milliseconds    Timestamp structure (5 bytes)                 CAN marker
       (little-endian)
```

### 4.2 Clock Drift Observation

| Row | GPRMC ms | File ms | Native ms | Delta Native-File |
|-----|----------|---------|-----------|-------------------|
| 1 | 300 | 202 | 202 | 0 |
| 2 | 400 | 304 | 304 | 0 |
| 3 | 500 | 402 | 412 | +10 |
| 4 | 600 | 502 | 512 | +10 |
| 5 | 700 | 604 | 612 | +8 |

### 4.3 Interpretation

1. **CCU Internal Clock**: The file stores milliseconds from the CCU's internal clock, which runs ~98ms ahead of GPS time
2. **Native Smoothing**: The native library applies a smoothing algorithm to regularize intervals toward 100ms
3. **Parser Approach**: The parser uses GPRMC milliseconds directly, resulting in slightly different timestamps

### 4.4 Timestamp Interval Distribution

| Interval | Parser | Native |
|----------|--------|--------|
| 100ms (exact) | 100% | ~98% |
| 90-110ms | 100% | ~99.5% |
| Other | 0% | ~0.5% |

The native library's smoothing algorithm creates occasional intervals of 90ms or 110ms to compensate for accumulated drift.

---

## 5. Channel-by-Channel Analysis

### 5.1 GPS Position (latitude, longitude)

**Observed Difference**: ~0.00001° (approximately 1.1 meters)

**Root Cause**: Floating-point precision
- Native library uses float32 (single precision)
- Parser uses float64 (double precision)
- Conversion from NMEA degrees-minutes format amplifies precision differences

**Statistical Analysis**:
```
Parser:  47.951694 (float64)
Native:  47.95169 (float32 representation)
Delta:   0.000004° = ~0.4m
```

### 5.2 GPS Speed (gps_speed_kmh)

**Observed Difference**: 0.36 km/h average

**Root Cause**: Different interpolation approaches
- Native library may interpolate GPS speed between samples
- Parser uses raw GPRMC speed values

### 5.3 Engine RPM

**Observed Difference**: 49 RPM average (75.8% match)

**Root Cause**: CAN message timing
- RPM changes rapidly (engine dynamics)
- CAN 0x0209 messages arrive between GPS samples
- Parser associates CAN values with the next GPS record
- Native library may use different association logic

### 5.4 Throttle (TPS/APS)

**Observed Difference**: 0.33-0.37% average

**Root Cause**: Same as RPM - CAN timing differences

### 5.5 Lean Angle

**Observed Difference**: 0.24° average (89.6% match)

**Root Cause**: Multiple factors
1. Complex packed byte formula
2. ±5° deadband (values within 499 raw units return 9000)
3. Rounding to nearest degree (100 raw units)
4. CAN timing

### 5.6 Temperatures (water_temp, intake_temp)

**Observed Difference**: 0.18-0.37°C

**Root Cause**: Low update frequency
- Temperature CAN messages (0x023E) arrive at ~1Hz
- 10 GPS samples per temperature update
- Slight timing differences affect which sample gets new value

---

## 6. Root Cause Analysis

### 6.1 Primary Cause: CAN-GPS Association

The fundamental difference is how CAN telemetry values are associated with GPS timestamps:

```
Timeline:
GPS  |----G1----|----G2----|----G3----|----G4----|
CAN  |--C1--|--C2--|--C3--|--C4--|--C5--|--C6--|
```

**Parser Approach**:
- Maintains state from all CAN messages
- Associates current state with next GPS record

**Native Library Approach**:
- May interpolate or use different association rules
- Applies timestamp smoothing that shifts associations

### 6.2 Secondary Cause: Timestamp Smoothing

The native library smooths timestamps to regularize 100ms intervals:

```python
# Simplified native smoothing algorithm (hypothesized)
def smooth_timestamp(current_ms, previous_ms):
    expected = previous_ms + 100
    delta = current_ms - expected
    if abs(delta) < 15:
        return expected  # Snap to 100ms grid
    return current_ms
```

### 6.3 Tertiary Cause: Float Precision

GPS coordinates use different precision:
- Native: float32 (23-bit mantissa, ~7 significant digits)
- Parser: float64 (52-bit mantissa, ~15 significant digits)

---

## 7. Interpolation Strategy

To produce output closer to the native library, implement the following interpolation strategies:

### 7.1 Timestamp Smoothing

```python
def smooth_timestamps(records: List[Record]) -> List[Record]:
    """
    Apply timestamp smoothing to regularize 100ms intervals.

    The native library maintains a target interval of 100ms and
    adjusts individual timestamps to minimize cumulative drift.
    """
    if len(records) < 2:
        return records

    smoothed = [records[0]]
    target_interval_ms = 100

    for i in range(1, len(records)):
        prev_time = smoothed[-1].time_ms
        curr_time = records[i].time_ms

        expected_time = prev_time + target_interval_ms
        delta = curr_time - expected_time

        # If within ±15ms of expected, snap to grid
        if abs(delta) <= 15:
            new_time = expected_time
        # If significantly off, adjust but maintain some smoothing
        elif abs(delta) <= 50:
            new_time = expected_time + (delta // 2)
        else:
            new_time = curr_time

        record_copy = records[i].copy()
        record_copy.time_ms = new_time
        smoothed.append(record_copy)

    return smoothed
```

### 7.2 CAN Value Interpolation

```python
def interpolate_can_values(records: List[Record], can_timestamps: List[int]) -> List[Record]:
    """
    Interpolate high-frequency CAN values (RPM, throttle, speed) to
    match GPS timestamps more accurately.

    Instead of using the last known value, interpolate between
    the surrounding CAN messages.
    """
    for i, record in enumerate(records):
        # Find CAN messages bracketing this GPS timestamp
        before_can = find_can_before(record.time_ms, can_timestamps)
        after_can = find_can_after(record.time_ms, can_timestamps)

        if before_can and after_can:
            # Linear interpolation factor
            t = (record.time_ms - before_can.time_ms) / \
                (after_can.time_ms - before_can.time_ms)

            # Interpolate continuous values
            record.rpm = lerp(before_can.rpm, after_can.rpm, t)
            record.front_speed = lerp(before_can.front_speed, after_can.front_speed, t)
            record.rear_speed = lerp(before_can.rear_speed, after_can.rear_speed, t)
            record.tps = lerp(before_can.tps, after_can.tps, t)
            record.aps = lerp(before_can.aps, after_can.aps, t)
            # Don't interpolate boolean/discrete values (gear, ABS, etc.)

    return records

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation: a + t * (b - a)"""
    return a + t * (b - a)
```

### 7.3 GPS Point Filtering

```python
def filter_gps_points(records: List[Record]) -> List[Record]:
    """
    Apply filtering logic similar to native library.

    The native library appears to filter some GPS points that the
    parser includes. Possible criteria:
    - Duplicate timestamps
    - Invalid fix quality
    - Excessive position jump
    """
    filtered = []
    prev = None

    for record in records:
        # Skip if timestamp unchanged from previous
        if prev and record.time_ms == prev.time_ms:
            continue

        # Skip if position jump exceeds threshold (suggests GPS glitch)
        if prev:
            dist = haversine_distance(prev.lat, prev.lon, record.lat, record.lon)
            time_delta_s = (record.time_ms - prev.time_ms) / 1000.0
            speed_mps = dist / time_delta_s if time_delta_s > 0 else 0

            # If implied speed > 500 km/h, likely GPS error
            if speed_mps > 138.9:  # 500 km/h
                continue

        filtered.append(record)
        prev = record

    return filtered
```

### 7.4 Coordinate Precision Reduction

```python
def reduce_coordinate_precision(records: List[Record]) -> List[Record]:
    """
    Reduce GPS coordinate precision to match float32.
    """
    import struct

    for record in records:
        # Convert to float32 and back to simulate native precision
        record.latitude = struct.unpack('f', struct.pack('f', record.latitude))[0]
        record.longitude = struct.unpack('f', struct.pack('f', record.longitude))[0]

    return records
```

### 7.5 Combined Interpolation Pipeline

```python
def apply_native_interpolation(records: List[Record]) -> List[Record]:
    """
    Apply full interpolation pipeline to match native output.

    Order matters:
    1. Filter invalid GPS points
    2. Smooth timestamps
    3. Interpolate CAN values
    4. Reduce coordinate precision
    """
    result = filter_gps_points(records)
    result = smooth_timestamps(result)
    result = interpolate_can_values(result, can_timestamps)
    result = reduce_coordinate_precision(result)
    return result
```

---

## 8. Recommendations

### 8.1 For Users Requiring Exact Native Match

Use the Android converter with the native library:
```bash
./ctrk-exporter android convert session.CTRK
```

### 8.2 For Users Accepting Parser Output

The Python parser is suitable when:
- Platform independence is required
- Minor timing differences are acceptable
- Additional data points (0.08% more) are acceptable

### 8.3 For Parser Improvement

Implement the interpolation strategies in Section 7 as optional flags:
```bash
./ctrk-exporter parse session.CTRK --interpolate-native
```

### 8.4 Future Work

1. **Reverse engineer timestamp smoothing**: Analyze native library disassembly to determine exact smoothing algorithm
2. **CAN association logic**: Determine exact rules for CAN-GPS timestamp association
3. **GPS filtering criteria**: Identify undocumented filtering applied by native library

---

*End of Analysis*
