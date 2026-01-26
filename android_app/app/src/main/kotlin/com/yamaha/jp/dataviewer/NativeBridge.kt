/*
 * Native library bindings for CTRK file parsing.
 * Method signatures are constrained by the external library's JNI interface.
 */
package com.yamaha.jp.dataviewer

import android.util.Log

/**
 * Singleton providing access to native parsing functions.
 * Acts as a bridge between Kotlin code and the external native library.
 */
class SensorsRecordIF private constructor() {

    companion object {
        private const val LOG_TAG = "NativeBridge"

        // Format identifiers
        const val FILE_TYPE_CCT = 0
        const val FILE_TYPE_TRG = 1
        const val CCT = "CCT"
        const val TRG = "TRG"

        // Status codes
        const val RET_NORMAL = 0
        const val RET_ERROR = -1
        const val RET_TIMESTAMP_ERROR = -2
        const val RET_READSIZE_OVER = -3
        const val RET_EMPTY = -4
        const val RET_LAPSPLIT_FAILED = -201
        const val RET_DAMAGE_RECOVERY = 64
        const val RET_TIME_STAMP_RECOVERY = 128

        // Constraints
        const val RECORD_SIZE_MAX = 72000
        const val LAP_ALL = 0

        // Coordinate sentinel values
        const val LAT_DEFAULT = 9999.0f
        const val LON_DEFAULT = 9999.0f

        @JvmStatic
        private val bridge = SensorsRecordIF()
        private val sessions: MutableList<LoggerFile> = mutableListOf()
        private var maxSamples = RECORD_SIZE_MAX

        @JvmStatic
        fun getInstance(): SensorsRecordIF = bridge

        @JvmStatic
        fun IsEffectiveLonLat(coord: Float): Boolean = coord < 1000.0f

        @JvmStatic
        fun getTotalLap(path: String): Int = try {
            GetTotalLap(path)
        } catch (e: Exception) {
            Log.e(LOG_TAG, "Lap count retrieval failed: ${e.message}")
            RET_ERROR
        }

        @JvmStatic
        fun getLapTimeRecordData(path: String, count: Int, output: Array<SensorsLapTimeRecord>, flag: Boolean): Int = try {
            val countHolder = intArrayOf(count)
            GetLapTimeRecordData(path, countHolder, output, flag)
        } catch (e: Exception) {
            Log.e(LOG_TAG, "Timing data retrieval failed: ${e.message}")
            RET_ERROR
        }

        @JvmStatic
        fun getRecordLineData(path: String, output: Array<SensorsRecordLine>): Int = try {
            val countHolder = intArrayOf(1)
            GetRecordLineData(path, countHolder, output)
        } catch (e: Exception) {
            Log.e(LOG_TAG, "Track line retrieval failed: ${e.message}")
            RET_ERROR
        }

        @JvmStatic
        fun judgeDamageLogFile(path: String): Boolean = try {
            DamageRecoveryLogFile(path, null, false) == RET_DAMAGE_RECOVERY
        } catch (e: Exception) {
            Log.e(LOG_TAG, "Damage check failed: ${e.message}")
            false
        }

        // External function declarations
        @JvmStatic private external fun GetTotalLap(fileName: String): Int
        @JvmStatic private external fun GetLapTimeRecordData(fileName: String, lapCount: IntArray, output: Array<SensorsLapTimeRecord>, flag: Boolean): Int
        @JvmStatic private external fun GetRecordLineData(fileName: String, count: IntArray, output: Array<SensorsRecordLine>): Int
        @JvmStatic private external fun DamageRecoveryLogFile(input: String, output: String?, check: Boolean): Int
        @JvmStatic private external fun TimeStampRecoveryLogFile(input: String, output: String): Int
    }

    // Instance-level external declarations
    private external fun GetSensorsRecordData(fileName: String, fileType: Int, lapIndex: Int,
                                               output: Array<SensorsRecord>, maxRecords: Int,
                                               actualCount: IntArray, ainInfo: LoggerFile.AINInfo): Int

    private external fun GetSensorsDistanceRecordData(fileName: String, fileType: Int, lapIndex: Int,
                                                       maxRecords: Int, distanceInterval: Float,
                                                       output: Array<SensorsRecord>, actualCount: IntArray): Int

    private external fun SplitLogFile(input: String, output: String, callback: Any?): Int
    external fun GetEncryptSecretKey(): String

    fun init(capacity: Int) {
        maxSamples = capacity
        sessions.clear()
        sessions.add(LoggerFile())
    }

    fun getSensorsRecordData(path: String, formatType: Int, lapIdx: Int,
                             output: Array<SensorsRecord>, maxCount: Int,
                             actualCount: IntArray, auxInfo: LoggerFile.AINInfo): Int = try {
        GetSensorsRecordData(path, formatType, lapIdx, output, maxCount, actualCount, auxInfo)
    } catch (e: Exception) {
        Log.e(LOG_TAG, "Record data retrieval failed: ${e.message}")
        RET_ERROR
    }

    fun getSensorsDistanceRecordData(path: String, formatType: Int, lapIdx: Int,
                                     maxCount: Int, interval: Float,
                                     output: Array<SensorsRecord>, actualCount: IntArray): Int = try {
        GetSensorsDistanceRecordData(path, formatType, lapIdx, maxCount, interval, output, actualCount)
    } catch (e: Exception) {
        Log.e(LOG_TAG, "Distance-based retrieval failed: ${e.message}")
        RET_ERROR
    }
}
