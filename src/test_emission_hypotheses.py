#!/usr/bin/env python3
"""
Test emission timestamp initialization hypotheses.

Investigates why the Python parser's emission clock starts 10-90ms ahead
of the native library, causing a systematic one-CAN-update shift for
fast-changing channels like RPM.

Phase 1 (Quick Tests):
  - Offset distribution across all file pairs
  - Truncation correlation (python_first_ms % 100 vs offset)
  - GPRMC gap (first record vs first GPS record in binary)

Phase 2 (Hypothesis Testing):
  - Re-parse CTRK files with modified initialization
  - Compare RPM match rate vs native for each hypothesis

Usage:
    python3 src/test_emission_hypotheses.py output/full_comparison/
"""

import csv
import struct
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ─── Helpers ────────────────────────────────────────────────────────────────

def load_csv_rows(path: Path) -> List[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def get_first_time_ms(path: Path) -> Optional[int]:
    """Read the first time_ms value from a CSV."""
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            return int(row['time_ms'])
    return None


def pos_match(row1: dict, row2: dict, epsilon: float = 0.000005) -> bool:
    lat1, lon1 = float(row1['latitude']), float(row1['longitude'])
    lat2, lon2 = float(row2['latitude']), float(row2['longitude'])
    return abs(lat1 - lat2) < epsilon and abs(lon1 - lon2) < epsilon


def align_records(rows_a: List[dict], rows_b: List[dict]) -> List[Tuple[dict, dict]]:
    """Align two record lists by GPS position. Returns (a_row, b_row) pairs."""
    aligned = []
    ai, bi = 0, 0
    while ai < len(rows_a) and bi < len(rows_b):
        if pos_match(rows_a[ai], rows_b[bi]):
            aligned.append((rows_a[ai], rows_b[bi]))
            ai += 1
            bi += 1
        else:
            found = False
            for look in range(1, 4):
                if ai + look < len(rows_a) and pos_match(rows_a[ai + look], rows_b[bi]):
                    ai += look
                    found = True
                    break
            if found:
                continue
            for look in range(1, 4):
                if bi + look < len(rows_b) and pos_match(rows_b[bi + look], rows_a[ai]):
                    bi += look
                    found = True
                    break
            if found:
                continue
            pts = int(rows_a[ai].get('time_ms', 0))
            nts = int(rows_b[bi].get('time_ms', 0))
            if pts <= nts:
                ai += 1
            else:
                bi += 1
    return aligned


def rpm_match_rate(aligned: List[Tuple[dict, dict]], tolerance: float = 2.0) -> float:
    """Compute RPM match rate for aligned record pairs."""
    if not aligned:
        return 0.0
    matches = 0
    for a_row, b_row in aligned:
        try:
            a_rpm = float(a_row['rpm'])
            b_rpm = float(b_row['rpm'])
            if abs(a_rpm - b_rpm) <= tolerance:
                matches += 1
        except (ValueError, KeyError):
            pass
    return 100.0 * matches / len(aligned)


def overall_match_rate(aligned: List[Tuple[dict, dict]]) -> float:
    """Compute overall match rate across all numeric channels."""
    tolerances = {
        'rpm': 2, 'throttle_grip': 0.5, 'throttle': 0.5,
        'front_speed_kmh': 0.5, 'rear_speed_kmh': 0.5, 'gear': 0,
        'acc_x_g': 0.02, 'acc_y_g': 0.02, 'lean_deg': 0.5,
        'pitch_deg_s': 0.5, 'water_temp': 0.5, 'intake_temp': 0.5,
        'fuel_cc': 0.05, 'front_brake_bar': 0.1, 'rear_brake_bar': 0.1,
        'gps_speed_kmh': 0.5,
    }
    bool_channels = {'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch'}
    total_matches = 0
    total_compared = 0
    for a_row, b_row in aligned:
        for ch, tol in tolerances.items():
            try:
                diff = abs(float(a_row[ch]) - float(b_row[ch]))
                total_compared += 1
                if diff <= tol:
                    total_matches += 1
            except (ValueError, KeyError):
                pass
        for ch in bool_channels:
            try:
                total_compared += 1
                if str(a_row[ch]).lower() == str(b_row[ch]).lower():
                    total_matches += 1
            except KeyError:
                pass
    return 100.0 * total_matches / total_compared if total_compared > 0 else 0.0


# ─── Binary CTRK inspection ────────────────────────────────────────────────

def ts_bytes_to_epoch_ms(ts_bytes: bytes) -> int:
    """Convert 10-byte timestamp to epoch ms (matching _get_time_data)."""
    millis = ts_bytes[0] | (ts_bytes[1] << 8)
    sec = ts_bytes[2]
    min_ = ts_bytes[3]
    hour = ts_bytes[4]
    day = ts_bytes[6]
    month = ts_bytes[7]
    year = ts_bytes[8] | (ts_bytes[9] << 8)
    dt = datetime(year, month, day, hour, min_, sec)
    return int(dt.timestamp() * 1000) + millis


def find_data_start(data: bytes) -> int:
    """Find where structured data begins (matching CTRKParser._find_data_start)."""
    off = 0x34
    while off < min(len(data), 500):
        if off + 4 > len(data):
            break
        entry_size = struct.unpack_from('<I', data, off)[0]
        if entry_size < 5 or entry_size > 200:
            break
        name_len = data[off + 4]
        if name_len < 1 or name_len > entry_size - 5:
            break
        off += entry_size
    return off


def validate_nmea_checksum(sentence: str) -> bool:
    star_idx = sentence.find('*')
    if star_idx < 1 or star_idx + 3 > len(sentence):
        return False
    computed = 0
    for ch in sentence[1:star_idx]:
        computed ^= ord(ch)
    try:
        expected = int(sentence[star_idx + 1:star_idx + 3], 16)
        return computed == expected
    except ValueError:
        return False


def inspect_ctrk_binary(filepath: Path) -> dict:
    """Extract timing info from a CTRK binary file.

    Returns:
        first_record_ms: timestamp of the very first record (any type)
        first_gps_record_ms: timestamp of the first type-2 record
        first_gprmc_ms: timestamp of the first valid GPRMC type-2 record
        gprmc_utc_str: the UTC time string from the first GPRMC sentence
        gprmc_utc_epoch_ms: epoch ms derived from the GPRMC UTC field
        first_record_type: type of the very first record
    """
    with open(filepath, 'rb') as f:
        data = f.read()

    if not data.startswith(b'HEAD'):
        return {}

    data_start = find_data_start(data)
    pos = data_start

    result = {
        'first_record_ms': None,
        'first_record_type': None,
        'first_gps_record_ms': None,
        'first_gprmc_ms': None,
        'gprmc_utc_str': None,
        'gprmc_utc_epoch_ms': None,
        'gprmc_date_str': None,
    }

    while pos + 14 <= len(data):
        rec_type = struct.unpack_from('<H', data, pos)[0]
        total_size = struct.unpack_from('<H', data, pos + 2)[0]

        if rec_type == 0 and total_size == 0:
            break
        if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
            break
        if pos + total_size > len(data):
            break

        ts_bytes = data[pos + 4:pos + 14]
        epoch_ms = ts_bytes_to_epoch_ms(ts_bytes)

        if result['first_record_ms'] is None:
            result['first_record_ms'] = epoch_ms
            result['first_record_type'] = rec_type

        if rec_type == 2:
            if result['first_gps_record_ms'] is None:
                result['first_gps_record_ms'] = epoch_ms

            payload = data[pos + 14:pos + total_size]
            if len(payload) > 6:
                sentence = payload.decode('ascii', errors='replace').rstrip('\r\n\x00')
                if sentence.startswith('$GPRMC') and validate_nmea_checksum(sentence):
                    if result['first_gprmc_ms'] is None:
                        result['first_gprmc_ms'] = epoch_ms
                        # Extract UTC time from GPRMC sentence
                        parts = sentence.split(',')
                        if len(parts) >= 10:
                            utc_str = parts[1]  # HHMMSS.sss
                            date_str = parts[9]  # DDMMYY
                            result['gprmc_utc_str'] = utc_str
                            result['gprmc_date_str'] = date_str
                            # Parse into epoch ms
                            try:
                                hh = int(utc_str[0:2])
                                mm = int(utc_str[2:4])
                                ss = int(utc_str[4:6])
                                frac = utc_str[6:]  # ".sss"
                                millis = int(float(frac) * 1000) if frac else 0
                                dd = int(date_str[0:2])
                                mo = int(date_str[2:4])
                                yy = int(date_str[4:6]) + 2000
                                dt = datetime(yy, mo, dd, hh, mm, ss)
                                result['gprmc_utc_epoch_ms'] = int(dt.timestamp() * 1000) + millis
                            except (ValueError, IndexError):
                                pass

        # Once we have all the data we need, stop
        if (result['first_record_ms'] is not None and
                result['first_gprmc_ms'] is not None and
                result['gprmc_utc_epoch_ms'] is not None):
            break

        pos += total_size

    return result


# ─── Phase 2: Re-parse with hypothesis variants ────────────────────────────

# Import the actual parser to subclass it
sys.path.insert(0, str(Path(__file__).parent))
from ctrk_parser import CTRKParser


class BaselineParser(CTRKParser):
    """Current behavior: last_emitted_ms = current_epoch_ms on first record."""
    pass


class TruncateParser(CTRKParser):
    """H-A: Truncate first emission to 100ms floor."""

    def _parse_data_section(self):
        """Override to truncate last_emitted_ms initialization."""
        data_start = self._find_data_start()
        pos = data_start
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0
        last_emitted_ms = None
        gps_count = 0
        can_count = 0
        checksum_failures = 0
        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

        while pos + 14 <= len(self.data):
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]
            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

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

            # === HYPOTHESIS A: Truncate to 100ms boundary ===
            if last_emitted_ms is None:
                last_emitted_ms = (current_epoch_ms // 100) * 100

            if rec_type == 1 and len(payload) >= 5:
                can_id = struct.unpack_from('<H', payload, 0)[0]
                can_data = payload[5:]
                from ctrk_parser import CAN_HANDLERS, parse_can_0x023e
                if can_id == 0x023E and len(can_data) >= 4:
                    parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                elif can_id in CAN_HANDLERS:
                    CAN_HANDLERS[can_id](can_data, self._state)
                can_count += 1

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
                            self._check_lap_crossing(current_lat, current_lon)
                            record = self._create_record(
                                last_emitted_ms, current_lat, current_lon, current_speed_knots)
                            self.records.append(record)
                            gps_count += 1
                    else:
                        checksum_failures += 1

            if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                self._check_lap_crossing(current_lat, current_lon)
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon, current_speed_knots)
                self.records.append(record)
                gps_count += 1
                last_emitted_ms = current_epoch_ms

            pos += total_size

        if has_gprmc and last_emitted_ms is not None:
            self._check_lap_crossing(current_lat, current_lon)
            record = self._create_record(
                current_epoch_ms, current_lat, current_lon, current_speed_knots)
            self.records.append(record)


