#!/usr/bin/env python3
"""
CTRK File Parser

Pure Python parser for Yamaha Y-Trac CTRK telemetry files.
Based on reverse engineering of the native library (radare2 disassembly).
All CAN message parsing formulas verified against native library output.

Features:
- LEAN formula includes native deadband and rounding
- All CAN byte positions confirmed by disassembly
- Lap detection via RECORDLINE crossing from header
- Fuel accumulator resets at each lap boundary

Usage:
    python ctrk_parser.py <input.CTRK> [output.csv]

License: MIT
"""

import struct
import csv
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


# =============================================================================
# CALIBRATION FACTORS (verified against native library)
# =============================================================================

class Calibration:
    """Calibration factors matching the native library output."""

    @staticmethod
    def rpm(raw: int) -> int:
        """Engine RPM."""
        return int(raw / 2.56)

    @staticmethod
    def wheel_speed_kmh(raw: int) -> float:
        """Wheel speed in km/h."""
        return (raw / 64.0) * 3.6

    @staticmethod
    def throttle(raw: int) -> float:
        """Throttle percentage (0-100%)."""
        return ((raw / 8.192) * 100.0) / 84.96

    @staticmethod
    def brake(raw: int) -> float:
        """Brake pressure in bar."""
        return raw / 32.0

    @staticmethod
    def lean(raw: int) -> float:
        """Lean angle in degrees. Raw 9000 = upright (0°)."""
        return (raw / 100.0) - 90.0

    @staticmethod
    def pitch(raw: int) -> float:
        """Pitch rate in deg/s."""
        return (raw / 100.0) - 300.0

    @staticmethod
    def acceleration(raw: int) -> float:
        """Acceleration in G."""
        return (raw / 1000.0) - 7.0

    @staticmethod
    def temperature(raw: int) -> float:
        """Temperature in Celsius."""
        return (raw / 1.6) - 30.0

    @staticmethod
    def fuel(raw: int) -> float:
        """Fuel in cc."""
        return raw / 100.0

    @staticmethod
    def gps_speed_kmh(knots: float) -> float:
        """GPS speed in km/h."""
        return knots * 1.852


# =============================================================================
# LAP DETECTION (via RECORDLINE crossing)
# =============================================================================

@dataclass
class FinishLine:
    """Finish line defined by two GPS points (P1 and P2)."""
    p1_lat: float
    p1_lng: float
    p2_lat: float
    p2_lng: float

    def side_of_line(self, lat: float, lng: float) -> float:
        """
        Compute which side of the finish line a point is on.
        Returns positive for one side, negative for the other, zero on the line.
        Uses cross product of vectors.
        """
        # Vector from P1 to P2
        dx = self.p2_lng - self.p1_lng
        dy = self.p2_lat - self.p1_lat
        # Vector from P1 to point
        px = lng - self.p1_lng
        py = lat - self.p1_lat
        # Cross product (z component)
        return dx * py - dy * px

    def crosses_line(self, lat1: float, lng1: float, lat2: float, lng2: float) -> bool:
        """
        Check if moving from (lat1, lng1) to (lat2, lng2) crosses the finish line.
        Returns True if the line segment crosses the finish line.
        """
        side1 = self.side_of_line(lat1, lng1)
        side2 = self.side_of_line(lat2, lng2)

        # Sign change means crossing
        if side1 * side2 >= 0:
            return False

        # Check if the crossing point is within the finish line segment
        # Using parametric intersection
        # Line 1: P1 to P2 (finish line)
        # Line 2: (lat1,lng1) to (lat2,lng2) (trajectory)

        dx1 = self.p2_lng - self.p1_lng
        dy1 = self.p2_lat - self.p1_lat
        dx2 = lng2 - lng1
        dy2 = lat2 - lat1

        denom = dx1 * dy2 - dy1 * dx2
        if abs(denom) < 1e-12:
            return False

        t = ((lng1 - self.p1_lng) * dy2 - (lat1 - self.p1_lat) * dx2) / denom

        # t should be between 0 and 1 for the crossing to be on the finish line segment
        return 0 <= t <= 1


