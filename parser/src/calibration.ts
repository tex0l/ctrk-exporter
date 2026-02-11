/**
 * Calibration factors for converting raw sensor values to engineering units.
 *
 * All calibration formulas have been verified against the native library output
 * via radare2 disassembly. The formulas convert raw integer values from CAN
 * messages to physical units (RPM, km/h, degrees, etc.).
 */
export class Calibration {
  /**
   * Convert raw RPM value to engine RPM.
   *
   * @param raw - Raw 16-bit value from CAN 0x0209 bytes 0-1 (big-endian)
   * @returns Engine RPM as integer
   *
   * @example
   * Calibration.rpm(25600) // returns 10000
   */
  static rpm(raw: number): number {
    return Math.trunc(raw / 2.56);
  }

  /**
   * Convert raw wheel speed value to km/h.
   *
   * @param raw - Raw 16-bit value from CAN 0x0264 (big-endian)
   * @returns Wheel speed in km/h
   *
   * @example
   * Calibration.wheelSpeedKmh(6400) // returns 360.0
   */
  static wheelSpeedKmh(raw: number): number {
    return (raw / 64.0) * 3.6;
  }

  /**
   * Convert raw throttle position to percentage.
   *
   * Works for both TPS (Throttle Position Sensor) and APS (Accelerator
   * Position Sensor) from CAN 0x0215.
   *
   * @param raw - Raw 16-bit value from CAN 0x0215 (big-endian)
   * @returns Throttle percentage (0-100%, may exceed 100% at full throttle)
   *
   * @example
   * Calibration.throttle(6963) // returns 100.0
   */
  static throttle(raw: number): number {
    return ((raw / 8.192) * 100.0) / 84.96;
  }

  /**
   * Convert raw brake pressure to bar.
   *
   * @param raw - Raw 16-bit value from CAN 0x0260 (big-endian)
   * @returns Brake hydraulic pressure in bar
   *
   * @example
   * Calibration.brake(320) // returns 10.0
   */
  static brake(raw: number): number {
    return raw / 32.0;
  }

  /**
   * Convert raw lean angle to degrees.
   *
   * The raw value 9000 represents upright (0 degrees). Values above 9000
   * indicate lean angle magnitude after deadband and rounding are applied.
   *
   * @param raw - Processed lean value from CAN 0x0258 (after decode_lean algorithm)
   * @returns Lean angle in degrees. 0.0 = upright, positive = leaning
   *
   * @example
   * Calibration.lean(9000) // returns 0.0
   * Calibration.lean(12000) // returns 30.0
   */
  static lean(raw: number): number {
    return raw / 100.0 - 90.0;
  }

  /**
   * Convert raw pitch rate to degrees per second.
   *
   * @param raw - Raw 16-bit value from CAN 0x0258 bytes 6-7 (big-endian)
   * @returns Pitch rate in deg/s. 0.0 = level, positive = nose up
   *
   * @example
   * Calibration.pitch(30000) // returns 0.0
   */
  static pitch(raw: number): number {
    return raw / 100.0 - 300.0;
  }

  /**
   * Convert raw acceleration to G-force.
   *
   * @param raw - Raw 16-bit value from CAN 0x0250 (big-endian)
   * @returns Acceleration in G. 0.0 = no acceleration
   *
   * @example
   * Calibration.acceleration(7000) // returns 0.0
   * Calibration.acceleration(8000) // returns 1.0
   */
  static acceleration(raw: number): number {
    return raw / 1000.0 - 7.0;
  }

  /**
   * Convert raw temperature to Celsius.
   *
   * Works for both water temperature and intake air temperature
   * from CAN 0x023E.
   *
   * @param raw - Raw 8-bit value from CAN 0x023E byte 0 or 1
   * @returns Temperature in degrees Celsius
   *
   * @example
   * Calibration.temperature(176) // returns 80.0
   */
  static temperature(raw: number): number {
    return raw / 1.6 - 30.0;
  }

  /**
   * Convert raw fuel consumption to cubic centimeters.
   *
   * @param raw - Accumulated fuel value (sum of deltas from CAN 0x023E)
   * @returns Fuel consumption in cc
   *
   * @example
   * Calibration.fuel(10000) // returns 100.0
   */
  static fuel(raw: number): number {
    return raw / 100.0;
  }

  /**
   * Convert GPS speed from knots to km/h.
   *
   * @param knots - Speed in nautical miles per hour (from GPRMC sentence)
   * @returns Speed in km/h
   *
   * @example
   * Calibration.gpsSpeedKmh(54.0) // returns 100.008
   */
  static gpsSpeedKmh(knots: number): number {
    return knots * 1.852;
  }
}
