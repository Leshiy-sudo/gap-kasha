package com.gapkassa.viewmodel

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.BuildConfig
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONObject
import retrofit2.HttpException

data class AuthUiState(
    val isLoading: Boolean = false,
    val errorResId: Int? = null,
    val errorMessage: String? = null,
    val isGoogleConfigured: Boolean = BuildConfig.GOOGLE_WEB_CLIENT_ID.isNotBlank(),
    val isMockGoogleAvailable: Boolean = BuildConfig.DEBUG && BuildConfig.GOOGLE_AUTH_ALLOW_MOCK
)

/**
 * Handles Google authentication and backend session exchange.
 */
class AuthViewModel(
    private val authRepository: AuthRepository,
    private val profileRepository: ProfileRepository,
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

    fun onGoogleProviderError(code: String) {
        if (code == "google_auth_cancelled") return
        val errorResId = mapProviderError(code)
        updateState {
            it.copy(
                isLoading = false,
                errorResId = errorResId,
                errorMessage = if (errorResId == null) code else null
            )
        }
    }

    fun loginWithGoogle(
        idToken: String,
        nonce: String?,
        onLoggedIn: () -> Unit
    ) {
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            val result = authRepository.loginWithGoogle(idToken, nonce)
            if (result.isSuccess) {
                result.getOrNull()?.let { user ->
                    profileRepository.cacheProfile(
                        UserProfile(
                            name = user.name.orEmpty(),
                            lastName = user.lastName.orEmpty(),
                            patronymic = user.patronymic.orEmpty(),
                            email = user.email,
                            phone = user.phone.orEmpty(),
                            photoUrl = user.photoUrl.orEmpty()
                        )
                    )
                }
                runCatching { profileRepository.refreshProfile() }
                updateState { it.copy(isLoading = false, errorResId = null, errorMessage = null) }
                onLoggedIn()
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorResId = mapBackendError(errorCode)
                updateState {
                    it.copy(
                        isLoading = false,
                        errorResId = errorResId,
                        errorMessage = if (errorResId == null) errorCode ?: result.exceptionOrNull()?.message else null
                    )
                }
            }
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

    private fun mapProviderError(code: String): Int? = when (code) {
        "google_auth_not_configured" -> com.gapkassa.R.string.error_google_auth_not_configured
        "google_auth_invalid_response" -> com.gapkassa.R.string.error_google_auth_failed
        "google_auth_mock_disabled" -> com.gapkassa.R.string.error_google_auth_failed
        "google_auth_failed" -> com.gapkassa.R.string.error_google_auth_failed
        else -> null
    }

    private fun mapBackendError(code: String?): Int? = when (code) {
        "google_auth_not_configured" -> com.gapkassa.R.string.error_google_auth_not_configured
        "google_auth_unavailable" -> com.gapkassa.R.string.error_google_auth_unavailable
        "google_token_invalid" -> com.gapkassa.R.string.error_google_auth_failed
        "google_nonce_invalid" -> com.gapkassa.R.string.error_google_auth_failed
        "google_email_not_verified" -> com.gapkassa.R.string.error_google_email_not_verified
        "google_email_conflict" -> com.gapkassa.R.string.error_google_auth_conflict
        "user_inactive" -> com.gapkassa.R.string.error_user_inactive
        else -> null
    }

    private companion object {
        const val KEY_ERROR_RES_ID = "google_auth_error_res_id"
        const val KEY_ERROR_MESSAGE = "google_auth_error_message"
    }
}
