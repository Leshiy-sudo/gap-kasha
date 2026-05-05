package com.gapkassa.data.preferences

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.gapkassa.BuildConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

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
    private val _hasStoredSession = MutableStateFlow(computeHasStoredSession())
    val hasStoredSessionFlow: StateFlow<Boolean> = _hasStoredSession

    var accessToken: String?
        get() = cachedAccessToken ?: prefs.getString(KEY_ACCESS, null)
        set(value) {
            cachedAccessToken = value
            prefs.edit().putString(KEY_ACCESS, value).apply()
            publishSessionState()
        }

    var refreshToken: String?
        get() = cachedRefreshToken ?: prefs.getString(KEY_REFRESH, null)
        set(value) {
            cachedRefreshToken = value
            prefs.edit().putString(KEY_REFRESH, value).apply()
            publishSessionState()
        }

    var userId: String?
        get() = cachedUserId ?: prefs.getString(KEY_USER_ID, null)
        set(value) {
            cachedUserId = value
            prefs.edit().putString(KEY_USER_ID, value).apply()
            publishSessionState()
        }

    var userEmail: String?
        get() = cachedUserEmail ?: prefs.getString(KEY_USER_EMAIL, null)
        set(value) {
            cachedUserEmail = value
            prefs.edit().putString(KEY_USER_EMAIL, value).apply()
        }

    val hasStoredSession: Boolean
        get() = computeHasStoredSession()

    fun saveSession(
        accessToken: String,
        refreshToken: String,
        userId: String,
        userEmail: String
    ) {
        cachedAccessToken = accessToken
        cachedRefreshToken = refreshToken
        cachedUserId = userId
        cachedUserEmail = userEmail
        prefs.edit()
            .putString(KEY_ACCESS, accessToken)
            .putString(KEY_REFRESH, refreshToken)
            .putString(KEY_USER_ID, userId)
            .putString(KEY_USER_EMAIL, userEmail)
            .apply()
        publishSessionState()
    }

    fun clear() {
        cachedAccessToken = null
        cachedRefreshToken = null
        cachedUserId = null
        cachedUserEmail = null
        prefs.edit().clear().commit()
        publishSessionState()
    }

    private fun computeHasStoredSession(): Boolean {
        val storedUserId = cachedUserId ?: prefs.getString(KEY_USER_ID, null)
        val storedAccessToken = cachedAccessToken ?: prefs.getString(KEY_ACCESS, null)
        val storedRefreshToken = cachedRefreshToken ?: prefs.getString(KEY_REFRESH, null)
        return !storedUserId.isNullOrBlank() &&
            (!storedAccessToken.isNullOrBlank() || !storedRefreshToken.isNullOrBlank())
    }

    private fun publishSessionState() {
        _hasStoredSession.value = computeHasStoredSession()
    }

    private companion object {
        const val KEY_ACCESS = "access_token"
        const val KEY_REFRESH = "refresh_token"
        const val KEY_USER_ID = "user_id"
        const val KEY_USER_EMAIL = "user_email"
    }
}
