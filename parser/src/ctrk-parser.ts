/**
 * CTRK Parser - Main parsing logic.
 *
 * Implements the complete CTRK file parsing algorithm with:
 * - Binary record parsing (14-byte headers + typed payloads)
 * - Timestamp computation (GetTimeDataEx)
 * - CAN message decoding for 21 telemetry channels
 * - GPS NMEA sentence parsing
 * - 10 Hz emission timing with GPS gating
 * - Lap detection via finish line crossing
 */

import { BufferReader } from './buffer-reader.js';
import { validateMagic, findDataStart, parseFinishLine } from './header-parser.js';
import { getTimeDataEx, createTimestampState } from './timestamp.js';
import { validateNmeaChecksum, parseGprmcSentence } from './nmea-parser.js';
import { crossesLine } from './finish-line.js';
import { parseCan0x023e, CAN_HANDLERS } from './can-handlers.js';
import type {
  FinishLine,
  TelemetryRecord,
  ChannelState,
  GpsState,
} from './types.js';

/**
 * Parser for Yamaha Y-Trac CTRK telemetry files.
 *
 * This class implements a complete CTRK file parser based on reverse engineering
 * of the native library (libSensorsRecordIF.so). It handles:
 *
 * - Binary file structure parsing (header, data section, footer)
 * - Timestamp computation with incremental optimization
 * - CAN message decoding for all 21 telemetry channels
 * - GPS NMEA sentence parsing with checksum validation
 * - 10 Hz emission timing with GPS gating
 * - Lap detection via finish line crossing
 */
export class CTRKParser {
  private data: Uint8Array;
  private records: TelemetryRecord[] = [];
  private finishLine: FinishLine | null = null;

  /**
   * Initialize the parser with file data.
   *
   * @param data - Complete CTRK file data as Uint8Array
   */
  constructor(data: Uint8Array) {
    this.data = data;
  }

  /**
   * Parse the CTRK file and extract telemetry records.
   *
   * Validates the header, extracts finish line coordinates, and processes
   * all data records to produce 10 Hz telemetry output.
   *
   * @returns Array of TelemetryRecord objects, one per 100ms emission interval
   * @throws Error if the file does not have valid CTRK header magic
   */
  parse(): TelemetryRecord[] {
    // Validate magic signature
    if (!validateMagic(this.data)) {
      throw new Error('Invalid CTRK file: expected "HEAD" magic');
    }

    console.log(`Parsing CTRK file (${this.data.length.toLocaleString()} bytes)`);

    // Parse finish line from header
    this.finishLine = parseFinishLine(this.data.slice(0, 500));
    if (this.finishLine) {
      console.log(
        `  Finish line: P1(${this.finishLine.p1_lat.toFixed(6)}, ${this.finishLine.p1_lng.toFixed(6)}) -> ` +
        `P2(${this.finishLine.p2_lat.toFixed(6)}, ${this.finishLine.p2_lng.toFixed(6)})`
      );
    } else {
      console.log('  Warning: Could not parse finish line from header, all records will be lap 1');
    }

    // Parse data section
    this.parseDataSection();

    return this.records;
  }

  /**
   * Get parsed telemetry records.
   *
   * @returns Array of parsed records (empty before parse() is called)
   */
  getRecords(): TelemetryRecord[] {
    return this.records;
  }

