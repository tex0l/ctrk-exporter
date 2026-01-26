/*
 * Native library initialization and path utilities.
 */
package com.yamaha.jp.dataviewer.jni

import android.app.Application
import android.content.Context
import android.util.Log

/**
 * Manages lifecycle of the native parsing library.
 */
class JNISupport private constructor(ctx: Context) {
    private val appContext: Context = ctx.applicationContext

    private external fun Initialize(): Int

    init {
        try {
            val result = Initialize()
            Log.d(LOG_TAG, "Native init returned: $result")
        } catch (e: Exception) {
            Log.e(LOG_TAG, "Init exception: ${e.message}")
        }
    }

    companion object {
        private const val LOG_TAG = "LibLoader"
        private const val LIB_NAME = "SensorsRecordIF"

        @Volatile
        private var loader: JNISupport? = null

        init {
            try {
                System.loadLibrary(LIB_NAME)
                Log.d(LOG_TAG, "Loaded: $LIB_NAME")
            } catch (e: UnsatisfiedLinkError) {
                Log.e(LOG_TAG, "Load failed: ${e.message}")
            }
        }

        @JvmStatic
        fun init(app: Application) {
            if (loader == null) {
                synchronized(this) {
                    if (loader == null) {
                        loader = JNISupport(app)
                    }
                }
            }
        }

        @JvmStatic
        fun init(ctx: Context) {
            if (loader == null) {
                synchronized(this) {
                    if (loader == null) {
                        loader = JNISupport(ctx)
                    }
                }
            }
        }

        @JvmStatic
        fun isInitialized(): Boolean = loader != null

        @JvmStatic
        fun getTemporaryDirectoryPath(): String =
            loader?.appContext?.externalCacheDir?.absolutePath ?: ""

        @JvmStatic
        fun getDefaultDirectoryPath(): String =
            loader?.appContext?.getExternalFilesDir(null)?.path ?: ""
    }
}