class FirstGPRMCParser(CTRKParser):
    """H-B: Initialize emission clock from first GPRMC record only."""

    def _parse_data_section(self):
        data_start = self._find_data_start()
        pos = data_start
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0
        last_emitted_ms = None
        gps_count = 0
        can_count = 0
        checksum_failures = 0
        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

        while pos + 14 <= len(self.data):
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]
            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

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

            # === HYPOTHESIS B: Only init from GPRMC records ===
            # (don't set last_emitted_ms from CAN records)

            if rec_type == 1 and len(payload) >= 5:
                can_id = struct.unpack_from('<H', payload, 0)[0]
                can_data = payload[5:]
                from ctrk_parser import CAN_HANDLERS, parse_can_0x023e
                if can_id == 0x023E and len(can_data) >= 4:
                    parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                elif can_id in CAN_HANDLERS:
                    CAN_HANDLERS[can_id](can_data, self._state)
                can_count += 1

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
                            # Init emission clock HERE (at first GPRMC)
                            if last_emitted_ms is None:
                                last_emitted_ms = current_epoch_ms
                            self._check_lap_crossing(current_lat, current_lon)
                            record = self._create_record(
                                last_emitted_ms, current_lat, current_lon, current_speed_knots)
                            self.records.append(record)
                            gps_count += 1
                    else:
                        checksum_failures += 1

            if has_gprmc and last_emitted_ms is not None and current_epoch_ms - last_emitted_ms >= 100:
                self._check_lap_crossing(current_lat, current_lon)
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon, current_speed_knots)
                self.records.append(record)
                gps_count += 1
                last_emitted_ms = current_epoch_ms

            pos += total_size

        if has_gprmc and last_emitted_ms is not None:
            self._check_lap_crossing(current_lat, current_lon)
            record = self._create_record(
                current_epoch_ms, current_lat, current_lon, current_speed_knots)
            self.records.append(record)


