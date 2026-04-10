package com.gapkassa.data.repository

import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.remote.BackendApi
import com.gapkassa.data.remote.ProfileUpdateRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Profile source of truth backed by API.
 */
class ProfileRepository(
    private val api: BackendApi
) {
    private val _profile = MutableStateFlow(UserProfile("", "", "", "", "", ""))
    val profileFlow: StateFlow<UserProfile> = _profile

    suspend fun refreshProfile(): UserProfile {
        val user = api.me()
        val profile = user.toProfile()
        _profile.value = profile
        return profile
    }

    suspend fun saveProfile(profile: UserProfile): UserProfile {
        val user = api.updateMe(
            ProfileUpdateRequest(
                name = profile.name,
                lastName = profile.lastName,
                patronymic = profile.patronymic,
                phone = profile.phone,
                photoUrl = profile.photoUrl
            )
        )
        val updated = user.toProfile()
        _profile.value = updated
        return updated
    }

    private fun com.gapkassa.data.remote.UserDto.toProfile(): UserProfile = UserProfile(
        name = name.orEmpty(),
        lastName = lastName.orEmpty(),
        patronymic = patronymic.orEmpty(),
        email = email,
        phone = phone.orEmpty(),
        photoUrl = photoUrl.orEmpty()
    )
}
