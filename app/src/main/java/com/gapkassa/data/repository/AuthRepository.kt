package com.gapkassa.data.repository

import com.gapkassa.data.preferences.TokenStore
import com.gapkassa.data.remote.BackendApi
import com.gapkassa.data.remote.LoginRequest
import com.gapkassa.data.remote.RegisterRequest
import com.gapkassa.data.remote.RegisterVerifyRequest
import com.gapkassa.data.remote.RefreshRequest
import com.gapkassa.data.remote.LogoutRequest
import com.gapkassa.data.remote.UserDto

/**
 * Authentication gateway backed by the local/remote API.
 */
class AuthRepository(
    private val api: BackendApi,
    private val tokenStore: TokenStore
) {
    val currentUserId: String?
        get() = tokenStore.userId

    val currentEmail: String?
        get() = tokenStore.userEmail

    suspend fun requestRegisterOtp(
        email: String,
        password: String,
        name: String?,
        lastName: String?,
        patronymic: String?,
        phone: String?
    ): Result<Unit> = runCatching {
        api.requestRegisterOtp(
            RegisterRequest(
                email = email,
                password = password,
                name = name,
                lastName = lastName,
                patronymic = patronymic,
                phone = phone
            )
        )
    }

    suspend fun verifyRegisterOtp(email: String, code: String): Result<UserDto> = runCatching {
        val response = api.verifyRegisterOtp(RegisterVerifyRequest(email, code))
        tokenStore.accessToken = response.accessToken
        tokenStore.refreshToken = response.refreshToken
        tokenStore.userId = response.user.id
        tokenStore.userEmail = response.user.email
        response.user
    }

    suspend fun login(email: String, password: String): Result<UserDto> = runCatching {
        val response = api.login(LoginRequest(email, password))
        tokenStore.accessToken = response.accessToken
        tokenStore.refreshToken = response.refreshToken
        tokenStore.userId = response.user.id
        tokenStore.userEmail = response.user.email
        response.user
    }

    suspend fun refreshTokens(): Result<Unit> = runCatching {
        val refreshToken = tokenStore.refreshToken ?: error("No refresh token")
        val response = api.refresh(RefreshRequest(refreshToken))
        tokenStore.accessToken = response.accessToken
        tokenStore.refreshToken = response.refreshToken
        tokenStore.userId = response.user.id
        tokenStore.userEmail = response.user.email
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
}
