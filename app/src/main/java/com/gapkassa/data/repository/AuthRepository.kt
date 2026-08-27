package com.gapkassa.data.repository

import com.gapkassa.data.preferences.TokenStore
import com.gapkassa.data.remote.BackendApi
import com.gapkassa.data.remote.PhoneAuthStartRequest
import com.gapkassa.data.remote.PhoneAuthVerifyRequest
import com.gapkassa.data.remote.RefreshRequest
import com.gapkassa.data.remote.LogoutRequest
import com.gapkassa.data.remote.AuthResponse
import com.gapkassa.data.remote.UserDto

/**
 * Authentication gateway backed by the local/remote API. Auth is phone number +
 * one-time code delivered via Telegram (Telegram Gateway API) — there is no
 * separate registration step, a first successful code verification creates the
 * account.
 */
class AuthRepository(
    private val api: BackendApi,
    private val tokenStore: TokenStore
) {
    val hasStoredSession: Boolean
        get() = tokenStore.hasStoredSession
    val hasStoredSessionFlow = tokenStore.hasStoredSessionFlow

    val currentUserId: String?
        get() = tokenStore.userId

    val currentPhone: String?
        get() = tokenStore.userPhone

    suspend fun startPhoneAuth(phone: String): Result<Unit> = runCatching {
        api.startPhoneAuth(PhoneAuthStartRequest(phone))
    }

    suspend fun verifyPhoneAuth(phone: String, code: String): Result<UserDto> = runCatching {
        val response = api.verifyPhoneAuth(PhoneAuthVerifyRequest(phone, code))
        persistAuth(response)
        response.user
    }

    suspend fun refreshTokens(): Result<Unit> = runCatching {
        val refreshToken = tokenStore.refreshToken ?: error("No refresh token")
        val response = api.refresh(RefreshRequest(refreshToken))
        persistAuth(response)
    }

    private fun persistAuth(response: AuthResponse) {
        tokenStore.saveSession(
            accessToken = response.accessToken,
            refreshToken = response.refreshToken,
            userId = response.user.id,
            userPhone = response.user.phone
        )
    }

    fun logout() {
        tokenStore.clear()
    }

    suspend fun logoutRemote(): Result<Unit> = runCatching {
        val refreshToken = tokenStore.refreshToken
        if (refreshToken != null) {
            api.logout(LogoutRequest(refreshToken))
        } else {
            api.logout(LogoutRequest(null))
        }
        tokenStore.clear()
    }

    suspend fun deleteAccount(): Result<Unit> = runCatching {
        api.deleteMe()
        tokenStore.clear()
    }
}
