package com.gapkassa.data.preferences

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.gapkassa.BuildConfig

class TokenStore(context: Context) {
    @Volatile
    private var cachedAccessToken: String? = null
    @Volatile
    private var cachedRefreshToken: String? = null
    @Volatile
    private var cachedUserId: String? = null
    @Volatile
    private var cachedUserEmail: String? = null
    private val prefs: SharedPreferences = runCatching {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            "gap_kassa_tokens",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }.getOrElse { error ->
        if (!BuildConfig.DEBUG) {
            throw IllegalStateException("Encrypted storage unavailable in release builds", error)
        }
        // Fallback for local/emulator environments where encrypted prefs might fail.
        context.getSharedPreferences("gap_kassa_tokens_plain", Context.MODE_PRIVATE)
    }

    var accessToken: String?
        get() = cachedAccessToken ?: prefs.getString(KEY_ACCESS, null)
        set(value) {
            cachedAccessToken = value
            prefs.edit().putString(KEY_ACCESS, value).apply()
        }

    var refreshToken: String?
        get() = cachedRefreshToken ?: prefs.getString(KEY_REFRESH, null)
        set(value) {
            cachedRefreshToken = value
            prefs.edit().putString(KEY_REFRESH, value).apply()
        }

    var userId: String?
        get() = cachedUserId ?: prefs.getString(KEY_USER_ID, null)
        set(value) {
            cachedUserId = value
            prefs.edit().putString(KEY_USER_ID, value).apply()
        }

    var userEmail: String?
        get() = cachedUserEmail ?: prefs.getString(KEY_USER_EMAIL, null)
        set(value) {
            cachedUserEmail = value
            prefs.edit().putString(KEY_USER_EMAIL, value).apply()
        }

    fun clear() {
        cachedAccessToken = null
        cachedRefreshToken = null
        cachedUserId = null
        cachedUserEmail = null
        prefs.edit().clear().apply()
    }

    private companion object {
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
        const val KEY_USER_ID = "user_id"
        const val KEY_USER_EMAIL = "user_email"
    }
}
