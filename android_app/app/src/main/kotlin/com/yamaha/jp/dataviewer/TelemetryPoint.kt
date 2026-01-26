/*
 * Telemetry data container for native library interop.
 * Field identifiers are constrained by JNI binding requirements.
 */
package com.yamaha.jp.dataviewer

/**
 * Single telemetry sample from a CTRK recording session.
 * Populated by the native parsing library via JNI reflection.
 */
class SensorsRecord {
    // Timing and position
    @JvmField var mTime: Long = 0
    @JvmField var mLat: Float = 9999.0f
    @JvmField var mLon: Float = 9999.0f
    @JvmField var mGpsSpeedKnot: Float = 0.0f

    // Powertrain sensors
    @JvmField var mRPM: Char = 0.toChar()
    @JvmField var mAPS: Short = 0
    @JvmField var mTPS: Short = 0
    @JvmField var mGEAR: Byte = 0

    // Thermal readings
    @JvmField var mWT: Short = 0
    @JvmField var mINTT: Short = 0

    // Velocity sensors
    @JvmField var mFSPEED: Short = 0
    @JvmField var mRSPEED: Short = 0

    // Hydraulic pressure
    @JvmField var mFPRESS: Short = 0
    @JvmField var mRPRESS: Short = 0

    // Orientation and dynamics
    @JvmField var mLEAN: Char = 0.toChar()
    @JvmField var mPITCH: Char = 0.toChar()
    @JvmField var mACCX: Short = 0
    @JvmField var mACCY: Short = 0

    // Consumption
    @JvmField var mFUEL: Int = 0

    // Electronic systems state
    @JvmField var mFABS: Boolean = false
    @JvmField var mRABS: Boolean = false
    @JvmField var mLAUNCH: Byte = 0
    @JvmField var mSCS: Byte = 0
    @JvmField var mTCS: Byte = 0
    @JvmField var mLIF: Byte = 0

    // External inputs
    @JvmField var mAIN1: String = ""
    @JvmField var mAIN2: String = ""

    // Bus frames
    @JvmField var mCAN0511: Long = 0
    @JvmField var mCAN051B: Long = 0
    @JvmField var mCAN0226: Long = 0
    @JvmField var mCAN0227: Long = 0

    fun hasValidCoordinates(): Boolean = mLon < 1000.0f && mLat < 1000.0f

    /**
     * Format with engineering unit conversions applied.
     */
    fun formatCalibrated(): String {
        val engineSpeed = mRPM.code / 2.56
        val gripPosition = ((mAPS / 8.192) * 100.0) / 84.96
        val valvePosition = ((mTPS / 8.192) * 100.0) / 84.96
        val coolantTemp = (mWT / 1.6) - 30.0
        val airTemp = (mINTT / 1.6) - 30.0
        val frontVelocity = (mFSPEED / 64.0) * 3.6
        val rearVelocity = (mRSPEED / 64.0) * 3.6
        val fuelUsed = mFUEL / 100.0
        val rollAngle = (mLEAN.code / 100.0) - 90.0
        val pitchRate = (mPITCH.code / 100.0) - 300.0
        val lateralG = (mACCX / 1000.0) - 7.0
        val longitudinalG = (mACCY / 1000.0) - 7.0
        val frontPressure = mFPRESS / 32.0
        val rearPressure = mRPRESS / 32.0

        return String.format(
            "%.0f,%.6f,%.6f,%.2f,%.0f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.2f,%.1f,%.1f,%.2f,%.2f,%.1f,%.1f,%d,%b,%b,%d,%d,%d,%d",
            mTime.toDouble(), mLat, mLon, mGpsSpeedKnot * 1.852f,
            engineSpeed, gripPosition, valvePosition, coolantTemp, airTemp,
            frontVelocity, rearVelocity, fuelUsed, rollAngle, pitchRate, lateralG, longitudinalG,
            frontPressure, rearPressure, mGEAR.toInt(),
            mFABS, mRABS, mTCS.toInt(), mSCS.toInt(), mLIF.toInt(), mLAUNCH.toInt()
        )
    }

    /**
     * Format with unprocessed sensor values.
     */
    fun formatRaw(): String = String.format(
        "%d,%.6f,%.6f,%.4f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%b,%b,%d,%d,%d,%d",
        mTime, mLat, mLon, mGpsSpeedKnot,
        mRPM.code, mAPS.toInt(), mTPS.toInt(), mWT.toInt(), mINTT.toInt(),
        mFSPEED.toInt(), mRSPEED.toInt(), mFUEL,
        mLEAN.code, mPITCH.code, mACCX.toInt(), mACCY.toInt(),
        mFPRESS.toInt(), mRPRESS.toInt(), mGEAR.toInt(),
        mFABS, mRABS, mTCS.toInt(), mSCS.toInt(), mLIF.toInt(), mLAUNCH.toInt()
    )

    override fun toString(): String =
        "TelemetryPoint[t=$mTime, rpm=${mRPM.code}, roll=${mLEAN.code}, gear=$mGEAR]"

    companion object {
        @JvmStatic
        fun calibratedCsvHeader(): String =
            "time_ms,latitude,longitude,gps_speed_kmh,rpm,throttle_grip,throttle,water_temp,intake_temp," +
            "front_speed_kmh,rear_speed_kmh,fuel_cc,lean_deg,pitch_deg_s,acc_x_g,acc_y_g," +
            "front_brake_bar,rear_brake_bar,gear,f_abs,r_abs,tcs,scs,lif,launch"

        @JvmStatic
        fun rawCsvHeader(): String =
            "time_ms,latitude,longitude,gps_speed_knots,rpm_raw,aps_raw,tps_raw,wt_raw,intt_raw," +
            "fspeed_raw,rspeed_raw,fuel_raw,lean_raw,pitch_raw,accx_raw,accy_raw," +
            "fpress_raw,rpress_raw,gear,f_abs,r_abs,tcs,scs,lif,launch"
    }
}