  /**
   * Parse the data section using continuous state processing.
   *
   * Iterates through all records in the data section, updating CAN state
   * and emitting telemetry records at 100ms intervals. State is carried
   * forward continuously across laps.
   */
  private parseDataSection(): void {
    const reader = new BufferReader(this.data);
    const dataStart = findDataStart(reader);
    let pos = dataStart;

    // Timestamp state
    const tsState = createTimestampState();
    let currentEpochMs = 0;

    // Emission state
    let lastEmittedMs: number | null = null;
    let gpsCount = 0;
    let canCount = 0;
    let checksumFailures = 0;

    // GPS state (sentinel 9999.0 matches native)
    const gpsState: GpsState = {
      latitude: 9999.0,
      longitude: 9999.0,
      speed_knots: 0.0,
    };
    let hasGprmc = false;

    // CAN state (zero-order hold)
    const canState: ChannelState = {
      rpm: 0,
      gear: 0,
      aps: 0,
      tps: 0,
      water_temp: 0,
      intake_temp: 0,
      front_speed: 0,
      rear_speed: 0,
      front_brake: 0,
      rear_brake: 0,
      acc_x: 0,
      acc_y: 0,
      lean: 0,
      lean_signed: 0,
      pitch: 0,
      f_abs: false,
      r_abs: false,
      tcs: 0,
      scs: 0,
      lif: 0,
      launch: 0,
      fuel: 0,
    };

    // Fuel accumulator (mutable reference)
    const fuelAcc = { value: 0 };

    // Lap tracking
    let currentLap = 1;
    let prevLat = 0.0;
    let prevLng = 0.0;

    // Main parsing loop
    while (pos + 14 <= this.data.length) {
      // Read 14-byte record header
      const view = new DataView(this.data.buffer, this.data.byteOffset, this.data.byteLength);
      const recType = view.getUint16(pos, true); // little-endian
      const totalSize = view.getUint16(pos + 2, true);

      // End-of-data detection
      if (recType === 0 && totalSize === 0) {
        break; // Null terminator
      }
      if (totalSize < 14 || totalSize > 500) {
        break; // Invalid size
      }
      if (![1, 2, 3, 4, 5].includes(recType)) {
        break; // Unknown type
      }
      if (pos + totalSize > this.data.length) {
        break; // Truncated record
      }

      // Extract timestamp bytes (bytes 4-13 of header)
      const tsBytes = this.data.slice(pos + 4, pos + 14);
      const payload = this.data.slice(pos + 14, pos + totalSize);

      // Timestamp computation (GetTimeDataEx algorithm)
      currentEpochMs = getTimeDataEx(tsBytes, tsState);

      // Initialize emission clock at first record
      if (lastEmittedMs === null) {
        lastEmittedMs = currentEpochMs;
      }

      // Process payload by record type
      if (recType === 1 && payload.length >= 5) {
        // CAN record
        const canView = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
        const canId = canView.getUint16(0, true); // little-endian
        const canData = payload.slice(5); // Skip CAN ID (2) + padding (2) + DLC (1)

        if (canId === 0x023e && canData.length >= 4) {
          // Fuel handler needs accumulator
          parseCan0x023e(canData, canState, fuelAcc);
        } else if (canId in CAN_HANDLERS) {
          // Standard CAN handlers
          CAN_HANDLERS[canId](canData, canState);
        }

        canCount++;
      } else if (recType === 2 && payload.length > 6) {
        // GPS/NMEA record
        const decoder = new TextDecoder('ascii');
        let sentence = decoder.decode(payload);
        // Remove trailing \r\n and null bytes
        sentence = sentence.replace(/[\r\n\x00]+$/g, '');

        if (sentence.startsWith('$GPRMC')) {
          if (validateNmeaChecksum(sentence)) {
            const gprmcData = parseGprmcSentence(sentence);
            if (gprmcData) {
              // Valid fix: update GPS state
              gpsState.latitude = gprmcData.latitude;
              gpsState.longitude = gprmcData.longitude;
              gpsState.speed_knots = gprmcData.speed_knots;
            }

            // Emit initial record at first GPRMC (regardless of status)
            if (!hasGprmc) {
              hasGprmc = true;
              this.checkLapCrossing(
                gpsState.latitude,
                gpsState.longitude,
                currentLap,
                fuelAcc,
                canState,
                prevLat,
                prevLng
              );
              const record = this.createRecord(
                lastEmittedMs,
                gpsState,
                canState,
                currentLap
              );
              this.records.push(record);
              gpsCount++;
            }
          } else {
            checksumFailures++;
          }
        }
      } else if (recType === 5) {
        // Lap marker: re-align emission clock
        lastEmittedMs = currentEpochMs;
      }
      // Types 3 and 4: skip (not decoded)

      // Emission check (100ms interval)
      if (hasGprmc && currentEpochMs - lastEmittedMs >= 100) {
        const crossingResult = this.checkLapCrossing(
          gpsState.latitude,
          gpsState.longitude,
          currentLap,
          fuelAcc,
          canState,
          prevLat,
          prevLng
        );
        currentLap = crossingResult.lap;
        prevLat = crossingResult.prevLat;
        prevLng = crossingResult.prevLng;

        const record = this.createRecord(
          currentEpochMs,
          gpsState,
          canState,
          currentLap
        );
        this.records.push(record);
        gpsCount++;
        lastEmittedMs = currentEpochMs;
      }

      pos += totalSize;
    }

    // Final record emission
    if (hasGprmc && lastEmittedMs !== null) {
      const crossingResult = this.checkLapCrossing(
        gpsState.latitude,
        gpsState.longitude,
        currentLap,
        fuelAcc,
        canState,
        prevLat,
        prevLng
      );
      currentLap = crossingResult.lap;

      const record = this.createRecord(
        currentEpochMs,
        gpsState,
        canState,
        currentLap
      );
      this.records.push(record);
      gpsCount++;
    }

    console.log(`  Found ${gpsCount} GPS records, ${canCount} CAN messages`);
    if (checksumFailures > 0) {
      console.log(`  Rejected ${checksumFailures} GPRMC sentences (bad checksum)`);
    }
    console.log(`  Built ${this.records.length} telemetry records`);
    console.log(`  Detected ${currentLap} laps`);
  }

