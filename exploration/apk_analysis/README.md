# APK Analysis & Native Library Extraction

This directory contains tools and documentation for extracting the native library (`libSensorsRecordIF.so`) from the official Y-Trac Android APK.

> **Tested with:** Y-Trac version 1.3.8
>
> **Platform:** macOS ARM (Apple Silicon) only

## Overview

The Y-Trac Android app includes a native library that parses CTRK telemetry files. This library can be extracted from the APK and used via Android emulator to produce reference output for validation.

## Prerequisites

### Required Tools

| Tool | Installation | Purpose |
|------|--------------|---------|
| unzip | Built-in | Extract APK contents |
| Android SDK | Manual install | Emulator runtime |
| ADB | Part of Android SDK | Device/emulator communication |

### Optional Tools

| Tool | Installation | Purpose |
|------|--------------|---------|
| jadx | `brew install jadx` | Decompile Java/Kotlin code |
| radare2 | `brew install radare2` | Disassemble native library |

## Quick Setup

The main CLI handles extraction automatically:

```bash
./ctrk-exporter android setup
```

This will:
1. Prompt you to download the APK (manual step)
2. Extract `libSensorsRecordIF.so` for all architectures
3. Copy libraries to the Android app's jniLibs directory
4. Build the converter app
5. Install on the emulator

## Manual Extraction

### Step 1: Obtain the APK

Download the official Y-Trac app APK from one of these sources:

- [APKPure - Y-Trac](https://apkpure.com/y-trac/com.yamaha.jp.dataviewer)
- [APKMirror](https://www.apkmirror.com/?s=y-trac)

Or extract from a device where it's installed:

```bash
# Find the APK path on device
adb shell pm path com.yamaha.jp.dataviewer
# Output: package:/data/app/.../base.apk

# Pull the APK
adb pull /data/app/.../base.apk ytrac.apk
```

### Step 2: Extract the APK

APK files are ZIP archives:

```bash
# Create extraction directory
mkdir -p ytrac_extracted

# Extract all contents
unzip ytrac.apk -d ytrac_extracted

# View native library architectures
ls ytrac_extracted/lib/
# Output: arm64-v8a  armeabi-v7a  x86  x86_64
```

### Step 3: Copy Native Libraries

Copy the libraries to the Android app's jniLibs directory:

```bash
# For ARM64 devices (most common)
mkdir -p ../android_app/app/src/main/jniLibs/arm64-v8a
cp ytrac_extracted/lib/arm64-v8a/libSensorsRecordIF.so \
   ../android_app/app/src/main/jniLibs/arm64-v8a/

# For x86_64 emulator
mkdir -p ../android_app/app/src/main/jniLibs/x86_64
cp ytrac_extracted/lib/x86_64/libSensorsRecordIF.so \
   ../android_app/app/src/main/jniLibs/x86_64/
```

### Step 4: Verify Extraction

Check the library was extracted correctly:

```bash
# Check file type
file ytrac_extracted/lib/arm64-v8a/libSensorsRecordIF.so
# Output: ELF 64-bit LSB shared object, ARM aarch64...

# Check exported symbols
nm -D ytrac_extracted/lib/arm64-v8a/libSensorsRecordIF.so | grep -i sensor
# Should show JNI function names
```

## Native Library Architectures

The Y-Trac APK includes libraries for multiple platforms:

| Architecture | Directory | Use Case |
|--------------|-----------|----------|
| arm64-v8a | `lib/arm64-v8a/` | Modern Android phones (64-bit ARM) |
| armeabi-v7a | `lib/armeabi-v7a/` | Older Android phones (32-bit ARM) |
| x86_64 | `lib/x86_64/` | Android emulator on Intel/AMD hosts |
| x86 | `lib/x86/` | Older Android emulators |

**Note:** For Apple Silicon Macs, use `arm64-v8a` with an ARM-based emulator image.

## Decompiling for Analysis (Optional)

To examine the Java/Kotlin code:

```bash
# Decompile the entire APK
jadx -d ytrac_decompiled ytrac.apk

# Key files to examine:
# - com/yamaha/jp/dataviewer/SensorsRecordIF.java  (JNI interface)
# - com/yamaha/jp/dataviewer/SensorsRecord.java    (Data structures)
# - com/yamaha/jp/dataviewer/util/SeriesDispInfo.java (Calibration formulas)
```

To analyze the native library:

```bash
# List all functions
r2 -q -c 'aaa; afl' ytrac_extracted/lib/x86_64/libSensorsRecordIF.so

# Disassemble a specific function
r2 -q -c 'aaa; s sym.GetSensorsRecordData; pdf' ytrac_extracted/lib/x86_64/libSensorsRecordIF.so
```

## Troubleshooting

### APK Download Issues

If APKPure or APKMirror are unavailable:
1. Install Y-Trac on a physical Android device
2. Use ADB to extract as shown in Step 1

### Library Not Found Errors

If the Android app crashes with "library not found":
1. Check the emulator architecture matches the library
2. For ARM Mac + ARM emulator: use `arm64-v8a`
3. For Intel Mac + Intel emulator: use `x86_64`

### Emulator Won't Start

```bash
# List available AVDs
~/Library/Android/sdk/emulator/emulator -list-avds

# Create a new AVD if needed
~/Library/Android/sdk/cmdline-tools/latest/bin/avdmanager create avd \
  -n test_device -k "system-images;android-34;google_apis;arm64-v8a" -d pixel_6
```

## Important Notes

- The native library (`libSensorsRecordIF.so`) is proprietary Yamaha code
- It is **NOT** included in this repository
- You must extract it yourself from the official APK
- Do not redistribute the extracted library
- This extraction is for personal/research use only
