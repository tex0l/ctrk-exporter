# APK Analysis & Native Library Extraction

This directory contains tools and documentation for extracting the native library
from the official Y-Trac APK for use with the CTRK Converter app.

> **Tested with Y-Trac version 1.3.8**
>
> **Platform:** macOS ARM (Apple Silicon) only

## Prerequisites

- **jadx** - APK decompiler: `brew install jadx`
- **unzip** - Standard tool for extracting APK contents
- **curl** or **wget** - For downloading the APK

## Quick Setup

Use the main CLI tool which handles everything:

```bash
./ctrk-exporter android setup
```

The CLI will prompt you to download the APK automatically (at your own risk) or manually.

Once you have the APK, it will:
1. Extract `libSensorsRecordIF.so` for all architectures
2. Copy them to the Android app's jniLibs directory
3. Build and install the converter app

## Manual Steps

### 1. Download the APK

Download the official Y-Trac app APK from one of these sources:
- [APKPure - Y-Trac](https://apkpure.com/y-trac/com.yamaha.jp.dataviewer)
- [APKMirror](https://www.apkmirror.com/?s=y-trac)

Or use ADB to pull it from a device where it's installed:
```bash
adb shell pm path com.yamaha.jp.dataviewer
adb pull /path/to/base.apk ytrac.apk
```

### 2. Extract the Native Library

APK files are ZIP archives. Extract the .so file:

```bash
unzip ytrac.apk -d ytrac_extracted
cp ytrac_extracted/lib/arm64-v8a/libSensorsRecordIF.so \
   ../android_app/app/src/main/jniLibs/arm64-v8a/
```

### 3. (Optional) Decompile for Analysis

To analyze the Java code:
```bash
jadx -d ytrac_decompiled ytrac.apk
```

Key files to examine:
- `com/yamaha/jp/dataviewer/SensorsRecordIF.java` - JNI interface
- `com/yamaha/jp/dataviewer/SensorsRecord.java` - Data structures
- `com/yamaha/jp/dataviewer/util/SeriesDispInfo.java` - Calibration formulas

## Native Library Architectures

The Y-Trac APK includes native libraries for multiple architectures:
- `arm64-v8a` - 64-bit ARM (most modern devices, recommended)
- `armeabi-v7a` - 32-bit ARM
- `x86` - Intel 32-bit (emulators)
- `x86_64` - Intel 64-bit (emulators)

For emulator testing, you may need to extract x86_64:
```bash
cp ytrac_extracted/lib/x86_64/libSensorsRecordIF.so \
   ../android_app/app/src/main/jniLibs/x86_64/
```

## Important Notes

- The native library (`libSensorsRecordIF.so`) is proprietary Yamaha code
- It is NOT included in this repository to avoid copyright issues
- You must extract it yourself from the official APK for personal use
- Do not redistribute the extracted library
