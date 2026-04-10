package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import com.gapkassa.utils.Validators
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
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
    private val profileRepository: ProfileRepository
) : ViewModel() {

    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state
    private var pendingProfile: UserProfile? = null

    fun updateEmail(value: String) {
        _state.update { it.copy(email = value, errorResId = null, errorMessage = null) }
    }

    fun updateName(value: String) {
        _state.update { it.copy(name = value, errorResId = null, errorMessage = null) }
    }

    fun updateLastName(value: String) {
        _state.update { it.copy(lastName = value, errorResId = null, errorMessage = null) }
    }

    fun updatePatronymic(value: String) {
        _state.update { it.copy(patronymic = value, errorResId = null, errorMessage = null) }
    }

    fun updatePhone(value: String) {
        _state.update { it.copy(phone = value, errorResId = null, errorMessage = null) }
    }

    fun updatePassword(value: String) {
        _state.update { it.copy(password = value, errorResId = null, errorMessage = null) }
    }

    fun updateConfirmPassword(value: String) {
        _state.update { it.copy(confirmPassword = value, errorResId = null, errorMessage = null) }
    }

    fun updateVerificationCode(value: String) {
        _state.update { it.copy(verificationCode = value, errorResId = null, errorMessage = null) }
    }

    fun login(onLoggedIn: () -> Unit) {
        val email = state.value.email
        val password = state.value.password
        if (!Validators.isEmailValid(email)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_email, errorMessage = null) }
            return
        }
        if (!Validators.isPasswordValid(password)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_password, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorResId = null, errorMessage = null, infoResId = null) }
            val result = authRepository.login(email, password)
            if (result.isSuccess) {
                runCatching { profileRepository.refreshProfile() }
                _state.update { it.copy(password = "", confirmPassword = "") }
                onLoggedIn()
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorRes = mapLoginError(errorCode) ?: com.gapkassa.R.string.error_email_password
                _state.update { it.copy(errorResId = errorRes, errorMessage = null) }
            }
            _state.update { it.copy(isLoading = false) }
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
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_name, errorMessage = null) }
            return
        }
        if (!Validators.isEmailValid(email)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_email, errorMessage = null) }
            return
        }
        if (!Validators.isPasswordValid(password)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_password, errorMessage = null) }
            return
        }
        if (password != confirmPassword) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_password_match, errorMessage = null) }
            return
        }
        if (phone.isNotBlank() && !Validators.isPhoneValid(phone)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_phone, errorMessage = null) }
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
            _state.update { it.copy(isLoading = true, errorResId = null, errorMessage = null, infoResId = null) }
            val result = authRepository.requestRegisterOtp(
                email = email,
                password = password,
                name = name,
                lastName = lastName.ifBlank { null },
                patronymic = patronymic.ifBlank { null },
                phone = phone.ifBlank { null }
            )
            if (result.isSuccess) {
                _state.update { it.copy(infoResId = com.gapkassa.R.string.message_verification_sent) }
                onVerificationRequired(email)
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorRes = mapRegisterOtpError(errorCode)
                _state.update { it.copy(errorResId = errorRes, errorMessage = null) }
            }
            _state.update { it.copy(isLoading = false) }
        }
    }

    fun verifyOtp(onVerified: () -> Unit) {
        val email = state.value.email
        val code = state.value.verificationCode.trim()
        if (code.isBlank()) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_verification_code, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            val result = authRepository.verifyRegisterOtp(email, code)
            if (result.isSuccess) {
                if (pendingProfile != null) {
                    profileRepository.saveProfile(pendingProfile!!)
                } else {
                    runCatching { profileRepository.refreshProfile() }
                }
                pendingProfile = null
                _state.update { it.copy(verificationCode = "", password = "", confirmPassword = "") }
                onVerified()
            } else {
                val errorCode = parseApiErrorCode(result.exceptionOrNull())
                val errorRes = mapVerifyOtpError(errorCode) ?: com.gapkassa.R.string.error_verification_code
                _state.update { it.copy(errorResId = errorRes, errorMessage = null) }
            }
            _state.update { it.copy(isLoading = false) }
        }
    }

    fun resendOtp() {
        requestOtpForRegister {}
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
        else -> null
    }

    private fun mapVerifyOtpError(code: String?): Int? = when (code) {
        "code_invalid" -> com.gapkassa.R.string.error_verification_code_invalid
        "code_expired" -> com.gapkassa.R.string.error_verification_code_expired
        "code_attempts_exceeded" -> com.gapkassa.R.string.error_verification_code_attempts
        "code_not_found" -> com.gapkassa.R.string.error_verification_code
        else -> null
    }
}
