import { Calibration } from '@tex0l/ctrk-parser';
import type { TelemetryRecord } from '@tex0l/ctrk-parser';

const CALIBRATED_HEADER = [
  'lap', 'time_ms', 'latitude', 'longitude', 'gps_speed_kmh',
  'rpm', 'throttle_grip', 'throttle', 'water_temp', 'intake_temp',
  'front_speed_kmh', 'rear_speed_kmh', 'fuel_cc', 'lean_deg', 'lean_signed_deg', 'pitch_deg_s',
  'acc_x_g', 'acc_y_g', 'front_brake_bar', 'rear_brake_bar', 'gear',
  'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch',
];

const RAW_HEADER = [
  'lap', 'time_ms', 'latitude', 'longitude', 'gps_speed_knots',
  'rpm_raw', 'aps_raw', 'tps_raw', 'wt_raw', 'intt_raw',
  'fspeed_raw', 'rspeed_raw', 'fuel_raw', 'lean_raw', 'lean_signed_raw', 'pitch_raw',
  'accx_raw', 'accy_raw', 'fpress_raw', 'rpress_raw', 'gear',
  'f_abs', 'r_abs', 'tcs', 'scs', 'lif', 'launch',
];

/** Dekker's split: partition a float into high and low halves for error-free arithmetic. */
function splitHigh(x: number): number {
  const c = (2 ** 27 + 1) * x;
  return c - (c - x);
}

/** Dekker's twoProd error term: returns the rounding error of a*b in float64. */
function twoProdErr(a: number, b: number): number {
  const p = a * b;
  const ah = splitHigh(a);
  const al = a - ah;
  const bh = splitHigh(b);
  const bl = b - bh;
  return ((ah * bh - p) + ah * bl + al * bh) + al * bl;
}

/**
 * Format a number with fixed decimals matching Python's round-half-to-even.
 *
 * JS toFixed rounds half-up, Python uses banker's rounding. They only disagree
 * at exact IEEE 754 midpoints (e.g. 0.25 -> "0.3" in JS, "0.2" in Python).
 * For near-midpoints like 0.05 (not exactly representable), both agree on
 * the rounding direction. We use Dekker's error-free product to distinguish
 * exact midpoints from near-midpoints.
 */
function pyFixed(value: number, decimals: number): string {
  const mult = 10 ** decimals;
  const abs = Math.abs(value);
  const shifted = abs * mult;
  const lower = Math.floor(shifted);
  const frac = shifted - lower;

  let rounded: number;
  if (frac === 0.5) {
    // Float multiplication landed exactly at midpoint.
    // Use the error term to determine if the true product is above/below/at midpoint.
    const err = twoProdErr(abs, mult);
    if (err > 0) {
      rounded = lower + 1; // True value above midpoint
    } else if (err < 0) {
      rounded = lower; // True value below midpoint
    } else {
      // Exact midpoint: banker's rounding (round to even)
      rounded = lower % 2 === 0 ? lower : lower + 1;
    }
  } else {
    rounded = Math.round(shifted);
  }

  const result = (rounded / mult).toFixed(decimals);
  return value < 0 ? '-' + result : result;
}

export function formatCalibratedCsv(records: TelemetryRecord[]): string {
  const lines: string[] = [CALIBRATED_HEADER.join(',')];

  for (const r of records) {
    lines.push([
      r.lap,
      r.time_ms,
      r.latitude.toFixed(6),
      r.longitude.toFixed(6),
      pyFixed(Calibration.gpsSpeedKmh(r.gps_speed_knots), 2),
      Calibration.rpm(r.rpm),
      pyFixed(Calibration.throttle(r.aps), 1),
      pyFixed(Calibration.throttle(r.tps), 1),
      pyFixed(Calibration.temperature(r.water_temp), 1),
      pyFixed(Calibration.temperature(r.intake_temp), 1),
      pyFixed(Calibration.wheelSpeedKmh(r.front_speed), 1),
      pyFixed(Calibration.wheelSpeedKmh(r.rear_speed), 1),
      pyFixed(Calibration.fuel(r.fuel), 2),
      pyFixed(Calibration.lean(r.lean), 1),
      pyFixed(Calibration.lean(r.lean_signed), 1),
      pyFixed(Calibration.pitch(r.pitch), 1),
      pyFixed(Calibration.acceleration(r.acc_x), 2),
      pyFixed(Calibration.acceleration(r.acc_y), 2),
      pyFixed(Calibration.brake(r.front_brake), 1),
      pyFixed(Calibration.brake(r.rear_brake), 1),
      r.gear,
      String(r.f_abs),
      String(r.r_abs),
      r.tcs,
      r.scs,
      r.lif,
      r.launch,
    ].join(','));
  }

  return lines.join('\r\n') + '\r\n';
}

export function formatRawCsv(records: TelemetryRecord[]): string {
  const lines: string[] = [RAW_HEADER.join(',')];

  for (const r of records) {
    lines.push([
      r.lap,
      r.time_ms,
      r.latitude.toFixed(6),
      r.longitude.toFixed(6),
      pyFixed(r.gps_speed_knots, 4),
      r.rpm,
      r.aps,
      r.tps,
      r.water_temp,
      r.intake_temp,
      r.front_speed,
      r.rear_speed,
      r.fuel,
      r.lean,
      r.lean_signed,
      r.pitch,
      r.acc_x,
      r.acc_y,
      r.front_brake,
      r.rear_brake,
      r.gear,
      String(r.f_abs),
      String(r.r_abs),
      r.tcs,
      r.scs,
      r.lif,
      r.launch,
    ].join(','));
  }

  return lines.join('\r\n') + '\r\n';
}
