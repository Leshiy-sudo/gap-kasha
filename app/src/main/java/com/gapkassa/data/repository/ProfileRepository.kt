package com.gapkassa.data.repository

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.gapkassa.data.model.UserProfile
import com.gapkassa.data.preferences.dataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

/**
 * Stores the current user's profile fields in DataStore.
 */
class ProfileRepository(private val context: Context) {
    private val nameKey = stringPreferencesKey("profile_name")
    private val lastNameKey = stringPreferencesKey("profile_last_name")
    private val patronymicKey = stringPreferencesKey("profile_patronymic")
    private val emailKey = stringPreferencesKey("profile_email")
    private val phoneKey = stringPreferencesKey("profile_phone")
    private val photoKey = stringPreferencesKey("profile_photo")

    val profileFlow: Flow<UserProfile> = context.dataStore.data
        .map { prefs ->
            UserProfile(
                name = prefs[nameKey] ?: "",
                lastName = prefs[lastNameKey] ?: "",
                patronymic = prefs[patronymicKey] ?: "",
                email = prefs[emailKey] ?: "",
                phone = prefs[phoneKey] ?: "",
                photoUrl = prefs[photoKey] ?: ""
            )
        }

    suspend fun saveProfile(profile: UserProfile) {
        context.dataStore.edit { prefs ->
            prefs[nameKey] = profile.name
            prefs[lastNameKey] = profile.lastName
            prefs[patronymicKey] = profile.patronymic
            prefs[emailKey] = profile.email
            prefs[phoneKey] = profile.phone
            prefs[photoKey] = profile.photoUrl
        }
    }

    suspend fun getProfile(): UserProfile = profileFlow.first()
}
