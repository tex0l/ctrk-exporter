/*
 * Container structures for organizing parsed telemetry sessions.
 */
package com.yamaha.jp.dataviewer

/**
 * Holds telemetry samples for one lap segment.
 */
class SensorsLapRecord(private val idx: Int) {
    private var samples: Array<SensorsRecord>? = null
    private var timing: SensorsLapTimeRecord? = null
    private var displayableCount: Int = 0

    constructor(idx: Int, capacity: Int) : this(idx) {
        preallocate(capacity)
    }

    fun preallocate(capacity: Int) {
        samples = Array(capacity) { SensorsRecord() }
    }

    fun getLapIndex(): Int = idx
    fun getRecords(): Array<SensorsRecord>? = samples
    fun setRecords(data: Array<SensorsRecord>) { samples = data }
    fun getDispCount(): Int = displayableCount
    fun setDispCount(count: Int) { displayableCount = count }
    fun getLapTimeRecord(): SensorsLapTimeRecord? = timing
    fun setLapTimeRecord(record: SensorsLapTimeRecord) { timing = record }

    override fun toString(): String =
        "LapSegment[idx=$idx, samples=${samples?.size ?: 0}, visible=$displayableCount]"
}

/**
 * Top-level container for a complete telemetry file.
 */
class LoggerFile {
    private var sourceName: String = ""
    private var formatType: Int = 0
    private var lapCount: Int = 0
    private var corrupted: Boolean = false
    private var activeLaps: IntArray? = null
    private var timingLine: SensorsRecordLine? = null
    private var auxInputs: AINInfo = AINInfo()
    private val segments: MutableList<SensorsLapRecord> = mutableListOf()
    private var samplingMode: ParseType? = null

    class AINInfo {
        @JvmField var mAIN1Valid: Boolean = false
        @JvmField var mAIN2Valid: Boolean = false
        @JvmField var mAIN1Format: Byte = 0
        @JvmField var mAIN2Format: Byte = 0
    }

    enum class ParseType(val code: Int) {
        DISTANCE(0),
        TIMESTAMP(1)
    }

    fun reset() {
        timingLine = null
        segments.clear()
        lapCount = 0
        activeLaps = null
        auxInputs = AINInfo()
        corrupted = false
        sourceName = ""
        formatType = 0
    }

    fun getFileName(): String = sourceName

    fun setFileName(name: String) {
        sourceName = name
        val extension = name.substringAfterLast('.').uppercase()
        formatType = if (extension == SensorsRecordIF.TRG) SensorsRecordIF.FILE_TYPE_TRG else SensorsRecordIF.FILE_TYPE_CCT
    }

    fun getFileType(): Int = formatType
    fun isBroken(): Boolean = corrupted
    fun setBroken(flag: Boolean) { corrupted = flag }

    fun getTotalLap(): Int = if (corrupted) 0 else lapCount

    fun setTotalLap(count: Int) {
        lapCount = count
        segments.clear()
        repeat(count) { i -> segments.add(SensorsLapRecord(i)) }
    }

    fun getCurrentLap(): Int = activeLaps?.firstOrNull() ?: 0
    fun getSelectedLaps(): IntArray? = activeLaps
    fun setSelectedLaps(laps: IntArray) { activeLaps = laps }

    fun getLapRecord(index: Int): SensorsLapRecord = segments[index]
    fun getLapRecord(): SensorsLapRecord = getLapRecord(getCurrentLap())

    fun getRecords(lapIndex: Int): Array<SensorsRecord>? = segments[lapIndex].getRecords()
    fun getRecords(): Array<SensorsRecord>? = getRecords(getCurrentLap())

    fun getRecord(recordIndex: Int, lapIndex: Int): SensorsRecord? = getRecords(lapIndex)?.get(recordIndex)
    fun getRecord(recordIndex: Int): SensorsRecord? = getRecord(recordIndex, getCurrentLap())

    fun getDispCount(lapIndex: Int): Int = segments[lapIndex].getDispCount()
    fun getDispCount(): Int = getDispCount(getCurrentLap())

    fun setDispCount(count: Int, lapIndex: Int) { segments[lapIndex].setDispCount(count) }
    fun setDispCount(count: Int) { setDispCount(count, getCurrentLap()) }

    fun getLapTimeRecord(index: Int): SensorsLapTimeRecord? = segments[index].getLapTimeRecord()
    fun getLapTimeRecord(): SensorsLapTimeRecord? = getLapTimeRecord(getCurrentLap())

    fun getLapTimeRecords(): Array<SensorsLapTimeRecord?> =
        Array(segments.size) { segments[it].getLapTimeRecord() }

    fun setLapTimeRecord(record: SensorsLapTimeRecord, lapIndex: Int) {
        while (segments.size <= lapIndex) {
            segments.add(SensorsLapRecord(segments.size))
        }
        segments[lapIndex].setLapTimeRecord(record)
    }

    fun setLapTimeRecord(record: SensorsLapTimeRecord) { setLapTimeRecord(record, getCurrentLap()) }

    fun setLapTimeRecords(records: Array<SensorsLapTimeRecord>) {
        records.forEachIndexed { i, r -> setLapTimeRecord(r, i) }
    }

    fun getRecordLine(): SensorsRecordLine? = timingLine
    fun setRecordLine(line: SensorsRecordLine) { timingLine = line }

    fun getAINInfo(): AINInfo = auxInputs
    fun getParseType(): ParseType? = samplingMode
    fun setParseType(type: ParseType) { samplingMode = type }
}
