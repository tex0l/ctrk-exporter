/*
 * Telemetry file converter UI.
 * Scans for recording files and exports them to CSV format.
 */
package com.ctrk.converter

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Environment
import android.util.Log
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.yamaha.jp.dataviewer.LoggerFile
import com.yamaha.jp.dataviewer.SensorsLapTimeRecord
import com.yamaha.jp.dataviewer.SensorsRecord
import com.yamaha.jp.dataviewer.SensorsRecordIF
import com.yamaha.jp.dataviewer.SensorsRecordLine
import com.yamaha.jp.dataviewer.jni.JNISupport
import java.io.File
import java.io.FileWriter
import java.io.PrintWriter

/**
 * Single-screen interface for batch telemetry conversion.
 */
class MainActivity : AppCompatActivity() {
    private lateinit var outputArea: TextView
    private val outputBuffer = StringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildInterface()
        requestStorageAccess()
        loadNativeLib()
    }

    private fun buildInterface() {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(16, 16, 16, 16)
        }

        val header = TextView(this).apply {
            text = "CTRK Converter"
            textSize = 24f
        }
        container.addView(header)

        val actionBtn = Button(this).apply {
            text = "Convert CTRK Files"
            setOnClickListener { startConversion() }
        }
        container.addView(actionBtn)

        val scrollPane = ScrollView(this)
        outputArea = TextView(this).apply {
            textSize = 12f
            setPadding(8, 8, 8, 8)
        }
        scrollPane.addView(outputArea)

        val scrollParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.MATCH_PARENT, 1f
        )
        scrollPane.layoutParams = scrollParams
        container.addView(scrollPane)

        setContentView(container)
    }

    private fun requestStorageAccess() {
        val required = arrayOf(
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE
        )
        val missing = required.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, missing.toTypedArray(), STORAGE_REQUEST)
        }
    }

    private fun loadNativeLib() {
        appendLog("Loading native library...")
        try {
            JNISupport.init(this)
            appendLog("Library ready: ${JNISupport.isInitialized()}")
        } catch (ex: Exception) {
            appendLog("ERROR: ${ex.message}")
        }
    }

    private fun appendLog(text: String) {
        Log.d(TAG, text)
        outputBuffer.append(text).append("\n")
        runOnUiThread { outputArea.text = outputBuffer.toString() }
    }

    private fun startConversion() {
        Thread { scanAndProcess() }.start()
    }

    private fun scanAndProcess() {
        appendLog("\n=== Starting Conversion ===\n")

        val searchLocations = listOf(
            Environment.getExternalStorageDirectory().path,
            "${Environment.getExternalStorageDirectory().path}/Download",
            getExternalFilesDir(null)?.path ?: "",
            "/sdcard/Download"
        )

        for (location in searchLocations) {
            val folder = File(location)
            if (!folder.exists() || !folder.isDirectory) continue

            appendLog("Scanning: $location")
            val recordings = folder.listFiles { _, name ->
                name.uppercase().let { it.endsWith(".CTRK") || it.endsWith(".CCT") }
            }

            recordings?.forEach { recording ->
                appendLog("\nProcessing: ${recording.name}")
                processFile(recording.absolutePath)
            }
        }

        appendLog("\n=== Complete ===")
    }

    private fun processFile(inputPath: String) {
        val sourceFile = File(inputPath)
        val baseName = sourceFile.nameWithoutExtension

        val calibratedPath = File(sourceFile.parent, "${baseName}_native.csv").absolutePath
        val rawPath = File(sourceFile.parent, "${baseName}_native_raw.csv").absolutePath

        appendLog("Output: $calibratedPath")

        try {
            var lapTotal = SensorsRecordIF.getTotalLap(inputPath)
            if (lapTotal <= 0) lapTotal = 1
            appendLog("Laps detected: $lapTotal")

            // Retrieve lap timing info
            val lapTimings = Array(lapTotal) { SensorsLapTimeRecord() }
            SensorsRecordIF.getLapTimeRecordData(inputPath, lapTotal, lapTimings, false)

            lapTimings.forEachIndexed { idx, timing ->
                val ms = timing.mTime
                appendLog("  Lap ${idx + 1}: ${ms / 60000}:%02d.%03d".format((ms % 60000) / 1000, ms % 1000))
            }

            // Retrieve track boundary
            val boundary = arrayOf(SensorsRecordLine())
            if (SensorsRecordIF.getRecordLineData(inputPath, boundary) == 0) {
                appendLog("  Track boundary: ${boundary[0]}")
            }

            val formatCode = if (inputPath.uppercase().endsWith(".TRG")) 1 else 0

            PrintWriter(FileWriter(calibratedPath)).use { calibratedWriter ->
                PrintWriter(FileWriter(rawPath)).use { rawWriter ->
                    calibratedWriter.println("lap,${SensorsRecord.calibratedCsvHeader()}")
                    rawWriter.println("lap,${SensorsRecord.rawCsvHeader()}")

                    var totalSamples = 0
                    val parser = SensorsRecordIF.getInstance()

                    for (lapIdx in 0 until lapTotal) {
                        appendLog("Extracting lap ${lapIdx + 1}...")

                        val samples = Array(SensorsRecordIF.RECORD_SIZE_MAX) { SensorsRecord() }
                        val sampleCount = intArrayOf(0)
                        val auxChannels = LoggerFile.AINInfo()

                        val status = parser.getSensorsRecordData(
                            inputPath, formatCode, lapIdx,
                            samples, SensorsRecordIF.RECORD_SIZE_MAX, sampleCount, auxChannels
                        )

                        if (status != 0) {
                            appendLog("  Error code: $status")
                            continue
                        }

                        appendLog("  Samples: ${sampleCount[0]}")

                        for (i in 0 until sampleCount[0]) {
                            val sample = samples[i]
                            calibratedWriter.println("${lapIdx + 1},${sample.formatCalibrated()}")
                            rawWriter.println("${lapIdx + 1},${sample.formatRaw()}")
                        }

                        totalSamples += sampleCount[0]
                    }

                    appendLog("Total samples exported: $totalSamples")
                }
            }

        } catch (ex: Exception) {
            appendLog("ERROR: ${ex.message}")
            ex.printStackTrace()
        }
    }

    companion object {
        private const val TAG = "TelemetryConverter"
        private const val STORAGE_REQUEST = 100
    }
}
