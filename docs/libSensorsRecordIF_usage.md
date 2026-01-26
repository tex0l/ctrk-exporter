# Documentation: libSensorsRecordIF.so Native Library Usage

## Overview

The `libSensorsRecordIF.so` native library is the core component of the Yamaha Y-trac Android application responsible for parsing CTRK/TRG telemetry files recorded by the CCU (Communication Control Unit) motorcycle data logger.

## 1. Library Loading and Initialization

### Location
- **Library file**: `libSensorsRecordIF.so`
- **Loading class**: `com.yamaha.jp.dataviewer.jni.JNISupport`

### Initialization Flow
```java
// JNISupport.java
static {
    System.loadLibrary("SensorsRecordIF");  // Loads libSensorsRecordIF.so
}

private native int Initialize();  // JNI callback for library initialization

private JNISupport(Context context) {
    this.context = context;
    Initialize();  // Called during construction
}

public static void init(Application application) {
    instance = new JNISupport(application);
    deleteSplittedFile();
}
```

The library is initialized in `AppApplication.onCreate()` when the Android application starts.

---

## 2. Native Method Declarations

All native methods are declared in `SensorsRecordIF.java`.

### 2.1 Initialization

| Method | Signature | Description |
|--------|-----------|-------------|
| `Initialize` | `private native int Initialize()` | Library initialization, called once at startup |

### 2.2 File Information Queries

| Method | Signature | Description |
|--------|-----------|-------------|
| `GetTotalLap` | `private static native int GetTotalLap(String fileName)` | Returns the total number of laps in a file |
| `GetRecordLineData` | `private static native int GetRecordLineData(String fileName, int[] count, SensorsRecordLine[] output)` | Gets track start/end GPS coordinates |
| `GetLapTimeRecordData` | `private static native int GetLapTimeRecordData(String fileName, int[] lapCount, SensorsLapTimeRecord[] output, boolean flag)` | Retrieves lap times and rankings |

### 2.3 Sensor Data Loading

| Method | Signature | Description |
|--------|-----------|-------------|
| `GetSensorsRecordData` | `private native int GetSensorsRecordData(String fileName, int fileType, int lapIndex, SensorsRecord[] output, int maxRecords, int[] actualCount, AINInfo ainInfo)` | Loads sensor records indexed by timestamp |
| `GetSensorsDistanceRecordData` | `private native int GetSensorsDistanceRecordData(String fileName, int fileType, int lapIndex, int maxRecords, float distanceInterval, SensorsRecord[] output, int[] actualCount)` | Loads sensor records indexed by distance traveled |

### 2.4 File Operations

| Method | Signature | Description |
|--------|-----------|-------------|
| `SplitLogFile` | `private native int SplitLogFile(String inputPath, String outputPath, Object result)` | Splits/compresses log files |
| `DamageRecoveryLogFile` | `private static native int DamageRecoveryLogFile(String inputPath, String outputPath, boolean performRecovery)` | Detects and recovers corrupted data |
| `TimeStampRecoveryLogFile` | `private static native int TimeStampRecoveryLogFile(String inputPath, String outputPath)` | Recovers missing timestamp data |

### 2.5 Encryption

| Method | Signature | Description |
|--------|-----------|-------------|
| `GetEncryptSecretKey` | `public native String GetEncryptSecretKey()` | Returns AES encryption key for CTRZ/CSRZ files |

---

## 3. Data Structures

### 3.1 SensorsRecord - Main telemetry data point

This is the primary output structure populated by the native library. Each instance represents one sample point.

```java
public class SensorsRecord {
    // Timing
    public long mTime = 0;                    // Timestamp in milliseconds

    // GPS Data
    public float mLat = 9999.0f;              // Latitude (9999.0 = invalid)
    public float mLon = 9999.0f;              // Longitude (9999.0 = invalid)
    public float mGpsSpeedKnot = 0.0f;        // GPS speed in knots

    // Engine Data
    public char mRPM = 0;                     // Engine RPM (NOTE: char = 16-bit unsigned)
    public byte mGEAR = 0;                    // Current gear (0-6)

    // Throttle Data
    public short mAPS = 0;                    // Accelerator Position Sensor (grip position)
    public short mTPS = 0;                    // Throttle Position Sensor (butterfly valve)

    // Wheel Speed
    public short mFSPEED = 0;                 // Front wheel speed (raw)
    public short mRSPEED = 0;                 // Rear wheel speed (raw)

    // Motion/IMU Data
    public char mLEAN = 0;                    // Lean angle (raw)
    public char mPITCH = 0;                   // Pitch angle (raw)
    public short mACCX = 0;                   // X-axis acceleration (raw)
    public short mACCY = 0;                   // Y-axis acceleration (raw)

    // Brake Data
    public short mFPRESS = 0;                 // Front brake pressure (raw)
    public short mRPRESS = 0;                 // Rear brake pressure (raw)

    // Temperature
    public short mWT = 0;                     // Water temperature (raw)
    public short mINTT = 0;                   // Intake air temperature (raw)

    // Fuel
    public int mFUEL = 0;                     // Fuel consumption (raw)

    // Electronic Control Systems Status
    public boolean mFABS = false;             // Front ABS active
    public boolean mRABS = false;             // Rear ABS active
    public byte mTCS = 0;                     // Traction Control System status
    public byte mSCS = 0;                     // Slide Control System status
    public byte mLIF = 0;                     // Lift Control status
    public byte mLAUNCH = 0;                  // Launch Control status

    // Analog Inputs (external sensors)
    public String mAIN1 = "";                 // Analog input 1 data
    public String mAIN2 = "";                 // Analog input 2 data

    // Raw CAN frames (for debugging/custom analysis)
    public long mCAN0511 = 0;                 // CAN frame 0x0511
    public long mCAN051B = 0;                 // CAN frame 0x051B
    public long mCAN0226 = 0;                 // CAN frame 0x0226
    public long mCAN0227 = 0;                 // CAN frame 0x0227
}
```

