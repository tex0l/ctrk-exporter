/*
 * Timing structures for lap-based telemetry segmentation.
 * Field identifiers are constrained by JNI binding requirements.
 */
package com.yamaha.jp.dataviewer

/**
 * Lap timing information filled by the native parser.
 */
class SensorsLapTimeRecord {
    @JvmField var mTime: Long = 0
    @JvmField var mRank: Byte = 0
    @JvmField var mNo: Byte = 0
}

/**
 * Geographic boundary defining the timing trigger zone.
 */
class SensorsRecordLine(
    @JvmField var mStartLat: Double = 0.0,
    @JvmField var mStartLon: Double = 0.0,
    @JvmField var mEndLat: Double = 0.0,
    @JvmField var mEndLon: Double = 0.0
) {
    override fun toString(): String =
        "TimingLine[origin=(%.6f,%.6f), terminus=(%.6f,%.6f)]".format(
            mStartLat, mStartLon, mEndLat, mEndLon
        )
}
