#!/usr/bin/env python3
"""
CTRK File Parser

A pure Python parser for Yamaha Y-Trac CTRK telemetry files (.CTRK).

This module provides functionality to parse binary CTRK files recorded by the
Yamaha Y-Trac CCU (Communication Control Unit) motorcycle data logger. It extracts
21 telemetry channels at 10 Hz including GPS position, engine parameters, IMU data,
brake inputs, and electronic control system states.

The parser is based on reverse engineering of the native library via radare2
disassembly, with all CAN message parsing formulas verified against native output.

Features:
    - Pure Python implementation with no external dependencies (stdlib only)
    - LEAN formula includes native deadband and rounding algorithm
    - All CAN byte positions confirmed by disassembly
    - Lap detection via RECORDLINE finish line crossing from header
    - Fuel accumulator with per-lap reset
    - Optional native-compatible per-lap processing mode

Example:
    Basic usage::

        from ctrk_parser import CTRKParser

        parser = CTRKParser("session.CTRK")
        records = parser.parse()
        parser.export_csv("session.csv")

    With native-compatible mode::

        parser = CTRKParser("session.CTRK", native_mode=True)
        records = parser.parse()

License:
    MIT

See Also:
    - docs/CTRK_FORMAT_SPECIFICATION.md for the complete binary format specification
    - docs/NATIVE_LIBRARY.md for native library reverse engineering notes
    - docs/COMPARISON.md for validation results against native library
"""

import struct
import csv
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from datetime import datetime


# =============================================================================
# CALIBRATION FACTORS
# =============================================================================