### 3.2 SensorsLapTimeRecord - Lap summary

```java
public class SensorsLapTimeRecord {
    public long mTime = 0;      // Lap time in milliseconds
    public byte mRank = 0;      // Ranking compared to other laps
    public byte mNo = 0;        // Lap number
}
```

### 3.3 SensorsRecordLine - Track boundaries

```java
public class SensorsRecordLine {
    public double mStartLat;    // Starting point latitude
    public double mStartLon;    // Starting point longitude
    public double mEndLat;      // Ending point latitude
    public double mEndLon;      // Ending point longitude
}
```

### 3.4 LoggerFile.AINInfo - Analog input configuration

```java
public static class AINInfo {
    public boolean mAIN1Valid = false;    // Is AIN1 data present
    public boolean mAIN2Valid = false;    // Is AIN2 data present
    public byte mAIN1Format = 0;          // AIN1 data format/scale
    public byte mAIN2Format = 0;          // AIN2 data format/scale
}
```

---

## 4. Return Codes

```java
public static final int RET_NORMAL = 0;              // Success
public static final int RET_ERROR = -1;              // General error
public static final int RET_TIMESTAMP_ERROR = -2;    // Timestamp parsing error
public static final int RET_READSIZE_OVER = -3;      // Read buffer exceeded
public static final int RET_EMPTY = -4;              // File is empty
public static final int RET_LAPSPLIT_FAILED = -201;  // Lap split failed

// Bitmask flags (can be OR'd with success)
public static final int RET_DAMAGE_RECOVERY = 64;    // Damage recovery was performed
public static final int RET_TIME_STAMP_RECOVERY = 128; // Timestamp recovery was performed
```

---

## 5. File Types

```java
// File extensions
public static final String CCT = "CCT";      // Uncompressed telemetry (.CTRK)
public static final String TRG = "TRG";      // Trigger/compressed format

// File type constants for native methods
public static final int FILE_TYPE_CCT = 0;   // CCT format
public static final int FILE_TYPE_TRG = 1;   // TRG format

// Encrypted variants
public static final String ENCRYPT_EXT_CCT = "CTRZ";  // Encrypted CCT
public static final String ENCRYPT_EXT_TRG = "CSRZ";  // Encrypted TRG
```

---

## 6. Data Processing Flow

### 6.1 Complete File Processing Sequence

```
1. JNISupport.init()           → Initialize native library
2. GetTotalLap(fileName)       → Get lap count
3. GetRecordLineData()         → Get track GPS boundaries
4. GetLapTimeRecordData()      → Get lap times summary
5. GetSensorsRecordData()      → Load full telemetry data
   OR
   GetSensorsDistanceRecordData() → Load distance-sampled data
```

