package com.gapkassa.data.repository

import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.preferences.ProfileCacheStore
import com.gapkassa.data.remote.BackendApi
import com.gapkassa.data.remote.ProfileUpdateRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Profile source of truth backed by API.
 */
class ProfileRepository(
    private val api: BackendApi,
    private val profileCacheStore: ProfileCacheStore
) {
    private val emptyProfile = UserProfile("", "", "", "", "", "")
    private val _profile = MutableStateFlow(profileCacheStore.read())
    val profileFlow: StateFlow<UserProfile> = _profile

    fun cacheProfile(profile: UserProfile) {
        profileCacheStore.write(profile)
        _profile.value = profile
    }

    fun clearCachedProfile() {
        profileCacheStore.clear()
        _profile.value = emptyProfile
    }

    suspend fun refreshProfile(): UserProfile {
        val user = api.me()
        val profile = user.toProfile()
        cacheProfile(profile)
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
        cacheProfile(updated)
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