def parse_finish_line(data: bytes) -> Optional[FinishLine]:
    """Parse RECORDLINE coordinates from CTRK header."""
    try:
        # Find P1.LAT
        p1_lat_pos = data.find(b'RECORDLINE.P1.LAT(')
        if p1_lat_pos == -1:
            return None
        p1_lat = struct.unpack('<d', data[p1_lat_pos + 18:p1_lat_pos + 26])[0]

        # Find P1.LNG
        p1_lng_pos = data.find(b'RECORDLINE.P1.LNG(')
        if p1_lng_pos == -1:
            return None
        p1_lng = struct.unpack('<d', data[p1_lng_pos + 18:p1_lng_pos + 26])[0]

        # Find P2.LAT
        p2_lat_pos = data.find(b'RECORDLINE.P2.LAT(')
        if p2_lat_pos == -1:
            return None
        p2_lat = struct.unpack('<d', data[p2_lat_pos + 18:p2_lat_pos + 26])[0]

        # Find P2.LNG
        p2_lng_pos = data.find(b'RECORDLINE.P2.LNG(')
        if p2_lng_pos == -1:
            return None
        p2_lng = struct.unpack('<d', data[p2_lng_pos + 18:p2_lng_pos + 26])[0]

        return FinishLine(p1_lat, p1_lng, p2_lat, p2_lng)
    except (struct.error, IndexError):
        return None


# =============================================================================
# CAN PARSING FUNCTIONS (verified by disassembly)
# =============================================================================

def parse_can_0x0209(data: bytes, state: dict):
    """Engine: RPM & Gear (verified @ 0x0000e14b)"""
    state['rpm'] = (data[0] << 8) | data[1]
    gear = data[4] & 0x07
    if gear != 7:  # 7 = invalid
        state['gear'] = gear


def parse_can_0x0215(data: bytes, state: dict):
    """Throttle: TPS, APS, electronic controls (verified @ 0x0000e170)"""
    state['tps'] = (data[0] << 8) | data[1]
    state['aps'] = (data[2] << 8) | data[3]
    state['launch'] = 1 if (data[6] & 0x60) else 0
    state['tcs'] = (data[7] >> 5) & 1
    state['scs'] = (data[7] >> 4) & 1
    state['lif'] = (data[7] >> 3) & 1


def parse_can_0x023e(data: bytes, state: dict, fuel_acc: list):
    """Temperature & Fuel (verified @ 0x0000e292)
    Note: Temperature uses single bytes, not 16-bit!
    """
    state['water_temp'] = data[0]  # Single byte
    state['intake_temp'] = data[1]  # Single byte
    fuel_delta = (data[2] << 8) | data[3]
    fuel_acc[0] += fuel_delta
    state['fuel'] = fuel_acc[0]


def parse_can_0x0250(data: bytes, state: dict):
    """Motion: Acceleration X/Y (verified @ 0x0000e0be)
    Note: This is ACC, NOT lean/pitch!
    """
    state['acc_x'] = (data[0] << 8) | data[1]
    state['acc_y'] = (data[2] << 8) | data[3]


def parse_can_0x0258(data: bytes, state: dict):
    """IMU: Lean & Pitch (verified @ 0x0000e1bc)

    LEAN formula from disassembly:
    1. Extract packed values from bytes 0-3
    2. Compute sum = val1 + val2
    3. Transform to deviation from center (9000)
    4. Apply deadband: if deviation <= 499, return 9000 (upright)
    5. Round deviation to nearest 100 (degree)
    """
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    # Extract packed values
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
    sum_val = (val1 + val2) & 0xFFFF

    # Transform to deviation from center (9000)
    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Apply deadband (~5 degrees)
    if deviation <= 499:
        state['lean'] = 9000  # Upright
        state['lean_signed'] = 9000
    else:
        # Round to nearest degree
        deviation_rounded = deviation - (deviation % 100)
        state['lean'] = (9000 + deviation_rounded) & 0xFFFF
        # Signed: preserve direction (sum_val < 9000 = negative lean)
        if sum_val < 9000:
            state['lean_signed'] = 9000 - deviation_rounded
        else:
            state['lean_signed'] = 9000 + deviation_rounded

    # Pitch is straightforward
    state['pitch'] = (data[6] << 8) | data[7]


def parse_can_0x0260(data: bytes, state: dict):
    """Brake pressure (verified @ 0x0000e226)"""
    state['front_brake'] = (data[0] << 8) | data[1]
    state['rear_brake'] = (data[2] << 8) | data[3]


