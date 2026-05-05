package com.gapkassa.data.preferences

import android.content.Context
import android.content.SharedPreferences
import android.os.Build
import com.gapkassa.BuildConfig
import com.gapkassa.data.remote.ClientErrorReportRequest
import org.json.JSONObject
import java.io.PrintWriter
import java.io.StringWriter
import java.time.Instant
import java.util.UUID

data class PendingCrashReport(
    val kind: String,
    val reportId: String,
    val occurredAt: String,
    val exceptionType: String?,
    val message: String,
    val stacktrace: String?,
    val threadName: String?,
    val appVersion: String,
    val buildType: String,
    val packageName: String,
    val apiBaseUrl: String,
    val deviceModel: String,
    val androidVersion: String,
    val userId: String?,
    val userEmail: String?
) {
    fun toRequest(): ClientErrorReportRequest = ClientErrorReportRequest(
        kind = kind,
        reportId = reportId,
        occurredAt = occurredAt,
        exceptionType = exceptionType,
        message = message,
        stacktrace = stacktrace,
        threadName = threadName,
        appVersion = appVersion,
        buildType = buildType,
        packageName = packageName,
        apiBaseUrl = apiBaseUrl,
        deviceModel = deviceModel,
        androidVersion = androidVersion,
        userId = userId,
        userEmail = userEmail
    )

    fun toJson(): String = JSONObject().apply {
        put("kind", kind)
        put("report_id", reportId)
        put("occurred_at", occurredAt)
        put("exception_type", exceptionType)
        put("message", message)
        put("stacktrace", stacktrace)
        put("thread_name", threadName)
        put("app_version", appVersion)
        put("build_type", buildType)
        put("package_name", packageName)
        put("api_base_url", apiBaseUrl)
        put("device_model", deviceModel)
        put("android_version", androidVersion)
        put("user_id", userId)
        put("user_email", userEmail)
    }.toString()

    companion object {
        fun capture(
            context: Context,
            thread: Thread,
            throwable: Throwable,
            tokenStore: TokenStore
        ): PendingCrashReport {
            val stackWriter = StringWriter()
            throwable.printStackTrace(PrintWriter(stackWriter))
            return PendingCrashReport(
                kind = "fatal",
                reportId = UUID.randomUUID().toString(),
                occurredAt = Instant.now().toString(),
                exceptionType = throwable::class.java.name,
                message = throwable.message ?: throwable::class.java.simpleName,
                stacktrace = stackWriter.toString(),
                threadName = thread.name,
                appVersion = BuildConfig.VERSION_NAME,
                buildType = if (BuildConfig.DEBUG) "debug" else "release",
                packageName = context.packageName,
                apiBaseUrl = BuildConfig.API_BASE_URL,
                deviceModel = Build.MODEL.orEmpty(),
                androidVersion = Build.VERSION.RELEASE.orEmpty(),
                userId = tokenStore.userId,
                userEmail = tokenStore.userEmail
            )
        }

        fun fromJson(raw: String): PendingCrashReport? = runCatching {
            val json = JSONObject(raw)
            PendingCrashReport(
                kind = json.optString("kind", "fatal"),
                reportId = json.optString("report_id"),
                occurredAt = json.optString("occurred_at"),
                exceptionType = json.optString("exception_type").ifBlank { null },
                message = json.optString("message"),
                stacktrace = json.optString("stacktrace").ifBlank { null },
                threadName = json.optString("thread_name").ifBlank { null },
                appVersion = json.optString("app_version"),
                buildType = json.optString("build_type"),
                packageName = json.optString("package_name"),
                apiBaseUrl = json.optString("api_base_url"),
                deviceModel = json.optString("device_model"),
                androidVersion = json.optString("android_version"),
                userId = json.optString("user_id").ifBlank { null },
                userEmail = json.optString("user_email").ifBlank { null }
            )
        }.getOrNull()
    }
}

class PendingCrashReportStore(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("gap_kassa_crash_reports", Context.MODE_PRIVATE)

    fun write(report: PendingCrashReport) {
        prefs.edit().putString(KEY_PENDING_REPORT, report.toJson()).commit()
    }

    fun read(): PendingCrashReport? {
        val raw = prefs.getString(KEY_PENDING_REPORT, null) ?: return null
        return PendingCrashReport.fromJson(raw)
    }

    fun clear() {
        prefs.edit().remove(KEY_PENDING_REPORT).commit()
    }

    private companion object {
        const val KEY_PENDING_REPORT = "pending_report"
    }
}
