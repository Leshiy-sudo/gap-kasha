package com.gapkassa.data.preferences

import android.content.Context
import com.gapkassa.data.remote.AppConfigResponse
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

class AppConfigStore(context: Context) {
    private val prefs = context.getSharedPreferences("gap_kassa_app_config", Context.MODE_PRIVATE)
    private val adapter = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()
        .adapter(AppConfigResponse::class.java)

    fun read(): AppConfigResponse? =
        prefs.getString(KEY_CONFIG, null)?.let { raw ->
            runCatching { adapter.fromJson(raw) }.getOrNull()
        }

    fun write(value: AppConfigResponse) {
        prefs.edit().putString(KEY_CONFIG, adapter.toJson(value)).apply()
    }

    private companion object {
        const val KEY_CONFIG = "cached_public_app_config"
    }
}
