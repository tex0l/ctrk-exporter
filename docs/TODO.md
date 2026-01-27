# TODO

## Optional: Native-Compatible Interpolation Mode

Implement optional timestamp smoothing and CAN interpolation to produce output closer to the native library:

```bash
./ctrk-exporter parse session.CTRK --interpolate-native
```

This would reduce the ~0.1% record count difference and improve per-sample matching rates.

**Priority:** Low (current output is functionally equivalent)

---

## Optional: Lap Detection

Parse lap timing data from CTRK files. The native library exposes `GetTotalLap()` and `GetLapTimeRecordData()` but the lap storage format is not yet documented.

**Priority:** Low

---

## Optional: Split/Recovery Functions

Implement equivalents of native `SplitLogFile()` and `DamageRecoveryLogFile()` functions.

**Priority:** Low
