package com.gapkassa.data.repository

import android.content.Context
import com.gapkassa.data.preferences.PendingCrashReport
import com.gapkassa.data.preferences.PendingCrashReportStore
import com.gapkassa.data.preferences.TokenStore
import com.gapkassa.data.remote.BackendApi

class FatalCrashHandler(
    private val context: Context,
    private val tokenStore: TokenStore,
    private val crashReportStore: PendingCrashReportStore,
    private val previousHandler: Thread.UncaughtExceptionHandler?
) : Thread.UncaughtExceptionHandler {

    override fun uncaughtException(thread: Thread, throwable: Throwable) {
        runCatching {
            crashReportStore.write(
                PendingCrashReport.capture(
                    context = context,
                    thread = thread,
                    throwable = throwable,
                    tokenStore = tokenStore
                )
            )
        }
        previousHandler?.uncaughtException(thread, throwable)
    }
}

class ClientErrorRepository(
    private val api: BackendApi,
    private val crashReportStore: PendingCrashReportStore
) {
    suspend fun flushPendingFatalReport() {
        val report = crashReportStore.read() ?: return
        runCatching {
            api.reportClientError(report.toRequest())
        }.onSuccess {
            crashReportStore.clear()
        }
    }
}