  /**
   * Check if the motorcycle crossed the finish line.
   *
   * Compares current position against previous position to detect
   * finish line crossing. On crossing, increments lap counter and
   * resets fuel accumulator.
   *
   * @param lat - Current latitude in decimal degrees
   * @param lon - Current longitude in decimal degrees
   * @param currentLap - Current lap number
   * @param fuelAcc - Mutable fuel accumulator object
   * @param canState - CAN state object to reset fuel value
   * @param prevLat - Previous latitude
   * @param prevLng - Previous longitude
   * @returns Object with updated lap, prevLat, prevLng
   */
  private checkLapCrossing(
    lat: number,
    lon: number,
    currentLap: number,
    fuelAcc: { value: number },
    canState: ChannelState,
    prevLat: number,
    prevLng: number
  ): { lap: number; prevLat: number; prevLng: number } {
    if (this.finishLine === null) {
      return { lap: currentLap, prevLat: lat, prevLng: lon };
    }

    // Need a previous position to check crossing
    if (prevLat === 0.0 && prevLng === 0.0) {
      return { lap: currentLap, prevLat: lat, prevLng: lon };
    }

    const crossed = crossesLine(this.finishLine, prevLat, prevLng, lat, lon);

    if (crossed) {
      // New lap started
      currentLap++;
      // Reset fuel accumulator
      fuelAcc.value = 0;
      canState.fuel = 0;
    }

    return { lap: currentLap, prevLat: lat, prevLng: lon };
  }

  /**
   * Create a TelemetryRecord from current accumulated CAN state.
   *
   * Snapshots the current state into a new TelemetryRecord
   * object with the provided GPS data and timestamp.
   *
   * @param timeMs - Unix timestamp in milliseconds
   * @param gpsState - GPS state object
   * @param canState - CAN state object
   * @param lap - Current lap number
   * @returns New TelemetryRecord with all current channel values
   */
  private createRecord(
    timeMs: number,
    gpsState: GpsState,
    canState: ChannelState,
    lap: number
  ): TelemetryRecord {
    return {
      lap,
      time_ms: timeMs,
      latitude: gpsState.latitude,
      longitude: gpsState.longitude,
      gps_speed_knots: gpsState.speed_knots,
      rpm: canState.rpm,
      gear: canState.gear,
      aps: canState.aps,
      tps: canState.tps,
      water_temp: canState.water_temp,
      intake_temp: canState.intake_temp,
      front_speed: canState.front_speed,
      rear_speed: canState.rear_speed,
      fuel: canState.fuel,
      lean: canState.lean,
      lean_signed: canState.lean_signed,
      pitch: canState.pitch,
      acc_x: canState.acc_x,
      acc_y: canState.acc_y,
      front_brake: canState.front_brake,
      rear_brake: canState.rear_brake,
      f_abs: canState.f_abs,
      r_abs: canState.r_abs,
      tcs: canState.tcs,
      scs: canState.scs,
      lif: canState.lif,
      launch: canState.launch,
    };
  }
}