class GPRMCTimeParser(CTRKParser):
    """H-C: Use GPRMC embedded UTC time for emission clock init."""

    def _parse_data_section(self):
        data_start = self._find_data_start()
        pos = data_start
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0
        last_emitted_ms = None
        gps_count = 0
        can_count = 0
        checksum_failures = 0
        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

        while pos + 14 <= len(self.data):
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]
            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

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

            if rec_type == 1 and len(payload) >= 5:
                can_id = struct.unpack_from('<H', payload, 0)[0]
                can_data = payload[5:]
                from ctrk_parser import CAN_HANDLERS, parse_can_0x023e
                if can_id == 0x023E and len(can_data) >= 4:
                    parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                elif can_id in CAN_HANDLERS:
                    CAN_HANDLERS[can_id](can_data, self._state)
                can_count += 1

            elif rec_type == 2 and len(payload) > 6:
                sentence = payload.decode('ascii', errors='replace').rstrip('\r\n\x00')
                if sentence.startswith('$GPRMC'):
                    if self._validate_nmea_checksum(sentence):
                        gps_data = self._parse_gprmc_sentence(sentence)
                        if gps_data:
                            current_lat = gps_data['latitude']
                            current_lon = gps_data['longitude']
                            current_speed_knots = gps_data['speed_knots']

                        # === HYPOTHESIS C: Use GPRMC UTC time for init ===
                        if not has_gprmc:
                            has_gprmc = True
                            parts = sentence.split(',')
                            if len(parts) >= 10:
                                try:
                                    utc_str = parts[1]
                                    date_str = parts[9]
                                    hh = int(utc_str[0:2])
                                    mm = int(utc_str[2:4])
                                    ss = int(utc_str[4:6])
                                    frac = utc_str[6:]
                                    millis = int(float(frac) * 1000) if frac else 0
                                    dd = int(date_str[0:2])
                                    mo = int(date_str[2:4])
                                    yy = int(date_str[4:6]) + 2000
                                    dt = datetime(yy, mo, dd, hh, mm, ss)
                                    last_emitted_ms = int(dt.timestamp() * 1000) + millis
                                except (ValueError, IndexError):
                                    pass
                            self._check_lap_crossing(current_lat, current_lon)
                            record = self._create_record(
                                last_emitted_ms, current_lat, current_lon, current_speed_knots)
                            self.records.append(record)
                            gps_count += 1
                    else:
                        checksum_failures += 1

            if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                self._check_lap_crossing(current_lat, current_lon)
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon, current_speed_knots)
                self.records.append(record)
                gps_count += 1
                last_emitted_ms = current_epoch_ms

            pos += total_size

        if has_gprmc and last_emitted_ms is not None:
            self._check_lap_crossing(current_lat, current_lon)
            record = self._create_record(
                current_epoch_ms, current_lat, current_lon, current_speed_knots)
            self.records.append(record)