def parse_can_0x0264(data: bytes, state: dict):
    """Wheel speed (verified @ 0x0000e07a)"""
    state['front_speed'] = (data[0] << 8) | data[1]
    state['rear_speed'] = (data[2] << 8) | data[3]


def parse_can_0x0268(data: bytes, state: dict):
    """ABS status (verified @ 0x0000e2b7) - R_ABS=bit0, F_ABS=bit1"""
    state['r_abs'] = bool(data[4] & 1)
    state['f_abs'] = bool((data[4] >> 1) & 1)


CAN_HANDLERS = {
    0x0209: parse_can_0x0209,
    0x0215: parse_can_0x0215,
    0x0250: parse_can_0x0250,
    0x0258: parse_can_0x0258,
    0x0260: parse_can_0x0260,
    0x0264: parse_can_0x0264,
    0x0268: parse_can_0x0268,
    # 0x023E handled separately due to fuel accumulator
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TelemetryRecord:
    """Single telemetry sample with raw values."""
    lap: int = 0
    time_ms: int = 0

    # GPS
    latitude: float = 0.0
    longitude: float = 0.0
    gps_speed_knots: float = 0.0

    # Engine (raw)
    rpm: int = 0
    gear: int = 0

    # Throttle (raw)
    aps: int = 0
    tps: int = 0

    # Temperature (raw) - single bytes from 0x023E
    water_temp: int = 0
    intake_temp: int = 0

    # Wheel Speed (raw)
    front_speed: int = 0
    rear_speed: int = 0

    # Fuel (raw) - cumulative
    fuel: int = 0

    # IMU (raw)
    lean: int = 0
    lean_signed: int = 0
    pitch: int = 0

    # Acceleration (raw)
    acc_x: int = 0
    acc_y: int = 0

    # Brakes (raw)
    front_brake: int = 0
    rear_brake: int = 0

    # Electronic systems
    f_abs: bool = False
    r_abs: bool = False
    tcs: int = 0
    scs: int = 0
    lif: int = 0
    launch: int = 0


# =============================================================================
# PARSER
# =============================================================================

class CTRKParser:
    """Parser v7 based on verified reverse engineering of libSensorsRecordIF.so"""

    MAGIC = b'HEAD'

    def __init__(self, filepath: str, native_mode: bool = False):
        self.filepath = Path(filepath)
        self.native_mode = native_mode
        self.data = b''
        self.records: List[TelemetryRecord] = []
        self._fuel_accumulator = [0]  # Use list for mutable reference
        self._state = {
            'rpm': 0, 'gear': 0, 'aps': 0, 'tps': 0,
            'water_temp': 0, 'intake_temp': 0,
            'front_speed': 0, 'rear_speed': 0,
            'front_brake': 0, 'rear_brake': 0,
            'acc_x': 0, 'acc_y': 0,
            'lean': 0, 'lean_signed': 0, 'pitch': 0,
            'f_abs': False, 'r_abs': False,
            'tcs': 0, 'scs': 0, 'lif': 0, 'launch': 0,
            'fuel': 0,
        }
        self._finish_line: Optional[FinishLine] = None
        self._current_lap = 1
        self._prev_lat = 0.0
        self._prev_lng = 0.0

    def parse(self) -> List[TelemetryRecord]:
        """Parse the CTRK file."""
        with open(self.filepath, 'rb') as f:
            self.data = f.read()

        print(f"Parsing {self.filepath.name} ({len(self.data):,} bytes)")

        if not self.data.startswith(self.MAGIC):
            raise ValueError(f"Invalid CTRK file: expected 'HEAD' magic")

        # Parse finish line from header
        self._finish_line = parse_finish_line(self.data[:500])
        if self._finish_line:
            print(f"  Finish line: P1({self._finish_line.p1_lat:.6f}, {self._finish_line.p1_lng:.6f}) -> "
                  f"P2({self._finish_line.p2_lat:.6f}, {self._finish_line.p2_lng:.6f})")
        else:
            print("  Warning: Could not parse finish line from header, all records will be lap 1")

        if self.native_mode:
            self._parse_perlap()
        else:
            self._parse_data_section()

        return self.records

    def _check_lap_crossing(self, lat: float, lng: float) -> bool:
        """
        Check if we crossed the finish line.
        Returns True if a new lap started (crossing detected).

        Each crossing increments the lap counter and resets fuel.
        Lap 1 ends at the first crossing, Lap 2 starts.
        """
        if self._finish_line is None:
            return False

        # Need a previous position to check crossing
        if self._prev_lat == 0.0 and self._prev_lng == 0.0:
            self._prev_lat = lat
            self._prev_lng = lng
            return False

        crossed = self._finish_line.crosses_line(self._prev_lat, self._prev_lng, lat, lng)

        self._prev_lat = lat
        self._prev_lng = lng

        if crossed:
            # Every crossing starts a new lap
            self._current_lap += 1
            # Reset fuel accumulator for new lap
            self._fuel_accumulator[0] = 0
            self._state['fuel'] = 0
            return True

        return False

    def _find_data_start(self) -> int:
        """Find where the structured data section begins.

        The file header structure:
          - 0x00-0x03: "HEAD" magic
          - 0x04-0x33: fixed header fields (52 bytes total with magic)
          - 0x34+: variable-length header entries (RECORDLINE coords, CCU_VERSION)
          - Data records start immediately after the last header entry
        """
        off = 0x34
        while off < min(len(self.data), 500):
            if off + 4 > len(self.data):
                break
            entry_size = struct.unpack_from('<I', self.data, off)[0]
            if entry_size < 5 or entry_size > 200:
                break
            name_len = self.data[off + 4]
            if name_len < 1 or name_len > entry_size - 5:
                break
            off += entry_size
        return off

    def _get_time_data(self, ts_bytes: bytes) -> int:
        """Convert 10-byte timestamp structure to epoch milliseconds.

        Matches native GetTimeData function at 0xdf40.

        Timestamp structure:
            [0:2]  millis  (uint16 LE, 0-999)
            [2]    seconds
            [3]    minutes
            [4]    hours
            [5]    weekday (not used for time computation)
            [6]    day
            [7]    month
            [8:10] year    (uint16 LE)
        """
        millis = ts_bytes[0] | (ts_bytes[1] << 8)
        sec = ts_bytes[2]
        min_ = ts_bytes[3]
        hour = ts_bytes[4]
        day = ts_bytes[6]
        month = ts_bytes[7]
        year = ts_bytes[8] | (ts_bytes[9] << 8)

        dt = datetime(year, month, day, hour, min_, sec)
        return int(dt.timestamp() * 1000) + millis

    @staticmethod
    def _validate_nmea_checksum(sentence: str) -> bool:
        """Validate NMEA XOR checksum.

        Matches native AnalisysNMEA checksum validation at 0xe3f8.
        Computes XOR of all bytes between '$' and '*', compares with
        the 2-hex-digit checksum after '*'.
        """
        star_idx = sentence.find('*')
        if star_idx < 1 or star_idx + 3 > len(sentence):
            return False

        computed = 0
        for ch in sentence[1:star_idx]:
            computed ^= ord(ch)

        try:
            stated = int(sentence[star_idx + 1:star_idx + 3], 16)
        except ValueError:
            return False

        return computed == stated

    @staticmethod
    def _parse_gprmc_sentence(sentence: str) -> Optional[dict]:
        """Parse NMEA GPRMC sentence for GPS position and speed.

        Timestamps are not extracted here — they come from the
        14-byte record header instead.
        """
        try:
            parts = sentence.split(',')
            if len(parts) < 8 or parts[2] != 'A':
                return None

            lat_str = parts[3]
            lat = float(lat_str[:2]) + float(lat_str[2:]) / 60.0
            if parts[4] == 'S':
                lat = -lat

            lon_str = parts[5]
            lon = float(lon_str[:3]) + float(lon_str[3:]) / 60.0
            if parts[6] == 'W':
                lon = -lon

            speed_knots = float(parts[7]) if parts[7] else 0.0

            return {'latitude': lat, 'longitude': lon, 'speed_knots': speed_knots}
        except (ValueError, IndexError):
            return None

    def _create_record(self, time_ms: int, lat: float, lon: float,
                       speed_knots: float) -> TelemetryRecord:
        """Create a TelemetryRecord from current accumulated CAN state."""
        return TelemetryRecord(
            lap=self._current_lap,
            time_ms=time_ms,
            latitude=lat,
            longitude=lon,
            gps_speed_knots=speed_knots,
            rpm=self._state['rpm'],
            gear=self._state['gear'],
            aps=self._state['aps'],
            tps=self._state['tps'],
            water_temp=self._state['water_temp'],
            intake_temp=self._state['intake_temp'],
            front_speed=self._state['front_speed'],
            rear_speed=self._state['rear_speed'],
            front_brake=self._state['front_brake'],
            rear_brake=self._state['rear_brake'],
            acc_x=self._state['acc_x'],
            acc_y=self._state['acc_y'],
            lean=self._state['lean'],
            lean_signed=self._state['lean_signed'],
            pitch=self._state['pitch'],
            f_abs=self._state['f_abs'],
            r_abs=self._state['r_abs'],
            tcs=self._state['tcs'],
            scs=self._state['scs'],
            lif=self._state['lif'],
            launch=self._state['launch'],
            fuel=self._state['fuel'],
        )

    def _parse_data_section(self):
        """Parse the structured record data section.

        The CTRK data section consists of sequential records, each with a
        14-byte header followed by a variable-length payload:

            Header (14 bytes):
                [0:2]   record_type  (uint16 LE): 1=CAN, 2=GPS/NMEA, 5=Lap
                [2:4]   total_size   (uint16 LE): header + payload
                [4:14]  timestamp    (10 bytes: millis, sec, min, hour, wday, day, month, year)

            Payload (total_size - 14 bytes):
                CAN:  [canid(2)][pad(2)][DLC(1)][data(DLC)]
                GPS:  NMEA sentence text (e.g. "$GPRMC,...*XX\\r\\n")
                Lap:  lap timing data

        Records are emitted at 100ms intervals (10Hz), matching the native
        library's time-interval filtering (max_interval=100ms).

        Based on disassembly of GetSensorsRecordData at 0xa970.
        """
        data_start = self._find_data_start()
        pos = data_start

        # GetTimeDataEx state: tracks previous record for incremental computation
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0

        # Emission state: tracks when the last record was emitted
        last_emitted_ms = None
        gps_count = 0
        can_count = 0
        checksum_failures = 0

        # Current GPS state (updated by type-2 GPS records)
        # Sentinel 9999.0 matches native behavior when no fix is acquired
        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False  # True once any GPRMC (A or V) has been seen

        while pos + 14 <= len(self.data):
            # Read 14-byte record header
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]

            # Stop conditions: end-of-data marker or invalid header
            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

            # === Timestamp computation (GetTimeDataEx logic) ===
            # Always update current_epoch_ms when timestamp bytes change.
            # prev_epoch_ms / prev_ts_bytes are used solely for incremental
            # computation, independent of emission timing.
            if prev_ts_bytes is None or ts_bytes != prev_ts_bytes:
                if prev_ts_bytes is None:
                    current_epoch_ms = self._get_time_data(ts_bytes)
                elif ts_bytes[2:10] == prev_ts_bytes[2:10]:
                    # Same second: incremental millis update
                    prev_millis = prev_ts_bytes[0] | (prev_ts_bytes[1] << 8)
                    curr_millis = ts_bytes[0] | (ts_bytes[1] << 8)
                    current_epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)
                    # Handle millis wrapping (e.g., 999 -> 8) within the same
                    # second field. This occurs when the hardware timestamp
                    # capture is non-atomic: millis rolled over but the second
                    # field hasn't incremented yet. Add 1000ms to compensate.
                    if curr_millis < prev_millis:
                        current_epoch_ms += 1000
                else:
                    # Different second: full recomputation
                    current_epoch_ms = self._get_time_data(ts_bytes)

                prev_epoch_ms = current_epoch_ms
                prev_ts_bytes = ts_bytes

            # Start the emission clock at the very first record,
            # matching native GetSensorsRecordData behavior.
            if last_emitted_ms is None:
                last_emitted_ms = current_epoch_ms

            # === Process payload by record type ===
            if rec_type == 1 and len(payload) >= 5:
                # CAN record: [canid(2)][pad(2)][DLC(1)][data...]
                can_id = struct.unpack_from('<H', payload, 0)[0]
                can_data = payload[5:]

                if can_id == 0x023E and len(can_data) >= 4:
                    parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                elif can_id in CAN_HANDLERS:
                    CAN_HANDLERS[can_id](can_data, self._state)

                can_count += 1

            elif rec_type == 2 and len(payload) > 6:
                # GPS/NMEA record
                sentence = payload.decode('ascii', errors='replace').rstrip('\r\n\x00')
                if sentence.startswith('$GPRMC'):
                    if self._validate_nmea_checksum(sentence):
                        gps_data = self._parse_gprmc_sentence(sentence)
                        if gps_data:
                            # Valid fix (status 'A') — update position
                            current_lat = gps_data['latitude']
                            current_lon = gps_data['longitude']
                            current_speed_knots = gps_data['speed_knots']
                        # Emit initial record at the first GPRMC (even 'V' status).
                        # Uses clock start time (first record's timestamp).
                        if not has_gprmc:
                            has_gprmc = True
                            self._check_lap_crossing(current_lat, current_lon)
                            record = self._create_record(
                                last_emitted_ms, current_lat, current_lon,
                                current_speed_knots)
                            self.records.append(record)
                            gps_count += 1
                    else:
                        checksum_failures += 1

            elif rec_type == 5:
                # Lap marker record: re-align emission clock.
                # Native GetSensorsRecordData is called per-lap with memset(0),
                # which zeroes prev_emitted_epoch_ms at each lap boundary.
                # This re-aligns the 100ms emission grid at every lap start.
                last_emitted_ms = current_epoch_ms

            # === Emission check after payload (100ms interval) ===
            if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                self._check_lap_crossing(current_lat, current_lon)
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon,
                    current_speed_knots)
                self.records.append(record)
                gps_count += 1
                last_emitted_ms = current_epoch_ms

            pos += total_size

        # Emit final accumulated record
        if has_gprmc and last_emitted_ms is not None:
            self._check_lap_crossing(current_lat, current_lon)
            record = self._create_record(
                current_epoch_ms, current_lat, current_lon, current_speed_knots)
            self.records.append(record)
            gps_count += 1

        print(f"  Found {gps_count} GPS records, {can_count} CAN messages")
        if checksum_failures:
            print(f"  Rejected {checksum_failures} GPRMC sentences (bad checksum)")
        print(f"  Built {len(self.records)} telemetry records")
        print(f"  Detected {self._current_lap} laps")

    def _scan_lap_boundaries(self) -> list:
        """Scan data section for type-5 Lap marker records.

        Returns list of byte offsets where each type-5 record starts.
        Matches native fcn.0000a430 lap counter at 0xa4c9.
        """
        data_start = self._find_data_start()
        pos = data_start
        boundaries = []

        while pos + 14 <= len(self.data):
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]

            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            if rec_type == 5:
                boundaries.append(pos)

            pos += total_size

        return boundaries

    def _parse_perlap(self):
        """Per-lap parsing matching native GetSensorsRecordData behavior.

        Processes each lap independently with full state reset, matching
        the native library's per-lap architecture where GetSensorsRecordData
        is called once per lap with memset(0) at entry.
        """
        data_start = self._find_data_start()
        data_end = len(self.data)
        type5_offsets = self._scan_lap_boundaries()

        # Build lap ranges: [(start_offset, end_offset), ...]
        # Matches moveToLapLogRecorOffset(lapIndex) at 0xed50:
        #   lapIndex=0 -> data_start (before any type-5)
        #   lapIndex=N -> position after the Nth type-5 record
        lap_ranges = []

        if len(type5_offsets) == 0:
            lap_ranges.append((data_start, data_end))
        else:
            # Lap 1: data_start to first type-5
            lap_ranges.append((data_start, type5_offsets[0]))

            # Subsequent laps: from after one type-5 to the next
            for i in range(len(type5_offsets)):
                t5_pos = type5_offsets[i]
                t5_size = struct.unpack_from('<H', self.data, t5_pos + 2)[0]
                start_after_t5 = t5_pos + t5_size

                if i + 1 < len(type5_offsets):
                    end = type5_offsets[i + 1]
                else:
                    end = data_end

                lap_ranges.append((start_after_t5, end))

        total_laps = len(lap_ranges)
        print(f"  Native mode: {total_laps} laps ({len(type5_offsets)} type-5 markers)")

        for lap_idx, (start, end) in enumerate(lap_ranges):
            self._parse_lap_range(start, end, lap_idx + 1)

        print(f"  Built {len(self.records)} telemetry records")
        print(f"  Processed {total_laps} laps")

    def _parse_lap_range(self, start: int, end: int, lap_number: int):
        """Process records in [start, end) with fully reset state.

        Matches native GetSensorsRecordData behavior for a single lap:
        memset(state, 0, 0x2c8) at 0xa9fc and memset(aux, 0, 0x2e0) at 0xaa10.
        """
        # === CAN STATE RESET (matching memset at 0xa9fc) ===
        self._state = {
            'rpm': 0, 'gear': 0, 'aps': 0, 'tps': 0,
            'water_temp': 0, 'intake_temp': 0,
            'front_speed': 0, 'rear_speed': 0,
            'front_brake': 0, 'rear_brake': 0,
            'acc_x': 0, 'acc_y': 0,
            'lean': 0, 'lean_signed': 0, 'pitch': 0,
            'f_abs': False, 'r_abs': False,
            'tcs': 0, 'scs': 0, 'lif': 0, 'launch': 0,
            'fuel': 0,
        }
        self._fuel_accumulator = [0]
        self._current_lap = lap_number

        # === AUXILIARY STATE RESET (matching memset at 0xaa10) ===
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0
        last_emitted_ms = None

        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

        # === RECORD PROCESSING LOOP ===
        pos = start
        while pos + 14 <= end:
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]

            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > end:
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

            # --- Timestamp computation (GetTimeDataEx) ---
            if prev_ts_bytes is None or ts_bytes != prev_ts_bytes:
                if prev_ts_bytes is None:
                    current_epoch_ms = self._get_time_data(ts_bytes)
                elif ts_bytes[2:10] == prev_ts_bytes[2:10]:
                    prev_millis = prev_ts_bytes[0] | (prev_ts_bytes[1] << 8)
                    curr_millis = ts_bytes[0] | (ts_bytes[1] << 8)
                    current_epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)
                    if curr_millis < prev_millis:
                        current_epoch_ms += 1000
                else:
                    current_epoch_ms = self._get_time_data(ts_bytes)

                prev_epoch_ms = current_epoch_ms
                prev_ts_bytes = ts_bytes

            if last_emitted_ms is None:
                last_emitted_ms = current_epoch_ms

            # --- Payload processing ---
            if rec_type == 1 and len(payload) >= 5:
                can_id = struct.unpack_from('<H', payload, 0)[0]
                can_data = payload[5:]
                if can_id == 0x023E and len(can_data) >= 4:
                    parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                elif can_id in CAN_HANDLERS:
                    CAN_HANDLERS[can_id](can_data, self._state)

            elif rec_type == 2 and len(payload) > 6:
                sentence = payload.decode('ascii', errors='replace').rstrip('\r\n\x00')
                if sentence.startswith('$GPRMC'):
                    if self._validate_nmea_checksum(sentence):
                        gps_data = self._parse_gprmc_sentence(sentence)
                        if gps_data:
                            current_lat = gps_data['latitude']
                            current_lon = gps_data['longitude']
                            current_speed_knots = gps_data['speed_knots']
                        if not has_gprmc:
                            has_gprmc = True
                            record = self._create_record(
                                last_emitted_ms, current_lat, current_lon,
                                current_speed_knots)
                            self.records.append(record)

            # Type-5 records within a lap range are ignored
            # (boundaries are pre-computed by _scan_lap_boundaries)

            # --- Emission check (100ms interval) ---
            if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon,
                    current_speed_knots)
                self.records.append(record)
                last_emitted_ms = current_epoch_ms

            pos += total_size

        # Final emission for this lap
        if has_gprmc and last_emitted_ms is not None:
            record = self._create_record(
                current_epoch_ms, current_lat, current_lon, current_speed_knots)
            self.records.append(record)

    def export_csv(self, output_path: str):
        """Export records to CSV matching native library format."""
        if not self.records:
            print("No records to export")
            return

        fieldnames = [
            'lap', 'time_ms', 'latitude', 'longitude', 'gps_speed_kmh',
            'rpm', 'throttle_grip', 'throttle', 'water_temp', 'intake_temp',
            'front_speed_kmh', 'rear_speed_kmh', 'fuel_cc', 'lean_deg', 'lean_signed_deg', 'pitch_deg_s',
            'acc_x_g', 'acc_y_g', 'front_brake_bar', 'rear_brake_bar', 'gear',
            'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch'
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in self.records:
                row = {
                    'lap': r.lap,
                    'time_ms': r.time_ms,
                    'latitude': f"{r.latitude:.6f}",
                    'longitude': f"{r.longitude:.6f}",
                    'gps_speed_kmh': f"{Calibration.gps_speed_kmh(r.gps_speed_knots):.2f}",
                    'rpm': Calibration.rpm(r.rpm),
                    'throttle_grip': f"{Calibration.throttle(r.aps):.1f}",
                    'throttle': f"{Calibration.throttle(r.tps):.1f}",
                    'water_temp': f"{Calibration.temperature(r.water_temp):.1f}",
                    'intake_temp': f"{Calibration.temperature(r.intake_temp):.1f}",
                    'front_speed_kmh': f"{Calibration.wheel_speed_kmh(r.front_speed):.1f}",
                    'rear_speed_kmh': f"{Calibration.wheel_speed_kmh(r.rear_speed):.1f}",
                    'fuel_cc': f"{Calibration.fuel(r.fuel):.2f}",
                    'lean_deg': f"{Calibration.lean(r.lean):.1f}",
                    'lean_signed_deg': f"{Calibration.lean(r.lean_signed):.1f}",
                    'pitch_deg_s': f"{Calibration.pitch(r.pitch):.1f}",
                    'acc_x_g': f"{Calibration.acceleration(r.acc_x):.2f}",
                    'acc_y_g': f"{Calibration.acceleration(r.acc_y):.2f}",
                    'front_brake_bar': f"{Calibration.brake(r.front_brake):.1f}",
                    'rear_brake_bar': f"{Calibration.brake(r.rear_brake):.1f}",
                    'gear': r.gear,
                    'f_abs': str(r.f_abs).lower(),
                    'r_abs': str(r.r_abs).lower(),
                    'tcs': r.tcs,
                    'scs': r.scs,
                    'lif': r.lif,
                    'launch': r.launch,
                }
                writer.writerow(row)

        print(f"Exported {len(self.records)} records to {output_path}")

    def export_raw_csv(self, output_path: str):
        """Export raw (uncalibrated) values to CSV for comparison with native."""
        if not self.records:
            print("No records to export")
            return

        fieldnames = [
            'lap', 'time_ms', 'latitude', 'longitude', 'gps_speed_knots',
            'rpm_raw', 'aps_raw', 'tps_raw', 'wt_raw', 'intt_raw',
            'fspeed_raw', 'rspeed_raw', 'fuel_raw', 'lean_raw', 'lean_signed_raw', 'pitch_raw',
            'accx_raw', 'accy_raw', 'fpress_raw', 'rpress_raw', 'gear',
            'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch'
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in self.records:
                row = {
                    'lap': r.lap,
                    'time_ms': r.time_ms,
                    'latitude': f"{r.latitude:.6f}",
                    'longitude': f"{r.longitude:.6f}",
                    'gps_speed_knots': f"{r.gps_speed_knots:.4f}",
                    'rpm_raw': r.rpm,
                    'aps_raw': r.aps,
                    'tps_raw': r.tps,
                    'wt_raw': r.water_temp,
                    'intt_raw': r.intake_temp,
                    'fspeed_raw': r.front_speed,
                    'rspeed_raw': r.rear_speed,
                    'fuel_raw': r.fuel,
                    'lean_raw': r.lean,
                    'lean_signed_raw': r.lean_signed,
                    'pitch_raw': r.pitch,
                    'accx_raw': r.acc_x,
                    'accy_raw': r.acc_y,
                    'fpress_raw': r.front_brake,
                    'rpress_raw': r.rear_brake,
                    'gear': r.gear,
                    'f_abs': str(r.f_abs).lower(),
                    'r_abs': str(r.r_abs).lower(),
                    'tcs': r.tcs,
                    'scs': r.scs,
                    'lif': r.lif,
                    'launch': r.launch,
                }
                writer.writerow(row)

        print(f"Exported {len(self.records)} raw records to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python ctrk_parser.py <input.CTRK> [output.csv]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else str(Path(input_path).with_suffix('')) + '_parsed.csv'
    raw_output_path = str(Path(input_path).with_suffix('')) + '_parsed_raw.csv'

    parser = CTRKParser(input_path)
    parser.parse()
    parser.export_csv(output_path)
    parser.export_raw_csv(raw_output_path)


if __name__ == '__main__':
    main()
