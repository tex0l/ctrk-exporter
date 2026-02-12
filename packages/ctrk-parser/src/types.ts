/**
 * TypeScript type definitions for CTRK telemetry parser
 */

/**
 * Represents a finish line defined by two GPS coordinates.
 *
 * The finish line is a line segment between P1 and P2 that defines
 * the start/finish line on the track. Lap detection works by checking
 * if the motorcycle's trajectory crosses this line segment.
 */
export interface FinishLine {
  p1_lat: number;
  p1_lng: number;
  p2_lat: number;
  p2_lng: number;
}

/**
 * A single telemetry sample containing all channel values.
 *
 * This interface holds raw (uncalibrated) sensor values for a single
 * point in time. Use the Calibration class methods to convert raw
 * values to engineering units.
 */
export interface TelemetryRecord {
  lap: number;
  time_ms: number;

  // GPS
  latitude: number;
  longitude: number;
  gps_speed_knots: number;

  // Engine (raw)
  rpm: number;
  gear: number;

  // Throttle (raw)
  aps: number;
  tps: number;

  // Temperature (raw) - single bytes from 0x023E
  water_temp: number;
  intake_temp: number;

  // Wheel Speed (raw)
  front_speed: number;
  rear_speed: number;

  // Fuel (raw) - cumulative
  fuel: number;

  // IMU (raw)
  lean: number;
  lean_signed: number;
  pitch: number;

  // Acceleration (raw)
  acc_x: number;
  acc_y: number;

  // Brakes (raw)
  front_brake: number;
  rear_brake: number;

  // Electronic systems
  f_abs: boolean;
  r_abs: boolean;
  tcs: number;
  scs: number;
  lif: number;
  launch: number;
}

/**
 * Internal state for CAN message accumulation (zero-order hold).
 */
export interface ChannelState {
  rpm: number;
  gear: number;
  aps: number;
  tps: number;
  water_temp: number;
  intake_temp: number;
  front_speed: number;
  rear_speed: number;
  front_brake: number;
  rear_brake: number;
  acc_x: number;
  acc_y: number;
  lean: number;
  lean_signed: number;
  pitch: number;
  f_abs: boolean;
  r_abs: boolean;
  tcs: number;
  scs: number;
  lif: number;
  launch: number;
  fuel: number;
}

/**
 * GPS state tracked during parsing.
 */
export interface GpsState {
  latitude: number; // 9999.0 = no fix
  longitude: number; // 9999.0 = no fix
  speed_knots: number;
}

/**
 * Parsed GPRMC sentence data.
 */
export interface GprmcData {
  latitude: number;
  longitude: number;
  speed_knots: number;
}
