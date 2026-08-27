package com.gapkassa.viewmodel

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.BuildConfig
import com.gapkassa.auth.TestIdentities
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import com.gapkassa.data.repository.RoomRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

private fun isLocalApiBuild(): Boolean {
    val url = BuildConfig.API_BASE_URL.lowercase()
    return url.contains("10.0.2.2") ||
        url.contains("127.0.0.1") ||
        url.contains("localhost")
}

data class AuthUiState(
    val isLoading: Boolean = false,
    val errorResId: Int? = null,
    val errorMessage: String? = null,
    val phone: String = "",
    val codeSent: Boolean = false,
    val isMockAvailable: Boolean = BuildConfig.DEBUG &&
        BuildConfig.PHONE_AUTH_ALLOW_MOCK &&
        isLocalApiBuild()
)

/**
 * Handles phone number + Telegram one-time code authentication. There is no
 * separate registration step: a first successful code verification for a phone
 * number creates the account.
 */
class AuthViewModel(
    private val authRepository: AuthRepository,
    private val profileRepository: ProfileRepository,
    private val roomRepository: RoomRepository,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    private val _state = MutableStateFlow(loadInitialState())
    val state: StateFlow<AuthUiState> = _state

    private fun loadInitialState(): AuthUiState {
        return AuthUiState(
            errorResId = savedStateHandle[KEY_ERROR_RES_ID],
            errorMessage = savedStateHandle[KEY_ERROR_MESSAGE],
        )
    }

    private fun persistState(state: AuthUiState) {
        savedStateHandle[KEY_ERROR_RES_ID] = state.errorResId
        savedStateHandle[KEY_ERROR_MESSAGE] = state.errorMessage
    }

    private fun updateState(transform: (AuthUiState) -> AuthUiState) {
        _state.update { current ->
            val updated = transform(current)
            persistState(updated)
            updated
        }
    }

    fun clearError() {
        updateState { it.copy(errorResId = null, errorMessage = null) }
    }

    /** Step 1: request a Telegram code for the given phone number. */
    fun startPhoneAuth(phone: String) {
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null, phone = phone) }
            val result = authRepository.startPhoneAuth(phone)
            if (result.isSuccess) {
                updateState { it.copy(isLoading = false, codeSent = true) }
            } else {
                applyBackendError(result.exceptionOrNull())
            }
        }
    }

    /** Step 2: verify the code the user typed in for the phone number from step 1. */
    fun verifyCode(code: String, onLoggedIn: () -> Unit) {
        val phone = _state.value.phone
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            finishVerification(phone, code, onLoggedIn)
        }
    }

    /** Debug-only quick login: runs both steps against the fixed mock code, no real Telegram round-trip. */
    fun loginAsTestIdentity(phone: String, onLoggedIn: () -> Unit) {
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null, phone = phone) }
            val startResult = authRepository.startPhoneAuth(phone)
            if (startResult.isFailure) {
                applyBackendError(startResult.exceptionOrNull())
                return@launch
            }
            finishVerification(phone, TestIdentities.MOCK_CODE, onLoggedIn)
        }
    }

    private suspend fun finishVerification(phone: String, code: String, onLoggedIn: () -> Unit) {
        val result = authRepository.verifyPhoneAuth(phone, code)
        if (result.isSuccess) {
            result.getOrNull()?.let { user ->
                profileRepository.cacheProfile(
                    UserProfile(
                        name = user.name.orEmpty(),
                        lastName = user.lastName.orEmpty(),
                        patronymic = user.patronymic.orEmpty(),
                        phone = user.phone,
                        photoUrl = user.photoUrl.orEmpty()
                    )
                )
                if (user.phone == TestIdentities.CREATOR.phone) {
                    runCatching {
                        roomRepository.ensureFixedTestRoom(
                            creatorPhone = TestIdentities.CREATOR.phone,
                            memberPhones = TestIdentities.MEMBERS.map { it.phone }
                        )
                    }
                }
            }
            runCatching { profileRepository.refreshProfile() }
            updateState { it.copy(isLoading = false, errorResId = null, errorMessage = null) }
            onLoggedIn()
        } else {
            applyBackendError(result.exceptionOrNull())
        }
    }

    private fun applyBackendError(throwable: Throwable?) {
        val errorCode = parseApiErrorCode(throwable)
        val errorResId = mapBackendError(errorCode)
        updateState {
            it.copy(
                isLoading = false,
                errorResId = errorResId,
                errorMessage = if (errorResId == null) errorCode ?: throwable?.message else null
            )
        }
    }

    private fun parseApiErrorCode(throwable: Throwable?): String? {
        val httpException = throwable as? HttpException ?: return null
        return runCatching {
            val errorBody = httpException.response()?.errorBody()?.string().orEmpty()
            if (errorBody.isBlank()) return@runCatching null
            JSONObject(errorBody).optString("detail").takeIf { it.isNotBlank() }
        }.getOrNull()
    }

    private fun mapBackendError(code: String?): Int? = when (code) {
        "invalid_phone" -> com.gapkassa.R.string.error_phone
        "invalid_code", "code_not_found" -> com.gapkassa.R.string.error_verification_code
        "code_invalid" -> com.gapkassa.R.string.error_verification_code_invalid
        "code_expired" -> com.gapkassa.R.string.error_verification_code_expired
        "code_attempts_exceeded" -> com.gapkassa.R.string.error_verification_code_attempts
        "otp_cooldown" -> com.gapkassa.R.string.error_otp_cooldown
        "otp_daily_limit" -> com.gapkassa.R.string.error_otp_daily_limit
        "telegram_not_found" -> com.gapkassa.R.string.error_telegram_not_found
        "telegram_gateway_not_configured", "telegram_gateway_unavailable" -> com.gapkassa.R.string.error_telegram_gateway_unavailable
        "login_locked" -> com.gapkassa.R.string.error_login_locked
        "user_inactive" -> com.gapkassa.R.string.error_user_inactive
        else -> null
    }

    private companion object {
        const val KEY_ERROR_RES_ID = "phone_auth_error_res_id"
        const val KEY_ERROR_MESSAGE = "phone_auth_error_message"
    }
}
