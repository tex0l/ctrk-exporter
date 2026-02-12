#!/usr/bin/env node
/**
 * Test script for parsing a real CTRK file with the TypeScript parser.
 */

import { readFileSync } from 'fs';
import { CTRKParser } from './dist/index.js';

const filename = process.argv[2] || '../../input/20250729-170818.CTRK';

console.log(`Loading file: ${filename}`);
const data = readFileSync(filename);
const uint8Data = new Uint8Array(data.buffer, data.byteOffset, data.byteLength);

console.log(`File size: ${uint8Data.length.toLocaleString()} bytes`);
console.log('Parsing...\n');

const parser = new CTRKParser(uint8Data);
const records = parser.parse();

console.log('\nSample records (first 5):');
for (let i = 0; i < Math.min(5, records.length); i++) {
  const r = records[i];
  console.log(`\nRecord ${i + 1}:`);
  console.log(`  Lap: ${r.lap}`);
  console.log(`  Time: ${new Date(r.time_ms).toISOString()}`);
  console.log(`  GPS: ${r.latitude.toFixed(6)}, ${r.longitude.toFixed(6)} (${r.gps_speed_knots.toFixed(2)} knots)`);
  console.log(`  RPM: ${r.rpm}, Gear: ${r.gear}`);
  console.log(`  Throttle: TPS=${r.tps}, APS=${r.aps}`);
  console.log(`  Lean: ${r.lean} (signed: ${r.lean_signed}), Pitch: ${r.pitch}`);
  console.log(`  Brake: Front=${r.front_brake}, Rear=${r.rear_brake}`);
  console.log(`  Fuel: ${r.fuel}`);
}

console.log(`\nTotal records: ${records.length}`);
console.log(`Laps detected: ${Math.max(...records.map(r => r.lap))}`);
