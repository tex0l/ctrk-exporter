/**
 * CAN message handlers for decoding binary CAN payloads.
 *
 * All byte positions and formulas verified against native library
 * via radare2 disassembly.
 */

import type { ChannelState } from './types.js';

/**
 * Parse CAN message 0x0209: Engine RPM and Gear.
 *
 * Extracts RPM from bytes 0-1 (big-endian uint16) and gear from byte 4
 * (lower 3 bits). Gear value 7 is rejected as invalid (gear transition).
 *
 * @param data - CAN payload bytes (minimum 5 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0209(data: Uint8Array, state: ChannelState): void {
  if (data.length < 5) return;

  // RPM: big-endian uint16
  state.rpm = (data[0] << 8) | data[1];

  // Gear: lower 3 bits of byte 4, reject value 7
  const gear = data[4] & 0x07;
  if (gear !== 7) {
    state.gear = gear;
  }
}

/**
 * Parse CAN message 0x0215: Throttle and Electronic Controls.
 *
 * Extracts:
 * - TPS (Throttle Position Sensor) from bytes 0-1
 * - APS (Accelerator Position Sensor) from bytes 2-3
 * - Launch control status from byte 6 bits 5-6
 * - TCS, SCS, LIF status from byte 7 bits 3-5
 *
 * @param data - CAN payload bytes (minimum 8 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0215(data: Uint8Array, state: ChannelState): void {
  if (data.length < 8) return;

  // TPS: big-endian uint16
  state.tps = (data[0] << 8) | data[1];

  // APS: big-endian uint16
  state.aps = (data[2] << 8) | data[3];

  // Launch: byte 6 bits 5-6 (0x60 mask)
  state.launch = (data[6] & 0x60) !== 0 ? 1 : 0;

  // TCS: byte 7 bit 5
  state.tcs = (data[7] >> 5) & 1;

  // SCS: byte 7 bit 4
  state.scs = (data[7] >> 4) & 1;

  // LIF: byte 7 bit 3
  state.lif = (data[7] >> 3) & 1;
}

/**
 * Parse CAN message 0x023E: Temperature and Fuel.
 *
 * Extracts:
 * - Water temperature from byte 0 (single byte, NOT uint16)
 * - Intake air temperature from byte 1 (single byte)
 * - Fuel consumption delta from bytes 2-3 (big-endian uint16)
 *
 * The fuel value is a delta that must be accumulated.
 *
 * @param data - CAN payload bytes (minimum 4 bytes required)
 * @param state - Mutable state object to update with parsed values
 * @param fuelAcc - Mutable object with fuel accumulator { value: number }
 */
export function parseCan0x023e(
  data: Uint8Array,
  state: ChannelState,
  fuelAcc: { value: number }
): void {
  if (data.length < 4) return;

  // Temperatures are single bytes (uint8)
  state.water_temp = data[0];
  state.intake_temp = data[1];

  // Fuel delta: big-endian uint16
  const fuelDelta = (data[2] << 8) | data[3];
  fuelAcc.value += fuelDelta;
  state.fuel = fuelAcc.value;
}

