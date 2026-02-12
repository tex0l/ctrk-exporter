#!/usr/bin/env node

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, basename, join } from 'node:path';
import { CTRKParser } from '@tex0l/ctrk-parser';
import { formatCalibratedCsv, formatRawCsv } from './csv-export.js';

function main(): void {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] !== 'parse') {
    console.log('Usage: ctrk-parser parse <file.CTRK>... [-o OUTPUT_DIR] [--raw]');
    process.exit(1);
  }

  const files: string[] = [];
  let outputDir: string | null = null;
  let raw = false;

  for (let i = 1; i < args.length; i++) {
    if (args[i] === '-o' || args[i] === '--output') {
      i++;
      outputDir = args[i];
    } else if (args[i] === '--raw') {
      raw = true;
    } else {
      files.push(args[i]);
    }
  }

  if (files.length === 0) {
    console.error('Error: No input files specified');
    process.exit(1);
  }

  let outDir: string;
  if (outputDir) {
    outDir = resolve(outputDir);
  } else {
    const now = new Date();
    const pad = (n: number): string => String(n).padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
    outDir = resolve('output', timestamp);
  }
  mkdirSync(outDir, { recursive: true });

  for (let idx = 0; idx < files.length; idx++) {
    const filePath = resolve(files[idx]);
    const stem = basename(filePath).replace(/\.[^.]+$/, '');

    console.log(`[${idx + 1}/${files.length}] Parsing ${basename(filePath)}...`);

    const data = new Uint8Array(readFileSync(filePath));
    const parser = new CTRKParser(data);
    const records = parser.parse();

    // The parser computes UTC timestamps, but CTRK timestamps represent local time.
    // Adjust to local time to match Python's datetime().timestamp() behavior.
    if (records.length > 0) {
      const tzOffsetMs = new Date(records[0].time_ms).getTimezoneOffset() * 60000;
      for (const r of records) {
        r.time_ms += tzOffsetMs;
      }
    }

    const csvPath = join(outDir, `${stem}_parsed.csv`);
    writeFileSync(csvPath, formatCalibratedCsv(records));
    console.log(`Exported ${records.length} records to ${csvPath}`);

    if (raw) {
      const rawPath = join(outDir, `${stem}_parsed.raw.csv`);
      writeFileSync(rawPath, formatRawCsv(records));
      console.log(`Exported ${records.length} raw records to ${rawPath}`);
    }
  }

  console.log(`\nOutput: ${outDir} (${files.length} files)`);
}

main();