### 6.2 Detailed Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Start                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  JNISupport.init(application)                               │
│  ├── System.loadLibrary("SensorsRecordIF")                  │
│  └── Initialize() [NATIVE]                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  User selects .CTRK file                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  SensorsRecordIF.prepare(loggerFile)                        │
│  ├── Check if file exists                                   │
│  ├── GetTotalLap(fileName) [NATIVE]                         │
│  │   └── Returns lap count (or 0 if damaged)                │
│  └── loggerFile.setTotalLap(count)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Optional: Damage Detection/Recovery                         │
│  ├── DamageRecoveryLogFile(file, null, false) [NATIVE]      │
│  │   └── Returns RET_DAMAGE_RECOVERY if damage detected     │
│  └── If damaged:                                             │
│      ├── DamageRecoveryLogFile(file, output, true)          │
│      └── TimeStampRecoveryLogFile(file, output)             │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Load Lap Information                                        │
│  ├── GetLapTimeRecordData() [NATIVE]                        │
│  │   └── Fills SensorsLapTimeRecord[] with times/ranks      │
│  └── GetRecordLineData() [NATIVE]                           │
│      └── Fills SensorsRecordLine with GPS start/end         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Load Sensor Data (per lap)                                  │
│  ├── Allocate SensorsRecord[72000]                          │
│  ├── GetSensorsRecordData() [NATIVE]                        │
│  │   ├── fileName: path to .CTRK file                       │
│  │   ├── fileType: 0=CCT, 1=TRG                             │
│  │   ├── lapIndex: 0-based lap index                        │
│  │   ├── output: SensorsRecord array to fill                │
│  │   ├── maxRecords: 72000                                  │
│  │   ├── actualCount[]: returns actual records loaded       │
│  │   └── ainInfo: receives AIN configuration                │
│  └── Store in LoggerFile.mLapRecords[lap]                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Data Ready for Display                                      │
│  ├── SensorsRecord[] contains all telemetry points          │
│  ├── Each SensorsRecord has raw values from native lib      │
│  └── Java code applies calibration for display              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Encryption Details

### Algorithm Configuration
- **Algorithm**: AES (Advanced Encryption Standard)
- **Mode**: CFB8 (Cipher Feedback, 8-bit)
- **Padding**: NoPadding
- **IV**: 16 bytes of zeros
- **Key**: Retrieved from native library via `GetEncryptSecretKey()`

### Java Implementation
```java
public static Cipher setupEncrypt(int mode) throws Exception {
    String key = SensorsRecordIF.getInstance().GetEncryptSecretKey();
    IvParameterSpec iv = new IvParameterSpec(new byte[16]); // All zeros
    Cipher cipher = Cipher.getInstance("AES/CFB8/NoPadding");
    cipher.init(mode, new SecretKeySpec(key.getBytes(), "AES"), iv);
    return cipher;
}
```

---

## 8. Constants

```java
// Maximum records per lap
public static final int RECORD_SIZE_MAX = 72000;

// GPS coordinate validation
public static final float LAT_DEFAULT = 9999.0f;  // Invalid marker
public static final float LON_DEFAULT = 9999.0f;  // Invalid marker

public static boolean IsEffectiveLonLat(float coord) {
    return coord < 1000.0f;  // Valid if < 1000
}
```

---

## 9. Java Files Using the Native Library

### Core JNI Files
- `com/yamaha/jp/dataviewer/jni/JNISupport.java` - Library loading
- `com/yamaha/jp/dataviewer/SensorsRecordIF.java` - Native method declarations

### Data Structures
- `com/yamaha/jp/dataviewer/SensorsRecord.java`
- `com/yamaha/jp/dataviewer/SensorsRecordLine.java`
- `com/yamaha/jp/dataviewer/SensorsLapRecord.java`
- `com/yamaha/jp/dataviewer/SensorsLapTimeRecord.java`
- `com/yamaha/jp/dataviewer/LoggerFile.java`

### UI Components
- `com/yamaha/jp/dataviewer/ChartViewFragment.java`
- `com/yamaha/jp/dataviewer/GraphViewFragment.java`
- `com/yamaha/jp/dataviewer/MapViewFragment.java`

### Utilities
- `com/yamaha/jp/dataviewer/util/CipherFileIo.java` - Encryption wrapper
- `com/yamaha/jp/dataviewer/util/SeriesDispInfo.java` - Display calibration factors

---

## 10. Calibration Factors (from SeriesDispInfo.java)

The native library returns **raw values**. The Java application applies calibration for display:

| Sensor | Formula | Unit |
|--------|---------|------|
| RPM | raw / 2.56 | RPM |
| Wheel Speed | raw / 64.0 | km/h |
| Brake Pressure | raw / 32.0 | bar |
| Lean Angle | (raw / 100.0) - 90.0 | degrees |
| Pitch Rate | (raw / 100.0) - 300.0 | deg/s |
| Acceleration | (raw / 1000.0) - 7.0 | G |
| Temperature | (raw / 1.6) - 30.0 | °C |
| Throttle | raw / 8.192 | % |
| Fuel | raw / 100.0 | - |

**Note**: These calibration factors from the APK may not match the actual raw values in the file. The native library may apply additional processing before returning values to Java.

---

## 11. Native Library Architectures

Available in the APK for multiple platforms:
- `arm64-v8a/libSensorsRecordIF.so` - ARM64 (modern Android)
- `armeabi-v7a/libSensorsRecordIF.so` - ARM32 (older Android)
- `x86/libSensorsRecordIF.so` - x86 (emulators)
- `x86_64/libSensorsRecordIF.so` - x86_64 (emulators)