/**
 * Parse CAN message 0x0250: Acceleration.
 *
 * Extracts longitudinal (X) and lateral (Y) acceleration from bytes 0-3.
 * Both values are big-endian uint16.
 *
 * @param data - CAN payload bytes (minimum 4 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0250(data: Uint8Array, state: ChannelState): void {
  if (data.length < 4) return;

  // ACC_X: big-endian uint16
  state.acc_x = (data[0] << 8) | data[1];

  // ACC_Y: big-endian uint16
  state.acc_y = (data[2] << 8) | data[3];
}

/**
 * Parse CAN message 0x0258: IMU (Lean and Pitch).
 *
 * Extracts:
 * - Lean angle from bytes 0-3 using special packed format with deadband
 * - Pitch rate from bytes 6-7 (big-endian uint16)
 *
 * The lean angle uses a complex algorithm with:
 * 1. Nibble interleaving across bytes 0-3
 * 2. Deviation from center (9000 = upright)
 * 3. Deadband: deviations <= 499 treated as upright
 * 4. Truncation to nearest 100 (floor, not round)
 *
 * @param data - CAN payload bytes (minimum 8 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0258(data: Uint8Array, state: ChannelState): void {
  if (data.length < 8) return;

  const b0 = data[0];
  const b1 = data[1];
  const b2 = data[2];
  const b3 = data[3];

  // Extract packed values from interleaved nibbles
  const val1Part = (b0 << 4) | (b2 & 0x0f);
  const val1 = val1Part << 8;
  const val2 = ((b1 & 0x0f) << 4) | (b3 >> 4);
  const sumVal = (val1 + val2) & 0xffff;

  // Transform to deviation from center (9000 = upright)
  let deviation: number;
  if (sumVal < 9000) {
    deviation = 9000 - sumVal;
  } else {
    deviation = (sumVal - 9000) & 0xffff;
  }

  // Apply deadband (~5 degrees)
  if (deviation <= 499) {
    state.lean = 9000; // Upright
    state.lean_signed = 9000;
  } else {
    // Truncate to nearest 100 (degree resolution)
    const deviationRounded = deviation - (deviation % 100);
    state.lean = (9000 + deviationRounded) & 0xffff;

    // Signed: preserve direction (sumVal < 9000 = negative lean)
    if (sumVal < 9000) {
      state.lean_signed = 9000 - deviationRounded;
    } else {
      state.lean_signed = 9000 + deviationRounded;
    }
  }

  // Pitch is straightforward: big-endian uint16
  state.pitch = (data[6] << 8) | data[7];
}

/**
 * Parse CAN message 0x0260: Brake Pressure.
 *
 * Extracts front and rear brake hydraulic pressure from bytes 0-3.
 * Both values are big-endian uint16.
 *
 * @param data - CAN payload bytes (minimum 4 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0260(data: Uint8Array, state: ChannelState): void {
  if (data.length < 4) return;

  // Front brake: big-endian uint16
  state.front_brake = (data[0] << 8) | data[1];

  // Rear brake: big-endian uint16
  state.rear_brake = (data[2] << 8) | data[3];
}

/**
 * Parse CAN message 0x0264: Wheel Speed.
 *
 * Extracts front and rear wheel speed from bytes 0-3.
 * Both values are big-endian uint16.
 *
 * @param data - CAN payload bytes (minimum 4 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0264(data: Uint8Array, state: ChannelState): void {
  if (data.length < 4) return;

  // Front speed: big-endian uint16
  state.front_speed = (data[0] << 8) | data[1];

  // Rear speed: big-endian uint16
  state.rear_speed = (data[2] << 8) | data[3];
}

/**
 * Parse CAN message 0x0268: ABS Status.
 *
 * Extracts front and rear ABS active flags from byte 4.
 * R_ABS is bit 0, F_ABS is bit 1 (counterintuitive order).
 *
 * @param data - CAN payload bytes (minimum 5 bytes required)
 * @param state - Mutable state object to update with parsed values
 */
export function parseCan0x0268(data: Uint8Array, state: ChannelState): void {
  if (data.length < 5) return;

  // R_ABS: bit 0
  state.r_abs = (data[4] & 1) !== 0;

  // F_ABS: bit 1
  state.f_abs = ((data[4] >> 1) & 1) !== 0;
}

/**
 * CAN handler dispatch table.
 * Maps CAN ID to handler function.
 */
export const CAN_HANDLERS: {
  [key: number]: (data: Uint8Array, state: ChannelState) => void;
} = {
  0x0209: parseCan0x0209,
  0x0215: parseCan0x0215,
  0x0250: parseCan0x0250,
  0x0258: parseCan0x0258,
  0x0260: parseCan0x0260,
  0x0264: parseCan0x0264,
  0x0268: parseCan0x0268,
  // 0x023E handled separately due to fuel accumulator
};