class TruncateEventParser(CTRKParser):
    """H-E: Truncate initial + event-driven after."""

    def _parse_data_section(self):
        data_start = self._find_data_start()
        pos = data_start
        prev_ts_bytes = None
        prev_epoch_ms = 0
        current_epoch_ms = 0
        last_emitted_ms = None
        gps_count = 0
        can_count = 0
        checksum_failures = 0
        current_lat = 9999.0
        current_lon = 9999.0
        current_speed_knots = 0.0
        has_gprmc = False

        while pos + 14 <= len(self.data):
            rec_type = struct.unpack_from('<H', self.data, pos)[0]
            total_size = struct.unpack_from('<H', self.data, pos + 2)[0]
            if rec_type == 0 and total_size == 0:
                break
            if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                break
            if pos + total_size > len(self.data):
                break

            ts_bytes = self.data[pos + 4:pos + 14]
            payload = self.data[pos + 14:pos + total_size]

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

            # === HYPOTHESIS E: Truncate initial, event-driven after ===
            if last_emitted_ms is None:
                last_emitted_ms = (current_epoch_ms // 100) * 100

            if rec_type == 1 and len(payload) >= 5:
                can_id = struct.unpack_from('<H', payload, 0)[0]
                can_data = payload[5:]
                from ctrk_parser import CAN_HANDLERS, parse_can_0x023e
                if can_id == 0x023E and len(can_data) >= 4:
                    parse_can_0x023e(can_data, self._state, self._fuel_accumulator)
                elif can_id in CAN_HANDLERS:
                    CAN_HANDLERS[can_id](can_data, self._state)
                can_count += 1

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
                            self._check_lap_crossing(current_lat, current_lon)
                            record = self._create_record(
                                last_emitted_ms, current_lat, current_lon, current_speed_knots)
                            self.records.append(record)
                            gps_count += 1
                    else:
                        checksum_failures += 1

            # Event-driven after initial (= current_epoch_ms, not += 100)
            if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                self._check_lap_crossing(current_lat, current_lon)
                record = self._create_record(
                    current_epoch_ms, current_lat, current_lon, current_speed_knots)
                self.records.append(record)
                gps_count += 1
                last_emitted_ms = current_epoch_ms

            pos += total_size

        if has_gprmc and last_emitted_ms is not None:
            self._check_lap_crossing(current_lat, current_lon)
            record = self._create_record(
                current_epoch_ms, current_lat, current_lon, current_speed_knots)
            self.records.append(record)


def records_to_dicts(records) -> List[dict]:
    """Convert TelemetryRecord list to list of dicts matching CSV export format."""
    from ctrk_parser import Calibration
    rows = []
    for r in records:
        rows.append({
            'lap': str(r.lap),
            'time_ms': str(r.time_ms),
            'latitude': f"{r.latitude:.6f}",
            'longitude': f"{r.longitude:.6f}",
            'gps_speed_kmh': f"{Calibration.gps_speed_kmh(r.gps_speed_knots):.2f}",
            'rpm': str(Calibration.rpm(r.rpm)),
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
            'gear': str(r.gear),
            'f_abs': str(r.f_abs).lower(),
            'r_abs': str(r.r_abs).lower(),
            'tcs': str(r.tcs),
            'scs': str(r.scs),
            'lif': str(r.lif),
            'launch': str(r.launch),
        })
    return rows


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 src/test_emission_hypotheses.py output/full_comparison/")
        sys.exit(1)

    comparison_dir = Path(sys.argv[1])
    input_dir = Path(__file__).parent.parent / 'input'

    # Find file pairs
    native_files = sorted(comparison_dir.glob('*_native.csv'))
    parsed_map = {}
    for f in comparison_dir.glob('*_parsed.csv'):
        basename = f.name.replace('_parsed.csv', '')
        parsed_map[basename] = f

    pairs = []
    for nf in native_files:
        basename = nf.name.replace('_native.csv', '')
        if basename in parsed_map:
            ctrk_path = input_dir / f"{basename}.CTRK"
            pairs.append((basename, parsed_map[basename], nf, ctrk_path))

    print(f"Found {len(pairs)} file pairs with native + parsed CSVs")
    print()

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1: Quick Tests
    # ═══════════════════════════════════════════════════════════════════════

    print("=" * 80)
    print("PHASE 1: QUICK TESTS")
    print("=" * 80)

    # ── Quick Test 1: Offset Distribution ──────────────────────────────────
    print("\n── Quick Test 1: First Emission Offset (Python - Native) ──")
    print(f"{'File':<25} {'Python ms':>15} {'Native ms':>15} {'Offset':>8} {'Py%100':>7}")
    print("-" * 75)

    offsets = []
    truncation_data = []

    for basename, parsed_path, native_path, ctrk_path in pairs:
        p_ms = get_first_time_ms(parsed_path)
        n_ms = get_first_time_ms(native_path)
        if p_ms is not None and n_ms is not None:
            offset = p_ms - n_ms
            py_mod = p_ms % 100
            offsets.append((basename, offset, py_mod, p_ms, n_ms))
            truncation_data.append((offset, py_mod))
            print(f"{basename:<25} {p_ms:>15} {n_ms:>15} {offset:>+8} {py_mod:>7}")

    print("-" * 75)
    if offsets:
        off_vals = [o[1] for o in offsets]
        print(f"{'STATS':<25} {'min':>15} {'max':>15} {'mean':>8} {'median':>7}")
        off_sorted = sorted(off_vals)
        median = off_sorted[len(off_sorted) // 2]
        print(f"{'':25} {min(off_vals):>+15} {max(off_vals):>+15} "
              f"{sum(off_vals)/len(off_vals):>+8.1f} {median:>+7}")

    # ── Quick Test 2: Truncation Correlation ──────────────────────────────
    print("\n── Quick Test 2: Truncation Correlation ──")
    print("If H-A is correct: offset ≈ python_first_ms % 100")
    print(f"{'File':<25} {'Offset':>8} {'Py%100':>7} {'Diff':>7} {'Match?':>7}")
    print("-" * 60)

    trunc_match = 0
    for basename, offset, py_mod, p_ms, n_ms in offsets:
        diff = offset - py_mod
        match = abs(diff) <= 5
        if match:
            trunc_match += 1
        print(f"{basename:<25} {offset:>+8} {py_mod:>7} {diff:>+7} {'YES' if match else 'no':>7}")

    print("-" * 60)
    print(f"Truncation matches (±5ms): {trunc_match}/{len(offsets)} "
          f"({100*trunc_match/len(offsets):.0f}%)" if offsets else "No data")

    # ── Quick Test 3: GPRMC Gap in Binary ─────────────────────────────────
    print("\n── Quick Test 3: Binary CTRK Analysis ──")
    print(f"{'File':<25} {'1stRec':>6} {'1stRec ms':>15} {'1stGPRMC ms':>15} "
          f"{'Gap':>7} {'GPRMC UTC':>14} {'UTC-Hdr':>8}")
    print("-" * 100)

    for basename, parsed_path, native_path, ctrk_path in pairs:
        if not ctrk_path.exists():
            print(f"{basename:<25} CTRK file not found")
            continue
        info = inspect_ctrk_binary(ctrk_path)
        if not info.get('first_record_ms'):
            print(f"{basename:<25} Could not parse binary")
            continue

        first_type = f"T{info['first_record_type']}"
        first_ms = info['first_record_ms']
        gprmc_ms = info.get('first_gprmc_ms', '-')
        gap = gprmc_ms - first_ms if isinstance(gprmc_ms, int) else '-'
        utc_str = info.get('gprmc_utc_str', '-')
        utc_epoch = info.get('gprmc_utc_epoch_ms')
        utc_hdr_diff = utc_epoch - gprmc_ms if utc_epoch and isinstance(gprmc_ms, int) else '-'

        print(f"{basename:<25} {first_type:>6} {first_ms:>15} "
              f"{gprmc_ms if isinstance(gprmc_ms, int) else '-':>15} "
              f"{gap if isinstance(gap, int) else '-':>+7} "
              f"{utc_str:>14} "
              f"{utc_hdr_diff if isinstance(utc_hdr_diff, int) else '-':>+8}")

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2: Hypothesis Testing (re-parse and compare)
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("PHASE 2: HYPOTHESIS TESTING (re-parse with modified initialization)")
    print("=" * 80)

    # Limit to files that have both CTRK source and native CSV
    testable = [(b, p, n, c) for b, p, n, c in pairs if c.exists()]
    print(f"\nTestable files (CTRK + native CSV): {len(testable)}")

    hypotheses = {
        'Baseline': BaselineParser,
        'H-A Truncate': TruncateParser,
        'H-B FirstGPRMC': FirstGPRMCParser,
        'H-C GPRMCTime': GPRMCTimeParser,
        'H-E TruncEvent': TruncateEventParser,
    }

    # Also test fixed offsets (H-D)
    fixed_offsets = [20, 30, 40, 50, 60]

    # Collect results
    results = {}

    for hyp_name, parser_class in hypotheses.items():
        print(f"\n  Testing {hyp_name}...", end='', flush=True)
        rpm_rates = []
        overall_rates = []

        for basename, _, native_path, ctrk_path in testable:
            try:
                parser = parser_class(str(ctrk_path))
                # Suppress parser output
                import io
                import contextlib
                with contextlib.redirect_stdout(io.StringIO()):
                    parser.parse()

                hyp_rows = records_to_dicts(parser.records)
                native_rows = load_csv_rows(native_path)

                aligned = align_records(hyp_rows, native_rows)
                rpm_rates.append(rpm_match_rate(aligned))
                overall_rates.append(overall_match_rate(aligned))
            except Exception as e:
                print(f"\n    Error on {basename}: {e}")

        avg_rpm = sum(rpm_rates) / len(rpm_rates) if rpm_rates else 0
        avg_overall = sum(overall_rates) / len(overall_rates) if overall_rates else 0
        results[hyp_name] = {
            'avg_rpm': avg_rpm,
            'avg_overall': avg_overall,
            'rpm_rates': rpm_rates,
            'overall_rates': overall_rates,
        }
        print(f" RPM={avg_rpm:.1f}%, Overall={avg_overall:.1f}%")

    # Test fixed offsets (H-D)
    for offset_val in fixed_offsets:
        hyp_name = f'H-D Offset-{offset_val}'
        print(f"\n  Testing {hyp_name}...", end='', flush=True)
        rpm_rates = []
        overall_rates = []

        for basename, _, native_path, ctrk_path in testable:
            try:
                parser = BaselineParser(str(ctrk_path))
                import io, contextlib
                with contextlib.redirect_stdout(io.StringIO()):
                    parser.data = open(ctrk_path, 'rb').read()
                    # We need to manually parse with the offset
                    # Reset parser state
                    parser.records = []
                    parser._fuel_accumulator = [0]
                    parser._state = {
                        'rpm': 0, 'gear': 0, 'aps': 0, 'tps': 0,
                        'water_temp': 0, 'intake_temp': 0,
                        'front_speed': 0, 'rear_speed': 0,
                        'front_brake': 0, 'rear_brake': 0,
                        'acc_x': 0, 'acc_y': 0,
                        'lean': 0, 'pitch': 0,
                        'f_abs': False, 'r_abs': False,
                        'tcs': 0, 'scs': 0, 'lif': 0, 'launch': 0,
                        'fuel': 0,
                    }
                    from ctrk_parser import parse_finish_line
                    parser._finish_line = parse_finish_line(parser.data[:500])
                    parser._current_lap = 1
                    parser._prev_lat = 0.0
                    parser._prev_lng = 0.0

                    # Custom parse with fixed offset subtraction
                    data_start = parser._find_data_start()
                    pos = data_start
                    prev_ts_bytes = None
                    prev_epoch_ms = 0
                    current_epoch_ms = 0
                    last_emitted_ms = None
                    current_lat = 9999.0
                    current_lon = 9999.0
                    current_speed_knots = 0.0
                    has_gprmc = False

                    while pos + 14 <= len(parser.data):
                        rec_type = struct.unpack_from('<H', parser.data, pos)[0]
                        total_size = struct.unpack_from('<H', parser.data, pos + 2)[0]
                        if rec_type == 0 and total_size == 0:
                            break
                        if total_size < 14 or total_size > 500 or rec_type not in (1, 2, 3, 4, 5):
                            break
                        if pos + total_size > len(parser.data):
                            break

                        ts_bytes = parser.data[pos + 4:pos + 14]
                        payload = parser.data[pos + 14:pos + total_size]

                        if prev_ts_bytes is None or ts_bytes != prev_ts_bytes:
                            if prev_ts_bytes is None:
                                current_epoch_ms = parser._get_time_data(ts_bytes)
                            elif ts_bytes[2:10] == prev_ts_bytes[2:10]:
                                prev_millis = prev_ts_bytes[0] | (prev_ts_bytes[1] << 8)
                                curr_millis = ts_bytes[0] | (ts_bytes[1] << 8)
                                current_epoch_ms = curr_millis + (prev_epoch_ms - prev_millis)
                                if curr_millis < prev_millis:
                                    current_epoch_ms += 1000
                            else:
                                current_epoch_ms = parser._get_time_data(ts_bytes)
                            prev_epoch_ms = current_epoch_ms
                            prev_ts_bytes = ts_bytes

                        # HYPOTHESIS D: Subtract fixed offset
                        if last_emitted_ms is None:
                            last_emitted_ms = current_epoch_ms - offset_val

                        if rec_type == 1 and len(payload) >= 5:
                            can_id = struct.unpack_from('<H', payload, 0)[0]
                            can_data = payload[5:]
                            from ctrk_parser import CAN_HANDLERS, parse_can_0x023e
                            if can_id == 0x023E and len(can_data) >= 4:
                                parse_can_0x023e(can_data, parser._state, parser._fuel_accumulator)
                            elif can_id in CAN_HANDLERS:
                                CAN_HANDLERS[can_id](can_data, parser._state)

                        elif rec_type == 2 and len(payload) > 6:
                            sentence = payload.decode('ascii', errors='replace').rstrip('\r\n\x00')
                            if sentence.startswith('$GPRMC'):
                                if parser._validate_nmea_checksum(sentence):
                                    gps_data = parser._parse_gprmc_sentence(sentence)
                                    if gps_data:
                                        current_lat = gps_data['latitude']
                                        current_lon = gps_data['longitude']
                                        current_speed_knots = gps_data['speed_knots']
                                    if not has_gprmc:
                                        has_gprmc = True
                                        parser._check_lap_crossing(current_lat, current_lon)
                                        record = parser._create_record(
                                            last_emitted_ms, current_lat, current_lon, current_speed_knots)
                                        parser.records.append(record)

                        if has_gprmc and current_epoch_ms - last_emitted_ms >= 100:
                            parser._check_lap_crossing(current_lat, current_lon)
                            record = parser._create_record(
                                current_epoch_ms, current_lat, current_lon, current_speed_knots)
                            parser.records.append(record)
                            last_emitted_ms = current_epoch_ms

                        pos += total_size

                    if has_gprmc and last_emitted_ms is not None:
                        parser._check_lap_crossing(current_lat, current_lon)
                        record = parser._create_record(
                            current_epoch_ms, current_lat, current_lon, current_speed_knots)
                        parser.records.append(record)

                hyp_rows = records_to_dicts(parser.records)
                native_rows = load_csv_rows(native_path)
                aligned = align_records(hyp_rows, native_rows)
                rpm_rates.append(rpm_match_rate(aligned))
                overall_rates.append(overall_match_rate(aligned))
            except Exception as e:
                print(f"\n    Error on {basename}: {e}")

        avg_rpm = sum(rpm_rates) / len(rpm_rates) if rpm_rates else 0
        avg_overall = sum(overall_rates) / len(overall_rates) if overall_rates else 0
        results[hyp_name] = {
            'avg_rpm': avg_rpm,
            'avg_overall': avg_overall,
            'rpm_rates': rpm_rates,
            'overall_rates': overall_rates,
        }
        print(f" RPM={avg_rpm:.1f}%, Overall={avg_overall:.1f}%")

    # ═══════════════════════════════════════════════════════════════════════
    # Summary Table
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    baseline_rpm = results.get('Baseline', {}).get('avg_rpm', 0)
    baseline_overall = results.get('Baseline', {}).get('avg_overall', 0)

    print(f"\n{'Hypothesis':<22} {'Avg RPM Match':>14} {'Delta RPM':>10} "
          f"{'Avg Overall':>12} {'Delta Ovr':>10}")
    print("-" * 72)

    for hyp_name in ['Baseline', 'H-A Truncate', 'H-B FirstGPRMC', 'H-C GPRMCTime',
                     'H-E TruncEvent'] + [f'H-D Offset-{v}' for v in fixed_offsets]:
        if hyp_name not in results:
            continue
        r = results[hyp_name]
        delta_rpm = r['avg_rpm'] - baseline_rpm
        delta_ovr = r['avg_overall'] - baseline_overall
        marker = ' <-- BEST' if hyp_name != 'Baseline' and delta_rpm == max(
            results[h]['avg_rpm'] - baseline_rpm for h in results if h != 'Baseline') else ''
        print(f"{hyp_name:<22} {r['avg_rpm']:>13.2f}% {delta_rpm:>+9.2f}% "
              f"{r['avg_overall']:>11.2f}% {delta_ovr:>+9.2f}%{marker}")

    # Per-file breakdown for best hypothesis
    best_hyp = max((h for h in results if h != 'Baseline'),
                   key=lambda h: results[h]['avg_rpm'])
    print(f"\n── Per-file RPM breakdown: {best_hyp} vs Baseline ──")
    print(f"{'File':<25} {'Baseline RPM':>13} {best_hyp + ' RPM':>15} {'Delta':>8}")
    print("-" * 65)

    baseline_rpms = results['Baseline']['rpm_rates']
    best_rpms = results[best_hyp]['rpm_rates']
    test_files = [(b, p, n, c) for b, p, n, c in pairs if c.exists()]

    for i, (basename, _, _, _) in enumerate(test_files):
        if i < len(baseline_rpms) and i < len(best_rpms):
            delta = best_rpms[i] - baseline_rpms[i]
            marker = ' !!!' if delta < -5 else (' +++' if delta > 5 else '')
            print(f"{basename:<25} {baseline_rpms[i]:>12.2f}% {best_rpms[i]:>14.2f}% "
                  f"{delta:>+7.2f}%{marker}")

    print("\nDone.")


if __name__ == '__main__':
    main()