class Calibration:
    """
    Calibration factors for converting raw sensor values to engineering units.

    All calibration formulas have been verified against the native library output
    via radare2 disassembly. The formulas convert raw integer values from CAN
    messages to physical units (RPM, km/h, degrees, etc.).

    Note:
        These are static methods for stateless conversion. Each method takes a
        raw integer value and returns the calibrated floating-point result.

    Example:
        >>> Calibration.rpm(25600)
        10000
        >>> Calibration.temperature(176)
        80.0
    """

    @staticmethod
    def rpm(raw: int) -> int:
        """
        Convert raw RPM value to engine RPM.

        Args:
            raw: Raw 16-bit value from CAN 0x0209 bytes 0-1 (big-endian).

        Returns:
            Engine RPM as integer.

        Example:
            >>> Calibration.rpm(25600)
            10000
        """
        return int(raw / 2.56)

    @staticmethod
    def wheel_speed_kmh(raw: int) -> float:
        """
        Convert raw wheel speed value to km/h.

        Args:
            raw: Raw 16-bit value from CAN 0x0264 (big-endian).

        Returns:
            Wheel speed in km/h.

        Example:
            >>> Calibration.wheel_speed_kmh(6400)
            360.0
        """
        return (raw / 64.0) * 3.6

    @staticmethod
    def throttle(raw: int) -> float:
        """
        Convert raw throttle position to percentage.

        Works for both TPS (Throttle Position Sensor) and APS (Accelerator
        Position Sensor) from CAN 0x0215.

        Args:
            raw: Raw 16-bit value from CAN 0x0215 (big-endian).

        Returns:
            Throttle percentage (0-100%, may exceed 100% at full throttle).

        Example:
            >>> Calibration.throttle(6963)
            100.0
        """
        return ((raw / 8.192) * 100.0) / 84.96

    @staticmethod
    def brake(raw: int) -> float:
        """
        Convert raw brake pressure to bar.

        Args:
            raw: Raw 16-bit value from CAN 0x0260 (big-endian).

        Returns:
            Brake hydraulic pressure in bar.

        Example:
            >>> Calibration.brake(320)
            10.0
        """
        return raw / 32.0

    @staticmethod
    def lean(raw: int) -> float:
        """
        Convert raw lean angle to degrees.

        The raw value 9000 represents upright (0 degrees). Values above 9000
        indicate lean angle magnitude after deadband and rounding are applied.

        Args:
            raw: Processed lean value from CAN 0x0258 (after decode_lean algorithm).

        Returns:
            Lean angle in degrees. 0.0 = upright, positive = leaning.

        Example:
            >>> Calibration.lean(9000)
            0.0
            >>> Calibration.lean(12000)
            30.0
        """
        return (raw / 100.0) - 90.0

    @staticmethod
    def pitch(raw: int) -> float:
        """
        Convert raw pitch rate to degrees per second.

        Args:
            raw: Raw 16-bit value from CAN 0x0258 bytes 6-7 (big-endian).

        Returns:
            Pitch rate in deg/s. 0.0 = level, positive = nose up.

        Example:
            >>> Calibration.pitch(30000)
            0.0
        """
        return (raw / 100.0) - 300.0

    @staticmethod
    def acceleration(raw: int) -> float:
        """
        Convert raw acceleration to G-force.

        Args:
            raw: Raw 16-bit value from CAN 0x0250 (big-endian).

        Returns:
            Acceleration in G. 0.0 = no acceleration.

        Example:
            >>> Calibration.acceleration(7000)
            0.0
            >>> Calibration.acceleration(8000)
            1.0
        """
        return (raw / 1000.0) - 7.0

    @staticmethod
    def temperature(raw: int) -> float:
        """
        Convert raw temperature to Celsius.

        Works for both water temperature and intake air temperature
        from CAN 0x023E.

        Args:
            raw: Raw 8-bit value from CAN 0x023E byte 0 or 1.

        Returns:
            Temperature in degrees Celsius.

        Example:
            >>> Calibration.temperature(176)
            80.0
        """
        return (raw / 1.6) - 30.0

    @staticmethod
    def fuel(raw: int) -> float:
        """
        Convert raw fuel consumption to cubic centimeters.

        Args:
            raw: Accumulated fuel value (sum of deltas from CAN 0x023E).

        Returns:
            Fuel consumption in cc.

        Example:
            >>> Calibration.fuel(10000)
            100.0
        """
        return raw / 100.0

    @staticmethod
    def gps_speed_kmh(knots: float) -> float:
        """
        Convert GPS speed from knots to km/h.

        Args:
            knots: Speed in nautical miles per hour (from GPRMC sentence).

        Returns:
            Speed in km/h.

        Example:
            >>> Calibration.gps_speed_kmh(54.0)
            100.008
        """
        return knots * 1.852


# =============================================================================
# LAP DETECTION
# =============================================================================

@dataclass
class FinishLine:
    """
    Represents a finish line defined by two GPS coordinates.

    The finish line is a line segment between two points (P1 and P2) that
    defines the start/finish line on the track. Lap detection works by
    checking if the motorcycle's trajectory crosses this line segment.

    Attributes:
        p1_lat: Latitude of point 1 in decimal degrees.
        p1_lng: Longitude of point 1 in decimal degrees.
        p2_lat: Latitude of point 2 in decimal degrees.
        p2_lng: Longitude of point 2 in decimal degrees.

    Note:
        The coordinates are stored in the CTRK file header as RECORDLINE
        entries. If no RECORDLINE entries exist, lap detection is disabled.
    """
    p1_lat: float
    p1_lng: float
    p2_lat: float
    p2_lng: float

    def side_of_line(self, lat: float, lng: float) -> float:
        """
        Determine which side of the finish line a point is on.

        Uses the cross product of vectors to compute signed distance from
        the line. The sign indicates which side of the line the point is on.

        Args:
            lat: Latitude of the point in decimal degrees.
            lng: Longitude of the point in decimal degrees.

        Returns:
            Signed value indicating side of line:
            - Positive: point is on one side
            - Negative: point is on the other side
            - Zero: point is exactly on the line
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
        Check if a trajectory segment crosses the finish line.

        Determines if the line segment from (lat1, lng1) to (lat2, lng2)
        intersects with the finish line segment from P1 to P2.

        Args:
            lat1: Starting latitude in decimal degrees.
            lng1: Starting longitude in decimal degrees.
            lat2: Ending latitude in decimal degrees.
            lng2: Ending longitude in decimal degrees.

        Returns:
            True if the trajectory crosses the finish line, False otherwise.

        Note:
            This method uses a two-step algorithm:
            1. Side-of-line test to check if endpoints are on opposite sides
            2. Parametric intersection to verify crossing is within segment bounds
        """
        side1 = self.side_of_line(lat1, lng1)
        side2 = self.side_of_line(lat2, lng2)

        # Sign change means potential crossing
        if side1 * side2 >= 0:
            return False

        # Check if the crossing point is within the finish line segment
        # Using parametric intersection
        dx1 = self.p2_lng - self.p1_lng
        dy1 = self.p2_lat - self.p1_lat
        dx2 = lng2 - lng1
        dy2 = lat2 - lat1

        denom = dx1 * dy2 - dy1 * dx2
        if abs(denom) < 1e-12:
            return False  # Parallel lines

        t = ((lng1 - self.p1_lng) * dy2 - (lat1 - self.p1_lat) * dx2) / denom

        # t should be between 0 and 1 for crossing to be on the finish line segment
        return 0 <= t <= 1


