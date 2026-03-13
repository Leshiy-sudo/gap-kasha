package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * Handles profile persistence and logout side effects.
 */
class ProfileViewModel(
    private val authRepository: AuthRepository,
    private val actionLogRepository: ActionLogRepository,
    private val profileRepository: ProfileRepository
) : ViewModel() {
    val profile: StateFlow<UserProfile> = profileRepository.profileFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), UserProfile("", "", "", "", "", ""))

    fun logout(onDone: () -> Unit) {
        viewModelScope.launch {
            authRepository.currentUserId?.let { userId ->
                actionLogRepository.log(userId, null, "logout")
            }
            authRepository.logout()
            onDone()
        }
    }

    fun saveProfile(profile: UserProfile, onDone: () -> Unit) {
        viewModelScope.launch {
            profileRepository.saveProfile(profile)
            onDone()
        }
    }
}
