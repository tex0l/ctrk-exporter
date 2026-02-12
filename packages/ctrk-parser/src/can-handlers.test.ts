import { describe, it, expect, beforeEach } from 'vitest';
import {
  parseCan0x0209,
  parseCan0x0215,
  parseCan0x023e,
  parseCan0x0250,
  parseCan0x0258,
  parseCan0x0260,
  parseCan0x0264,
  parseCan0x0268,
} from './can-handlers.js';
import type { ChannelState } from './types.js';

describe('CAN Handlers', () => {
  let state: ChannelState;

  beforeEach(() => {
    state = {
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
  });

  describe('parseCan0x0209', () => {
    it('should parse RPM and gear', () => {
      const data = new Uint8Array([0x64, 0x00, 0x00, 0x00, 0x03, 0x00]);
      parseCan0x0209(data, state);

      expect(state.rpm).toBe(0x6400); // 25600
      expect(state.gear).toBe(3);
    });

    it('should reject gear value 7', () => {
      const data = new Uint8Array([0x64, 0x00, 0x00, 0x00, 0x07, 0x00]);
      state.gear = 2; // Previous gear
      parseCan0x0209(data, state);

      expect(state.gear).toBe(2); // Should retain previous value
    });

    it('should handle short payload', () => {
      const data = new Uint8Array([0x64, 0x00]);
      parseCan0x0209(data, state);
      // Should not throw, just not update
    });
  });

  describe('parseCan0x0215', () => {
    it('should parse throttle and controls', () => {
      const data = new Uint8Array([
        0x1b,
        0x33, // TPS
        0x1c,
        0x44, // APS
        0x00,
        0x00,
        0x60, // Launch (byte 6)
        0x08, // byte 7: bit3=LIF=1, bit4=SCS=0, bit5=TCS=0
      ]);
      parseCan0x0215(data, state);

      expect(state.tps).toBe(0x1b33);
      expect(state.aps).toBe(0x1c44);
      expect(state.launch).toBe(1);
      expect(state.lif).toBe(1);
      expect(state.tcs).toBe(0);
      expect(state.scs).toBe(0);
    });

    it('should parse electronic control flags', () => {
      const data = new Uint8Array([
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x08, // byte 7: bit3=LIF=1, bit4=SCS=0, bit5=TCS=0
      ]);
      parseCan0x0215(data, state);

      expect(state.tcs).toBe(0);
      expect(state.scs).toBe(0);
      expect(state.lif).toBe(1);
    });
  });

  describe('parseCan0x023e', () => {
    it('should parse temperatures and fuel delta', () => {
      const data = new Uint8Array([
        0xb0, // water temp (176)
        0x60, // intake temp (96)
        0x00,
        0x64, // fuel delta (100)
      ]);
      const fuelAcc = { value: 0 };
      parseCan0x023e(data, state, fuelAcc);

      expect(state.water_temp).toBe(176);
      expect(state.intake_temp).toBe(96);
      expect(state.fuel).toBe(100);
      expect(fuelAcc.value).toBe(100);
    });

    it('should accumulate fuel deltas', () => {
      const data = new Uint8Array([0x00, 0x00, 0x00, 0x64]);
      const fuelAcc = { value: 500 };

      parseCan0x023e(data, state, fuelAcc);
      expect(state.fuel).toBe(600);
      expect(fuelAcc.value).toBe(600);
    });
  });

  describe('parseCan0x0250', () => {
    it('should parse acceleration', () => {
      const data = new Uint8Array([
        0x1b,
        0x58, // ACC_X (7000)
        0x1f,
        0x40, // ACC_Y (8000)
        0x00,
        0x00,
        0x00,
        0x00,
      ]);
      parseCan0x0250(data, state);

      expect(state.acc_x).toBe(7000);
      expect(state.acc_y).toBe(8000);
    });
  });

  describe('parseCan0x0258', () => {
    it('should parse lean angle with deadband', () => {
      // Construct bytes that result in sumVal = 9100 (within deadband)
      // val1_part = (2 << 4) | (3 & 0x0f) = 35
      // val1 = 35 << 8 = 8960
      // val2 = ((8 & 0x0f) << 4) | (0xc0 >> 4) = (8 << 4) | 12 = 140
      // sumVal = 8960 + 140 = 9100 -> deviation = 100 -> within deadband
      const data = new Uint8Array([
        0x02,
        0x08,
        0x03,
        0xc0, // Lean bytes (sumVal = 9100)
        0x00,
        0x00,
        0x75,
        0x30, // Pitch (30000)
      ]);
      parseCan0x0258(data, state);

      expect(state.lean).toBe(9000); // Upright (within deadband)
      expect(state.lean_signed).toBe(9000);
      expect(state.pitch).toBe(30000);
    });

    it('should parse lean angle above deadband', () => {
      // Construct bytes that result in sumVal > 9500
      const data = new Uint8Array([
        0x09,
        0x00,
        0x06,
        0x00, // Lean encoding
        0x00,
        0x00,
        0x75,
        0x30, // Pitch
      ]);
      parseCan0x0258(data, state);

      // Should be above deadband threshold (> 9000 + 499)
      expect(state.lean).toBeGreaterThan(9000);
      expect(state.pitch).toBe(30000);
    });
  });

  describe('parseCan0x0260', () => {
    it('should parse brake pressures', () => {
      const data = new Uint8Array([
        0x01,
        0x40, // Front brake (320)
        0x00,
        0xa0, // Rear brake (160)
        0x00,
        0x00,
        0x00,
        0x00,
      ]);
      parseCan0x0260(data, state);

      expect(state.front_brake).toBe(320);
      expect(state.rear_brake).toBe(160);
    });
  });

  describe('parseCan0x0264', () => {
    it('should parse wheel speeds', () => {
      const data = new Uint8Array([
        0x19,
        0x00, // Front speed (6400)
        0x18,
        0x00, // Rear speed (6144)
      ]);
      parseCan0x0264(data, state);

      expect(state.front_speed).toBe(6400);
      expect(state.rear_speed).toBe(6144);
    });
  });

  describe('parseCan0x0268', () => {
    it('should parse ABS flags', () => {
      const data = new Uint8Array([0x00, 0x00, 0x00, 0x00, 0x03, 0x00]);
      parseCan0x0268(data, state);

      expect(state.r_abs).toBe(true); // Bit 0
      expect(state.f_abs).toBe(true); // Bit 1
    });

    it('should parse ABS flags independently', () => {
      const data = new Uint8Array([0x00, 0x00, 0x00, 0x00, 0x01, 0x00]);
      parseCan0x0268(data, state);

      expect(state.r_abs).toBe(true);
      expect(state.f_abs).toBe(false);
    });
  });
});