def parse_finish_line(data: bytes) -> Optional[FinishLine]:
    """
    Extract finish line coordinates from CTRK file header.

    Searches for RECORDLINE.P1.LAT, P1.LNG, P2.LAT, and P2.LNG entries
    in the header and parses their double-precision floating point values.

    Args:
        data: Raw bytes from the CTRK file header (first ~500 bytes).

    Returns:
        FinishLine object with parsed coordinates, or None if coordinates
        are not found or cannot be parsed.

    Note:
        The RECORDLINE values are stored as: `(` prefix byte followed by
        8 bytes of IEEE 754 double-precision float (little-endian).
    """
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
# CAN MESSAGE HANDLERS
# =============================================================================

def parse_can_0x0209(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0209: Engine RPM and Gear.

    Extracts RPM from bytes 0-1 (big-endian uint16) and gear from byte 4
    (lower 3 bits). Gear value 7 is rejected as invalid (gear transition).

    Args:
        data: CAN payload bytes (minimum 5 bytes required).
        state: Mutable state dictionary to update with parsed values.

    Note:
        Verified against native library at address 0x0000e14b.
    """
    state['rpm'] = (data[0] << 8) | data[1]
    gear = data[4] & 0x07
    if gear != 7:  # 7 = invalid (transitioning)
        state['gear'] = gear


def parse_can_0x0215(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0215: Throttle and Electronic Controls.

    Extracts:
    - TPS (Throttle Position Sensor) from bytes 0-1
    - APS (Accelerator Position Sensor) from bytes 2-3
    - Launch control status from byte 6 bits 5-6
    - TCS, SCS, LIF status from byte 7 bits 3-5

    Args:
        data: CAN payload bytes (minimum 8 bytes required).
        state: Mutable state dictionary to update with parsed values.

    Note:
        Verified against native library at address 0x0000e170.
    """
    state['tps'] = (data[0] << 8) | data[1]
    state['aps'] = (data[2] << 8) | data[3]
    state['launch'] = 1 if (data[6] & 0x60) else 0
    state['tcs'] = (data[7] >> 5) & 1
    state['scs'] = (data[7] >> 4) & 1
    state['lif'] = (data[7] >> 3) & 1


def parse_can_0x023e(data: bytes, state: dict, fuel_acc: list) -> None:
    """
    Parse CAN message 0x023E: Temperature and Fuel.

    Extracts:
    - Water temperature from byte 0 (single byte, NOT uint16)
    - Intake air temperature from byte 1 (single byte)
    - Fuel consumption delta from bytes 2-3 (big-endian uint16)

    The fuel value is a delta that must be accumulated. The fuel_acc list
    is used as a mutable container to maintain the accumulator across calls.

    Args:
        data: CAN payload bytes (minimum 4 bytes required).
        state: Mutable state dictionary to update with parsed values.
        fuel_acc: Single-element list containing the fuel accumulator [value].

    Note:
        Verified against native library at address 0x0000e292.
        Temperature uses single bytes, not 16-bit values.
    """
    state['water_temp'] = data[0]  # Single byte
    state['intake_temp'] = data[1]  # Single byte
    fuel_delta = (data[2] << 8) | data[3]
    fuel_acc[0] += fuel_delta
    state['fuel'] = fuel_acc[0]


def parse_can_0x0250(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0250: Acceleration.

    Extracts longitudinal (X) and lateral (Y) acceleration from bytes 0-3.
    Both values are big-endian uint16.

    Args:
        data: CAN payload bytes (minimum 4 bytes required).
        state: Mutable state dictionary to update with parsed values.

    Note:
        Verified against native library at address 0x0000e0be.
        This is acceleration data, NOT lean/pitch (those are in 0x0258).
    """
    state['acc_x'] = (data[0] << 8) | data[1]
    state['acc_y'] = (data[2] << 8) | data[3]


def parse_can_0x0258(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0258: IMU (Lean and Pitch).

    Extracts:
    - Lean angle from bytes 0-3 using special packed format with deadband
    - Pitch rate from bytes 6-7 (big-endian uint16)

    The lean angle uses a complex algorithm with:
    1. Nibble interleaving across bytes 0-3
    2. Deviation from center (9000 = upright)
    3. Deadband: deviations <= 499 treated as upright
    4. Truncation to nearest 100 (floor, not round)

    Args:
        data: CAN payload bytes (minimum 8 bytes required).
        state: Mutable state dictionary to update with parsed values.
            Updates 'lean' (absolute) and 'lean_signed' (with direction).

    Note:
        Verified against native library at addresses 0x0000e1bc-0x0000e32e.
    """
    b0, b1, b2, b3 = data[0], data[1], data[2], data[3]

    # Extract packed values from interleaved nibbles
    val1_part = (b0 << 4) | (b2 & 0x0f)
    val1 = val1_part << 8
    val2 = ((b1 & 0x0f) << 4) | (b3 >> 4)
    sum_val = (val1 + val2) & 0xFFFF

    # Transform to deviation from center (9000 = upright)
    if sum_val < 9000:
        deviation = 9000 - sum_val
    else:
        deviation = (sum_val - 9000) & 0xFFFF

    # Apply deadband (~5 degrees)
    if deviation <= 499:
        state['lean'] = 9000  # Upright
        state['lean_signed'] = 9000
    else:
        # Truncate to nearest 100 (degree resolution)
        deviation_rounded = deviation - (deviation % 100)
        state['lean'] = (9000 + deviation_rounded) & 0xFFFF
        # Signed: preserve direction (sum_val < 9000 = negative lean)
        if sum_val < 9000:
            state['lean_signed'] = 9000 - deviation_rounded
        else:
            state['lean_signed'] = 9000 + deviation_rounded

    # Pitch is straightforward
    state['pitch'] = (data[6] << 8) | data[7]


def parse_can_0x0260(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0260: Brake Pressure.

    Extracts front and rear brake hydraulic pressure from bytes 0-3.
    Both values are big-endian uint16.

    Args:
        data: CAN payload bytes (minimum 4 bytes required).
        state: Mutable state dictionary to update with parsed values.

    Note:
        Verified against native library at address 0x0000e226.
    """
    state['front_brake'] = (data[0] << 8) | data[1]
    state['rear_brake'] = (data[2] << 8) | data[3]


def parse_can_0x0264(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0264: Wheel Speed.

    Extracts front and rear wheel speed from bytes 0-3.
    Both values are big-endian uint16.

    Args:
        data: CAN payload bytes (minimum 4 bytes required).
        state: Mutable state dictionary to update with parsed values.

    Note:
        Verified against native library at address 0x0000e07a.
    """
    state['front_speed'] = (data[0] << 8) | data[1]
    state['rear_speed'] = (data[2] << 8) | data[3]


def parse_can_0x0268(data: bytes, state: dict) -> None:
    """
    Parse CAN message 0x0268: ABS Status.

    Extracts front and rear ABS active flags from byte 4.
    R_ABS is bit 0, F_ABS is bit 1 (counterintuitive order).

    Args:
        data: CAN payload bytes (minimum 5 bytes required).
        state: Mutable state dictionary to update with parsed values.

    Note:
        Verified against native library at address 0x0000e2b7.
        Bit order is R_ABS=bit0, F_ABS=bit1 (not the other way around).
    """
    state['r_abs'] = bool(data[4] & 1)
    state['f_abs'] = bool((data[4] >> 1) & 1)


# CAN handler dispatch table
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
    """
    A single telemetry sample containing all channel values.

    This dataclass holds raw (uncalibrated) sensor values for a single
    point in time. Use the Calibration class methods to convert raw
    values to engineering units.

    Attributes:
        lap: Current lap number (1-based, increments at finish line crossing).
        time_ms: Unix timestamp in milliseconds (UTC).
        latitude: GPS latitude in decimal degrees (9999.0 = no fix).
        longitude: GPS longitude in decimal degrees (9999.0 = no fix).
        gps_speed_knots: GPS ground speed in knots.
        rpm: Raw engine RPM value.
        gear: Gear position (0=neutral, 1-6).
        aps: Raw accelerator position sensor value.
        tps: Raw throttle position sensor value.
        water_temp: Raw coolant temperature value.
        intake_temp: Raw intake air temperature value.
        front_speed: Raw front wheel speed value.
        rear_speed: Raw rear wheel speed value.
        fuel: Raw cumulative fuel consumption value.
        lean: Raw lean angle (absolute, always >= 9000 after processing).
        lean_signed: Raw lean angle with direction preserved.
        pitch: Raw pitch rate value.
        acc_x: Raw longitudinal acceleration value.
        acc_y: Raw lateral acceleration value.
        front_brake: Raw front brake pressure value.
        rear_brake: Raw rear brake pressure value.
        f_abs: Front ABS active flag.
        r_abs: Rear ABS active flag.
        tcs: Traction Control System active (0 or 1).
        scs: Slide Control System active (0 or 1).
        lif: Lift Control active (0 or 1).
        launch: Launch Control active (0 or 1).
    """
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
    """
    Parser for Yamaha Y-Trac CTRK telemetry files.

    This class implements a complete CTRK file parser based on reverse engineering
    of the native library (libSensorsRecordIF.so). It handles:

    - Binary file structure parsing (header, data section, footer)
    - Timestamp computation with incremental optimization
    - CAN message decoding for all 21 telemetry channels
    - GPS NMEA sentence parsing with checksum validation
    - 10 Hz emission timing with GPS gating
    - Lap detection via finish line crossing

    Attributes:
        filepath: Path to the CTRK file being parsed.
        native_mode: If True, use per-lap processing matching native library.
        records: List of parsed TelemetryRecord objects (populated after parse()).

    Example:
        >>> parser = CTRKParser("session.CTRK")
        >>> records = parser.parse()
        >>> print(f"Parsed {len(records)} records")
        >>> parser.export_csv("session.csv")

    Note:
        The parser achieves 94.9% match rate against native library output
        across 22 channels and 420,000+ records. See docs/COMPARISON.md for
        detailed validation results.
    """

    MAGIC = b'HEAD'

    def __init__(self, filepath: str, native_mode: bool = False):
        """
        Initialize the parser with a file path.

        Args:
            filepath: Path to the CTRK file to parse.
            native_mode: If True, process each lap independently with full state
                reset, matching native library behavior. This improves match rate
                for fuel_cc but produces physically impossible values at lap
                boundaries. Default is False for continuous state processing.
        """
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
        """
        Parse the CTRK file and extract telemetry records.

        Reads the entire file, validates the header, extracts finish line
        coordinates, and processes all data records to produce 10 Hz
        telemetry output.

        Returns:
            List of TelemetryRecord objects, one per 100ms emission interval.

        Raises:
            FileNotFoundError: If the CTRK file does not exist.
            ValueError: If the file does not have valid CTRK header magic.

        Note:
            This method populates self.records and also returns the list.
            Subsequent calls will re-parse the file from scratch.
        """
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
        Check if the motorcycle crossed the finish line.

        Compares current position against previous position to detect
        finish line crossing. On crossing, increments lap counter and
        resets fuel accumulator.

        Args:
            lat: Current latitude in decimal degrees.
            lng: Current longitude in decimal degrees.

        Returns:
            True if a new lap started (crossing detected), False otherwise.
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
        """
        Find the byte offset where the data section begins.

        The CTRK header contains variable-length entries starting at 0x34.
        This method iterates through those entries to find where they end
        and the data records begin.

        Returns:
            Byte offset of the first data record (typically ~0xCB).
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
        """
        Convert 10-byte timestamp structure to Unix epoch milliseconds.

        Matches the native GetTimeData function behavior. Parses calendar
        fields from the timestamp bytes and converts to epoch time.

        Args:
            ts_bytes: 10-byte timestamp from record header.
                Format: [millis(2LE)][sec][min][hour][wday][day][month][year(2LE)]

        Returns:
            Unix timestamp in milliseconds (UTC).
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
        """
        Validate NMEA sentence XOR checksum.

        Computes XOR of all bytes between '$' and '*', then compares
        with the stated 2-digit hex checksum after '*'.

        Args:
            sentence: Complete NMEA sentence string including $ and *XX.

        Returns:
            True if checksum is valid, False otherwise.
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
        """
        Parse NMEA GPRMC sentence for GPS position and speed.

        Extracts latitude, longitude, and ground speed from a valid
        GPRMC sentence. Only processes sentences with status 'A' (active fix).

        Args:
            sentence: GPRMC sentence string (comma-separated fields).

        Returns:
            Dictionary with 'latitude', 'longitude', 'speed_knots' keys,
            or None if the sentence cannot be parsed or has void status.

        Note:
            Timestamps are NOT extracted from GPRMC - they come from the
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
        """
        Create a TelemetryRecord from current accumulated CAN state.

        Snapshots the current state dictionary into a new TelemetryRecord
        object with the provided GPS data and timestamp.

        Args:
            time_ms: Unix timestamp in milliseconds.
            lat: GPS latitude in decimal degrees.
            lon: GPS longitude in decimal degrees.
            speed_knots: GPS ground speed in knots.

        Returns:
            New TelemetryRecord with all current channel values.
        """
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

    def _parse_data_section(self) -> None:
        """
        Parse the data section using continuous state processing.

        Iterates through all records in the data section, updating CAN state
        and emitting telemetry records at 100ms intervals. State is carried
        forward continuously across laps (unlike native_mode which resets).

        This method implements the main parsing loop with:
        - Incremental timestamp computation (GetTimeDataEx algorithm)
        - GPS gating (emission only after first GPRMC)
        - 100ms emission interval
        - Lap detection via finish line crossing
        - Emission clock reset at type-5 lap markers

        Note:
            Results are stored in self.records.
        """
        data_start = self._find_data_start()
        pos = data_start

        # GetTimeDataEx state
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0

        # Emission state
        last_emitted_ms = None
        gps_count = 0
        can_count = 0
        checksum_failures = 0

        # GPS state (sentinel 9999.0 matches native)
        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

        while pos + 14 <= len(self.data):
            # Read 14-byte record header
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]

            # End-of-data detection
            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

            # Timestamp computation (GetTimeDataEx algorithm)
            if prev_ts_bytes is None or ts_bytes != prev_ts_bytes:
                if prev_ts_bytes is None:
                    current_epoch_ms = self._get_time_data(ts_bytes)
                elif ts_bytes[2:10] == prev_ts_bytes[2:10]:
                    # Same second: incremental millis update
                    prev_millis = prev_ts_bytes[0] | (prev_ts_bytes[1] << 8)
                    curr_millis = ts_bytes[0] | (ts_bytes[1] << 8)
                    current_epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)
                    # Handle millis wrapping (hardware edge case)
                    if curr_millis < prev_millis:
                        current_epoch_ms += 1000
                else:
                    # Different second: full recomputation
                    current_epoch_ms = self._get_time_data(ts_bytes)

                prev_epoch_ms = current_epoch_ms
                prev_ts_bytes = ts_bytes

            # Initialize emission clock at first record
            if last_emitted_ms is None:
                last_emitted_ms = current_epoch_ms

            # Process payload by record type
            if rec_type == 1 and len(payload) >= 5:
                # CAN record
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
                            current_lat = gps_data['latitude']
                            current_lon = gps_data['longitude']
                            current_speed_knots = gps_data['speed_knots']
                        # Emit initial record at first GPRMC
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
                # Lap marker: re-align emission clock
                last_emitted_ms = current_epoch_ms

            # Emission check (100ms interval)
            if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                self._check_lap_crossing(current_lat, current_lon)
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon,
                    current_speed_knots)
                self.records.append(record)
                gps_count += 1
                last_emitted_ms = current_epoch_ms

            pos += total_size

        # Final record emission
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
        """
        Scan data section for type-5 Lap marker record positions.

        Used by native_mode to partition data into per-lap segments
        before processing.

        Returns:
            List of byte offsets where type-5 records start.
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

    def _parse_perlap(self) -> None:
        """
        Parse using per-lap processing mode (native-compatible).

        Processes each lap independently with full state reset, matching
        the native library's behavior where GetSensorsRecordData is called
        once per lap with memset(0) at entry.

        This mode produces higher match rate for fuel_cc but generates
        physically impossible values at lap boundaries due to state reset.

        Note:
            Results are stored in self.records.
        """
        data_start = self._find_data_start()
        data_end = len(self.data)
        type5_offsets = self._scan_lap_boundaries()

        # Build lap ranges: [(start_offset, end_offset), ...]
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

    def _parse_lap_range(self, start: int, end: int, lap_number: int) -> None:
        """
        Process records in a single lap range with full state reset.

        Matches native GetSensorsRecordData behavior for a single lap:
        memset(state, 0, 0x2c8) and memset(aux, 0, 0x2e0) at entry.

        Args:
            start: Byte offset of first record in this lap.
            end: Byte offset past the last record in this lap.
            lap_number: Lap number to assign to emitted records.
        """
        # Full state reset (matching native memset)
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

        # Auxiliary state reset
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0
        last_emitted_ms = None

        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

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

            # Timestamp computation
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

            # Payload processing
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

            # Emission check
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

    def export_csv(self, output_path: str) -> None:
        """
        Export parsed records to CSV with calibrated values.

        Writes all telemetry records to a CSV file with engineering units
        (RPM, km/h, degrees, etc.) matching the native library output format.

        Args:
            output_path: Path for the output CSV file.

        Note:
            Records must be parsed first via parse() method.
        """
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

    def export_raw_csv(self, output_path: str) -> None:
        """
        Export parsed records to CSV with raw (uncalibrated) values.

        Writes all telemetry records with raw integer sensor values,
        useful for debugging and comparison with native library internals.

        Args:
            output_path: Path for the output CSV file.

        Note:
            Records must be parsed first via parse() method.
        """
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
    """
    Command-line entry point for standalone parser execution.

    Usage:
        python ctrk_parser.py <input.CTRK> [output.csv]

    If output.csv is not specified, creates <input>_parsed.csv and
    <input>_parsed_raw.csv in the same directory as the input file.
    """
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
