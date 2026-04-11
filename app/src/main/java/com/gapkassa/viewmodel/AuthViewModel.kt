package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import com.gapkassa.utils.Validators
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import retrofit2.HttpException
import org.json.JSONObject

/**
 * UI state for email + password auth with registration OTP.
 */
data class AuthUiState(
    val name: String = "",
    val lastName: String = "",
    val patronymic: String = "",
    val email: String = "",
    val phone: String = "",
    val password: String = "",
    val confirmPassword: String = "",
    val verificationCode: String = "",
    val otpCooldownRemaining: Int = 0,
    val isLoading: Boolean = false,
    val errorResId: Int? = null,
    val errorMessage: String? = null,
    val infoResId: Int? = null
)

/**
 * Handles registration OTP and password login.
 */
class AuthViewModel(
    private val authRepository: AuthRepository,
    private val profileRepository: ProfileRepository,
    private val savedStateHandle: SavedStateHandle
) : ViewModel() {

    private val _state = MutableStateFlow(loadInitialState())
    val state: StateFlow<AuthUiState> = _state
    private var pendingProfile: UserProfile? = null
    private var otpCooldownJob: Job? = null

    init {
        val remaining = _state.value.otpCooldownRemaining
        if (remaining > 0) {
            startOtpCooldown(remaining)
        }
    }

    private fun loadInitialState(): AuthUiState {
        return AuthUiState(
            name = savedStateHandle[KEY_NAME] ?: "",
            lastName = savedStateHandle[KEY_LAST_NAME] ?: "",
            patronymic = savedStateHandle[KEY_PATRONYMIC] ?: "",
            email = savedStateHandle[KEY_EMAIL] ?: "",
            phone = savedStateHandle[KEY_PHONE] ?: "",
            password = savedStateHandle[KEY_PASSWORD] ?: "",
            confirmPassword = savedStateHandle[KEY_CONFIRM_PASSWORD] ?: "",
            verificationCode = savedStateHandle[KEY_VERIFICATION_CODE] ?: "",
            otpCooldownRemaining = savedStateHandle[KEY_OTP_COOLDOWN] ?: 0
        )
    }

    private fun persistFields(state: AuthUiState) {
        savedStateHandle[KEY_NAME] = state.name
        savedStateHandle[KEY_LAST_NAME] = state.lastName
        savedStateHandle[KEY_PATRONYMIC] = state.patronymic
        savedStateHandle[KEY_EMAIL] = state.email
        savedStateHandle[KEY_PHONE] = state.phone
        savedStateHandle[KEY_PASSWORD] = state.password
        savedStateHandle[KEY_CONFIRM_PASSWORD] = state.confirmPassword
        savedStateHandle[KEY_VERIFICATION_CODE] = state.verificationCode
        savedStateHandle[KEY_OTP_COOLDOWN] = state.otpCooldownRemaining
    }

    private fun updateState(transform: (AuthUiState) -> AuthUiState) {
        _state.update { current ->
            val updated = transform(current)
            persistFields(updated)
            updated
        }
    }

    fun updateEmail(value: String) {
        updateState { it.copy(email = value, errorResId = null, errorMessage = null) }
    }

    fun updateName(value: String) {
        updateState { it.copy(name = value, errorResId = null, errorMessage = null) }
    }

    fun updateLastName(value: String) {
        updateState { it.copy(lastName = value, errorResId = null, errorMessage = null) }
    }

    fun updatePatronymic(value: String) {
        updateState { it.copy(patronymic = value, errorResId = null, errorMessage = null) }
    }

    fun updatePhone(value: String) {
        updateState { it.copy(phone = value, errorResId = null, errorMessage = null) }
    }

    fun updatePassword(value: String) {
        updateState { it.copy(password = value, errorResId = null, errorMessage = null) }
    }

    fun updateConfirmPassword(value: String) {
        updateState { it.copy(confirmPassword = value, errorResId = null, errorMessage = null) }
    }

    fun updateVerificationCode(value: String) {
        updateState { it.copy(verificationCode = value, errorResId = null, errorMessage = null) }
    }

    fun login(onLoggedIn: () -> Unit) {
        val email = state.value.email
        val password = state.value.password
        if (!Validators.isEmailValid(email)) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_email, errorMessage = null) }
            return
        }
        if (!Validators.isPasswordValid(password)) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_password, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null, infoResId = null) }
            val result = authRepository.login(email, password)
            if (result.isSuccess) {
                runCatching { profileRepository.refreshProfile() }
                updateState { it.copy(password = "", confirmPassword = "") }
                onLoggedIn()
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorRes = mapLoginError(errorCode) ?: com.gapkassa.R.string.error_email_password
                updateState { it.copy(errorResId = errorRes, errorMessage = null) }
            }
            updateState { it.copy(isLoading = false) }
        }
    }

    fun requestOtpForRegister(onVerificationRequired: (String) -> Unit) {
        val name = state.value.name
        val lastName = state.value.lastName
        val patronymic = state.value.patronymic
        val email = state.value.email
        val phone = state.value.phone
        val password = state.value.password
        val confirmPassword = state.value.confirmPassword
        if (!Validators.isNameValid(name)) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_name, errorMessage = null) }
            return
        }
        if (!Validators.isEmailValid(email)) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_email, errorMessage = null) }
            return
        }
        if (!Validators.isPasswordValid(password)) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_password, errorMessage = null) }
            return
        }
        if (password != confirmPassword) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_password_match, errorMessage = null) }
            return
        }
        if (phone.isNotBlank() && !Validators.isPhoneValid(phone)) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_phone, errorMessage = null) }
            return
        }
        pendingProfile = UserProfile(
            name = name,
            lastName = lastName,
            patronymic = patronymic,
            email = email,
            phone = phone,
            photoUrl = ""
        )
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null, infoResId = null) }
            val result = authRepository.requestRegisterOtp(
                email = email,
                password = password,
                name = name,
                lastName = lastName.ifBlank { null },
                patronymic = patronymic.ifBlank { null },
                phone = phone.ifBlank { null }
            )
            if (result.isSuccess) {
                updateState { it.copy(infoResId = com.gapkassa.R.string.message_verification_sent) }
                startOtpCooldown(OTP_COOLDOWN_SECONDS)
                onVerificationRequired(email)
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorRes = mapRegisterOtpError(errorCode)
                updateState { it.copy(errorResId = errorRes, errorMessage = null) }
                if (errorCode == "otp_cooldown") {
                    startOtpCooldown(OTP_COOLDOWN_SECONDS)
                }
            }
            updateState { it.copy(isLoading = false) }
        }
    }

    fun verifyOtp(onVerified: () -> Unit) {
        val email = state.value.email
        val code = state.value.verificationCode.trim()
        if (code.isBlank()) {
            updateState { it.copy(errorResId = com.gapkassa.R.string.error_verification_code, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            updateState { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            val result = authRepository.verifyRegisterOtp(email, code)
            if (result.isSuccess) {
                val profile = pendingProfile ?: UserProfile(
                    name = state.value.name,
                    lastName = state.value.lastName,
                    patronymic = state.value.patronymic,
                    email = state.value.email,
                    phone = state.value.phone,
                    photoUrl = ""
                )
                runCatching { profileRepository.saveProfile(profile) }
                pendingProfile = null
                updateState { it.copy(verificationCode = "", password = "", confirmPassword = "") }
                onVerified()
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorRes = mapVerifyOtpError(errorCode) ?: com.gapkassa.R.string.error_verification_code
                updateState { it.copy(errorResId = errorRes, errorMessage = null) }
            }
            updateState { it.copy(isLoading = false) }
        }
    }

    fun resendOtp() {
        if (state.value.otpCooldownRemaining > 0) return
        requestOtpForRegister {}
    }

    private fun startOtpCooldown(seconds: Int) {
        otpCooldownJob?.cancel()
        updateState { it.copy(otpCooldownRemaining = seconds) }
        otpCooldownJob = viewModelScope.launch {
            var remaining = seconds
            while (remaining > 0) {
                delay(1000)
                remaining -= 1
                updateState { it.copy(otpCooldownRemaining = remaining) }
            }
        }
    }

    private fun parseApiErrorCode(throwable: Throwable?): String? {
        val http = throwable as? HttpException ?: return null
        val body = http.response()?.errorBody()?.string() ?: return null
        return runCatching { JSONObject(body).optString("detail") }
            .getOrNull()
            ?.takeIf { it.isNotBlank() }
    }

    private fun mapLoginError(code: String?): Int? = when (code) {
        "email_not_verified" -> com.gapkassa.R.string.error_email_not_verified
        "login_locked" -> com.gapkassa.R.string.error_login_locked
        "user_inactive" -> com.gapkassa.R.string.error_user_inactive
        "invalid_credentials" -> com.gapkassa.R.string.error_email_password
        else -> null
    }

    private fun mapRegisterOtpError(code: String?): Int? = when (code) {
        "email_exists" -> com.gapkassa.R.string.error_email_exists
        "otp_cooldown" -> com.gapkassa.R.string.error_otp_cooldown
        "password_invalid" -> com.gapkassa.R.string.error_password
        "invalid_email" -> com.gapkassa.R.string.error_email
        "email_send_failed" -> com.gapkassa.R.string.error_email_send_failed
        else -> null
    }

    private fun mapVerifyOtpError(code: String?): Int? = when (code) {
        "code_invalid" -> com.gapkassa.R.string.error_verification_code_invalid
        "code_expired" -> com.gapkassa.R.string.error_verification_code_expired
        "code_attempts_exceeded" -> com.gapkassa.R.string.error_verification_code_attempts
        "code_not_found" -> com.gapkassa.R.string.error_verification_code
        else -> null
    }

    companion object {
        private const val KEY_NAME = "auth_name"
        private const val KEY_LAST_NAME = "auth_last_name"
        private const val KEY_PATRONYMIC = "auth_patronymic"
        private const val KEY_EMAIL = "auth_email"
        private const val KEY_PHONE = "auth_phone"
        private const val KEY_PASSWORD = "auth_password"
        private const val KEY_CONFIRM_PASSWORD = "auth_confirm_password"
        private const val KEY_VERIFICATION_CODE = "auth_verification_code"
        private const val KEY_OTP_COOLDOWN = "auth_otp_cooldown"
        private const val OTP_COOLDOWN_SECONDS = 30
    }
}
