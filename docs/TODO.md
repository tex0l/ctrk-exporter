# TODO

## Parser / Spec Discrepancies

### Timestamp Source (Section 6)
**Issue:** The spec says timestamps use milliseconds from the file structure (2 bytes before GPRMC), but the parser uses milliseconds from the GPRMC sentence itself (e.g., `"144110.300"` → 300ms).

**Files:**
- `docs/CTRK_FORMAT_SPECIFICATION.md` Section 6
- `src/ctrk_parser.py` lines 660-691 (`_compute_timestamp`)

**Action:** Verify which source the native library uses, then align spec and parser.

---

### Year Encoding (Section 4.2)
**Issue:** The spec says `07 E9 = year 2025 encoded as little-endian (0xE907 = 2025)` but this is incorrect. `0x07E9 = 2025` in big-endian, not little-endian.

**Files:**
- `docs/CTRK_FORMAT_SPECIFICATION.md` Section 4.2

**Action:** Correct the endianness description.

---

### CAN Record Data Offset (Section 8.1)
**Issue:** The spec says CAN data starts at offset 7 (after 2-byte Flags at offset 5), but the parser reads data at offset 8 (`self.data[pos+8:pos+16]`).

**Files:**
- `docs/CTRK_FORMAT_SPECIFICATION.md` Section 8.1
- `src/ctrk_parser.py` line 588

**Action:** Hex dump a CAN record to verify the exact structure and offsets.
