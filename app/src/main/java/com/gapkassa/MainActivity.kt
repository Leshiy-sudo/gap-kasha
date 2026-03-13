package com.gapkassa

import android.content.Context
import android.os.Bundle
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
import com.gapkassa.data.repository.SettingsRepository
import com.gapkassa.ui.AppNavGraph
import com.gapkassa.ui.LocalAppContainer
import com.gapkassa.ui.theme.GapKassaTheme
import com.gapkassa.utils.LocaleUtils

/**
 * Main Compose host that applies theme and provides the app container to the navigation graph.
 */
class MainActivity : AppCompatActivity() {
    override fun attachBaseContext(newBase: Context) {
        val language = SettingsRepository.readLanguageBlocking(newBase)
        val wrapped = LocaleUtils.wrapContext(newBase, language)
        super.attachBaseContext(wrapped)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as GapKassaApp
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
}
