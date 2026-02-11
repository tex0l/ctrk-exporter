import { describe, it, expect } from 'vitest';
import { sideOfLine, crossesLine } from './finish-line.js';
import type { FinishLine } from './types.js';

describe('Finish Line', () => {
  const finishLine: FinishLine = {
    p1_lat: 47.95,
    p1_lng: 0.21,
    p2_lat: 47.95,
    p2_lng: 0.22,
  };

  describe('sideOfLine', () => {
    it('should return positive for point on one side', () => {
      const side = sideOfLine(finishLine, 47.951, 0.215);
      expect(side).toBeGreaterThan(0);
    });

    it('should return negative for point on opposite side', () => {
      const side = sideOfLine(finishLine, 47.949, 0.215);
      expect(side).toBeLessThan(0);
    });

    it('should return zero for point on line', () => {
      const side = sideOfLine(finishLine, 47.95, 0.215);
      expect(Math.abs(side)).toBeLessThan(1e-10);
    });
  });

  describe('crossesLine', () => {
    it('should detect crossing when trajectory crosses finish line', () => {
      const lat1 = 47.949;
      const lng1 = 0.215;
      const lat2 = 47.951;
      const lng2 = 0.215;

      expect(crossesLine(finishLine, lat1, lng1, lat2, lng2)).toBe(true);
    });

    it('should not detect crossing when both points on same side', () => {
      const lat1 = 47.949;
      const lng1 = 0.215;
      const lat2 = 47.9485;
      const lng2 = 0.215;

      expect(crossesLine(finishLine, lat1, lng1, lat2, lng2)).toBe(false);
    });

    it('should not detect crossing when intersection outside segment', () => {
      const lat1 = 47.949;
      const lng1 = 0.19; // Far left of finish line
      const lat2 = 47.951;
      const lng2 = 0.2;

      expect(crossesLine(finishLine, lat1, lng1, lat2, lng2)).toBe(false);
    });

    it('should handle parallel trajectories', () => {
      const lat1 = 47.951;
      const lng1 = 0.21;
      const lat2 = 47.951;
      const lng2 = 0.22;

      expect(crossesLine(finishLine, lat1, lng1, lat2, lng2)).toBe(false);
    });
  });
});
