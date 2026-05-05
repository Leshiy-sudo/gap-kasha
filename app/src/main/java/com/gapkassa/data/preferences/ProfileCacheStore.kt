package com.gapkassa.data.preferences

import android.content.Context
import com.gapkassa.data.model.UserProfile

class ProfileCacheStore(context: Context) {
    private val prefs = context.getSharedPreferences("gap_kassa_profile", Context.MODE_PRIVATE)

    fun read(): UserProfile = UserProfile(
        name = prefs.getString(KEY_NAME, "").orEmpty(),
        lastName = prefs.getString(KEY_LAST_NAME, "").orEmpty(),
        patronymic = prefs.getString(KEY_PATRONYMIC, "").orEmpty(),
        email = prefs.getString(KEY_EMAIL, "").orEmpty(),
        phone = prefs.getString(KEY_PHONE, "").orEmpty(),
        photoUrl = prefs.getString(KEY_PHOTO_URL, "").orEmpty()
    )

    fun write(profile: UserProfile) {
        prefs.edit()
            .putString(KEY_NAME, profile.name)
            .putString(KEY_LAST_NAME, profile.lastName)
            .putString(KEY_PATRONYMIC, profile.patronymic)
            .putString(KEY_EMAIL, profile.email)
            .putString(KEY_PHONE, profile.phone)
            .putString(KEY_PHOTO_URL, profile.photoUrl)
            .apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    private companion object {
        const val KEY_NAME = "profile_name"
        const val KEY_LAST_NAME = "profile_last_name"
        const val KEY_PATRONYMIC = "profile_patronymic"
        const val KEY_EMAIL = "profile_email"
        const val KEY_PHONE = "profile_phone"
        const val KEY_PHOTO_URL = "profile_photo_url"
    }
}
