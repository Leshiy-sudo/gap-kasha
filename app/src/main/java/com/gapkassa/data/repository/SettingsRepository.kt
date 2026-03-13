package com.gapkassa.data.repository

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.gapkassa.data.preferences.dataStore
import com.gapkassa.utils.LocaleUtils
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking

/** Theme mode persisted in DataStore and applied to Compose. */
enum class ThemeMode {
    LIGHT,
    DARK
}

/**
 * Persists UI preferences (theme, language) and applies locale changes.
 */
class SettingsRepository(private val context: Context) {
    companion object {
        private val languageKey = stringPreferencesKey("language")

        fun readLanguageBlocking(context: Context): String = runBlocking {
            context.dataStore.data.first()[languageKey] ?: "ru"
        }
    }

    private val themeKey = stringPreferencesKey("theme_mode")

    val themeModeFlow: Flow<ThemeMode> = context.dataStore.data
        .map { prefs ->
            when (prefs[themeKey]) {
                "dark" -> ThemeMode.DARK
                else -> ThemeMode.LIGHT
            }
        }

    val languageFlow: Flow<String> = context.dataStore.data
        .map { prefs -> prefs[languageKey] ?: "ru" }

    suspend fun setThemeMode(mode: ThemeMode) {
        context.dataStore.edit { prefs ->
            prefs[themeKey] = if (mode == ThemeMode.DARK) "dark" else "light"
        }
    }

    suspend fun setLanguage(language: String) {
        context.dataStore.edit { prefs ->
            prefs[languageKey] = language
        }
        LocaleUtils.applyAppLocale(context, language)
    }

    suspend fun applyStoredLanguage() {
        val language = languageFlow.first()
        LocaleUtils.applyAppLocale(context, language)
    }
}
