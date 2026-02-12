import { describe, it, expect } from 'vitest';
import { Calibration } from './calibration.js';

describe('Calibration', () => {
  describe('rpm', () => {
    it('should convert raw RPM to engine RPM', () => {
      expect(Calibration.rpm(25600)).toBe(10000);
      expect(Calibration.rpm(0)).toBe(0);
      expect(Calibration.rpm(2560)).toBe(1000);
    });

    it('should truncate RPM to integer', () => {
      expect(Calibration.rpm(25601)).toBe(10000); // 10000.390625 -> 10000
      expect(Calibration.rpm(2561)).toBe(1000); // 1000.390625 -> 1000
    });
  });

  describe('wheelSpeedKmh', () => {
    it('should convert raw wheel speed to km/h', () => {
      expect(Calibration.wheelSpeedKmh(6400)).toBe(360.0);
      expect(Calibration.wheelSpeedKmh(0)).toBe(0.0);
      expect(Calibration.wheelSpeedKmh(64)).toBe(3.6);
    });
  });

  describe('throttle', () => {
    it('should convert raw throttle to percentage', () => {
      // Formula: ((raw / 8.192) * 100) / 84.96
      // Test with a known value
      const result = Calibration.throttle(6963);
      expect(result).toBeCloseTo(1000.44, 1); // Actual result
      expect(Calibration.throttle(0)).toBe(0.0);

      // Test with a value that gives ~100%: 696 -> ~10%
      expect(Calibration.throttle(696)).toBeCloseTo(100.04, 1);
    });
  });

  describe('brake', () => {
    it('should convert raw brake pressure to bar', () => {
      expect(Calibration.brake(320)).toBe(10.0);
      expect(Calibration.brake(0)).toBe(0.0);
      expect(Calibration.brake(32)).toBe(1.0);
    });
  });

  describe('lean', () => {
    it('should convert raw lean angle to degrees', () => {
      expect(Calibration.lean(9000)).toBe(0.0);
      expect(Calibration.lean(12000)).toBe(30.0);
      expect(Calibration.lean(6000)).toBe(-30.0);
    });
  });

  describe('pitch', () => {
    it('should convert raw pitch rate to deg/s', () => {
      expect(Calibration.pitch(30000)).toBe(0.0);
      expect(Calibration.pitch(31000)).toBe(10.0);
      expect(Calibration.pitch(29000)).toBe(-10.0);
    });
  });

  describe('acceleration', () => {
    it('should convert raw acceleration to G', () => {
      expect(Calibration.acceleration(7000)).toBe(0.0);
      expect(Calibration.acceleration(8000)).toBe(1.0);
      expect(Calibration.acceleration(6000)).toBe(-1.0);
    });
  });

  describe('temperature', () => {
    it('should convert raw temperature to Celsius', () => {
      expect(Calibration.temperature(176)).toBe(80.0);
      expect(Calibration.temperature(48)).toBe(0.0);
    });
  });

  describe('fuel', () => {
    it('should convert raw fuel to cc', () => {
      expect(Calibration.fuel(10000)).toBe(100.0);
      expect(Calibration.fuel(0)).toBe(0.0);
      expect(Calibration.fuel(100)).toBe(1.0);
    });
  });

  describe('gpsSpeedKmh', () => {
    it('should convert knots to km/h', () => {
      expect(Calibration.gpsSpeedKmh(54.0)).toBeCloseTo(100.008, 3);
      expect(Calibration.gpsSpeedKmh(0)).toBe(0.0);
    });
  });
});
