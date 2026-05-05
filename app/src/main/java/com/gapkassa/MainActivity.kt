package com.gapkassa

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.core.content.ContextCompat
import com.gapkassa.data.repository.SettingsRepository
import com.gapkassa.notifications.GapKassaNotifications
import com.gapkassa.ui.AppNavGraph
import com.gapkassa.ui.LocalAppContainer
import com.gapkassa.ui.theme.GapKassaTheme
import com.gapkassa.utils.LocaleUtils
import com.google.firebase.messaging.FirebaseMessaging
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

/**
 * Main Compose host that applies theme and provides the app container to the navigation graph.
 */
class MainActivity : AppCompatActivity() {
    private val requestNotificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun attachBaseContext(newBase: Context) {
        val language = SettingsRepository.readLanguageBlocking(newBase)
        val wrapped = LocaleUtils.wrapContext(newBase, language)
        super.attachBaseContext(wrapped)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as GapKassaApp
        if (app.isFirebaseMessagingAvailable) {
            GapKassaNotifications.ensureChannel(this)
            askNotificationPermissionIfNeeded()
            syncFcmTokenIfPossible(app)
        }
        setContent {
            val themeMode by app.settingsRepository.themeModeFlow.collectAsState(initial = com.gapkassa.data.repository.ThemeMode.LIGHT)
            GapKassaTheme(themeMode = themeMode) {
                val view = LocalView.current
                val isLight = themeMode == com.gapkassa.data.repository.ThemeMode.LIGHT
                val backgroundColor = MaterialTheme.colorScheme.background
                SideEffect {
                    val controller = WindowCompat.getInsetsController(window, view)
                    controller.isAppearanceLightStatusBars = isLight
                    controller.isAppearanceLightNavigationBars = isLight
                    window.statusBarColor = backgroundColor.toArgb()
                    window.navigationBarColor = backgroundColor.toArgb()
                }
                Surface(color = androidx.compose.material3.MaterialTheme.colorScheme.background) {
                    CompositionLocalProvider(
                        LocalAppContainer provides app
                    ) {
                        AppNavGraph()
                    }
                }
            }
        }
    }

    private fun askNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val permissionState = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.POST_NOTIFICATIONS
        )
        if (permissionState != PackageManager.PERMISSION_GRANTED) {
            requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private fun syncFcmTokenIfPossible(app: GapKassaApp) {
        if (!app.isFirebaseMessagingAvailable || !app.authRepository.hasStoredSession) return
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            lifecycleScope.launch {
                runCatching { app.notificationRepository.registerFcmToken(token) }
            }
        }
    }
}
