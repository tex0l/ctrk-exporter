import { describe, it, expect } from 'vitest';
import { validateNmeaChecksum, parseGprmcSentence } from './nmea-parser.js';

describe('nmea-parser', () => {
  describe('validateNmeaChecksum', () => {
    it('should validate correct checksum', () => {
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*65';
      expect(validateNmeaChecksum(sentence)).toBe(true);
    });

    it('should reject incorrect checksum', () => {
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*FF';
      expect(validateNmeaChecksum(sentence)).toBe(false);
    });

    it('should reject sentence without asterisk', () => {
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A';
      expect(validateNmeaChecksum(sentence)).toBe(false);
    });

    it('should reject sentence with truncated checksum', () => {
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*6';
      expect(validateNmeaChecksum(sentence)).toBe(false);
    });

    it('should reject empty sentence', () => {
      expect(validateNmeaChecksum('')).toBe(false);
    });

    it('should reject sentence with invalid hex checksum', () => {
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*GG';
      expect(validateNmeaChecksum(sentence)).toBe(false);
    });
  });

  describe('parseGprmcSentence', () => {
    it('should parse valid GPRMC sentence with status A', () => {
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*65';
      const result = parseGprmcSentence(sentence);

      expect(result).not.toBeNull();
      expect(result?.latitude).toBeCloseTo(47.950683, 5);
      expect(result?.longitude).toBeCloseTo(0.208733, 5);
      expect(result?.speed_knots).toBeCloseTo(5.14, 2);
    });

    it('should convert latitude degrees-minutes correctly', () => {
      // 47°57.0410' N = 47 + (57.0410 / 60) = 47.950683
      const sentence = '$GPRMC,120000.000,A,4757.0410,N,00000.0000,E,0.00,0.00,010125,,,A*6E';
      const result = parseGprmcSentence(sentence);
      expect(result?.latitude).toBeCloseTo(47.950683, 5);
    });

    it('should convert longitude degrees-minutes correctly', () => {
      // 000°12.5240' E = 0 + (12.5240 / 60) = 0.208733
      const sentence = '$GPRMC,120000.000,A,0000.0000,N,00012.5240,E,0.00,0.00,010125,,,A*6A';
      const result = parseGprmcSentence(sentence);
      expect(result?.longitude).toBeCloseTo(0.208733, 5);
    });

    it('should apply negative sign for southern hemisphere', () => {
      const sentence = '$GPRMC,120000.000,A,4757.0410,S,00012.5240,E,0.00,0.00,010125,,,A*73';
      const result = parseGprmcSentence(sentence);
      expect(result?.latitude).toBeCloseTo(-47.950683, 5);
    });

    it('should apply negative sign for western hemisphere', () => {
      const sentence = '$GPRMC,120000.000,A,4757.0410,N,00012.5240,W,0.00,0.00,010125,,,A*7C';
      const result = parseGprmcSentence(sentence);
      expect(result?.longitude).toBeCloseTo(-0.208733, 5);
    });

    it('should return null for status V (void)', () => {
      const sentence = '$GPRMC,122135.000,V,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*72';
      const result = parseGprmcSentence(sentence);
      expect(result).toBeNull();
    });

    it('should handle zero speed', () => {
      const sentence = '$GPRMC,120000.000,A,4757.0410,N,00012.5240,E,0.00,0.00,010125,,,A*6E';
      const result = parseGprmcSentence(sentence);
      expect(result?.speed_knots).toBe(0.0);
    });

    it('should handle empty speed field', () => {
      const sentence = '$GPRMC,120000.000,A,4757.0410,N,00012.5240,E,,0.00,010125,,,A*70';
      const result = parseGprmcSentence(sentence);
      expect(result?.speed_knots).toBe(0.0);
    });

    it('should return null for malformed sentence (insufficient fields)', () => {
      const sentence = '$GPRMC,120000.000,A';
      const result = parseGprmcSentence(sentence);
      expect(result).toBeNull();
    });

    it('should return null for invalid coordinate format', () => {
      const sentence = '$GPRMC,120000.000,A,XX,N,00012.5240,E,0.00,0.00,010125,,,A*XX';
      const result = parseGprmcSentence(sentence);
      expect(result).toBeNull();
    });

    it('should parse real-world example from spec', () => {
      // Example from CTRK_FORMAT_SPECIFICATION.md
      const sentence = '$GPRMC,122135.000,A,4757.0410,N,00012.5240,E,5.14,334.60,290725,,,A*65';
      const result = parseGprmcSentence(sentence);

      expect(result).not.toBeNull();
      // Lat: 47 + (57.0410 / 60) = 47.950683
      expect(result?.latitude).toBeCloseTo(47.950683, 5);
      // Lon: 0 + (12.5240 / 60) = 0.208733
      expect(result?.longitude).toBeCloseTo(0.208733, 5);
      expect(result?.speed_knots).toBeCloseTo(5.14, 2);
    });
  });
});
