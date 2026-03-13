package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import com.gapkassa.utils.Validators
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * UI state for login/registration flows.
 */
data class AuthUiState(
    val name: String = "",
    val lastName: String = "",
    val patronymic: String = "",
    val email: String = "",
    val phone: String = "",
    val password: String = "",
    val confirmPassword: String = "",
    val isLoading: Boolean = false,
    val errorResId: Int? = null,
    val errorMessage: String? = null
)

/**
 * Handles auth flows and keeps validation errors localized via string resources.
 */
class AuthViewModel(
    private val authRepository: AuthRepository,
    private val actionLogRepository: ActionLogRepository,
    private val profileRepository: ProfileRepository
) : ViewModel() {

    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state

    fun updateEmail(value: String) {
        _state.update { it.copy(email = value) }
    }

    fun updateName(value: String) {
        _state.update { it.copy(name = value) }
    }

    fun updateLastName(value: String) {
        _state.update { it.copy(lastName = value) }
    }

    fun updatePatronymic(value: String) {
        _state.update { it.copy(patronymic = value) }
    }

    fun updatePhone(value: String) {
        _state.update { it.copy(phone = value) }
    }

    fun updatePassword(value: String) {
        _state.update { it.copy(password = value) }
    }

    fun updateConfirmPassword(value: String) {
        _state.update { it.copy(confirmPassword = value) }
    }

    fun login(onSuccess: () -> Unit) {
        val email = state.value.email
        val password = state.value.password
        if (!Validators.isEmailValid(email) || !Validators.isPasswordValid(password)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_email_password, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            val result = authRepository.login(email, password)
            if (result.isSuccess) {
                val existing = profileRepository.getProfile()
                val displayName = state.value.name.ifBlank {
                    existing.name.ifBlank { email.substringBefore("@").ifBlank { "Пользователь" } }
                }
                profileRepository.saveProfile(
                    UserProfile(
                        name = displayName,
                        lastName = state.value.lastName.ifBlank { existing.lastName },
                        patronymic = state.value.patronymic.ifBlank { existing.patronymic },
                        email = email,
                        phone = state.value.phone.ifBlank { existing.phone },
                        photoUrl = existing.photoUrl
                    )
                )
                authRepository.currentUserId?.let { userId ->
                    actionLogRepository.log(userId, null, "login")
                }
                onSuccess()
            } else {
                _state.update { it.copy(errorResId = com.gapkassa.R.string.error_login_failed, errorMessage = null) }
            }
            _state.update { it.copy(isLoading = false) }
        }
    }

    fun register(onSuccess: () -> Unit) {
        val name = state.value.name
        val lastName = state.value.lastName
        val patronymic = state.value.patronymic
        val email = state.value.email
        val phone = state.value.phone
        val password = state.value.password
        val confirm = state.value.confirmPassword
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
        if (password != confirm) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_password_match, errorMessage = null) }
            return
        }
        if (phone.isNotBlank() && !Validators.isPhoneValid(phone)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_phone, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            val result = authRepository.register(email, password)
            if (result.isSuccess) {
                profileRepository.saveProfile(
                    UserProfile(
                        name = name,
                        lastName = lastName,
                        patronymic = patronymic,
                        email = email,
                        phone = phone,
                        photoUrl = ""
                    )
                )
                authRepository.currentUserId?.let { userId ->
                    actionLogRepository.log(userId, null, "register")
                }
                onSuccess()
            } else {
                _state.update { it.copy(errorMessage = result.exceptionOrNull()?.message, errorResId = null) }
            }
            _state.update { it.copy(isLoading = false) }
        }
    }

    fun resetPassword() {
        val email = state.value.email
        if (!Validators.isEmailValid(email)) {
            _state.update { it.copy(errorResId = com.gapkassa.R.string.error_email, errorMessage = null) }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, errorResId = null, errorMessage = null) }
            val result = authRepository.resetPassword(email)
            if (result.isFailure) {
                _state.update { it.copy(errorMessage = result.exceptionOrNull()?.message, errorResId = null) }
            }
            _state.update { it.copy(isLoading = false) }
        }
    }
}
