# Bug Report: CTRK-Exporter Web Edition

**Date:** 2026-02-07
**Reporter:** QA Agent

---

## Bug #1: formatDelta() Missing Negative Sign

**Severity:** Low
**Priority:** Medium
**Status:** Open
**Component:** Lap Timing (lap-timing.ts)

### Description

The `formatDelta()` function incorrectly formats negative delta times by omitting the negative sign.

### Location

**File:** `/Users/timotheerebours/PersonalProjects/louis-file/web/src/lib/lap-timing.ts`
**Lines:** 146-150

### Current Behavior

```typescript
formatDelta(-567)   // Returns: "0.567" (WRONG)
formatDelta(1234)   // Returns: "+1.234" (correct)
formatDelta(0)      // Returns: "+0.000" (correct)
```

### Expected Behavior

```typescript
formatDelta(-567)   // Should return: "-0.567"
formatDelta(1234)   // Should return: "+1.234"
formatDelta(0)      // Should return: "+0.000"
```

### Root Cause

The sign variable is set to empty string for negative values, but then the absolute value is used:

```typescript
const sign = delta_ms >= 0 ? '+' : '';  // Empty string for negative
const seconds = Math.abs(delta_ms) / 1000;  // Always positive
return `${sign}${seconds.toFixed(3)}`;  // No negative sign
```

### Proposed Fix

Change line 147 to:

```typescript
const sign = delta_ms >= 0 ? '+' : '-';
```

**Complete Fixed Function:**

```typescript
export function formatDelta(delta_ms: number): string {
  const sign = delta_ms >= 0 ? '+' : '-';
  const seconds = Math.abs(delta_ms) / 1000;
  return `${sign}${seconds.toFixed(3)}`;
}
```

### Test Case

```typescript
it('should format negative deltas with - sign', () => {
  expect(formatDelta(-567)).toBe('-0.567');  // Currently FAILS
});
```

### Impact

**User-Facing:**
- Lap timing table shows deltas without negative signs
- Users cannot visually distinguish slower laps from faster laps
- CSV exports have incorrect delta formatting

**Technical:**
- No data corruption
- No functional breakage
- Purely a display issue

**Workaround:** None. Users must mentally note that missing signs indicate slower laps.

### Steps to Reproduce

1. Upload any CTRK file with multiple laps
2. Navigate to lap timing table
3. Observe delta column for laps slower than best lap
4. Notice missing negative sign

### Environment

- All browsers
- All platforms
- Web Edition v0.1.0

### Related Files

- `/Users/timotheerebours/PersonalProjects/louis-file/web/src/components/LapTimingTable.vue` - Uses formatDelta()
- `/Users/timotheerebours/PersonalProjects/louis-file/web/src/lib/export-utils.ts` - May use formatDelta() for CSV export

### Verification

After fix, run:

```bash
cd /Users/timotheerebours/PersonalProjects/louis-file/web
npm test
```

Verify test "should format negative deltas with - sign" passes.

---

**Fix Effort:** 1 line change, 5 minutes
**Test Effort:** 1 minute (automated test already exists)
**Release Blocker:** No (cosmetic issue)
