package com.gapkassa

import android.app.Application
import com.gapkassa.BuildConfig
import com.gapkassa.data.db.AppDatabase
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ProfileRepository
import com.gapkassa.data.repository.RoomRepository
import com.gapkassa.data.repository.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Application root that wires Room database and repositories.
 * Also applies persisted settings (language) and seeds demo data in debug builds.
 */
class GapKassaApp : Application() {
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    lateinit var database: AppDatabase
        private set
    lateinit var authRepository: AuthRepository
        private set
    lateinit var roomRepository: RoomRepository
        private set
    lateinit var actionLogRepository: ActionLogRepository
        private set
    lateinit var settingsRepository: SettingsRepository
        private set
    lateinit var profileRepository: ProfileRepository
        private set

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getInstance(this)
        authRepository = AuthRepository(applicationContext)
        roomRepository = RoomRepository(database)
        actionLogRepository = ActionLogRepository(database)
        settingsRepository = SettingsRepository(applicationContext)
        profileRepository = ProfileRepository(applicationContext)
        if (BuildConfig.DEBUG) {
            appScope.launch {
                roomRepository.seedDemoIfEmpty()
            }
        }
        appScope.launch {
            settingsRepository.applyStoredLanguage()
        }
    }
}
