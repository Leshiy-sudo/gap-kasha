package com.gapkassa

import android.app.Application
import com.gapkassa.BuildConfig
import com.gapkassa.auth.GoogleAuthManager
import com.gapkassa.data.db.AppDatabase
import com.gapkassa.data.preferences.AppConfigStore
import com.gapkassa.data.preferences.PendingCrashReportStore
import com.gapkassa.data.preferences.ProfileCacheStore
import com.gapkassa.data.preferences.TokenStore
import com.gapkassa.data.remote.ApiClient
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.ClientErrorRepository
import com.gapkassa.data.repository.FatalCrashHandler
import com.gapkassa.data.repository.NotificationRepository
import com.gapkassa.data.repository.ProfileRepository
import com.gapkassa.data.repository.RemoteConfigRepository
import com.gapkassa.data.repository.RoomRepository
import com.gapkassa.data.repository.SettingsRepository
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
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
    lateinit var tokenStore: TokenStore
        private set
    lateinit var apiClient: ApiClient
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
    lateinit var remoteConfigRepository: RemoteConfigRepository
        private set
    lateinit var notificationRepository: NotificationRepository
        private set
    lateinit var clientErrorRepository: ClientErrorRepository
        private set
    var isFirebaseMessagingAvailable: Boolean = false
        private set

    override fun onCreate() {
        super.onCreate()
        isFirebaseMessagingAvailable = runCatching {
            FirebaseApp.initializeApp(this) != null || FirebaseApp.getApps(this).isNotEmpty()
        }.getOrDefault(false)
        database = AppDatabase.getInstance(this)
        tokenStore = TokenStore(applicationContext)
        apiClient = ApiClient(tokenStore)
        authRepository = AuthRepository(apiClient.backendApi, tokenStore)
        notificationRepository = NotificationRepository(apiClient.backendApi)
        clientErrorRepository = ClientErrorRepository(
            apiClient.backendApi,
            PendingCrashReportStore(applicationContext)
        )
        roomRepository = RoomRepository(database, apiClient.backendApi)
        actionLogRepository = ActionLogRepository(database)
        settingsRepository = SettingsRepository(applicationContext)
        profileRepository = ProfileRepository(
            apiClient.backendApi,
            ProfileCacheStore(applicationContext)
        )
        installFatalCrashHandler()
        remoteConfigRepository = RemoteConfigRepository(
            apiClient.backendApi,
            AppConfigStore(applicationContext)
        )
        if (BuildConfig.DEBUG) {
            appScope.launch {
                roomRepository.seedDemoIfEmpty()
            }
        }
        appScope.launch {
            settingsRepository.applyStoredLanguage()
            remoteConfigRepository.refresh(SettingsRepository.readLanguageBlocking(applicationContext))
        }
        appScope.launch {
            runCatching { clientErrorRepository.flushPendingFatalReport() }
        }
    }

    fun onAuthenticated() {
        appScope.launch {
            runCatching { clientErrorRepository.flushPendingFatalReport() }
        }
        if (!isFirebaseMessagingAvailable || !authRepository.hasStoredSession) return
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            appScope.launch {
                runCatching { notificationRepository.registerFcmToken(token) }
            }
        }
    }

    fun onSignedOut() {
        appScope.launch {
            GoogleAuthManager(applicationContext).clearCredentialState()
        }
    }

    private fun installFatalCrashHandler() {
        val previousHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler(
            FatalCrashHandler(
                context = applicationContext,
                tokenStore = tokenStore,
                crashReportStore = PendingCrashReportStore(applicationContext),
                previousHandler = previousHandler
            )
        )
    }
}
