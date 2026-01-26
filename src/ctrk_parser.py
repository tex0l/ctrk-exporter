#!/usr/bin/env python3
"""
CTRK File Parser

Pure Python parser for Yamaha Y-Trac CTRK/CCT telemetry files.
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
import re
import csv
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
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
    else:
        # Round to nearest degree
        deviation_rounded = deviation - (deviation % 100)
        state['lean'] = (9000 + deviation_rounded) & 0xFFFF

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
    """ABS status (verified @ 0x0000e2b7)"""
    state['f_abs'] = bool(data[4] & 1)
    state['r_abs'] = bool((data[4] >> 1) & 1)


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
    lean: int = 9000  # Default: upright
    pitch: int = 30000  # Default: 0 deg/s

    # Acceleration (raw)
    acc_x: int = 7000  # Default: 0 G
    acc_y: int = 7000  # Default: 0 G

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
    """Parser v6 based on verified reverse engineering of libSensorsRecordIF.so"""

    MAGIC = b'HEAD'

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.data = b''
        self.records: List[TelemetryRecord] = []
        self._fuel_accumulator = [0]  # Use list for mutable reference
        self._state = {
            'rpm': 0, 'gear': 0, 'aps': 0, 'tps': 0,
            'water_temp': 0, 'intake_temp': 0,
            'front_speed': 0, 'rear_speed': 0,
            'front_brake': 0, 'rear_brake': 0,
            'acc_x': 7000, 'acc_y': 7000,
            'lean': 9000, 'pitch': 30000,
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

    def _create_initial_record(self) -> Optional[TelemetryRecord]:
        """Create an initial zero-row like the native library.

        The native library creates a first row with:
        - Timestamp from file structure (offset -10 before first GPRMC)
        - GPS data from first GPRMC
        - All CAN values = 0
        """
        # Find first GPRMC
        pos = self.data.find(b'$GPRMC')
        if pos == -1 or pos < 12:
            return None

        # Extract file milliseconds from structure
        file_millis = self.data[pos - 10] | (self.data[pos - 9] << 8)

        # Parse the first GPRMC
        end = self.data.find(b'\r\n', pos)
        if end == -1:
            end = self.data.find(b'\n', pos)
        if end == -1:
            return None

        sentence = self.data[pos:end].decode('ascii', errors='ignore')
        parts = sentence.split(',')
        if len(parts) < 10 or parts[2] != 'A':
            return None

        try:
            time_str = parts[1]
            date_str = parts[9] if len(parts) > 9 else ""

            hours = int(time_str[0:2])
            minutes = int(time_str[2:4])
            seconds = int(time_str[4:6])

            if len(date_str) >= 6:
                day = int(date_str[0:2])
                month = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
            else:
                return None

            dt = datetime(year, month, day, hours, minutes, seconds)
            timestamp_ms = int(dt.timestamp()) * 1000 + file_millis

            # Parse GPS coordinates
            lat_str = parts[3]
            lat_deg = float(lat_str[:2])
            lat_min = float(lat_str[2:])
            latitude = lat_deg + lat_min / 60.0
            if parts[4] == 'S':
                latitude = -latitude

            lon_str = parts[5]
            lon_deg = float(lon_str[:3])
            lon_min = float(lon_str[3:])
            longitude = lon_deg + lon_min / 60.0
            if parts[6] == 'W':
                longitude = -longitude

            speed_knots = float(parts[7]) if parts[7] else 0.0

            # Create initial record with all CAN values = 0
            return TelemetryRecord(
                lap=1,
                time_ms=timestamp_ms,
                latitude=latitude,
                longitude=longitude,
                gps_speed_knots=speed_knots,
                # All CAN values explicitly set to 0
                rpm=0, gear=0, aps=0, tps=0,
                water_temp=0, intake_temp=0,
                front_speed=0, rear_speed=0,
                fuel=0, lean=0, pitch=0,
                acc_x=0, acc_y=0,
                front_brake=0, rear_brake=0,
                f_abs=False, r_abs=False,
                tcs=0, scs=0, lif=0, launch=0,
            )
        except (ValueError, IndexError):
            return None

    def _parse_data_section(self):
        """Parse the interleaved GPS and CAN data."""
        pos = 0
        current_record = None
        gps_count = 0
        can_count = 0

        VALID_CAN_IDS = set(CAN_HANDLERS.keys()) | {0x023E}

        # Add initial empty row like native library
        # Native creates a zero-row with GPS data but all CAN values = 0
        initial_record = self._create_initial_record()
        if initial_record:
            self.records.append(initial_record)

        while pos < len(self.data) - 20:
            # Look for GPS NMEA sentence
            if self.data[pos:pos+6] == b'$GPRMC':
                end = self.data.find(b'\r\n', pos)
                if end == -1:
                    end = self.data.find(b'\n', pos)
                if end == -1:
                    pos += 1
                    continue

                sentence = self.data[pos:end].decode('ascii', errors='ignore')
                gps_data = self._parse_gprmc(sentence)

                if gps_data:
                    # Save previous record
                    if current_record and current_record.time_ms > 0:
                        self.records.append(current_record)

                    # Check for lap crossing before creating new record
                    self._check_lap_crossing(gps_data['latitude'], gps_data['longitude'])

                    # Create new record with current CAN state
                    current_record = TelemetryRecord(
                        lap=self._current_lap,
                        time_ms=gps_data['time_ms'],
                        latitude=gps_data['latitude'],
                        longitude=gps_data['longitude'],
                        gps_speed_knots=gps_data['speed_knots'],
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
                        pitch=self._state['pitch'],
                        f_abs=self._state['f_abs'],
                        r_abs=self._state['r_abs'],
                        tcs=self._state['tcs'],
                        scs=self._state['scs'],
                        lif=self._state['lif'],
                        launch=self._state['launch'],
                        fuel=self._state['fuel'],
                    )
                    gps_count += 1

                pos = end + 1
                continue

            # Look for CAN message: 07 E9 07 [CAN_ID 2 bytes]
            if (self.data[pos] == 0x07 and
                self.data[pos+1] == 0xE9 and
                self.data[pos+2] == 0x07 and
                pos + 16 <= len(self.data)):

                can_id = struct.unpack('<H', self.data[pos+3:pos+5])[0]

                if can_id in VALID_CAN_IDS:
                    can_data = self.data[pos+8:pos+16]

                    if len(can_data) >= 8:
                        # Process CAN message
                        if can_id == 0x023E:
                            parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                        elif can_id in CAN_HANDLERS:
                            CAN_HANDLERS[can_id](can_data, self._state)

                        # Apply to current record
                        if current_record:
                            self._apply_state_to_record(current_record)

                        can_count += 1

                    pos += 16
                    continue

            pos += 1

        # Don't forget last record
        if current_record and current_record.time_ms > 0:
            self.records.append(current_record)

        print(f"  Found {gps_count} GPS records, {can_count} CAN messages")
        print(f"  Built {len(self.records)} telemetry records")
        print(f"  Detected {self._current_lap} laps")

    def _parse_gprmc(self, sentence: str) -> Optional[dict]:
        """Parse NMEA GPRMC sentence."""
        try:
            parts = sentence.split(',')
            if len(parts) < 10 or parts[2] != 'A':
                return None

            # Time
            time_str = parts[1]

            # Latitude
            lat_str = parts[3]
            lat_deg = float(lat_str[:2])
            lat_min = float(lat_str[2:])
            latitude = lat_deg + lat_min / 60.0
            if parts[4] == 'S':
                latitude = -latitude

            # Longitude
            lon_str = parts[5]
            lon_deg = float(lon_str[:3])
            lon_min = float(lon_str[3:])
            longitude = lon_deg + lon_min / 60.0
            if parts[6] == 'W':
                longitude = -longitude

            # Speed
            speed_knots = float(parts[7]) if parts[7] else 0.0

            # Date
            date_str = parts[9] if len(parts) > 9 else ""

            # Compute timestamp from GPRMC time string
            timestamp_ms = self._compute_timestamp(time_str, date_str)

            return {
                'time_ms': timestamp_ms,
                'latitude': latitude,
                'longitude': longitude,
                'speed_knots': speed_knots,
            }
        except (ValueError, IndexError):
            return None

    def _compute_timestamp(self, time_str: str, date_str: str) -> int:
        """Compute Unix timestamp in milliseconds from GPRMC time string.

        Uses the milliseconds from the GPRMC time string (e.g., "144110.300" -> 300ms).
        This avoids synchronization issues with file structure milliseconds.
        """
        try:
            hours = int(time_str[0:2])
            minutes = int(time_str[2:4])
            seconds = int(time_str[4:6])

            # Parse milliseconds from GPRMC time string (e.g., ".300" -> 300)
            if len(time_str) > 6 and time_str[6] == '.':
                ms_str = time_str[7:]
                # Pad or truncate to 3 digits
                ms_str = (ms_str + '000')[:3]
                millis = int(ms_str)
            else:
                millis = 0

            if len(date_str) >= 6:
                day = int(date_str[0:2])
                month = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
            else:
                now = datetime.utcnow()
                day, month, year = now.day, now.month, now.year

            dt = datetime(year, month, day, hours, minutes, seconds)
            return int(dt.timestamp()) * 1000 + millis
        except (ValueError, IndexError):
            return 0

    def _apply_state_to_record(self, record: TelemetryRecord):
        """Apply current CAN state to a telemetry record."""
        record.rpm = self._state['rpm']
        record.gear = self._state['gear']
        record.aps = self._state['aps']
        record.tps = self._state['tps']
        record.water_temp = self._state['water_temp']
        record.intake_temp = self._state['intake_temp']
        record.front_speed = self._state['front_speed']
        record.rear_speed = self._state['rear_speed']
        record.front_brake = self._state['front_brake']
        record.rear_brake = self._state['rear_brake']
        record.acc_x = self._state['acc_x']
        record.acc_y = self._state['acc_y']
        record.lean = self._state['lean']
        record.pitch = self._state['pitch']
        record.f_abs = self._state['f_abs']
        record.r_abs = self._state['r_abs']
        record.tcs = self._state['tcs']
        record.scs = self._state['scs']
        record.lif = self._state['lif']
        record.launch = self._state['launch']
        record.fuel = self._state['fuel']

    def export_csv(self, output_path: str):
        """Export records to CSV matching native library format."""
        if not self.records:
            print("No records to export")
            return

        fieldnames = [
            'lap', 'time_ms', 'latitude', 'longitude', 'gps_speed_kmh',
            'rpm', 'throttle_grip', 'throttle', 'water_temp', 'intake_temp',
            'front_speed_kmh', 'rear_speed_kmh', 'fuel_cc', 'lean_deg', 'pitch_deg_s',
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
            'fspeed_raw', 'rspeed_raw', 'fuel_raw', 'lean_raw', 'pitch_raw',
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
