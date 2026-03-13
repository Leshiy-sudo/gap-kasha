package com.gapkassa.data.preferences

import android.content.Context
import androidx.datastore.preferences.preferencesDataStore

// Shared DataStore instance for lightweight app preferences (theme, language, profile).
val Context.dataStore by preferencesDataStore(name = "gap_kassa_prefs")
